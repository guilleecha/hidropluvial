"""
Pasos del wizard para tiempo de concentración y tormentas.
"""

import questionary

from hidropluvial.cli.wizard.styles import validate_positive_float
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult
from hidropluvial.cli.wizard.steps.nrcs_config import NRCSConfigMixin


class StepMetodosTc(NRCSConfigMixin, WizardStep):
    """Paso: Métodos de tiempo de concentración."""

    @property
    def title(self) -> str:
        return "Tiempo de Concentración"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        tc_choices = []
        if self.state.c:
            tc_choices.append(questionary.Choice("Desbordes (recomendado cuencas urbanas)", checked=True))
        if self.state.length_m:
            tc_choices.append(questionary.Choice("Kirpich (cuencas rurales)", checked=self.state.c is None))
            tc_choices.append(questionary.Choice("Temez", checked=False))
        # NRCS siempre disponible (usa segmentos propios)
        tc_choices.append(questionary.Choice("NRCS (método de velocidades TR-55)", checked=False))

        if not tc_choices:
            self.echo("  Se necesita longitud de cauce o coeficiente C para calcular Tc")
            return StepResult.BACK

        res, tc_methods = self.checkbox("Métodos de Tc a calcular:", tc_choices)

        if res != StepResult.NEXT:
            return res

        if not tc_methods:
            self.echo("  Debes seleccionar al menos un método de Tc")
            return self.execute()

        self.state.tc_methods = tc_methods

        # Si se seleccionó Desbordes, preguntar por t0
        uses_desbordes = any("Desbordes" in m for m in tc_methods)
        if uses_desbordes:
            res = self._configure_t0()
            if res != StepResult.NEXT:
                return res
        else:
            self.state.t0_min = 5.0  # Valor por defecto (no se usará)

        # Si se seleccionó NRCS, configurar segmentos (método del mixin)
        uses_nrcs = any("NRCS" in m for m in tc_methods)
        if uses_nrcs:
            res = self._configure_nrcs()
            if res != StepResult.NEXT:
                return res

        return StepResult.NEXT

    def _configure_t0(self) -> StepResult:
        """Configura el tiempo de entrada inicial t0 para método Desbordes."""
        self.echo("\n  El método Desbordes usa un tiempo de entrada inicial (t0).")

        res, configurar = self.confirm(
            "¿Configurar t0? (default: 5 min)",
            default=False,
        )

        if res != StepResult.NEXT:
            return res

        if not configurar:
            self.state.t0_min = 5.0
            self.echo("  Usando t0 = 5 min (valor por defecto)")
            return StepResult.NEXT

        self.echo("\n  Tiempo de entrada inicial (t0):")
        self.echo("    t0 = 5 min - Valor típico (default)")
        self.echo("    t0 < 5 min - Cuencas muy urbanizadas")
        self.echo("    t0 > 5 min - Cuencas rurales")

        t0_choices = [
            "5 min - Valor típico (default)",
            "3 min - Cuenca muy urbanizada",
            "10 min - Cuenca rural",
            "Otro valor",
        ]

        res, t0_choice = self.select("Tiempo t0:", t0_choices)

        if res != StepResult.NEXT:
            return res

        if t0_choice:
            if "5 min" in t0_choice:
                self.state.t0_min = 5.0
            elif "3 min" in t0_choice:
                self.state.t0_min = 3.0
            elif "10 min" in t0_choice:
                self.state.t0_min = 10.0
            elif "Otro" in t0_choice:
                res, val = self.text(
                    "Valor de t0 (minutos):",
                    validate=validate_positive_float,
                    default="5",
                )
                if res != StepResult.NEXT:
                    return res
                if val:
                    self.state.t0_min = float(val)

        self.echo(f"\n  Configurado: t0 = {self.state.t0_min} min")
        return StepResult.NEXT


class StepIntervaloTiempo(WizardStep):
    """Paso: Intervalo de tiempo dt del hietograma."""

    @property
    def title(self) -> str:
        return "Intervalo de Tiempo"

    def execute(self) -> StepResult:
        from hidropluvial.core.hydrograph import recommended_dt

        self.echo(f"\n-- {self.title} --\n")

        # Calcular dt recomendado basado en el Tc mínimo
        tc_min_hr = self._get_min_tc_hr()
        if tc_min_hr:
            dt_rec_hr = recommended_dt(tc_min_hr)
            dt_rec_min = dt_rec_hr * 60
            # Redondear a valor práctico (1, 2, 5, 10, 15 min)
            practical_values = [1, 2, 5, 10, 15, 30]
            dt_practical = min(practical_values, key=lambda x: abs(x - dt_rec_min))
            self.echo(f"  Tc mínimo estimado: {tc_min_hr * 60:.1f} min")
            self.echo(f"  dt recomendado: {dt_rec_min:.1f} min -> {dt_practical} min")
        else:
            dt_practical = 5

        self.echo("\n  El intervalo dt afecta la forma del hidrograma:")
        self.echo("    - dt pequeno: picos mas altos, mayor precision")
        self.echo("    - dt grande:  picos mas bajos, menor precision")
        self.echo(f"    - Maximo recomendado: dt <= 0.25 x Tp\n")

        res, configurar = self.confirm(
            f"¿Usar dt = {dt_practical} min? (recomendado)",
            default=True,
        )

        if res != StepResult.NEXT:
            return res

        if configurar:
            self.state.dt_min = float(dt_practical)
            self.echo(f"\n  Configurado: dt = {dt_practical} min")
            return StepResult.NEXT

        # Opciones de dt
        dt_choices = [
            "1 min - Muy detallado (cuencas pequeñas)",
            "2 min - Detallado",
            "5 min - Estándar (default)",
            "10 min - Tormentas largas (24h)",
            "15 min - TR-55 tabular",
            "Otro valor",
        ]

        res, dt_choice = self.select("Intervalo de tiempo dt:", dt_choices)

        if res != StepResult.NEXT:
            return res

        if dt_choice:
            if "1 min" in dt_choice:
                self.state.dt_min = 1.0
            elif "2 min" in dt_choice:
                self.state.dt_min = 2.0
            elif "5 min" in dt_choice:
                self.state.dt_min = 5.0
            elif "10 min" in dt_choice:
                self.state.dt_min = 10.0
            elif "15 min" in dt_choice:
                self.state.dt_min = 15.0
            elif "Otro" in dt_choice:
                res, val = self.text(
                    "Valor de dt (minutos, 1-30):",
                    validate=lambda x: self._validate_dt(x),
                    default="5",
                )
                if res != StepResult.NEXT:
                    return res
                if val:
                    self.state.dt_min = float(val)

        self.echo(f"\n  Configurado: dt = {self.state.dt_min} min")
        return StepResult.NEXT

    def _get_min_tc_hr(self) -> float | None:
        """Estima el Tc mínimo basado en los métodos seleccionados."""
        from hidropluvial.core import kirpich, desbordes, temez
        from hidropluvial.core.tc import nrcs_velocity_method

        tc_values = []

        for method_str in self.state.tc_methods:
            method = method_str.split()[0].lower()

            if method == "kirpich" and self.state.length_m:
                tc = kirpich(self.state.length_m, self.state.slope_pct / 100)
                tc_values.append(tc)
            elif method == "temez" and self.state.length_m:
                tc = temez(self.state.length_m / 1000, self.state.slope_pct / 100)
                tc_values.append(tc)
            elif method == "desbordes" and self.state.c:
                tc = desbordes(
                    self.state.area_ha,
                    self.state.slope_pct,
                    self.state.c,
                    self.state.t0_min,
                )
                tc_values.append(tc)
            elif method == "nrcs" and self.state.nrcs_segments:
                tc = nrcs_velocity_method(
                    self.state.nrcs_segments,
                    self.state.p2_mm or 50.0,
                )
                tc_values.append(tc)

        return min(tc_values) if tc_values else None

    def _validate_dt(self, value: str) -> bool | str:
        """Valida entrada de dt."""
        try:
            v = float(value)
            if v < 1:
                return "dt debe ser >= 1 minuto"
            if v > 30:
                return "dt debe ser <= 30 minutos"
            return True
        except ValueError:
            return "Debe ser un número válido"


class StepTormenta(WizardStep):
    """Paso: Tipo de tormenta y períodos de retorno."""

    @property
    def title(self) -> str:
        return "Tormenta de Diseño"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        # Tipo de tormenta
        storm_choices = [
            questionary.Choice("GZ (6 horas) - recomendado drenaje urbano", checked=True),
            questionary.Choice("Bloques alternantes - duración según Tc", checked=False),
            questionary.Choice("Bloques 24 horas - obras mayores", checked=False),
            questionary.Choice("Bimodal - tormentas doble pico", checked=False),
            questionary.Choice("Huff (cuartil 2) - basado en datos históricos", checked=False),
            questionary.Choice("SCS Tipo II - distribución SCS 24h", checked=False),
        ]

        res, storm_types = self.checkbox("Tipos de tormenta a analizar:", storm_choices)

        if res != StepResult.NEXT:
            return res

        if not storm_types:
            self.echo("  Debes seleccionar al menos un tipo de tormenta")
            return self.execute()

        # Convertir a códigos
        self.state.storm_codes = []
        for storm_type in storm_types:
            if "GZ" in storm_type:
                self.state.storm_codes.append("gz")
            elif "Bloques alternantes" in storm_type:
                self.state.storm_codes.append("blocks")
            elif "24 horas" in storm_type:
                self.state.storm_codes.append("blocks24")
            elif "Bimodal" in storm_type:
                self.state.storm_codes.append("bimodal")
            elif "Huff" in storm_type:
                self.state.storm_codes.append("huff_q2")
            elif "SCS Tipo II" in storm_type:
                self.state.storm_codes.append("scs_ii")

        # Períodos de retorno
        tr_choices = [
            questionary.Choice("2 años", checked=True),
            questionary.Choice("5 años", checked=False),
            questionary.Choice("10 años", checked=True),
            questionary.Choice("25 años", checked=True),
            questionary.Choice("50 años", checked=False),
            questionary.Choice("100 años", checked=False),
        ]

        res, return_periods = self.checkbox("Períodos de retorno a analizar:", tr_choices)

        if res == StepResult.BACK:
            return self.execute()
        if res != StepResult.NEXT:
            return res

        if not return_periods:
            self.echo("  Debes seleccionar al menos un período de retorno")
            return self.execute()

        self.state.return_periods = [int(tr.split()[0]) for tr in return_periods]

        # Factor X para GZ
        if "gz" in self.state.storm_codes:
            x_result = self._collect_x_factors()
            if x_result == StepResult.BACK:
                return self.execute()
            if x_result != StepResult.NEXT:
                return x_result

        # Configuración bimodal
        if "bimodal" in self.state.storm_codes:
            bimodal_result = self._configure_bimodal()
            if bimodal_result == StepResult.BACK:
                return self.execute()
            if bimodal_result != StepResult.NEXT:
                return bimodal_result

        return StepResult.NEXT

    def _collect_x_factors(self) -> StepResult:
        """Recolecta factores X morfológicos."""
        from hidropluvial.cli.theme import print_x_factor_table

        print_x_factor_table()

        x_choices = [
            questionary.Choice("1.00 - Método racional", checked=True),
            questionary.Choice("1.25 - Urbano alta pendiente", checked=True),
            questionary.Choice("1.67 - Método NRCS", checked=False),
            questionary.Choice("2.25 - Uso mixto", checked=False),
            questionary.Choice("3.33 - Rural sinuoso", checked=False),
            questionary.Choice("5.50 - Rural pend. baja", checked=False),
            questionary.Choice("12.0 - Rural pend. muy baja", checked=False),
        ]

        res, x_selected = self.checkbox("Valores de X a analizar:", x_choices)

        if res != StepResult.NEXT:
            return res

        if x_selected:
            self.state.x_factors = [float(x.split(" - ")[0]) for x in x_selected]
        else:
            self.state.x_factors = [1.0]

        return StepResult.NEXT

    def _configure_bimodal(self) -> StepResult:
        """Configura parámetros de tormenta bimodal."""
        self.echo("\n  ┌─────────────────────────────────────────────────────────┐")
        self.echo("  │           TORMENTA BIMODAL (DOBLE PICO)                 │")
        self.echo("  ├─────────────────────────────────────────────────────────┤")
        self.echo("  │  Intensidad                                             │")
        self.echo("  │      ▲                                                  │")
        self.echo("  │      │    ╱╲              ╱╲                            │")
        self.echo("  │      │   ╱  ╲            ╱  ╲                           │")
        self.echo("  │      │  ╱    ╲    ──    ╱    ╲                          │")
        self.echo("  │      │ ╱      ╲────────╱      ╲                         │")
        self.echo("  │      └─────────────────────────────► Tiempo             │")
        self.echo("  │        Pico 1         Pico 2                            │")
        self.echo("  ├─────────────────────────────────────────────────────────┤")
        self.echo("  │  Útil para:                                             │")
        self.echo("  │  • Regiones costeras/tropicales                         │")
        self.echo("  │  • Tormentas frontales de larga duración                │")
        self.echo("  │  • Cuencas con respuesta mixta                          │")
        self.echo("  └─────────────────────────────────────────────────────────┘")

        self.echo(f"\n  Configuración por defecto:")
        self.echo(f"    • Pico 1: 25% de la duración (primera hora en tormenta 6h)")
        self.echo(f"    • Pico 2: 75% de la duración (hora 4.5 en tormenta 6h)")
        self.echo(f"    • Volumen: 50% en cada pico\n")

        res, configurar = self.confirm(
            "¿Configurar posición de picos? (default: 25%/75%, vol 50/50)",
            default=False,
        )

        if res != StepResult.NEXT:
            return res

        if not configurar:
            self.echo("  Usando configuración por defecto")
            return StepResult.NEXT

        # Opciones predefinidas
        self.echo("\n  Configuraciones típicas:")
        config_choices = [
            "Estándar (25%/75%) - picos simétricos",
            "Adelantada (15%/50%) - pico principal temprano",
            "Tardía (50%/85%) - pico principal tardío",
            "Asimétrica (20%/70%, vol 60/40) - primer pico dominante",
            "Personalizada - ingresar valores",
        ]

        res, config_choice = self.select("Configuración de picos:", config_choices)

        if res != StepResult.NEXT:
            return res

        if config_choice:
            if "Estándar" in config_choice:
                self.state.bimodal_peak1 = 0.25
                self.state.bimodal_peak2 = 0.75
                self.state.bimodal_vol_split = 0.5
            elif "Adelantada" in config_choice:
                self.state.bimodal_peak1 = 0.15
                self.state.bimodal_peak2 = 0.50
                self.state.bimodal_vol_split = 0.5
            elif "Tardía" in config_choice:
                self.state.bimodal_peak1 = 0.50
                self.state.bimodal_peak2 = 0.85
                self.state.bimodal_vol_split = 0.5
            elif "Asimétrica" in config_choice:
                self.state.bimodal_peak1 = 0.20
                self.state.bimodal_peak2 = 0.70
                self.state.bimodal_vol_split = 0.6
            elif "Personalizada" in config_choice:
                custom_result = self._configure_bimodal_custom()
                if custom_result != StepResult.NEXT:
                    return custom_result

        self.echo(f"\n  Configurado:")
        self.echo(f"    • Pico 1: {self.state.bimodal_peak1*100:.0f}% de la duración")
        self.echo(f"    • Pico 2: {self.state.bimodal_peak2*100:.0f}% de la duración")
        self.echo(f"    • Volumen pico 1: {self.state.bimodal_vol_split*100:.0f}%")
        self.echo(f"    • Volumen pico 2: {(1-self.state.bimodal_vol_split)*100:.0f}%")

        return StepResult.NEXT

    def _configure_bimodal_custom(self) -> StepResult:
        """Configura parámetros bimodales personalizados."""
        self.echo("\n  Ingresa valores personalizados (0-100%):\n")

        # Pico 1
        res, peak1_str = self.text(
            "Posición del primer pico (% de duración, ej: 25):",
            validate=lambda x: self._validate_percent(x, 5, 45),
            default="25",
        )
        if res != StepResult.NEXT:
            return res
        if peak1_str:
            self.state.bimodal_peak1 = float(peak1_str) / 100

        # Pico 2
        min_peak2 = self.state.bimodal_peak1 * 100 + 20  # Al menos 20% después del pico 1
        res, peak2_str = self.text(
            f"Posición del segundo pico (% de duración, mín {min_peak2:.0f}):",
            validate=lambda x: self._validate_percent(x, min_peak2, 95),
            default="75",
        )
        if res != StepResult.NEXT:
            return res
        if peak2_str:
            self.state.bimodal_peak2 = float(peak2_str) / 100

        # Distribución de volumen
        res, vol_str = self.text(
            "Porcentaje del volumen en el primer pico (ej: 50 para 50/50):",
            validate=lambda x: self._validate_percent(x, 20, 80),
            default="50",
        )
        if res != StepResult.NEXT:
            return res
        if vol_str:
            self.state.bimodal_vol_split = float(vol_str) / 100

        return StepResult.NEXT

    def _validate_percent(self, value: str, min_val: float, max_val: float) -> bool | str:
        """Valida entrada de porcentaje."""
        try:
            v = float(value)
            if v < min_val:
                return f"Debe ser >= {min_val:.0f}%"
            if v > max_val:
                return f"Debe ser <= {max_val:.0f}%"
            return True
        except ValueError:
            return "Debe ser un número válido"


class StepSalida(WizardStep):
    """Paso: Configuración de salida."""

    @property
    def title(self) -> str:
        return "Configuración de Salida"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, generar = self.confirm("¿Generar reporte LaTeX?", default=True)

        if res != StepResult.NEXT:
            return res

        if generar:
            default_name = self.state.nombre.lower().replace(" ", "_")
            res, output = self.text(
                "Nombre del archivo (sin extensión):",
                default=default_name,
                back_option=False,
            )
            if res != StepResult.NEXT:
                return res
            self.state.output_name = output if output else default_name

        return StepResult.NEXT
