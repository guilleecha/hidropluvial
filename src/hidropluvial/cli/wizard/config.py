"""
WizardConfig - Recolecta datos de cuenca y parametros de analisis.
"""

from dataclasses import dataclass, field
from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import (
    WIZARD_STYLE,
    validate_positive_float,
    validate_range,
)


@dataclass
class WizardConfig:
    """Configuracion recolectada por el wizard."""

    # Datos de cuenca
    nombre: str = ""
    area_ha: float = 0.0
    slope_pct: float = 0.0
    p3_10: float = 0.0
    c: Optional[float] = None
    cn: Optional[int] = None
    length_m: Optional[float] = None

    # Datos de ponderación (para recálculo por Tr)
    c_weighted_data: Optional[dict] = None  # {table_key, items con table_index}

    # Parámetros avanzados
    amc: str = "II"  # Condición de humedad antecedente: I, II, III
    lambda_coef: float = 0.2  # Coeficiente lambda para abstracción inicial
    t0_min: float = 5.0  # Tiempo de entrada inicial para Desbordes

    # Parametros de analisis
    tc_methods: list[str] = field(default_factory=list)
    storm_codes: list[str] = field(default_factory=lambda: ["gz"])
    return_periods: list[int] = field(default_factory=list)
    x_factors: list[float] = field(default_factory=lambda: [1.0])

    # Salida
    output_name: Optional[str] = None

    @classmethod
    def from_wizard(cls) -> Optional["WizardConfig"]:
        """Recolecta datos interactivamente con navegación."""
        from hidropluvial.cli.wizard.steps import WizardNavigator

        navigator = WizardNavigator()
        state = navigator.run()

        if state is None:
            return None

        # Convertir WizardState a WizardConfig
        config = cls(
            nombre=state.nombre,
            area_ha=state.area_ha,
            slope_pct=state.slope_pct,
            p3_10=state.p3_10,
            c=state.c,
            cn=state.cn,
            length_m=state.length_m,
            c_weighted_data=state.c_weighted_data,
            amc=state.amc,
            lambda_coef=state.lambda_coef,
            t0_min=state.t0_min,
            tc_methods=state.tc_methods,
            storm_codes=state.storm_codes,
            return_periods=state.return_periods,
            x_factors=state.x_factors,
            output_name=state.output_name,
        )

        return config

    @classmethod
    def from_wizard_legacy(cls) -> Optional["WizardConfig"]:
        """Recolecta datos interactivamente (versión sin navegación)."""
        config = cls()

        if not config._collect_cuenca_data():
            return None

        if not config._collect_tc_methods():
            return None

        if not config._collect_storm_params():
            return None

        if not config._collect_output_params():
            return None

        return config

    def _collect_cuenca_data(self) -> bool:
        """Recolecta datos de la cuenca."""
        typer.echo("\n-- Datos de la Cuenca --\n")

        # Nombre
        self.nombre = questionary.text(
            "Nombre de la cuenca:",
            validate=lambda x: len(x) > 0 or "El nombre no puede estar vacio",
            style=WIZARD_STYLE,
        ).ask()

        if self.nombre is None:
            return False

        # Area
        area = questionary.text(
            "Area de la cuenca (ha):",
            validate=validate_positive_float,
            style=WIZARD_STYLE,
        ).ask()

        if area is None:
            return False
        self.area_ha = float(area)

        # Pendiente
        slope = questionary.text(
            "Pendiente media (%):",
            validate=validate_positive_float,
            style=WIZARD_STYLE,
        ).ask()

        if slope is None:
            return False
        self.slope_pct = float(slope)

        # P3,10
        typer.echo("\n  Tip: Consulta la tabla IDF de DINAGUA para tu estacion")
        p3_10 = questionary.text(
            "Precipitacion P(3h, Tr=10) en mm:",
            validate=validate_positive_float,
            style=WIZARD_STYLE,
        ).ask()

        if p3_10 is None:
            return False
        self.p3_10 = float(p3_10)

        # Metodo de escorrentia
        metodo_esc = questionary.select(
            "Metodo de escorrentia:",
            choices=[
                "Coeficiente C (racional/GZ) - drenaje urbano",
                "Curva Numero CN (SCS) - cuencas rurales/mixtas",
                "Ambos (C y CN) - comparar metodologias",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if metodo_esc is None:
            return False

        if "Coeficiente C" in metodo_esc or "Ambos" in metodo_esc:
            self.c = self._collect_c_value()
            if self.c is None and "Ambos" not in metodo_esc:
                return False

        if "Curva Numero" in metodo_esc or "Ambos" in metodo_esc:
            self.cn = self._collect_cn_value()
            if self.cn is None and "Ambos" not in metodo_esc:
                return False

        # Verificar que al menos uno fue ingresado
        if self.c is None and self.cn is None:
            typer.echo("  Error: Debes ingresar al menos C o CN")
            return False

        # Longitud del cauce (opcional)
        tiene_longitud = questionary.confirm(
            "Conoces la longitud del cauce principal?",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

        if tiene_longitud:
            length = questionary.text(
                "Longitud del cauce (m):",
                validate=validate_positive_float,
                style=WIZARD_STYLE,
            ).ask()
            if length:
                self.length_m = float(length)

        return True

    def _collect_tc_methods(self) -> bool:
        """Recolecta metodos de tiempo de concentracion."""
        typer.echo("\n-- Tiempo de Concentracion --\n")

        tc_choices = []
        if self.c:
            tc_choices.append(questionary.Choice("Desbordes (recomendado cuencas urbanas)", checked=True))
        if self.length_m:
            tc_choices.append(questionary.Choice("Kirpich (cuencas rurales)", checked=self.c is None))
            tc_choices.append(questionary.Choice("Temez", checked=False))

        if not tc_choices:
            typer.echo("  Se necesita longitud de cauce o coeficiente C para calcular Tc")
            return False

        tc_methods = questionary.checkbox(
            "Metodos de Tc a calcular:",
            choices=tc_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not tc_methods:
            typer.echo("  Debes seleccionar al menos un metodo de Tc")
            return False

        self.tc_methods = tc_methods
        return True

    def _collect_storm_params(self) -> bool:
        """Recolecta parametros de tormenta."""
        typer.echo("\n-- Tormenta de Diseno --\n")

        storm_choices = [
            questionary.Choice("GZ (6 horas) - recomendado drenaje urbano", checked=True),
            questionary.Choice("Bloques alternantes - duracion segun Tc", checked=False),
            questionary.Choice("Bloques 24 horas - obras mayores", checked=False),
        ]

        storm_types = questionary.checkbox(
            "Tipos de tormenta a analizar:",
            choices=storm_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not storm_types:
            typer.echo("  Debes seleccionar al menos un tipo de tormenta")
            return False

        # Convertir a codigos
        self.storm_codes = []
        for storm_type in storm_types:
            if "GZ" in storm_type:
                self.storm_codes.append("gz")
            elif "Bloques alternantes" in storm_type:
                self.storm_codes.append("blocks")
            elif "24 horas" in storm_type:
                self.storm_codes.append("blocks24")

        # Periodos de retorno
        tr_choices = [
            questionary.Choice("2 anos", checked=True),
            questionary.Choice("5 anos", checked=False),
            questionary.Choice("10 anos", checked=True),
            questionary.Choice("25 anos", checked=True),
            questionary.Choice("50 anos", checked=False),
            questionary.Choice("100 anos", checked=False),
        ]

        return_periods = questionary.checkbox(
            "Periodos de retorno a analizar:",
            choices=tr_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not return_periods:
            typer.echo("  Debes seleccionar al menos un periodo de retorno")
            return False

        # Parsear periodos
        self.return_periods = [int(tr.split()[0]) for tr in return_periods]

        # Factor X morfologico para GZ
        if "gz" in self.storm_codes:
            typer.echo("\n  Factor X morfologico (forma del hidrograma triangular):")
            typer.echo("    X=1.00  Metodo racional (respuesta rapida)")
            typer.echo("    X=1.25  Areas urbanas con pendiente")
            typer.echo("    X=1.67  Metodo SCS/NRCS")
            typer.echo("    X=2.25+ Cuencas rurales/mixtas\n")

            x_choices = [
                questionary.Choice("1.00 - Metodo racional", checked=True),
                questionary.Choice("1.25 - Urbano con pendiente", checked=True),
                questionary.Choice("1.67 - SCS/NRCS", checked=False),
                questionary.Choice("2.25 - Uso mixto rural/urbano", checked=False),
            ]

            x_selected = questionary.checkbox(
                "Valores de X a analizar:",
                choices=x_choices,
                style=WIZARD_STYLE,
            ).ask()

            if x_selected:
                self.x_factors = [float(x.split(" - ")[0]) for x in x_selected]

            if not self.x_factors:
                self.x_factors = [1.0]

        return True

    def _collect_output_params(self) -> bool:
        """Recolecta parametros de salida."""
        typer.echo("\n-- Salida --\n")

        generar_reporte = questionary.confirm(
            "Generar reporte LaTeX?",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

        if generar_reporte:
            default_name = self.nombre.lower().replace(" ", "_")
            self.output_name = questionary.text(
                "Nombre del archivo (sin extension):",
                default=default_name,
                style=WIZARD_STYLE,
            ).ask()

        return True

    def get_n_combinations(self) -> int:
        """Calcula numero total de combinaciones."""
        n_tc = len(self.tc_methods)
        n_tr = len(self.return_periods)
        n_storms = len(self.storm_codes)
        # X solo aplica para tormentas GZ
        n_x = len(self.x_factors) if "gz" in self.storm_codes else 1
        n_non_gz = len([s for s in self.storm_codes if s != "gz"])
        n_gz = 1 if "gz" in self.storm_codes else 0
        return n_tc * n_tr * (n_gz * n_x + n_non_gz)

    def print_summary(self) -> None:
        """Imprime resumen de configuracion."""
        n_total = self.get_n_combinations()
        n_tc = len(self.tc_methods)
        n_tr = len(self.return_periods)
        n_storms = len(self.storm_codes)
        n_x = len(self.x_factors) if "gz" in self.storm_codes else 1

        typer.echo("\n-- Resumen --\n")
        typer.echo(f"  Cuenca:      {self.nombre}")
        typer.echo(f"  Area:        {self.area_ha} ha")
        typer.echo(f"  Pendiente:   {self.slope_pct} %")
        typer.echo(f"  P(3h,Tr10):  {self.p3_10} mm")
        if self.c:
            typer.echo(f"  Coef. C:     {self.c}")
        if self.cn:
            typer.echo(f"  Curva CN:    {self.cn}")
        if self.length_m:
            typer.echo(f"  Longitud:    {self.length_m} m")
        typer.echo(f"  Metodos Tc:  {', '.join(self.tc_methods)}")
        typer.echo(f"  Tormentas:   {', '.join(self.storm_codes)}")
        typer.echo(f"  Tr:          {', '.join(str(tr) for tr in self.return_periods)} anos")
        if "gz" in self.storm_codes:
            typer.echo(f"  Factor X:    {', '.join(f'{x:.2f}' for x in self.x_factors)}")

        typer.echo(f"\n  => Se generaran {n_total} analisis ({n_tc} Tc x {n_tr} Tr x {n_storms} tormentas)")

    def _collect_c_value(self) -> Optional[float]:
        """Recolecta coeficiente C (manual o ponderado)."""
        typer.echo("\n-- Coeficiente de Escorrentia C --\n")

        metodo = questionary.select(
            "Como deseas obtener C?",
            choices=[
                "Ingresar valor directamente",
                "Calcular C ponderado por coberturas (Ven Te Chow)",
                "Calcular C ponderado por coberturas (FHWA)",
                "Calcular C ponderado por coberturas (Tabla Uruguay)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if metodo is None:
            return None

        if "directamente" in metodo:
            typer.echo("  Tip: C tipicos -> Urbano denso: 0.7-0.9, Residencial: 0.4-0.7, Rural: 0.2-0.4")
            c_value = questionary.text(
                "Coeficiente de escorrentia C (0.1-0.95):",
                validate=lambda x: validate_range(x, 0.1, 0.95),
                style=WIZARD_STYLE,
            ).ask()
            if c_value is None:
                return None
            return float(c_value)
        else:
            # Calcular ponderado
            if "Chow" in metodo:
                table_key = "chow"
            elif "FHWA" in metodo:
                table_key = "fhwa"
            else:
                table_key = "uruguay"

            return self._calculate_weighted_c(table_key)

    def _calculate_weighted_c(self, table_key: str) -> Optional[float]:
        """Calcula C ponderado interactivamente y guarda datos para recálculo."""
        from hidropluvial.core.coefficients import (
            C_TABLES, ChowCEntry, FHWACEntry, weighted_c
        )
        from hidropluvial.cli.theme import (
            print_c_table_chow, print_c_table_fhwa, print_c_table_simple, print_info
        )

        table_name, table_data = C_TABLES[table_key]
        first_entry = table_data[0]
        is_chow = isinstance(first_entry, ChowCEntry)
        is_fhwa = isinstance(first_entry, FHWACEntry)

        # Para tabla Ven Te Chow: SIEMPRE usar Tr=2 como base
        # Para FHWA: usar Tr base (<=10)
        tr = 2 if is_chow else 10

        if is_chow:
            print_c_table_chow(table_data, table_name, selection_mode=True)
        elif is_fhwa:
            print_c_table_fhwa(table_data, table_name, tr=tr)
        else:
            print_c_table_simple(table_data, table_name)

        print_info(f"Área de la cuenca: {self.area_ha} ha")
        typer.echo("  Asigna coberturas. Presiona Enter sin valor para terminar.\n")

        # Guardamos áreas, coeficientes e índices de tabla
        coverage_data = []  # Lista de {area, c_val, table_index, description}
        area_remaining = self.area_ha

        while area_remaining > 0.001:
            typer.echo(f"  Area restante: {area_remaining:.3f} ha ({area_remaining/self.area_ha*100:.1f}%)")

            # Construir choices - para Chow siempre mostrar C(Tr2)
            choices = []
            for i, e in enumerate(table_data):
                if is_chow:
                    c_val = e.c_tr2  # Siempre Tr2
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f} para Tr2)")
                elif is_fhwa:
                    c_val = e.c_base  # C base
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")
                else:
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={e.c_recommended:.2f})")

            choices.append("Asignar area restante a una cobertura")
            choices.append("Terminar")

            selection = questionary.select(
                "Selecciona cobertura:",
                choices=choices,
                style=WIZARD_STYLE,
            ).ask()

            if selection is None or "Terminar" in selection:
                break

            if "Asignar area" in selection:
                cov_choices = []
                for i, e in enumerate(table_data):
                    if is_chow:
                        c_val = e.c_tr2
                    elif is_fhwa:
                        c_val = e.c_base
                    else:
                        c_val = e.c_recommended
                    cov_choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")

                cov_selection = questionary.select(
                    "Cobertura para area restante:",
                    choices=cov_choices,
                    style=WIZARD_STYLE,
                ).ask()

                if cov_selection:
                    idx = int(cov_selection.split(".")[0]) - 1
                    entry = table_data[idx]
                    if is_chow:
                        c_val = entry.c_tr2
                    elif is_fhwa:
                        c_val = entry.c_base
                    else:
                        c_val = entry.c_recommended
                    coverage_data.append({
                        "area": area_remaining,
                        "c_val": c_val,
                        "table_index": idx,
                        "description": f"{entry.category}: {entry.description}",
                    })
                    area_remaining = 0
                break

            # Obtener indice
            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]

            area_str = questionary.text(
                f"Area (ha, max {area_remaining:.3f}):",
                validate=lambda x: self._validate_area_input(x, area_remaining),
                style=WIZARD_STYLE,
            ).ask()

            if area_str is None or area_str.strip() == "":
                break

            area_val = float(area_str)
            if area_val > 0:
                if is_chow:
                    c_val = entry.c_tr2
                elif is_fhwa:
                    c_val = entry.c_base
                else:
                    c_val = entry.c_recommended
                coverage_data.append({
                    "area": area_val,
                    "c_val": c_val,
                    "table_index": idx,
                    "description": f"{entry.category}: {entry.description}",
                })
                area_remaining -= area_val
                typer.echo(f"  + {area_val:.3f} ha con C={c_val:.2f}")

        if not coverage_data:
            typer.echo("  No se asignaron coberturas.")
            return None

        # Calcular C ponderado
        areas = [d["area"] for d in coverage_data]
        coefficients = [d["c_val"] for d in coverage_data]
        c_weighted = weighted_c(areas, coefficients)

        # Guardar datos de ponderación para recálculo por Tr
        self.c_weighted_data = {
            "table_key": table_key,
            "base_tr": tr,
            "items": coverage_data,
        }

        if is_chow:
            typer.echo(f"\n  => C ponderado (Tr2) = {c_weighted:.3f}")
            typer.echo("     Este valor se ajustara segun el Tr de cada analisis.")
        else:
            typer.echo(f"\n  => C ponderado = {c_weighted:.3f}")

        return c_weighted

    def _collect_cn_value(self) -> Optional[int]:
        """Recolecta Curva Numero CN (manual o ponderada)."""
        typer.echo("\n-- Curva Numero CN --\n")

        metodo = questionary.select(
            "Como deseas obtener CN?",
            choices=[
                "Ingresar valor directamente",
                "Calcular CN ponderado por coberturas (tablas NRCS)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if metodo is None:
            return None

        if "directamente" in metodo:
            typer.echo("  Tip: CN tipicos -> Urbano: 85-95, Residencial: 70-85, Bosque: 55-70")
            cn_value = questionary.text(
                "Curva Numero CN (30-98):",
                validate=lambda x: validate_range(x, 30, 98),
                style=WIZARD_STYLE,
            ).ask()
            if cn_value is None:
                return None
            return int(round(float(cn_value)))
        else:
            return self._calculate_weighted_cn()

    def _calculate_weighted_cn(self) -> Optional[int]:
        """Calcula CN ponderado interactivamente, permitiendo mezclar tablas."""
        from hidropluvial.core.coefficients import CN_TABLES, weighted_cn
        from hidropluvial.cli.theme import print_cn_table

        # Solicitar grupo de suelo
        soil = questionary.select(
            "Grupo hidrologico de suelo:",
            choices=[
                "A - Alta infiltracion (arena, grava)",
                "B - Moderada infiltracion (limo arenoso)",
                "C - Baja infiltracion (limo arcilloso)",
                "D - Muy baja infiltracion (arcilla)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if soil is None:
            return None

        soil_group = soil[0]  # Primera letra

        typer.echo(f"\n  Grupo de suelo: {soil_group}")
        typer.echo(f"  Area de la cuenca: {self.area_ha} ha")
        typer.echo("  Puedes mezclar coberturas urbanas y agricolas.\n")

        areas = []
        cn_values = []
        area_remaining = self.area_ha
        current_table = None

        while area_remaining > 0.001:
            typer.echo(f"\n  Area restante: {area_remaining:.3f} ha ({area_remaining/self.area_ha*100:.1f}%)")

            # Elegir tabla o accion
            table_choice = questionary.select(
                "Agregar cobertura de:",
                choices=[
                    "Tabla Urbana (residencial, comercial, industrial)",
                    "Tabla Agricola (cultivos, pasturas, bosque)",
                    "Asignar todo el area restante",
                    "Terminar",
                ],
                style=WIZARD_STYLE,
            ).ask()

            if table_choice is None or "Terminar" in table_choice:
                break

            if "Asignar todo" in table_choice:
                # Elegir tabla para area restante
                final_table = questionary.select(
                    "De que tabla?",
                    choices=["Urbana", "Agricola"],
                    style=WIZARD_STYLE,
                ).ask()

                if final_table is None:
                    break

                table_key = "urban" if "Urbana" in final_table else "agricultural"
                _, table_data = CN_TABLES[table_key]

                cov_choices = []
                for i, e in enumerate(table_data):
                    cn = e.get_cn(soil_group)
                    cond = f" ({e.condition})" if e.condition != "N/A" else ""
                    cov_choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

                cov_selection = questionary.select(
                    "Cobertura para area restante:",
                    choices=cov_choices,
                    style=WIZARD_STYLE,
                ).ask()

                if cov_selection:
                    idx = int(cov_selection.split(".")[0]) - 1
                    entry = table_data[idx]
                    cn = entry.get_cn(soil_group)
                    areas.append(area_remaining)
                    cn_values.append(cn)
                    area_remaining = 0
                break

            # Determinar tabla seleccionada
            if "Urbana" in table_choice:
                table_key = "urban"
                table_name, table_data = CN_TABLES["urban"]
            else:
                table_key = "agricultural"
                table_name, table_data = CN_TABLES["agricultural"]

            # Mostrar tabla si cambio
            if current_table != table_key:
                print_cn_table(table_data, table_name)
                current_table = table_key

            # Seleccionar cobertura de la tabla elegida
            choices = []
            for i, e in enumerate(table_data):
                cn = e.get_cn(soil_group)
                cond = f" ({e.condition})" if e.condition != "N/A" else ""
                choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

            choices.append("Volver (elegir otra tabla)")

            selection = questionary.select(
                "Selecciona cobertura:",
                choices=choices,
                style=WIZARD_STYLE,
            ).ask()

            if selection is None or "Volver" in selection:
                continue

            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]
            cn = entry.get_cn(soil_group)

            area_str = questionary.text(
                f"Area para '{entry.description}' (ha, max {area_remaining:.3f}):",
                validate=lambda x: self._validate_area_input(x, area_remaining),
                style=WIZARD_STYLE,
            ).ask()

            if area_str is None or area_str.strip() == "":
                continue

            area_val = float(area_str)
            if area_val > 0:
                areas.append(area_val)
                cn_values.append(cn)
                area_remaining -= area_val
                typer.echo(f"  + {area_val:.3f} ha con CN={cn}")

        if not areas:
            typer.echo("  No se asignaron coberturas.")
            return None

        cn_weighted = weighted_cn(areas, cn_values)
        cn_rounded = int(round(cn_weighted))
        typer.echo(f"\n  => CN ponderado = {cn_weighted:.1f} -> {cn_rounded}")
        return cn_rounded

    def _validate_area_input(self, value: str, max_area: float) -> bool | str:
        """Valida entrada de area."""
        if value.strip() == "":
            return True
        try:
            v = float(value)
            if v < 0:
                return "El area no puede ser negativa"
            if v > max_area:
                return f"El area no puede exceder {max_area:.3f} ha"
            return True
        except ValueError:
            return "Debe ser un numero valido"
