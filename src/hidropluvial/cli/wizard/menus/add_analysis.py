"""
Menú para agregar analisis adicionales.

Permite seleccionar exactamente qué análisis agregar, similar al wizard inicial,
detectando y descartando duplicados de análisis ya existentes.
"""

from typing import Optional, Set, Tuple

import questionary

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner
from hidropluvial.core import kirpich, desbordes, temez
from hidropluvial.core.tc import nrcs_velocity_method, SHEET_FLOW_N, SHALLOW_FLOW_K
from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment


def _get_analysis_key(analysis) -> Tuple[str, str, int, float, str]:
    """
    Genera una clave única para identificar un análisis.

    Returns:
        Tupla (tc_method, storm_type, return_period, x_factor, runoff_method)
    """
    tc_method = analysis.hydrograph.tc_method.lower()
    storm_type = analysis.storm.type.lower()
    return_period = analysis.storm.return_period
    x_factor = analysis.hydrograph.x_factor or 1.0
    # Obtener método de escorrentía de los parámetros del Tc
    runoff_method = ""
    if analysis.tc.parameters:
        runoff_method = analysis.tc.parameters.get("runoff_method", "")
    return (tc_method, storm_type, return_period, x_factor, runoff_method)


class AddAnalysisMenu(SessionMenu):
    """Menú para agregar analisis adicionales a una cuenca."""

    def __init__(
        self,
        basin,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(basin)
        self.c = c
        self.cn = cn
        self.length = length
        # Obtener claves de análisis existentes para detectar duplicados
        self._existing_keys: Set[Tuple[str, str, int, float]] = set()
        for a in basin.analyses:
            self._existing_keys.add(_get_analysis_key(a))

    def show(self) -> None:
        """Muestra menú de opciones para agregar análisis."""
        while True:
            self.echo("\n-- Agregar Analisis --\n")
            self.echo(f"  Cuenca: {self.basin.name} ({len(self.basin.analyses)} análisis)\n")

            que_agregar = self.select(
                "¿Cómo quieres agregar análisis?",
                choices=[
                    "Selección individual (elegir Tc, tormenta, Tr, X)",
                    "Agregar rápido por categoría",
                    "← Volver",
                ],
            )

            if que_agregar is None or "Volver" in que_agregar:
                return

            if "individual" in que_agregar.lower():
                self._add_individual()
            elif "rápido" in que_agregar.lower():
                self._add_quick_menu()

            # Recargar sesion para mostrar contador actualizado
            self.reload_session()

    def _add_individual(self) -> None:
        """Wizard de selección individual para agregar análisis específicos."""
        self.echo("\n  === Selección Individual ===\n")

        # Verificar si faltan datos básicos y ofrecerlos al inicio
        self._check_and_request_missing_data()

        # 1. Obtener métodos Tc disponibles
        tc_existentes = [tc.method for tc in self.basin.tc_results]
        tc_no_calculados = self._get_available_tc_methods(tc_existentes)

        # Si no hay Tc calculados, ofrecer calcularlos
        if not tc_existentes:
            self.warning("No hay métodos de Tc calculados en esta cuenca")
            if not self._offer_calculate_tc():
                return
            tc_existentes = [tc.method for tc in self.basin.tc_results]
            if not tc_existentes:
                return
            # Actualizar lista de no calculados
            tc_no_calculados = self._get_available_tc_methods(tc_existentes)

        # Construir opciones de Tc
        tc_choices = []

        # Primero: Tc YA calculados (con valor) - marcados por defecto
        for tc_result in self.basin.tc_results:
            method_display = self._format_method_name(tc_result.method)
            tc_choices.append(questionary.Choice(
                f"{method_display} (Tc = {tc_result.tc_min:.1f} min)",
                value=tc_result.method.lower(),
                checked=True
            ))

        # Segundo: Tc NO calculados (ofrecer calcularlos)
        for tc in tc_no_calculados:
            # Indicar si requiere datos adicionales
            tc_lower = tc.lower()
            extra_info = ""
            if tc_lower in ("kirpich", "temez") and not self.length:
                extra_info = " - pedirá longitud"
            elif tc_lower == "desbordes" and not self.c:
                extra_info = " - pedirá coef. C"
            elif tc_lower == "nrcs" and not self.basin.nrcs_segments:
                extra_info = " - configurar segmentos"

            tc_choices.append(questionary.Choice(
                f"{tc} (calcular nuevo{extra_info})",
                value=f"calc:{tc_lower}",
                checked=False
            ))

        if not tc_choices:
            self.echo("  No hay métodos de Tc disponibles.\n")
            return

        tc_selected = self.checkbox("Métodos de Tc a usar:", tc_choices)
        if not tc_selected:
            return

        # Procesar selección: separar calculados de los que hay que calcular
        tc_methods_final = []
        for tc_method in tc_selected:
            if tc_method.startswith("calc:"):
                # Necesita calcularse
                method_name = tc_method.replace("calc:", "")
                if self._calculate_single_tc(method_name):
                    tc_methods_final.append(method_name)
            else:
                # Ya está calculado
                tc_methods_final.append(tc_method)

        if not tc_methods_final:
            self.warning("No se seleccionó ningún método de Tc")
            return

        tc_methods = tc_methods_final

        # 2. Seleccionar tipos de tormenta (múltiple)
        storm_choices = [
            questionary.Choice("GZ (6 horas) - DINAGUA Uruguay", checked=True),
            questionary.Choice("Bloques alternantes (duración = 2×Tc)", checked=False),
            questionary.Choice("Bloques 24 horas", checked=False),
            questionary.Choice("Bimodal Uruguay", checked=False),
        ]
        storm_types = self.checkbox("Tipos de tormenta:", storm_choices)
        if not storm_types:
            return
        storm_codes = [self._get_storm_code(st) for st in storm_types]

        # 3. Seleccionar período de retorno
        tr_choices = [
            questionary.Choice("2 años", checked=False),
            questionary.Choice("5 años", checked=False),
            questionary.Choice("10 años", checked=True),
            questionary.Choice("25 años", checked=False),
            questionary.Choice("50 años", checked=False),
            questionary.Choice("100 años", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno:", tr_choices)
        if not return_periods:
            return
        tr_list = [int(tr.split()[0]) for tr in return_periods]

        # 4. Seleccionar factor X (solo si hay GZ entre las tormentas)
        x_factors = [1.0]
        if "gz" in storm_codes:
            x_choices = [
                questionary.Choice("X=1.00 - Racional/urbano interno", checked=True),
                questionary.Choice("X=1.25 - Urbano (gran pendiente)", checked=False),
                questionary.Choice("X=1.67 - NRCS estándar", checked=False),
                questionary.Choice("X=2.25 - Mixto rural/urbano", checked=False),
                questionary.Choice("X=3.33 - Rural sinuoso", checked=False),
            ]
            x_selected = self.checkbox("Factor X (forma del hidrograma):", x_choices)
            if x_selected:
                x_factors = [float(x.split("=")[1].split()[0]) for x in x_selected]

        # Determinar métodos de escorrentía disponibles
        runoff_methods = []
        if self.c:
            runoff_methods.append("racional")
        if self.cn:
            runoff_methods.append("scs-cn")
        if not runoff_methods:
            self.warning("No hay métodos de escorrentía disponibles (requiere C o CN)")
            return

        # Calcular cuántos análisis nuevos se agregarán (descartando duplicados)
        new_analyses = []
        duplicates = []
        for tc_method in tc_methods:
            for storm_code in storm_codes:
                for tr in tr_list:
                    # Factor X solo aplica a GZ, para otras tormentas usar 1.0
                    x_list = x_factors if storm_code == "gz" else [1.0]
                    for x in x_list:
                        for runoff in runoff_methods:
                            key = (tc_method.lower(), storm_code, tr, x, runoff)
                            if key in self._existing_keys:
                                esc_label = "C" if runoff == "racional" else "CN"
                                duplicates.append(f"Tc={tc_method}, {storm_code}, Tr={tr}, X={x:.2f}, {esc_label}")
                            else:
                                new_analyses.append((tc_method, storm_code, tr, x, runoff))

        if duplicates:
            self.echo(f"\n  Se descartarán {len(duplicates)} análisis duplicados:")
            for dup in duplicates[:5]:  # Mostrar máximo 5
                self.echo(f"    - {dup}")
            if len(duplicates) > 5:
                self.echo(f"    ... y {len(duplicates) - 5} más")

        if not new_analyses:
            self.warning("Todos los análisis seleccionados ya existen")
            return

        # Mostrar resumen de métodos de escorrentía
        esc_labels = []
        if "racional" in runoff_methods:
            esc_labels.append("Racional (C)")
        if "scs-cn" in runoff_methods:
            esc_labels.append("SCS-CN")
        self.echo(f"\n  Métodos de escorrentía: {', '.join(esc_labels)}")

        # Confirmar
        self.echo(f"\n  Se agregarán {len(new_analyses)} análisis nuevos:")
        for tc, storm, tr, x, runoff in new_analyses[:5]:
            x_str = f", X={x:.2f}" if x != 1.0 else ""
            esc_label = "C" if runoff == "racional" else "CN"
            self.echo(f"    + Tc={tc}, {storm}, Tr={tr}{x_str}, {esc_label}")
        if len(new_analyses) > 5:
            self.echo(f"    ... y {len(new_analyses) - 5} más")

        if not self.confirm(f"\n¿Ejecutar {len(new_analyses)} análisis?", default=True):
            return

        # Ejecutar análisis por cada tipo de tormenta y método de escorrentía
        runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
        total_count = 0

        for storm_code in storm_codes:
            for runoff in runoff_methods:
                # Filtrar análisis para esta tormenta y método de escorrentía
                storm_analyses = [
                    (tc, tr, x) for tc, st, tr, x, r in new_analyses
                    if st == storm_code and r == runoff
                ]
                if not storm_analyses:
                    continue

                # Obtener Tc, Tr y X únicos para esta combinación
                unique_tcs = sorted(set(tc for tc, _, _ in storm_analyses))
                unique_trs = sorted(set(tr for _, tr, _ in storm_analyses))
                unique_xs = sorted(set(x for _, _, x in storm_analyses))

                count = runner.run(unique_tcs, storm_code, unique_trs, unique_xs, runoff_method=runoff)
                total_count += count

        self.success(f"Se agregaron {total_count} análisis")

    def _add_quick_menu(self) -> None:
        """Menú rápido por categoría (comportamiento original simplificado)."""
        while True:
            self.echo("\n  === Agregar Rápido ===\n")

            que_agregar = self.select(
                "¿Qué tipo de análisis quieres agregar?",
                choices=[
                    "Otra tormenta (Bloques, Bimodal, etc.)",
                    "Otros períodos de retorno",
                    "Otros valores de X",
                    "Otro método de Tc",
                    "← Volver",
                ],
            )

            if que_agregar is None or "Volver" in que_agregar:
                return

            tc_existentes = [tc.method for tc in self.basin.tc_results]

            if "tormenta" in que_agregar.lower():
                self._add_storm(tc_existentes)
            elif "retorno" in que_agregar.lower():
                self._add_return_periods(tc_existentes)
            elif "X" in que_agregar:
                self._add_x_factors(tc_existentes)
            elif "Tc" in que_agregar:
                self._add_tc_method(tc_existentes)

            # Actualizar claves existentes
            self._existing_keys.clear()
            for a in self.basin.analyses:
                self._existing_keys.add(_get_analysis_key(a))

    def _check_and_request_missing_data(self) -> None:
        """
        Verifica datos faltantes de la cuenca y ofrece ingresarlos.

        Esto permite al usuario completar datos antes de seleccionar
        métodos de Tc, evitando sorpresas durante el cálculo.
        """
        from hidropluvial.database import get_database

        missing = []
        if not self.length:
            missing.append("Longitud del cauce (para Kirpich/Temez)")
        if not self.c:
            missing.append("Coeficiente C (para Desbordes)")

        if not missing:
            return

        self.echo("  La cuenca tiene datos faltantes que algunos métodos de Tc requieren:\n")
        for m in missing:
            self.echo(f"    • {m}")
        self.echo("")

        if not self.confirm("¿Deseas completar estos datos ahora?", default=True):
            return

        db = get_database()

        # Solicitar longitud si falta
        if not self.length:
            self.echo("\n  La longitud del cauce principal es necesaria para Kirpich y Temez.")
            length_str = self.text("Longitud del cauce (metros, dejar vacío para omitir):", default="")
            if length_str:
                try:
                    self.length = float(length_str)
                    self.basin.length_m = self.length
                    db.update_basin(self.basin.id, length_m=self.length)
                    self.success(f"Longitud guardada: {self.length} m")
                except ValueError:
                    self.warning("Valor inválido, se omite longitud")

        # Solicitar C si falta
        if not self.c:
            self.echo("\n  El coeficiente C es necesario para el método Desbordes.")
            c_str = self.text("Coeficiente C (0.1 - 1.0, dejar vacío para omitir):", default="")
            if c_str:
                try:
                    c_val = float(c_str)
                    if 0.1 <= c_val <= 1.0:
                        self.c = c_val
                        self.basin.c = self.c
                        db.update_basin(self.basin.id, c=self.c)
                        self.success(f"Coeficiente C guardado: {self.c}")
                    else:
                        self.warning("C debe estar entre 0.1 y 1.0, se omite")
                except ValueError:
                    self.warning("Valor inválido, se omite C")

        self.echo("")

    def _add_storm(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nueva tormenta."""
        storm_type = self.select(
            "Tipo de tormenta:",
            choices=[
                "GZ (6 horas)",
                "Bloques alternantes",
                "Bloques 24 horas",
                "Bimodal Uruguay",
                "← Cancelar",
            ],
        )

        if storm_type is None or "Cancelar" in storm_type:
            return

        storm_code = self._get_storm_code(storm_type)

        # Períodos de retorno
        tr_choices = [
            questionary.Choice("2", checked=True),
            questionary.Choice("10", checked=True),
            questionary.Choice("25", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno:", tr_choices)

        if not return_periods:
            return

        # Factor X solo para GZ
        x_factors = [1.0]
        if storm_code == "gz":
            x_factors = self._ask_x_factors()

        # Mostrar preview y confirmar
        n_new = self._preview_and_confirm(
            tc_existentes, storm_code,
            [int(tr) for tr in return_periods],
            x_factors
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, storm_code, [int(tr) for tr in return_periods], x_factors)
            self.success(f"Se agregaron {count} análisis")

    def _get_storm_code(self, storm_type: str) -> str:
        """Convierte tipo de tormenta a codigo."""
        if "Bloques alternantes" in storm_type:
            return "blocks"
        elif "24 horas" in storm_type:
            return "blocks24"
        elif "Bimodal" in storm_type:
            return "bimodal"
        return "gz"

    def _ask_x_factors(self) -> list[float]:
        """Solicita valores de X para GZ."""
        x_choices = [
            questionary.Choice("1.00", checked=True),
            questionary.Choice("1.25", checked=True),
        ]
        x_selected = self.checkbox("Valores de X:", x_choices)
        if x_selected:
            return [float(x) for x in x_selected]
        return [1.0]

    def _preview_and_confirm(
        self,
        tc_methods: list[str],
        storm_code: str,
        return_periods: list[int],
        x_factors: list[float]
    ) -> int:
        """
        Muestra preview de análisis a agregar y confirma.

        Returns:
            Número de análisis nuevos (0 si cancela o todos son duplicados)
        """
        new_analyses = []
        duplicates = []

        for tc in tc_methods:
            for tr in return_periods:
                for x in x_factors:
                    key = (tc.lower(), storm_code, tr, x)
                    if key in self._existing_keys:
                        duplicates.append(key)
                    else:
                        new_analyses.append(key)

        if duplicates:
            self.echo(f"\n  Se descartarán {len(duplicates)} análisis duplicados")

        if not new_analyses:
            self.warning("Todos los análisis seleccionados ya existen")
            return 0

        self.echo(f"\n  Se agregarán {len(new_analyses)} análisis nuevos")

        if not self.confirm(f"¿Continuar?", default=True):
            return 0

        return len(new_analyses)

    def _add_return_periods(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nuevos períodos de retorno."""
        tr_choices = [
            questionary.Choice("2", checked=False),
            questionary.Choice("5", checked=False),
            questionary.Choice("10", checked=False),
            questionary.Choice("25", checked=False),
            questionary.Choice("50", checked=True),
            questionary.Choice("100", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno adicionales:", tr_choices)

        if not return_periods:
            return

        # Usar GZ por defecto y X=[1.0, 1.25]
        n_new = self._preview_and_confirm(
            tc_existentes, "gz",
            [int(tr) for tr in return_periods],
            [1.0, 1.25]
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, "gz", [int(tr) for tr in return_periods], [1.0, 1.25])
            self.success(f"Se agregaron {count} análisis")

    def _add_x_factors(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nuevos valores de X."""
        x_choices = [
            questionary.Choice("1.00", checked=False),
            questionary.Choice("1.25", checked=False),
            questionary.Choice("1.67", checked=True),
            questionary.Choice("2.25", checked=False),
            questionary.Choice("3.33", checked=False),
        ]
        x_selected = self.checkbox("Valores de X adicionales:", x_choices)

        if not x_selected:
            return

        x_factors = [float(x) for x in x_selected]

        # Usar Tr existentes o defaults
        existing_trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
        if not existing_trs:
            existing_trs = [2, 10, 25]

        n_new = self._preview_and_confirm(
            tc_existentes, "gz",
            existing_trs,
            x_factors
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, "gz", existing_trs, x_factors)
            self.success(f"Se agregaron {count} análisis")

    def _add_tc_method(self, tc_existentes: list[str]) -> None:
        """Agrega nuevos métodos de Tc y ejecuta análisis."""
        available_methods = self._get_available_tc_methods(tc_existentes)

        if not available_methods:
            self.echo("  No hay métodos de Tc adicionales disponibles.")
            return

        # Construir choices con descripciones
        tc_choices = []
        for method in available_methods:
            if method == "Desbordes":
                tc_choices.append(questionary.Choice(
                    "Desbordes (recomendado cuencas urbanas)",
                    checked=True
                ))
            elif method == "Kirpich":
                tc_choices.append(questionary.Choice(
                    "Kirpich (cuencas rurales)",
                    checked=False
                ))
            elif method == "Temez":
                tc_choices.append(questionary.Choice(
                    "Temez",
                    checked=False
                ))
            elif method == "NRCS":
                tc_choices.append(questionary.Choice(
                    "NRCS (método de velocidades TR-55)",
                    checked=False
                ))

        selected = self.checkbox("Selecciona método(s) de Tc:", tc_choices)
        if not selected:
            return

        # Calcular cada método seleccionado
        new_methods = []
        for tc_method in selected:
            # Extraer nombre del método (sin descripción)
            method = tc_method.split()[0].lower()
            tc_hr, tc_params = self._calculate_tc_with_params(method)
            if tc_hr:
                result = self.manager.add_tc_result(self.basin, method, tc_hr, **tc_params)
                self.success(f"Tc ({method}): {result.tc_min:.1f} min")
                new_methods.append(method)

        if not new_methods:
            self.warning("No se pudo calcular ningún método de Tc")
            return

        # Usar Tr y X existentes o defaults
        existing_trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
        if not existing_trs:
            existing_trs = [2, 10, 25]

        n_new = self._preview_and_confirm(
            new_methods, "gz",
            existing_trs,
            [1.0, 1.25]
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(new_methods, "gz", existing_trs, [1.0, 1.25])
            self.success(f"Se agregaron {count} análisis")

    def _get_available_tc_methods(self, tc_existentes: list[str]) -> list[str]:
        """
        Retorna métodos de Tc disponibles (no calculados aún).

        Solo retorna métodos que se pueden calcular con los datos actuales
        o que pueden solicitar los datos faltantes interactivamente.
        """
        tc_choices = []
        tc_lower = [tc.lower() for tc in tc_existentes]

        # Desbordes: requiere C (se puede solicitar interactivamente)
        if "desbordes" not in tc_lower:
            tc_choices.append("Desbordes")

        # Kirpich: requiere longitud (se puede solicitar interactivamente)
        if "kirpich" not in tc_lower:
            tc_choices.append("Kirpich")

        # Temez: requiere longitud (se puede solicitar interactivamente)
        if "temez" not in tc_lower:
            tc_choices.append("Temez")

        # NRCS: siempre disponible (usa segmentos propios)
        if "nrcs" not in tc_lower:
            tc_choices.append("NRCS")

        return tc_choices

    def _format_method_name(self, method: str) -> str:
        """Formatea el nombre del método para mostrar."""
        method_lower = method.lower()
        if method_lower == "nrcs":
            return "NRCS"
        elif method_lower == "scs":
            return "SCS"
        return method.capitalize()

    def _calculate_tc_with_params(self, method: str) -> tuple[Optional[float], dict]:
        """Calcula Tc segun el método y retorna parametros usados."""
        if method == "kirpich" and self.length:
            tc_hr = kirpich(self.length, self.basin.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "temez" and self.length:
            tc_hr = temez(self.length / 1000, self.basin.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "desbordes" and self.c:
            tc_hr = desbordes(
                self.basin.area_ha,
                self.basin.slope_pct,
                self.c,
            )
            return tc_hr, {"c": self.c, "area_ha": self.basin.area_ha}
        elif method == "nrcs":
            # NRCS usa segmentos guardados en la cuenca
            if self.basin.nrcs_segments:
                p2_mm = self.basin.p2_mm or 50.0
                tc_hr = nrcs_velocity_method(self.basin.nrcs_segments, p2_mm)
                return tc_hr, {"p2_mm": p2_mm, "n_segments": len(self.basin.nrcs_segments)}
        return None, {}

    def _calculate_single_tc(self, method: str) -> bool:
        """
        Calcula un único método de Tc y lo guarda en la cuenca.

        Returns:
            True si se calculó exitosamente, False en caso contrario.
        """
        from hidropluvial.database import get_database
        db = get_database()

        # NRCS requiere configurar segmentos primero
        if method == "nrcs":
            if not self.basin.nrcs_segments:
                if not self._configure_nrcs():
                    return False

        # Kirpich y Temez requieren longitud
        if method in ("kirpich", "temez") and not self.length:
            self.echo(f"\n  El método {method.capitalize()} requiere la longitud del cauce principal.\n")
            length_str = self.text("Longitud del cauce (metros):", default="")
            if not length_str:
                self.warning("Longitud requerida para este método")
                return False
            try:
                self.length = float(length_str)
                # Guardar en la cuenca
                self.basin.length_m = self.length
                db.update_basin(self.basin.id, length_m=self.length)
                self.success(f"Longitud guardada: {self.length} m")
            except ValueError:
                self.error("Valor inválido")
                return False

        # Desbordes requiere C
        if method == "desbordes" and not self.c:
            self.echo(f"\n  El método Desbordes requiere el coeficiente de escorrentía C.\n")
            c_str = self.text("Coeficiente C (0.1 - 1.0):", default="")
            if not c_str:
                self.warning("Coeficiente C requerido para este método")
                return False
            try:
                self.c = float(c_str)
                if not 0.1 <= self.c <= 1.0:
                    self.warning("C debe estar entre 0.1 y 1.0")
                    self.c = None
                    return False
                # Guardar en la cuenca
                self.basin.c = self.c
                db.update_basin(self.basin.id, c=self.c)
                self.success(f"Coeficiente C guardado: {self.c}")
            except ValueError:
                self.error("Valor inválido")
                return False

        tc_hr, tc_params = self._calculate_tc_with_params(method)
        if tc_hr:
            from hidropluvial.models import TcResult

            db.add_tc_result(self.basin.id, method, tc_hr, tc_params)
            # Agregar al modelo en memoria
            result = TcResult(method=method, tc_hr=tc_hr, tc_min=tc_hr * 60, parameters=tc_params)
            self.basin.add_tc_result(result)
            method_display = self._format_method_name(method)
            self.success(f"Tc ({method_display}): {result.tc_min:.1f} min")
            return True
        return False

    def _offer_calculate_tc(self) -> bool:
        """Ofrece calcular Tc si no existe. Retorna True si se calculó alguno."""
        self.echo("\n  Primero necesitas calcular al menos un tiempo de concentración.\n")

        # Ofrecer todos los métodos, igual que el wizard general
        tc_choices = []

        # Desbordes requiere C
        if self.c:
            tc_choices.append(questionary.Choice(
                "Desbordes (recomendado cuencas urbanas)",
                checked=True
            ))
        else:
            tc_choices.append(questionary.Choice(
                "Desbordes (requiere coef. C)",
                checked=False
            ))

        # Kirpich y Temez requieren longitud
        if self.length:
            tc_choices.append(questionary.Choice(
                "Kirpich (cuencas rurales)",
                checked=(self.c is None)
            ))
            tc_choices.append(questionary.Choice("Temez", checked=False))
        else:
            tc_choices.append(questionary.Choice(
                "Kirpich (requiere longitud de cauce)",
                checked=False
            ))
            tc_choices.append(questionary.Choice(
                "Temez (requiere longitud de cauce)",
                checked=False
            ))

        tc_methods = self.checkbox("Selecciona método(s) de Tc:", tc_choices)

        if not tc_methods:
            return False

        # Verificar si necesitamos datos adicionales
        needs_length = any("Kirpich" in m or "Temez" in m for m in tc_methods)
        needs_c = any("Desbordes" in m for m in tc_methods)

        # Solicitar longitud si es necesaria y no la tenemos
        if needs_length and not self.length:
            self.echo("\n  Para Kirpich/Temez se necesita la longitud del cauce principal.\n")
            length_str = self.text("Longitud del cauce (metros):", default="")
            if not length_str:
                self.warning("No se puede calcular Kirpich/Temez sin longitud")
                tc_methods = [m for m in tc_methods if "Kirpich" not in m and "Temez" not in m]
            else:
                try:
                    self.length = float(length_str)
                    # Guardar en la cuenca
                    self.basin.length_m = self.length
                    from hidropluvial.database import get_database
                    db = get_database()
                    db.update_basin(self.basin.id, length_m=self.length)
                    self.success(f"Longitud guardada: {self.length} m")
                except ValueError:
                    self.error("Valor inválido")
                    tc_methods = [m for m in tc_methods if "Kirpich" not in m and "Temez" not in m]

        # Solicitar C si es necesario y no lo tenemos
        if needs_c and not self.c:
            self.echo("\n  Para Desbordes se necesita el coeficiente de escorrentía C.\n")
            c_str = self.text("Coeficiente C (0.1 - 1.0):", default="")
            if not c_str:
                self.warning("No se puede calcular Desbordes sin coeficiente C")
                tc_methods = [m for m in tc_methods if "Desbordes" not in m]
            else:
                try:
                    self.c = float(c_str)
                    if not 0.1 <= self.c <= 1.0:
                        self.warning("C debe estar entre 0.1 y 1.0")
                        tc_methods = [m for m in tc_methods if "Desbordes" not in m]
                        self.c = None
                    else:
                        # Guardar en la cuenca
                        self.basin.c = self.c
                        from hidropluvial.database import get_database
                        db = get_database()
                        db.update_basin(self.basin.id, c=self.c)
                        self.success(f"Coeficiente C guardado: {self.c}")
                except ValueError:
                    self.error("Valor inválido")
                    tc_methods = [m for m in tc_methods if "Desbordes" not in m]

        if not tc_methods:
            self.warning("No hay métodos de Tc disponibles con los datos actuales")
            return False

        from hidropluvial.database import get_database
        from hidropluvial.models import TcResult
        db = get_database()
        calculated = False

        for tc_method in tc_methods:
            # Extraer nombre del método (sin descripción)
            method = tc_method.split()[0].lower()
            tc_hr, tc_params = self._calculate_tc_with_params(method)
            if tc_hr:
                db.add_tc_result(self.basin.id, method, tc_hr, tc_params)
                # Agregar al modelo en memoria
                result = TcResult(method=method, tc_hr=tc_hr, tc_min=tc_hr * 60, parameters=tc_params)
                self.basin.add_tc_result(result)
                self.success(f"Tc ({method}): {result.tc_min:.1f} min")
                calculated = True

        return calculated

    # ========================================================================
    # Configuración NRCS
    # ========================================================================

    def _configure_nrcs(self) -> bool:
        """
        Configura segmentos para el método NRCS de velocidades.

        Returns:
            True si se configuró exitosamente, False si se canceló.
        """
        self.echo("\n  ┌─────────────────────────────────────────────────────────────┐")
        self.echo("  │           MÉTODO NRCS - VELOCIDADES (TR-55)                  │")
        self.echo("  ├─────────────────────────────────────────────────────────────┤")
        self.echo("  │  El método divide el recorrido del agua en segmentos:        │")
        self.echo("  │                                                              │")
        self.echo("  │  1. FLUJO LAMINAR (Sheet Flow) - máx 100m                    │")
        self.echo("  │  2. FLUJO CONCENTRADO (Shallow Flow) - cunetas, zanjas       │")
        self.echo("  │  3. FLUJO EN CANAL (Channel Flow) - arroyos, canales         │")
        self.echo("  └─────────────────────────────────────────────────────────────┘")

        # Configurar P2
        p2_mm = self._configure_p2()
        if p2_mm is None:
            return False

        segments = []

        while True:
            self.echo(f"\n  Segmentos definidos: {len(segments)}")
            if segments:
                self._show_segments_summary(segments)

            segment_choices = [
                "Agregar flujo laminar (sheet flow)",
                "Agregar flujo concentrado (shallow flow)",
                "Agregar flujo en canal (channel flow)",
            ]
            if segments:
                segment_choices.append("Terminar configuración")
            segment_choices.append("← Cancelar")

            choice = self.select("¿Qué tipo de segmento agregar?", segment_choices)

            if choice is None or "Cancelar" in choice:
                return False
            if "Terminar" in choice:
                break
            elif "laminar" in choice:
                segment = self._add_sheet_flow_segment(p2_mm)
                if segment:
                    segments.append(segment)
            elif "concentrado" in choice:
                segment = self._add_shallow_flow_segment()
                if segment:
                    segments.append(segment)
            elif "canal" in choice:
                segment = self._add_channel_flow_segment()
                if segment:
                    segments.append(segment)

        if not segments:
            self.warning("Debes agregar al menos un segmento")
            return False

        # Guardar en la base de datos
        from hidropluvial.database import get_database
        db = get_database()
        db.set_nrcs_segments(self.basin.id, segments, p2_mm)

        # Actualizar modelo en memoria
        self.basin.nrcs_segments = segments
        self.basin.p2_mm = p2_mm

        # Mostrar resumen
        tc_hr = nrcs_velocity_method(segments, p2_mm)
        self.echo("\n  ═══════════════════════════════════════════")
        self.echo("  RESUMEN MÉTODO NRCS")
        self.echo("  ───────────────────────────────────────────")
        self.echo(f"  Segmentos: {len(segments)}")
        self.echo(f"  P₂ (2 años, 24h): {p2_mm} mm")
        self.echo(f"  Tc calculado: {tc_hr * 60:.1f} min ({tc_hr:.2f} hr)")
        self.echo("  ═══════════════════════════════════════════")

        return True

    def _configure_p2(self) -> Optional[float]:
        """Configura P2 (precipitación 2 años, 24h) para flujo laminar."""
        self.echo("\n  El flujo laminar requiere P₂ (precipitación de 2 años, 24 horas).")

        # Estimar P2 desde P3,10 si está disponible
        p2_estimated = None
        if self.basin.p3_10:
            p2_estimated = self.basin.p3_10 * 0.5
            self.echo(f"  Estimación desde P3,10 = {self.basin.p3_10} mm:")
            self.echo(f"    P2,24h ≈ {p2_estimated:.1f} mm (factor 0.5)")

        p2_choices = []
        if p2_estimated:
            p2_choices.append(f"Usar estimado: {p2_estimated:.1f} mm")
        p2_choices.extend([
            "50 mm - Valor típico Uruguay",
            "40 mm - Zona semiárida",
            "60 mm - Zona húmeda",
            "Ingresar valor conocido",
            "← Cancelar",
        ])

        p2_choice = self.select("Precipitación P₂ (2 años, 24h):", p2_choices)

        if p2_choice is None or "Cancelar" in p2_choice:
            return None

        if "estimado" in p2_choice.lower():
            return p2_estimated
        elif "50 mm" in p2_choice:
            return 50.0
        elif "40 mm" in p2_choice:
            return 40.0
        elif "60 mm" in p2_choice:
            return 60.0
        elif "Ingresar" in p2_choice:
            val = self.text("Valor de P₂ (mm):", default="50")
            if val:
                try:
                    return float(val)
                except ValueError:
                    self.error("Valor inválido")
                    return None
        return 50.0

    def _add_sheet_flow_segment(self, p2_mm: float) -> Optional[SheetFlowSegment]:
        """Agrega un segmento de flujo laminar."""
        self.echo("\n  ── FLUJO LAMINAR (Sheet Flow) ──")
        self.echo("  Agua dispersa sobre superficie, típicamente primeros 30-100m")
        self.echo("  Longitud máxima: 100m\n")

        # Longitud
        length_str = self.text("Longitud del tramo (m, máx 100):", default="50")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0 or length > 100:
                self.error("Longitud debe estar entre 1 y 100 m")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        slope_str = self.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.3f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Coeficiente n
        self.echo("\n  Coeficientes de Manning para flujo laminar:")
        n_choices = [
            f"Superficie lisa (concreto, asfalto) - n = {SHEET_FLOW_N['smooth']:.3f}",
            f"Suelo desnudo/barbecho - n = {SHEET_FLOW_N['fallow']:.2f}",
            f"Pasto corto - n = {SHEET_FLOW_N['short_grass']:.2f}",
            f"Pasto denso - n = {SHEET_FLOW_N['dense_grass']:.2f}",
            f"Bosque ralo - n = {SHEET_FLOW_N['light_woods']:.2f}",
            f"Bosque denso - n = {SHEET_FLOW_N['dense_woods']:.2f}",
            "Ingresar valor personalizado",
        ]

        n_choice = self.select("Tipo de superficie:", n_choices)
        if not n_choice:
            return None

        if "lisa" in n_choice.lower():
            n_value = SHEET_FLOW_N["smooth"]
        elif "barbecho" in n_choice.lower():
            n_value = SHEET_FLOW_N["fallow"]
        elif "corto" in n_choice.lower():
            n_value = SHEET_FLOW_N["short_grass"]
        elif "denso" in n_choice.lower() and "pasto" in n_choice.lower():
            n_value = SHEET_FLOW_N["dense_grass"]
        elif "ralo" in n_choice.lower():
            n_value = SHEET_FLOW_N["light_woods"]
        elif "denso" in n_choice.lower():
            n_value = SHEET_FLOW_N["dense_woods"]
        else:
            n_str = self.text("Valor de n:", default="0.15")
            if not n_str:
                return None
            try:
                n_value = float(n_str)
            except ValueError:
                self.error("Valor inválido")
                return None

        segment = SheetFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            p2_mm=p2_mm,
        )
        self.success(f"Agregado: Flujo laminar L={length}m, n={n_value:.3f}, S={slope:.3f}")
        return segment

    def _add_shallow_flow_segment(self) -> Optional[ShallowFlowSegment]:
        """Agrega un segmento de flujo concentrado superficial."""
        self.echo("\n  ── FLUJO CONCENTRADO (Shallow Flow) ──")
        self.echo("  Escorrentía en cunetas, zanjas pequeñas, surcos\n")

        # Longitud
        length_str = self.text("Longitud del tramo (m):", default="200")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0:
                self.error("Longitud debe ser positiva")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        slope_str = self.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.3f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Tipo de superficie
        self.echo("\n  Velocidades según tipo de superficie:")
        surface_choices = [
            f"Pavimentado - k = {SHALLOW_FLOW_K['paved']:.2f} m/s",
            f"Sin pavimentar - k = {SHALLOW_FLOW_K['unpaved']:.2f} m/s",
            f"Con pasto - k = {SHALLOW_FLOW_K['grassed']:.2f} m/s",
            f"Pasto corto - k = {SHALLOW_FLOW_K['short_grass']:.2f} m/s",
        ]

        surface_choice = self.select("Tipo de superficie:", surface_choices)
        if not surface_choice:
            return None

        if "Pavimentado" in surface_choice:
            surface = "paved"
        elif "Sin pavimentar" in surface_choice:
            surface = "unpaved"
        elif "Con pasto" in surface_choice:
            surface = "grassed"
        else:
            surface = "short_grass"

        segment = ShallowFlowSegment(
            length_m=length,
            slope=slope,
            surface=surface,
        )
        self.success(f"Agregado: Flujo concentrado L={length}m, superficie={surface}")
        return segment

    def _add_channel_flow_segment(self) -> Optional[ChannelFlowSegment]:
        """Agrega un segmento de flujo en canal."""
        self.echo("\n  ── FLUJO EN CANAL (Channel Flow) ──")
        self.echo("  Arroyos, canales definidos, colectores\n")

        # Longitud
        length_str = self.text("Longitud del tramo (m):", default="500")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0:
                self.error("Longitud debe ser positiva")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.005 = 0.5%)")
        slope_str = self.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.4f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        # Coeficiente n de Manning
        self.echo("\n  Coeficientes de Manning para canales:")
        channel_n_choices = [
            "Canal de concreto liso - n = 0.013",
            "Canal de concreto revestido - n = 0.017",
            "Canal de tierra limpio - n = 0.022",
            "Canal de tierra con vegetación - n = 0.030",
            "Arroyo natural limpio - n = 0.035",
            "Arroyo con vegetación - n = 0.050",
            "Arroyo sinuoso con poza - n = 0.070",
            "Ingresar valor personalizado",
        ]

        n_choice = self.select("Tipo de canal:", channel_n_choices)
        if not n_choice:
            return None

        n_values = {
            "liso": 0.013,
            "revestido": 0.017,
            "limpio": 0.022,
            "tierra con": 0.030,
            "natural limpio": 0.035,
            "con vegetación": 0.050,
            "sinuoso": 0.070,
        }

        n_value = None
        for key, val in n_values.items():
            if key in n_choice.lower():
                n_value = val
                break

        if n_value is None:
            n_str = self.text("Valor de n:", default="0.035")
            if not n_str:
                return None
            try:
                n_value = float(n_str)
            except ValueError:
                self.error("Valor inválido")
                return None

        # Radio hidráulico
        self.echo("\n  Radio hidráulico R = Área / Perímetro mojado")
        self.echo("  Valores típicos: 0.3-0.5m (cunetas), 0.5-1.5m (canales), 1-3m (arroyos)")

        r_str = self.text("Radio hidráulico (m):", default="0.5")
        if not r_str:
            return None
        try:
            r_value = float(r_str)
            if r_value <= 0:
                self.error("Radio debe ser positivo")
                return None
        except ValueError:
            self.error("Valor inválido")
            return None

        segment = ChannelFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            hydraulic_radius_m=r_value,
        )
        self.success(f"Agregado: Canal L={length}m, n={n_value:.3f}, R={r_value}m")
        return segment

    def _show_segments_summary(self, segments: list) -> None:
        """Muestra resumen de segmentos configurados."""
        self.echo("  ┌───────────────────────────────────────────┐")
        for i, seg in enumerate(segments, 1):
            if isinstance(seg, SheetFlowSegment):
                self.echo(f"  │ {i}. Laminar: L={seg.length_m}m, n={seg.n:.3f}           │")
            elif isinstance(seg, ShallowFlowSegment):
                self.echo(f"  │ {i}. Concentrado: L={seg.length_m}m, {seg.surface}     │")
            elif isinstance(seg, ChannelFlowSegment):
                self.echo(f"  │ {i}. Canal: L={seg.length_m}m, n={seg.n:.3f}, R={seg.hydraulic_radius_m}m  │")
        self.echo("  └───────────────────────────────────────────┘")
