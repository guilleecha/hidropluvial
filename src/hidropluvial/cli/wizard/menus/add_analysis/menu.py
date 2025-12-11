"""
Menú para agregar análisis adicionales.

Permite seleccionar exactamente qué análisis agregar, similar al wizard inicial,
detectando y descartando duplicados de análisis ya existentes.
"""

from typing import Optional, Set, Tuple

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner

from .weighted import (
    get_c_popup_options,
    get_cn_popup_options,
    calculate_weighted_c,
    calculate_weighted_cn,
)
from .tc_calculator import TcCalculator, format_method_name
from .bimodal_inline import (
    get_bimodal_state,
    set_bimodal_state,
    build_bimodal_summary,
    build_bimodal_popup_options,
    get_bimodal_parameters,
)
from .options import (
    STORM_OPTIONS,
    RETURN_PERIOD_OPTIONS,
    X_FACTOR_OPTIONS,
    RUNOFF_METHOD_OPTIONS,
    DEFAULT_STORM,
    DEFAULT_RETURN_PERIOD,
    DEFAULT_X_FACTOR,
    DEFAULT_RUNOFF_METHOD,
)


def _get_analysis_key(analysis) -> Tuple:
    """
    Genera una clave única para identificar un análisis.

    Returns:
        Tupla con parámetros que identifican unívocamente un análisis.
        Para tormentas bimodales incluye los parámetros de configuración.
    """
    tc_method = analysis.hydrograph.tc_method.lower()
    storm_type = analysis.storm.type.lower()
    return_period = analysis.storm.return_period
    x_factor = analysis.hydrograph.x_factor or 1.0
    # Obtener método de escorrentía de los parámetros del Tc
    runoff_method = ""
    if analysis.tc.parameters:
        runoff_method = analysis.tc.parameters.get("runoff_method", "")

    # Para tormentas bimodales, incluir parámetros de configuración
    if storm_type == "bimodal":
        bimodal_key = (
            analysis.storm.bimodal_peak1,
            analysis.storm.bimodal_peak2,
            analysis.storm.bimodal_vol_split,
            analysis.storm.bimodal_peak_width,
        )
        return (tc_method, storm_type, return_period, x_factor, runoff_method, bimodal_key)

    return (tc_method, storm_type, return_period, x_factor, runoff_method)


class AddAnalysisMenu(SessionMenu):
    """Menú para agregar análisis adicionales a una cuenca."""

    def __init__(
        self,
        basin,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(basin)
        # C y CN son sugerencias de valores anteriores, no obligatorios
        self._suggested_c = c or basin.c
        self._suggested_cn = cn or basin.cn
        self.length = length or basin.length_m
        # Valores seleccionados para este análisis (se piden al usuario)
        self.c = None
        self.cn = None
        # Configuración bimodal (valores por defecto)
        self.bimodal_duration_hr = 6.0
        self.bimodal_peak1 = 0.25
        self.bimodal_peak2 = 0.75
        self.bimodal_vol_split = 0.5
        self.bimodal_peak_width = 0.15
        # Obtener claves de análisis existentes para detectar duplicados
        self._existing_keys: Set[Tuple[str, str, int, float]] = set()
        for a in basin.analyses:
            self._existing_keys.add(_get_analysis_key(a))

    def show(self) -> None:
        """Muestra el wizard para agregar análisis."""
        self._add_analyses_form()

    def _add_analyses_form(self) -> None:
        """Formulario unificado para agregar análisis."""
        from hidropluvial.cli.viewer.form_viewer import interactive_form, FormResult

        while True:
            # Construir campos del formulario
            fields = self._build_form_fields()

            # Mostrar formulario
            result = interactive_form(
                title=f"Agregar Análisis - {self.basin.name}",
                fields=fields,
                allow_back=True,
            )

            if result is None or result.get("_result") == FormResult.BACK:
                return

            # Si se pidió recargar (después de agregar un Tc), continuar el loop
            if result.get("_result") == FormResult.RELOAD:
                continue

            # Procesar resultado y terminar
            self._process_form_result(result)
            return

    def _get_runoff_defaults(self) -> list:
        """Determina defaults para método de escorrentía."""
        runoff_defaults = []
        if self._suggested_c:
            runoff_defaults.append("C")
        if self._suggested_cn:
            runoff_defaults.append("CN")
        return runoff_defaults if runoff_defaults else [DEFAULT_RUNOFF_METHOD]

    def _build_form_fields(self) -> list:
        """Construye los campos del formulario de análisis."""
        from hidropluvial.cli.viewer.form_viewer import FormField, FieldType, FormState

        # Opciones de métodos Tc (todos disponibles, se calculan por análisis)
        tc_options = [
            {"name": "Desbordes (urbano, usa C)", "value": "desbordes"},
            {"name": "Kirpich (rural)", "value": "kirpich"},
            {"name": "Temez (rural)", "value": "temez"},
            {"name": "NRCS (velocidades TR-55)", "value": "nrcs"},
        ]
        # Default: Desbordes si hay C, Kirpich si hay longitud, NRCS si hay segmentos
        from .nrcs_inline import get_nrcs_state
        tc_defaults = []
        if self._suggested_c:
            tc_defaults.append("desbordes")
        if self.length:
            tc_defaults.append("kirpich")
        # Agregar NRCS si hay segmentos configurados
        nrcs_state = get_nrcs_state()
        if nrcs_state.segments:
            tc_defaults.append("nrcs")
        if not tc_defaults:
            tc_defaults = ["desbordes"]  # Por defecto

        # Callbacks para popups de C y CN
        def on_edit_c(field: FormField, state: FormState) -> list:
            return get_c_popup_options(
                lambda table_key: calculate_weighted_c(self.basin, table_key)
            )

        def on_edit_cn(field: FormField, state: FormState) -> list:
            return get_cn_popup_options(
                lambda soil: calculate_weighted_cn(self.basin, soil, self)
            )

        # Callback para gestionar métodos Tc (siempre disponible)
        def on_edit_tc(field: FormField, state: FormState) -> list:
            return self._get_tc_popup_options()

        # Callback para configurar tormentas
        def on_edit_storms(field: FormField, state: FormState) -> list:
            return self._get_storm_popup_options()

        # Hints con valores anteriores si existen
        c_hint = self._get_previous_c_values() or "Enter para opciones: valor, ponderador, típicos"
        cn_hint = self._get_previous_cn_values() or "Enter para opciones: valor, ponderador, típicos"
        if self._get_previous_c_values():
            c_hint = f"Anteriores: {c_hint}"
        if self._get_previous_cn_values():
            cn_hint = f"Anteriores: {cn_hint}"

        # Hint para Tc methods
        tc_hint = "Enter para ver opciones y requisitos"

        return [
            FormField(
                key="runoff_methods",
                label="Método de Escorrentía",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=RUNOFF_METHOD_OPTIONS,
                default=self._get_runoff_defaults(),
                hint="Selecciona uno o ambos métodos",
            ),
            FormField(
                key="c",
                label="Coeficiente C",
                field_type=FieldType.FLOAT,
                required=True,
                default=self._suggested_c,
                min_value=0.1,
                max_value=0.95,
                hint=c_hint,
                depends_on="runoff_methods",
                depends_value="C",
                disabled_hint="Requiere método Racional (C)",
                on_edit=on_edit_c,
            ),
            FormField(
                key="cn",
                label="Número de Curva CN",
                field_type=FieldType.INT,
                required=True,
                default=self._suggested_cn,
                min_value=30,
                max_value=98,
                hint=cn_hint,
                depends_on="runoff_methods",
                depends_value="CN",
                disabled_hint="Requiere método NRCS (CN)",
                on_edit=on_edit_cn,
            ),
            FormField(
                key="tc_methods",
                label="Métodos de Tc",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=tc_options,
                default=tc_defaults,
                hint=tc_hint,
                on_edit=on_edit_tc,
            ),
            FormField(
                key="storms",
                label="Tipos de tormenta",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=STORM_OPTIONS,
                default=[DEFAULT_STORM],
                hint="Enter para configurar bimodal",
                on_edit=on_edit_storms,
            ),
            FormField(
                key="return_periods",
                label="Períodos de retorno",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=RETURN_PERIOD_OPTIONS,
                default=[DEFAULT_RETURN_PERIOD],
                hint="Frecuencia del evento de diseño",
            ),
            FormField(
                key="x_factors",
                label="Factor X (hidrograma)",
                field_type=FieldType.CHECKBOX,
                required=False,
                options=X_FACTOR_OPTIONS,
                default=[DEFAULT_X_FACTOR],
                hint="Forma del hidrograma unitario",
            ),
        ]

    def _process_form_result(self, result: dict) -> None:
        """Procesa el resultado del formulario y ejecuta análisis."""
        runoff_selected = result.get("runoff_methods") or []
        c_val = result.get("c") if "C" in runoff_selected else None
        cn_val = result.get("cn") if "CN" in runoff_selected else None
        tc_methods = result.get("tc_methods") or []
        storms = result.get("storms") or []
        return_periods = result.get("return_periods") or []
        x_factors = result.get("x_factors") or [DEFAULT_X_FACTOR]

        # Guardar valores
        if c_val is not None:
            self.c = c_val
        if cn_val is not None:
            self.cn = int(cn_val)

        # Determinar métodos de escorrentía
        runoff_methods = []
        if self.c and "C" in runoff_selected:
            runoff_methods.append("racional")
        if self.cn and "CN" in runoff_selected:
            runoff_methods.append("scs-cn")

        if not runoff_methods:
            self.error("Debes completar al menos C o CN")
            return

        # Ejecutar análisis
        self._execute_analyses(tc_methods, storms, return_periods, x_factors, runoff_methods)

    def _execute_analyses(
        self,
        tc_methods: list,
        storms: list,
        return_periods: list,
        x_factors: list,
        runoff_methods: list,
    ) -> None:
        """Ejecuta los análisis con los parámetros dados."""
        # Calcular cuántos análisis nuevos se agregarán (descartando duplicados)
        new_analyses = []
        duplicates = []

        for tc_method in tc_methods:
            for storm_code in storms:
                for tr in return_periods:
                    for x in x_factors:
                        for runoff in runoff_methods:
                            # Para bimodal, incluir parámetros en la clave
                            if storm_code == "bimodal":
                                bimodal_key = (
                                    self.bimodal_peak1,
                                    self.bimodal_peak2,
                                    self.bimodal_vol_split,
                                    self.bimodal_peak_width,
                                )
                                key = (tc_method.lower(), storm_code, tr, x, runoff, bimodal_key)
                            else:
                                key = (tc_method.lower(), storm_code, tr, x, runoff)

                            if key in self._existing_keys:
                                esc_label = "C" if runoff == "racional" else "CN"
                                duplicates.append(f"Tc={tc_method}, {storm_code}, Tr={tr}, X={x:.2f}, {esc_label}")
                            else:
                                new_analyses.append((tc_method, storm_code, tr, x, runoff))

        if duplicates:
            self.warning(f"Se descartarán {len(duplicates)} análisis duplicados:")
            for dup in duplicates[:5]:
                self.info(f"  - {dup}")
            if len(duplicates) > 5:
                self.info(f"  ... y {len(duplicates) - 5} más")

        if not new_analyses:
            self.warning("Todos los análisis seleccionados ya existen")
            return

        # Mostrar resumen
        esc_labels = []
        if "racional" in runoff_methods:
            esc_labels.append(f"Racional (C={self.c:.2f})")
        if "scs-cn" in runoff_methods:
            esc_labels.append(f"SCS-CN (CN={self.cn})")
        self.info(f"Métodos de escorrentía: {', '.join(esc_labels)}")

        # Confirmar
        self.note(f"Se agregarán {len(new_analyses)} análisis nuevos:")
        for tc, storm, tr, x, runoff in new_analyses[:5]:
            x_str = f", X={x:.2f}" if x != 1.0 else ""
            esc_label = "C" if runoff == "racional" else "CN"
            self.info(f"  + Tc={tc}, {storm}, Tr={tr}{x_str}, {esc_label}")
        if len(new_analyses) > 5:
            self.info(f"  ... y {len(new_analyses) - 5} más")

        if not self.confirm(f"\n¿Ejecutar {len(new_analyses)} análisis?", default=True):
            return

        # Ejecutar análisis
        runner = AdditionalAnalysisRunner(
            self.basin,
            self.c,
            self.cn,
            bimodal_duration_hr=self.bimodal_duration_hr,
            bimodal_peak1=self.bimodal_peak1,
            bimodal_peak2=self.bimodal_peak2,
            bimodal_vol_split=self.bimodal_vol_split,
            bimodal_peak_width=self.bimodal_peak_width,
        )
        total_count = 0

        for storm_code in storms:
            for runoff in runoff_methods:
                # Filtrar análisis para esta tormenta y método de escorrentía
                storm_analyses = [
                    (tc, tr, x) for tc, st, tr, x, r in new_analyses
                    if st == storm_code and r == runoff
                ]
                if not storm_analyses:
                    continue

                # Obtener Tc, Tr y X únicos
                unique_tcs = sorted(set(tc for tc, _, _ in storm_analyses))
                unique_trs = sorted(set(tr for _, tr, _ in storm_analyses))
                unique_xs = sorted(set(x for _, _, x in storm_analyses))

                count = runner.run(unique_tcs, storm_code, unique_trs, unique_xs, runoff_method=runoff)
                total_count += count

        self.success(f"Se agregaron {total_count} análisis")

    def _get_tc_popup_options(self) -> list:
        """
        Construye opciones de popup para seleccionar métodos Tc.

        El Tc se calcula por análisis (no por cuenca) porque algunos métodos
        dependen de parámetros del análisis (ej: Desbordes depende de C).

        Returns:
            Lista de opciones para el popup
        """
        from hidropluvial.cli.theme import get_icons
        from .nrcs_inline import get_nrcs_state, build_nrcs_summary
        icons = get_icons()

        options = []

        # Métodos de Tc básicos (checkables)
        basic_methods = [
            ("desbordes", "Desbordes", "Cuencas urbanas, usa C"),
            ("kirpich", "Kirpich", "Cuencas rurales"),
            ("temez", "Temez", "Similar a Kirpich"),
        ]

        options.append({"separator": True, "title": "Métodos de Tc"})

        key_map = {"desbordes": "d", "kirpich": "k", "temez": "t"}

        for method_lower, method_display, base_hint in basic_methods:
            # Construir hint con info de parámetros
            hint = base_hint
            if method_lower == "desbordes":
                if self.c:
                    hint = f"C={self.c:.2f}"
                else:
                    hint = "Pedirá C"
            elif method_lower in ("kirpich", "temez"):
                if self.length:
                    hint = f"L={self.length:.0f}m"
                else:
                    hint = "Pedirá longitud"

            options.append({
                "key": key_map.get(method_lower, method_lower[0]),
                "label": method_display,
                "value": method_lower,
                "hint": hint,
                "checkable": True,
            })

        # NRCS como opción especial con calculadora
        options.append({"separator": True, "title": "Método NRCS (TR-55)"})

        # Verificar si hay segmentos configurados
        nrcs_state = get_nrcs_state()
        has_segments = bool(nrcs_state.segments)

        if has_segments:
            # Ya tiene segmentos configurados
            tc_summary = build_nrcs_summary(nrcs_state.segments, nrcs_state.p2_mm)
            options.append({
                "key": "n",
                "label": "NRCS",
                "value": "nrcs",
                "hint": tc_summary,
                "checkable": True,
            })
            # Opción para modificar
            options.append({
                "key": "c",
                "label": f"  {icons.edit} Modificar NRCS",
                "hint": "Abrir calculadora",
                "action": lambda: self._open_nrcs_calculator(),
            })
        else:
            # Sin segmentos - opción para configurar
            options.append({
                "key": "c",
                "label": f"  {icons.add} Configurar NRCS",
                "hint": "Abrir calculadora",
                "action": lambda: self._open_nrcs_calculator(),
            })
            # NRCS como checkable pero disabled
            options.append({
                "key": "n",
                "label": "NRCS",
                "value": "nrcs",
                "hint": "Configura primero",
                "checkable": True,
                "disabled": True,
            })

        return options

    def _open_nrcs_calculator(self) -> dict:
        """Abre la calculadora NRCS integrada en el form_viewer."""
        from .nrcs_inline import get_nrcs_state, set_nrcs_state

        nrcs_state = get_nrcs_state()

        def on_nrcs_confirm(result: dict) -> str:
            """Callback cuando se confirma la calculadora NRCS."""
            set_nrcs_state(
                segments=result["segments"],
                p2_mm=result["p2_mm"],
            )
            return "__reload__"

        return {
            "__open_nrcs_calculator__": True,
            "segments": nrcs_state.segments,
            "p2_mm": nrcs_state.p2_mm,
            "basin": self.basin,
            "callback": on_nrcs_confirm,
        }

    def _calculate_and_add_tc(self, method: str) -> str:
        """Calcula un método Tc y lo agrega a la cuenca. Retorna __reload__ para recargar formulario."""
        tc_calculator = TcCalculator(self.basin, self.c, self.length)
        if tc_calculator.calculate_and_save(method, self):
            return "__reload__"  # Indicar que hay que recargar el formulario
        return None

    def _get_storm_popup_options(self) -> list:
        """
        Construye opciones de popup para tipos de tormenta.

        Muestra:
        - Tipos de tormenta como checkboxes
        - Opción para configurar bimodal (abre panel inline)
        """
        from hidropluvial.cli.theme import get_icons

        icons = get_icons()
        options = []

        # Sección de tormentas estandarizadas
        options.append({"separator": True, "title": "Tormentas estandarizadas"})

        standard_storms = [
            ("gz", "g", "GZ (6 horas)", "DINAGUA Uruguay"),
            ("scs2", "s", "SCS Type II", "NRCS estándar"),
        ]

        for value, key, label, hint in standard_storms:
            options.append({
                "key": key,
                "label": label,
                "value": value,
                "hint": hint,
                "checkable": True,
            })

        # Sección de distribución temporal
        options.append({"separator": True, "title": "Distribución temporal"})

        temporal_storms = [
            ("chicago", "c", "Chicago", "Pico sintético IDF"),
            ("blocks", "a", "Bloques Alternados", "Duración 2×Tc"),
            ("blocks24", "h", "Bloques 24 horas", "Duración 24h"),
        ]

        for value, key, label, hint in temporal_storms:
            options.append({
                "key": key,
                "label": label,
                "value": value,
                "hint": hint,
                "checkable": True,
            })

        # Sección bimodal - solo seleccionable si está configurada
        bimodal_state = get_bimodal_state()
        bimodal_summary = build_bimodal_summary()

        options.append({"separator": True, "title": "Tormenta Bimodal"})

        if bimodal_state.is_configured:
            # Ya configurado - checkbox habilitado + opción de modificar
            options.append({
                "key": "b",
                "label": "Bimodal",
                "value": "bimodal",
                "hint": bimodal_summary,
                "checkable": True,
            })
            options.append({
                "key": "m",
                "label": f"  {icons.edit} Modificar configuración",
                "hint": "Abrir configurador",
                "action": lambda: self._open_bimodal_inline_config(),
            })
        else:
            # No configurado - opción para configurar primero
            options.append({
                "key": "m",
                "label": f"{icons.add} Configurar tormenta Bi-Modal",
                "hint": "Abrir configurador",
                "action": lambda: self._open_bimodal_inline_config(),
            })
            # Bimodal como checkbox pero deshabilitado
            options.append({
                "key": "b",
                "label": "Bimodal",
                "value": "bimodal",
                "hint": "Configura primero",
                "checkable": True,
                "disabled": True,
            })

        return options

    def _open_bimodal_inline_config(self) -> dict:
        """Abre la configuración bimodal inline (como NRCS)."""
        bimodal_state = get_bimodal_state()

        def on_bimodal_confirm(result: dict) -> str:
            """Callback cuando se confirma la configuración bimodal."""
            set_bimodal_state(
                duration_hr=result["duration_hr"],
                peak1=result["peak1"],
                peak2=result["peak2"],
                vol_split=result["vol_split"],
                peak_width=result["peak_width"],
                preset_name=result.get("preset_name"),
            )
            # Actualizar valores en el menú
            self.bimodal_duration_hr = result["duration_hr"]
            self.bimodal_peak1 = result["peak1"]
            self.bimodal_peak2 = result["peak2"]
            self.bimodal_vol_split = result["vol_split"]
            self.bimodal_peak_width = result["peak_width"]
            return "__reload__"

        return {
            "__open_bimodal_calculator__": True,
            "duration_hr": bimodal_state.duration_hr,
            "peak1": bimodal_state.peak1,
            "peak2": bimodal_state.peak2,
            "vol_split": bimodal_state.vol_split,
            "peak_width": bimodal_state.peak_width,
            "callback": on_bimodal_confirm,
        }

    def _get_previous_c_values(self) -> str:
        """Obtiene string con valores de C usados en análisis anteriores."""
        c_values = {}
        for a in self.basin.analyses:
            if a.tc.parameters and "c" in a.tc.parameters:
                c_val = a.tc.parameters["c"]
                c_values[c_val] = c_values.get(c_val, 0) + 1

        if not c_values:
            return ""

        # Formatear como "C=0.75 (5), C=0.80 (3)"
        parts = []
        for c_val, count in sorted(c_values.items(), key=lambda x: -x[1]):
            parts.append(f"C={c_val:.2f} ({count})")
        return ", ".join(parts[:3])  # Máximo 3 valores

    def _get_previous_cn_values(self) -> str:
        """Obtiene string con valores de CN usados en análisis anteriores."""
        cn_values = {}
        for a in self.basin.analyses:
            if a.tc.parameters:
                cn_val = a.tc.parameters.get("cn_adjusted") or a.tc.parameters.get("cn")
                if cn_val:
                    cn_int = int(cn_val)
                    cn_values[cn_int] = cn_values.get(cn_int, 0) + 1

        if not cn_values:
            return ""

        # Formatear como "CN=85 (4), CN=80 (2)"
        parts = []
        for cn_val, count in sorted(cn_values.items(), key=lambda x: -x[1]):
            parts.append(f"CN={cn_val} ({count})")
        return ", ".join(parts[:3])  # Máximo 3 valores

    def _check_and_request_tc_data(self) -> None:
        """
        Verifica datos faltantes para cálculo de Tc y ofrece ingresarlos.
        """
        from hidropluvial.database import get_database

        missing = []
        if not self.length:
            missing.append("Longitud del cauce (para Kirpich/Temez)")

        if not missing:
            return

        self.note("Datos opcionales para métodos de Tc:")
        for m in missing:
            self.info(f"  • {m}")

        if not self.confirm("¿Deseas completar estos datos?", default=False):
            return

        db = get_database()

        # Solicitar longitud si falta
        if not self.length:
            self.note("La longitud del cauce principal es necesaria para Kirpich y Temez.")
            length_str = self.text("Longitud del cauce (metros):", default="")
            if length_str:
                try:
                    self.length = float(length_str)
                    self.basin.length_m = self.length
                    db.update_basin(self.basin.id, length_m=self.length)
                    self.success(f"Longitud guardada: {self.length} m")
                except ValueError:
                    self.warning("Valor inválido, se omite longitud")

    def _offer_calculate_tc(self) -> bool:
        """Ofrece calcular Tc si no existe. Retorna True si se calculó alguno."""
        from hidropluvial.cli.viewer.form_viewer import (
            interactive_form, FormField, FieldType, FormResult
        )
        from hidropluvial.database import get_database
        from hidropluvial.models import TcResult

        # Construir opciones de métodos Tc
        tc_options = []

        # Desbordes
        desbordes_hint = "Recomendado cuencas urbanas"
        if not self.c:
            desbordes_hint = "Pedirá coef. C"
        tc_options.append({"name": f"Desbordes ({desbordes_hint})", "value": "desbordes"})

        # Kirpich
        kirpich_hint = "Cuencas rurales"
        if not self.length:
            kirpich_hint = "Pedirá longitud de cauce"
        tc_options.append({"name": f"Kirpich ({kirpich_hint})", "value": "kirpich"})

        # Temez
        temez_hint = "Similar a Kirpich"
        if not self.length:
            temez_hint = "Pedirá longitud de cauce"
        tc_options.append({"name": f"Temez ({temez_hint})", "value": "temez"})

        # NRCS
        nrcs_hint = "Método de velocidades TR-55"
        if self.basin.nrcs_segments:
            nrcs_hint = f"{len(self.basin.nrcs_segments)} segmentos configurados"
        else:
            nrcs_hint = "Configurar segmentos de flujo"
        tc_options.append({"name": f"NRCS ({nrcs_hint})", "value": "nrcs"})

        # Determinar default basado en datos disponibles
        default_tc = []
        if self.c:
            default_tc.append("desbordes")
        elif self.length:
            default_tc.append("kirpich")
        else:
            default_tc.append("desbordes")  # Por defecto, pedirá C

        # Campos del formulario
        fields = [
            FormField(
                key="tc_methods",
                label="Métodos de Tc a calcular",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=tc_options,
                default=default_tc,
                hint="Selecciona uno o más métodos",
            ),
            FormField(
                key="c",
                label="Coeficiente C",
                field_type=FieldType.FLOAT,
                required=True,
                default=self.c or self._suggested_c,
                min_value=0.1,
                max_value=1.0,
                hint="Requerido para Desbordes",
                depends_on="tc_methods",
                depends_value="desbordes",
                disabled_hint="Selecciona método Desbordes",
            ),
            FormField(
                key="length",
                label="Longitud del cauce",
                field_type=FieldType.FLOAT,
                required=True,
                default=self.length,
                unit="m",
                min_value=1,
                hint="Requerido para Kirpich/Temez",
                depends_on="tc_methods",
                depends_value=["kirpich", "temez"],  # Se activa con cualquiera
                disabled_hint="Selecciona Kirpich o Temez",
            ),
        ]

        # Mostrar formulario
        result = interactive_form(
            title="Calcular Tiempo de Concentración",
            fields=fields,
            allow_back=True,
        )

        if result is None:
            return False

        if result.get("_result") == FormResult.BACK:
            return False

        tc_methods = result.get("tc_methods") or []
        if not tc_methods:
            self.warning("No se seleccionó ningún método")
            return False

        # Obtener valores de C y longitud si se proporcionaron
        c_val = result.get("c")
        length_val = result.get("length")

        db = get_database()

        # Guardar C si se proporcionó
        if c_val and "desbordes" in tc_methods:
            self.c = c_val
            self.basin.c = self.c
            db.update_basin(self.basin.id, c=self.c)

        # Guardar longitud si se proporcionó (para Kirpich o Temez)
        if length_val and ("kirpich" in tc_methods or "temez" in tc_methods):
            self.length = length_val
            self.basin.length_m = self.length
            db.update_basin(self.basin.id, length_m=self.length)

        # Calcular Tc para cada método
        tc_calculator = TcCalculator(self.basin, self.c, self.length)
        calculated = False

        for method in tc_methods:
            # Verificar que tenemos los datos necesarios
            if method == "desbordes" and not self.c:
                self.warning(f"No se puede calcular {method} sin coeficiente C")
                continue
            if method in ("kirpich", "temez") and not self.length:
                self.warning(f"No se puede calcular {method} sin longitud de cauce")
                continue
            if method == "nrcs":
                # NRCS requiere segmentos configurados
                if not self.basin.nrcs_segments:
                    from .nrcs_config import NRCSConfigurator
                    configurator = NRCSConfigurator(self.basin, self)
                    if not configurator.configure():
                        self.warning("Configuración NRCS cancelada")
                        continue
                # Calcular Tc con NRCS
                from hidropluvial.core.tc import nrcs_velocity_method
                p2_mm = self.basin.p2_mm or 50.0
                tc_hr = nrcs_velocity_method(self.basin.nrcs_segments, p2_mm)
                tc_params = {
                    "segments": len(self.basin.nrcs_segments),
                    "p2_mm": p2_mm,
                }
                db.add_tc_result(self.basin.id, "nrcs", tc_hr, tc_params)
                tc_result = TcResult(method="nrcs", tc_hr=tc_hr, tc_min=tc_hr * 60, parameters=tc_params)
                self.basin.add_tc_result(tc_result)
                self.success(f"Tc (NRCS): {tc_result.tc_min:.1f} min")
                calculated = True
                continue

            tc_hr, tc_params = tc_calculator.calculate_with_params(method)
            if tc_hr:
                db.add_tc_result(self.basin.id, method, tc_hr, tc_params)
                tc_result = TcResult(method=method, tc_hr=tc_hr, tc_min=tc_hr * 60, parameters=tc_params)
                self.basin.add_tc_result(tc_result)
                method_display = format_method_name(method)
                self.success(f"Tc ({method_display}): {tc_result.tc_min:.1f} min")
                calculated = True

        return calculated
