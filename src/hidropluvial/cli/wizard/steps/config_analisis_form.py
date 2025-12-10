"""
Paso del wizard para configuración de análisis usando formulario interactivo.

Combina:
- Método de escorrentía (C/CN)
- Métodos de Tc
- Tipo de tormenta
- Períodos de retorno
"""

from typing import Optional, List, Any

from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult
from hidropluvial.cli.viewer.form_viewer import (
    FormField,
    FieldType,
    FieldStatus,
)
from hidropluvial.cli.viewer.config_form import interactive_config_form


class StepConfigAnalisisForm(WizardStep):
    """Paso: Configuración del análisis en formulario interactivo."""

    @property
    def title(self) -> str:
        return "Configuración del Análisis"

    def execute(self) -> StepResult:
        # Determinar métodos de Tc disponibles según datos
        tc_options = self._get_tc_options()
        storm_options = self._get_storm_options()
        tr_options = self._get_tr_options()

        # Definir campos del formulario
        fields = [
            # Sección: Escorrentía
            FormField(
                key="metodo_escorrentia",
                label="Método de escorrentía",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=[
                    {"name": "Coeficiente C (racional)", "value": "C", "checked": True},
                    {"name": "Curva Número CN (SCS)", "value": "CN", "checked": False},
                ],
                hint="Selecciona uno o ambos métodos",
            ),
            FormField(
                key="coef_c",
                label="Coeficiente C",
                field_type=FieldType.SELECT,
                required=False,
                options=[
                    {"name": "Ingresar valor directo", "value": "direct"},
                    {"name": "Calcular ponderado (Ven Te Chow)", "value": "chow"},
                    {"name": "Calcular ponderado (FHWA)", "value": "fhwa"},
                    {"name": "Calcular ponderado (Uruguay)", "value": "uruguay"},
                ],
                default="direct",
                hint="Método para obtener C",
            ),
            FormField(
                key="curva_cn",
                label="Curva Número CN",
                field_type=FieldType.SELECT,
                required=False,
                options=[
                    {"name": "Ingresar valor directo", "value": "direct"},
                    {"name": "Calcular ponderado (NRCS)", "value": "nrcs"},
                ],
                default="direct",
                hint="Método para obtener CN",
            ),
            # Sección: Tiempo de concentración
            FormField(
                key="metodos_tc",
                label="Métodos de Tc",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=tc_options,
                hint="Métodos para calcular tiempo de concentración",
            ),
            FormField(
                key="t0_min",
                label="Tiempo t0 (Desbordes)",
                field_type=FieldType.SELECT,
                required=False,
                options=[
                    {"name": "5 min - Típico", "value": 5.0},
                    {"name": "3 min - Muy urbanizado", "value": 3.0},
                    {"name": "10 min - Rural", "value": 10.0},
                    {"name": "Ingresar valor personalizado", "value": "custom"},
                ],
                default=5.0,
                hint="Tiempo de entrada inicial para método Desbordes",
            ),
            # Sección: Tormenta
            FormField(
                key="tipos_tormenta",
                label="Tipos de tormenta",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=storm_options,
                hint="Distribuciones temporales a analizar",
            ),
            FormField(
                key="periodos_retorno",
                label="Períodos de retorno",
                field_type=FieldType.CHECKBOX,
                required=True,
                options=tr_options,
                hint="Años de período de retorno",
            ),
            # Intervalo de tiempo
            FormField(
                key="dt_min",
                label="Intervalo dt",
                field_type=FieldType.SELECT,
                required=True,
                options=[
                    {"name": "5 min - Estándar", "value": 5},
                    {"name": "10 min - Tormentas largas", "value": 10},
                    {"name": "15 min - NRCS/TR-55", "value": 15},
                    {"name": "Ingresar valor personalizado", "value": "custom"},
                ],
                default=5,
                hint="Intervalo de discretización del hietograma",
            ),
        ]

        # Definir dependencias
        dependencies = {
            "coef_c": ("metodo_escorrentia", ["C"]),
            "curva_cn": ("metodo_escorrentia", ["CN"]),
            "t0_min": ("metodos_tc", ["desbordes"]),
        }

        # Mostrar formulario interactivo
        result = interactive_config_form(
            title="Configuración del Análisis",
            fields=fields,
            state=self.state,
            dependencies=dependencies,
        )

        if result is False:
            # Usuario quiere volver atrás
            return StepResult.BACK

        if result is None:
            return StepResult.CANCEL

        # Procesar resultados y guardar en estado
        return self._process_results(result)

    def _get_tc_options(self) -> List[dict]:
        """Obtiene opciones de Tc según datos disponibles."""
        options = []

        # Desbordes: requiere C (del estado actual O que se seleccione método C)
        # Dependencia OR: C existe en state O usuario selecciona método C
        has_c = self.state.c is not None
        options.append({
            "name": f"Desbordes (urbano){' - C=' + f'{self.state.c:.2f}' if has_c else ''}",
            "value": "desbordes",
            "checked": has_c,
            # Dependencia: disponible si C existe en state O si se selecciona método C
            "depends_on": ("_or", [
                ("_state.c", [True]),  # C ya existe en el state
                ("metodo_escorrentia", ["C"]),  # O se va a calcular C
            ]),
            "disabled_hint": "seleccionar método C en escorrentía",
        })

        # Kirpich y Temez: requieren longitud
        if self.state.length_m:
            options.append({
                "name": f"Kirpich (rural) - L={self.state.length_m:.0f}m",
                "value": "kirpich",
                "checked": not has_c,
            })
            options.append({
                "name": f"Temez - L={self.state.length_m:.0f}m",
                "value": "temez",
                "checked": False,
            })

        # NRCS siempre disponible
        options.append({
            "name": "NRCS TR-55 (velocidades)",
            "value": "nrcs",
            "checked": False,
        })

        return options

    def _get_storm_options(self) -> List[dict]:
        """Obtiene opciones de tormenta."""
        return [
            {"name": "GZ (6h) - drenaje urbano", "value": "gz", "checked": True},
            {"name": "Bloques alternantes", "value": "blocks", "checked": False},
            {"name": "Bloques 24h", "value": "blocks24", "checked": False},
            {"name": "SCS Tipo II (24h)", "value": "scs_ii", "checked": False},
            {"name": "Huff Q2", "value": "huff_q2", "checked": False},
            {"name": "Bimodal (doble pico)", "value": "bimodal", "checked": False},
        ]

    def _get_tr_options(self) -> List[dict]:
        """Obtiene opciones de período de retorno."""
        return [
            {"name": "2 años", "value": 2, "checked": True},
            {"name": "5 años", "value": 5, "checked": False},
            {"name": "10 años", "value": 10, "checked": True},
            {"name": "25 años", "value": 25, "checked": True},
            {"name": "50 años", "value": 50, "checked": False},
            {"name": "100 años", "value": 100, "checked": False},
        ]

    def _process_results(self, result: dict) -> StepResult:
        """Procesa los resultados del formulario y actualiza el estado."""
        # Métodos de escorrentía
        metodos_esc = result.get("metodo_escorrentia", [])
        usar_c = "C" in metodos_esc
        usar_cn = "CN" in metodos_esc

        # Obtener C si corresponde
        if usar_c:
            metodo_c = result.get("coef_c", "direct")
            if metodo_c == "direct":
                c_result = self._collect_c_direct()
                if c_result is None:
                    return StepResult.BACK
                self.state.c = c_result
            else:
                c_result = self._collect_c_weighted(metodo_c)
                if c_result is None:
                    return StepResult.BACK
                self.state.c = c_result

        # Obtener CN si corresponde
        if usar_cn:
            metodo_cn = result.get("curva_cn", "direct")
            if metodo_cn == "direct":
                cn_result = self._collect_cn_direct()
                if cn_result is None:
                    return StepResult.BACK
                self.state.cn = cn_result
            else:
                cn_result = self._collect_cn_weighted()
                if cn_result is None:
                    return StepResult.BACK
                self.state.cn = cn_result

        # Métodos de Tc
        tc_methods = result.get("metodos_tc", [])
        self.state.tc_methods = [self._tc_value_to_name(m) for m in tc_methods]

        # t0 para Desbordes
        if "desbordes" in tc_methods:
            t0_val = result.get("t0_min", 5.0)
            if t0_val == "custom":
                t0_result = self._collect_custom_t0()
                if t0_result is None:
                    return StepResult.BACK
                self.state.t0_min = t0_result
            else:
                self.state.t0_min = t0_val

        # Tipos de tormenta
        self.state.storm_codes = result.get("tipos_tormenta", ["gz"])

        # Períodos de retorno
        self.state.return_periods = result.get("periodos_retorno", [2, 10, 25])

        # dt
        dt_val = result.get("dt_min", 5)
        if dt_val == "custom":
            dt_result = self._collect_custom_dt()
            if dt_result is None:
                return StepResult.BACK
            self.state.dt_min = dt_result
        else:
            self.state.dt_min = dt_val

        # Configuraciones adicionales
        if "gz" in self.state.storm_codes:
            self._collect_x_factors()

        return StepResult.NEXT

    def _tc_value_to_name(self, value: str) -> str:
        """Convierte valor de Tc a nombre para compatibilidad."""
        mapping = {
            "desbordes": "Desbordes (recomendado cuencas urbanas)",
            "kirpich": "Kirpich (cuencas rurales)",
            "temez": "Temez",
            "nrcs": "NRCS (método de velocidades TR-55)",
        }
        return mapping.get(value, value)

    def _collect_c_direct(self) -> Optional[float]:
        """Recolecta C directo."""
        from hidropluvial.cli.wizard.styles import validate_range

        self.suggestion("C típicos: Urbano denso 0.7-0.9, Residencial 0.4-0.7, Rural 0.2-0.4")
        res, c_val = self.text(
            "Coeficiente de escorrentía C (0.1-0.95):",
            validate=lambda x: validate_range(x, 0.1, 0.95),
        )
        if res != StepResult.NEXT or not c_val:
            return None
        return float(c_val)

    def _collect_c_weighted(self, table_key: str) -> Optional[float]:
        """Recolecta C ponderado usando visor interactivo."""
        from hidropluvial.core.coefficients import (
            C_TABLES, ChowCEntry, FHWACEntry, weighted_c
        )
        from hidropluvial.cli.viewer.coverage_viewer import (
            interactive_coverage_viewer, CoverageRow
        )
        from hidropluvial.cli.theme import print_coverage_assignments_table

        table_name, table_data = C_TABLES[table_key]
        first_entry = table_data[0]
        is_chow = isinstance(first_entry, ChowCEntry)
        is_fhwa = isinstance(first_entry, FHWACEntry)

        def get_c_value(entry):
            if is_chow:
                return entry.c_tr2
            elif is_fhwa:
                return entry.c_base
            return entry.c_recommended

        rows = []
        for i, entry in enumerate(table_data):
            c_val = get_c_value(entry)
            rows.append(CoverageRow(
                index=i,
                category=entry.category,
                description=entry.description,
                value=c_val,
                value_label="C",
            ))

        coverage_data = interactive_coverage_viewer(
            rows=rows,
            total_area=self.state.area_ha,
            value_label="C",
            table_name=f"Tabla {table_name}",
        )

        if not coverage_data:
            return None

        areas = [d["area"] for d in coverage_data]
        coefficients = [d["c_val"] for d in coverage_data]
        c_weighted = weighted_c(areas, coefficients)

        print_coverage_assignments_table(
            coverage_data, self.state.area_ha, "C", c_weighted,
            title="Resultado Final"
        )

        return c_weighted

    def _collect_cn_direct(self) -> Optional[int]:
        """Recolecta CN directo."""
        from hidropluvial.cli.wizard.styles import validate_range

        self.suggestion("CN típicos: Urbano 85-95, Residencial 70-85, Bosque 55-70")
        res, cn_val = self.text(
            "Curva Número CN (30-98):",
            validate=lambda x: validate_range(x, 30, 98),
        )
        if res != StepResult.NEXT or not cn_val:
            return None
        return int(round(float(cn_val)))

    def _collect_cn_weighted(self) -> Optional[int]:
        """Recolecta CN ponderado usando visor interactivo."""
        from hidropluvial.core.coefficients import CN_TABLES, weighted_cn
        from hidropluvial.cli.viewer.coverage_viewer import (
            interactive_coverage_viewer, CoverageRow
        )
        from hidropluvial.cli.theme import print_coverage_assignments_table

        table_name, table_data = CN_TABLES["unified"]

        rows = []
        for i, entry in enumerate(table_data):
            cn_b = entry.get_cn("B")
            cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
            rows.append(CoverageRow(
                index=i,
                category=entry.category,
                description=f"{entry.description}{cond}",
                value=cn_b,
                value_label="CN",
            ))

        def get_cn_for_soil(idx: int, soil_group: str) -> int:
            return table_data[idx].get_cn(soil_group)

        coverage_data = interactive_coverage_viewer(
            rows=rows,
            total_area=self.state.area_ha,
            value_label="CN",
            table_name=f"Tabla {table_name}",
            on_get_cn_for_soil=get_cn_for_soil,
        )

        if not coverage_data:
            return None

        cn_weighted = weighted_cn(
            [d["area"] for d in coverage_data],
            [d["cn_val"] for d in coverage_data]
        )

        print_coverage_assignments_table(
            coverage_data, self.state.area_ha, "CN", cn_weighted,
            title="Resultado Final"
        )

        return int(round(cn_weighted))

    def _collect_custom_t0(self) -> Optional[float]:
        """Recolecta t0 personalizado."""
        from hidropluvial.cli.wizard.styles import validate_range

        self.suggestion("t0 típico: 3-10 min según urbanización")
        res, t0_val = self.text(
            "Tiempo de entrada t0 (minutos, 1-30):",
            validate=lambda x: validate_range(x, 1, 30),
            default="5",
        )
        if res != StepResult.NEXT or not t0_val:
            return None
        return float(t0_val)

    def _collect_custom_dt(self) -> Optional[float]:
        """Recolecta dt personalizado."""
        from hidropluvial.cli.wizard.styles import validate_range

        self.suggestion("dt recomendado: 5-15 min (mínimo 5 para evitar picos irreales)")
        res, dt_val = self.text(
            "Intervalo dt (minutos, 5-30):",
            validate=lambda x: validate_range(x, 5, 30),
            default="5",
        )
        if res != StepResult.NEXT or not dt_val:
            return None
        return float(dt_val)

    def _collect_x_factors(self) -> None:
        """Recolecta factores X para GZ usando panel interactivo."""
        from hidropluvial.cli.theme import print_x_factor_table

        print_x_factor_table()

        res, x_selected = self.checkbox(
            "Valores de X a analizar:",
            choices=[
                {"name": "1.00 - Método racional", "value": 1.0, "checked": True},
                {"name": "1.25 - Urbano alta pendiente", "value": 1.25, "checked": True},
                {"name": "1.67 - Método NRCS", "value": 1.67, "checked": False},
                {"name": "2.25 - Uso mixto", "value": 2.25, "checked": False},
                {"name": "3.33 - Rural sinuoso", "value": 3.33, "checked": False},
                {"name": "5.50 - Rural pend. baja", "value": 5.5, "checked": False},
            ],
        )

        if res == StepResult.NEXT and x_selected:
            self.state.x_factors = x_selected
        else:
            self.state.x_factors = [1.0, 1.25]
