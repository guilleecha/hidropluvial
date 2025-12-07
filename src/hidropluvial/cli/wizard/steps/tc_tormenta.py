"""
Pasos del wizard para tiempo de concentración y tormentas.
"""

from typing import Optional

import questionary

from hidropluvial.cli.wizard.styles import validate_positive_float
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult
from hidropluvial.cli.wizard.steps.nrcs_config import NRCSConfigMixin
from hidropluvial.cli.theme import print_info, print_suggestion


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
            # Redondear a valor práctico (5, 10, 15, 30 min) - mínimo 5 min
            practical_values = [5, 10, 15, 30]
            dt_practical = min(practical_values, key=lambda x: abs(x - dt_rec_min))
            self.echo(f"  Tc mínimo estimado: {tc_min_hr * 60:.1f} min")
            self.suggestion(f"dt recomendado: {dt_practical} min (teórico: {dt_rec_min:.1f} min)")
        else:
            dt_practical = 5

        self.echo("\n  El intervalo dt afecta la forma del hidrograma:")
        self.echo("    - dt pequeno: picos mas altos, mayor precision")
        self.echo("    - dt grande:  picos mas bajos, menor precision")
        self.echo("    - Limite minimo: 5 min (evita picos irreales de IDF)")
        self.echo("    - Maximo recomendado: dt <= 0.25 x Tp\n")

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

        # Opciones de dt (mínimo 5 min para evitar picos irreales)
        dt_choices = [
            "5 min - Estándar (default)",
            "10 min - Tormentas largas",
            "15 min - NRCS 24h / TR-55 tabular",
            "30 min - Tormentas 24h tradicional",
            "Otro valor (5-30 min)",
        ]

        res, dt_choice = self.select("Intervalo de tiempo dt:", dt_choices)

        if res != StepResult.NEXT:
            return res

        if dt_choice:
            if "5 min" in dt_choice:
                self.state.dt_min = 5.0
            elif "10 min" in dt_choice:
                self.state.dt_min = 10.0
            elif "15 min" in dt_choice:
                self.state.dt_min = 15.0
            elif "30 min" in dt_choice:
                self.state.dt_min = 30.0
            elif "Otro" in dt_choice:
                res, val = self.text(
                    "Valor de dt (minutos, 5-30):",
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
        """Valida entrada de dt (mínimo 5 min para evitar picos irreales)."""
        try:
            v = float(value)
            if v < 5:
                return "dt debe ser >= 5 minutos (evita picos irreales de IDF)"
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
            questionary.Choice("Precipitación personalizada - evaluar evento real", checked=False),
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
            elif "personalizada" in storm_type:
                self.state.storm_codes.append("custom")

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

        # Configuración tormenta personalizada
        if "custom" in self.state.storm_codes:
            custom_result = self._configure_custom_storm()
            if custom_result == StepResult.BACK:
                return self.execute()
            if custom_result != StepResult.NEXT:
                return custom_result

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
        self.echo("  │       ◄─ancho─►      ◄─ancho─►                          │")
        self.echo("  ├─────────────────────────────────────────────────────────┤")
        self.echo("  │  Cada pico tiene forma triangular. El volumen se        │")
        self.echo("  │  distribuye en varios intervalos dt, no en uno solo.    │")
        self.echo("  ├─────────────────────────────────────────────────────────┤")
        self.echo("  │  Útil para:                                             │")
        self.echo("  │  • Regiones costeras/tropicales                         │")
        self.echo("  │  • Tormentas frontales de larga duración                │")
        self.echo("  │  • Cuencas con respuesta mixta                          │")
        self.echo("  └─────────────────────────────────────────────────────────┘")

        # Estimar Tc para ofrecer como opción de duración
        tc_hr_est = self._estimate_tc()

        # Seleccionar duración de la tormenta
        duration_choices = [
            "6 horas (estándar Uruguay, igual que GZ)",
        ]
        if tc_hr_est:
            duration_choices.append(f"Tc estimado ({tc_hr_est:.2f} h)")
        duration_choices.extend([
            "3 horas (tormentas cortas intensas)",
            "12 horas (tormentas prolongadas)",
            "24 horas (eventos extremos)",
            "Personalizada",
        ])

        res, duration_choice = self.select("Duración de la tormenta bimodal:", duration_choices)
        if res != StepResult.NEXT:
            return res

        if duration_choice:
            if "6 horas" in duration_choice:
                self.state.bimodal_duration_hr = 6.0
            elif "Tc estimado" in duration_choice and tc_hr_est:
                self.state.bimodal_duration_hr = tc_hr_est
            elif "3 horas" in duration_choice:
                self.state.bimodal_duration_hr = 3.0
            elif "12 horas" in duration_choice:
                self.state.bimodal_duration_hr = 12.0
            elif "24 horas" in duration_choice:
                self.state.bimodal_duration_hr = 24.0
            elif "Personalizada" in duration_choice:
                res, dur_str = self.text(
                    "Duración en horas:",
                    default="6.0",
                    validate=lambda v: validate_positive_float(v),
                )
                if res != StepResult.NEXT:
                    return res
                if dur_str:
                    self.state.bimodal_duration_hr = float(dur_str)

        dur = self.state.bimodal_duration_hr
        width_min = dur * 60 * self.state.bimodal_peak_width * 2  # ancho total en minutos
        self.echo(f"\n  Configuración por defecto (duración {dur:.1f}h):")
        self.echo(f"    • Pico 1: 25% ({dur * 0.25:.1f}h)")
        self.echo(f"    • Pico 2: 75% ({dur * 0.75:.1f}h)")
        self.echo(f"    • Volumen: 50% en cada pico")
        self.echo(f"    • Ancho de picos: 15% ({width_min:.0f} min cada uno)\n")

        res, configurar = self.confirm(
            "¿Configurar parámetros de la tormenta bimodal?",
            default=False,
        )

        if res != StepResult.NEXT:
            return res

        if not configurar:
            print_info("Usando configuración por defecto (25%/75%, vol 50/50)")
            return StepResult.NEXT

        # Opciones predefinidas con sugerencias
        print_suggestion("Selecciona según el tipo de evento que quieras modelar:")
        self.echo("")

        config_choices = [
            # Simétricas (vol 50/50)
            "Estándar (25%/75%, vol 50/50) - dos eventos similares",
            "Adelantada (15%/50%, vol 50/50) - evento temprano + refuerzo",
            "Tardía (50%/85%, vol 50/50) - evento tardío dominante",
            # Primer pico dominante
            "Primer pico fuerte (25%/75%, vol 70/30) - tormenta principal + cola",
            "Frente de tormenta (20%/60%, vol 65/35) - entrada intensa",
            # Segundo pico dominante
            "Segundo pico fuerte (25%/75%, vol 30/70) - precursor + principal",
            "Tormenta creciente (30%/80%, vol 35/65) - intensificación gradual",
            # Personalizada
            "Personalizada - ingresar valores manualmente",
        ]

        res, config_choice = self.select("Configuración de picos y volumen:", config_choices)

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
            elif "Primer pico fuerte" in config_choice:
                self.state.bimodal_peak1 = 0.25
                self.state.bimodal_peak2 = 0.75
                self.state.bimodal_vol_split = 0.7
            elif "Frente de tormenta" in config_choice:
                self.state.bimodal_peak1 = 0.20
                self.state.bimodal_peak2 = 0.60
                self.state.bimodal_vol_split = 0.65
            elif "Segundo pico fuerte" in config_choice:
                self.state.bimodal_peak1 = 0.25
                self.state.bimodal_peak2 = 0.75
                self.state.bimodal_vol_split = 0.3
            elif "Tormenta creciente" in config_choice:
                self.state.bimodal_peak1 = 0.30
                self.state.bimodal_peak2 = 0.80
                self.state.bimodal_vol_split = 0.35
            elif "Personalizada" in config_choice:
                custom_result = self._configure_bimodal_custom()
                if custom_result != StepResult.NEXT:
                    return custom_result

        dur = self.state.bimodal_duration_hr
        vol1 = self.state.bimodal_vol_split * 100
        vol2 = (1 - self.state.bimodal_vol_split) * 100
        width_min = dur * 60 * self.state.bimodal_peak_width * 2

        print_info(f"Configurado (duración {dur:.1f}h):")
        self.echo(f"    Pico 1: {self.state.bimodal_peak1*100:.0f}% ({dur * self.state.bimodal_peak1:.1f}h) - {vol1:.0f}% del volumen")
        self.echo(f"    Pico 2: {self.state.bimodal_peak2*100:.0f}% ({dur * self.state.bimodal_peak2:.1f}h) - {vol2:.0f}% del volumen")
        self.echo(f"    Ancho de picos: {self.state.bimodal_peak_width*100:.0f}% ({width_min:.0f} min)")

        return StepResult.NEXT

    def _configure_bimodal_custom(self) -> StepResult:
        """Configura parámetros bimodales personalizados."""
        self.echo("\n  Ingresa valores personalizados:\n")

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

        # Ancho de picos
        dur = self.state.bimodal_duration_hr
        print_info("El ancho define cuántos intervalos dt ocupa cada pico triangular.")
        print_suggestion("Valores típicos: 10-20%. Mayor ancho = picos más suaves.")
        current_width_min = dur * 60 * self.state.bimodal_peak_width * 2
        self.echo(f"  Actual: {self.state.bimodal_peak_width*100:.0f}% = {current_width_min:.0f} min por pico\n")

        res, width_str = self.text(
            "Ancho de cada pico (% de duración, ej: 15):",
            validate=lambda x: self._validate_percent(x, 5, 30),
            default="15",
        )
        if res != StepResult.NEXT:
            return res
        if width_str:
            self.state.bimodal_peak_width = float(width_str) / 100

        return StepResult.NEXT

    def _estimate_tc(self) -> Optional[float]:
        """Estima el Tc basándose en los métodos seleccionados y datos disponibles."""
        from hidropluvial.core import kirpich, desbordes, temez

        tc_values = []

        for method in self.state.tc_methods:
            method_lower = method.lower()
            if "kirpich" in method_lower and self.state.length_m:
                tc_hr = kirpich(self.state.length_m, self.state.slope_pct / 100)
                tc_values.append(tc_hr)
            elif "temez" in method_lower and self.state.length_m:
                tc_hr = temez(self.state.length_m / 1000, self.state.slope_pct / 100)
                tc_values.append(tc_hr)
            elif "desbordes" in method_lower and self.state.c:
                tc_hr = desbordes(self.state.area_ha, self.state.slope_pct, self.state.c)
                tc_values.append(tc_hr)

        if tc_values:
            return sum(tc_values) / len(tc_values)
        return None

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

    def _configure_custom_storm(self) -> StepResult:
        """Configura parámetros de tormenta personalizada."""
        from hidropluvial.cli.wizard.styles import validate_positive_float

        self.echo("\n  ┌─────────────────────────────────────────────────────────┐")
        self.echo("  │         PRECIPITACIÓN PERSONALIZADA                     │")
        self.echo("  ├─────────────────────────────────────────────────────────┤")
        self.echo("  │  Opciones:                                              │")
        self.echo("  │  • Pacum total: Ingresar precipitación acumulada y     │")
        self.echo("  │    seleccionar distribución temporal                    │")
        self.echo("  │  • Hietograma: Ingresar serie de tiempo de lluvia      │")
        self.echo("  │    (para evaluar eventos medidos/reales)                │")
        self.echo("  └─────────────────────────────────────────────────────────┘")

        type_choices = [
            "Pacum total - Precipitación acumulada con distribución",
            "Hietograma - Serie de tiempo de lluvia (evento real)",
        ]

        res, type_choice = self.select("Tipo de datos personalizados:", type_choices)
        if res != StepResult.NEXT:
            return res

        if type_choice and "Pacum" in type_choice:
            return self._configure_custom_pacum()
        elif type_choice and "Hietograma" in type_choice:
            return self._configure_custom_hyetograph()

        return StepResult.NEXT

    def _configure_custom_pacum(self) -> StepResult:
        """Configura precipitación total personalizada."""
        from hidropluvial.cli.wizard.styles import validate_positive_float

        self.echo("\n  Ingresa la precipitación acumulada del evento:")
        print_info("Ejemplo: 80 mm para un evento de 6 horas")

        res, depth_str = self.text(
            "Precipitación total (mm):",
            validate=validate_positive_float,
            default="80",
        )
        if res != StepResult.NEXT:
            return res
        if depth_str:
            self.state.custom_depth_mm = float(depth_str)

        # Duración
        tc_hr_est = self._estimate_tc()
        duration_choices = [
            "6 horas (estándar Uruguay)",
        ]
        if tc_hr_est:
            duration_choices.append(f"Tc estimado ({tc_hr_est:.2f} h)")
        duration_choices.extend([
            "3 horas (tormentas cortas)",
            "12 horas (tormentas prolongadas)",
            "24 horas (eventos extremos)",
            "Personalizada",
        ])

        res, dur_choice = self.select("Duración del evento:", duration_choices)
        if res != StepResult.NEXT:
            return res

        if dur_choice:
            if "6 horas" in dur_choice:
                self.state.custom_duration_hr = 6.0
            elif "Tc estimado" in dur_choice and tc_hr_est:
                self.state.custom_duration_hr = tc_hr_est
            elif "3 horas" in dur_choice:
                self.state.custom_duration_hr = 3.0
            elif "12 horas" in dur_choice:
                self.state.custom_duration_hr = 12.0
            elif "24 horas" in dur_choice:
                self.state.custom_duration_hr = 24.0
            elif "Personalizada" in dur_choice:
                res, dur_str = self.text(
                    "Duración en horas:",
                    validate=validate_positive_float,
                    default="6.0",
                )
                if res != StepResult.NEXT:
                    return res
                if dur_str:
                    self.state.custom_duration_hr = float(dur_str)

        # Distribución temporal
        self.echo("\n  Selecciona cómo distribuir la precipitación en el tiempo:")
        dist_choices = [
            "Bloques alternantes - pico en primer tercio (estilo GZ)",
            "Bloques alternantes (centro) - pico centrado",
            "SCS Tipo II - distribución NRCS 24h",
            "Huff Q2 - basado en datos históricos",
            "Triangular - distribución simple",
            "Uniforme - intensidad constante",
        ]

        res, dist_choice = self.select("Distribución temporal:", dist_choices)
        if res != StepResult.NEXT:
            return res

        if dist_choice:
            if "alternantes (centro)" in dist_choice:
                self.state.custom_distribution = "alternating_blocks"
            elif "alternantes" in dist_choice.lower():
                self.state.custom_distribution = "alternating_blocks_gz"
            elif "SCS" in dist_choice:
                self.state.custom_distribution = "scs_type_ii"
            elif "Huff" in dist_choice:
                self.state.custom_distribution = "huff_q2"
            elif "Triangular" in dist_choice:
                self.state.custom_distribution = "triangular"
            elif "Uniforme" in dist_choice:
                self.state.custom_distribution = "uniform"

        dur = self.state.custom_duration_hr
        print_info(f"Configurado: {self.state.custom_depth_mm:.1f} mm en {dur:.1f}h")
        self.echo(f"    Distribución: {self.state.custom_distribution}")

        return StepResult.NEXT

    def _configure_custom_hyetograph(self) -> StepResult:
        """Configura hietograma personalizado desde datos."""
        from hidropluvial.cli.wizard.styles import validate_positive_float

        self.echo("\n  Ingresa los datos del hietograma (evento medido/real):")
        print_info("Formato: tiempo (min) y precipitación (mm) por intervalo")
        print_suggestion("Ejemplo: intervalos de 5 min con lluvia en cada uno")

        # Preguntar intervalo de tiempo
        res, dt_str = self.text(
            "Intervalo de tiempo dt (minutos):",
            validate=validate_positive_float,
            default="5",
        )
        if res != StepResult.NEXT:
            return res

        dt = float(dt_str) if dt_str else 5.0

        # Preguntar número de intervalos
        res, n_str = self.text(
            "Número de intervalos:",
            validate=lambda x: x.isdigit() and int(x) >= 2 or "Mínimo 2 intervalos",
            default="12",
        )
        if res != StepResult.NEXT:
            return res

        n_intervals = int(n_str) if n_str else 12

        # Recolectar datos de precipitación
        self.echo(f"\n  Ingresa la precipitación para cada intervalo de {dt:.0f} min:")
        self.echo("  (Ingresa 0 para intervalos sin lluvia)\n")

        depths = []
        times = []
        for i in range(n_intervals):
            t_start = i * dt
            t_end = (i + 1) * dt
            t_center = t_start + dt / 2

            res, depth_str = self.text(
                f"  Intervalo {i+1} ({t_start:.0f}-{t_end:.0f} min) [mm]:",
                validate=lambda x: self._validate_non_negative(x),
                default="0",
                back_option=False,
            )
            if res != StepResult.NEXT:
                return res

            depth = float(depth_str) if depth_str else 0.0
            depths.append(depth)
            times.append(t_center)

        self.state.custom_hyetograph_time = times
        self.state.custom_hyetograph_depth = depths

        total = sum(depths)
        duration_hr = (n_intervals * dt) / 60
        print_info(f"Configurado: {total:.1f} mm total en {duration_hr:.1f}h")
        print_info(f"Pico: {max(depths):.1f} mm en intervalo de {dt:.0f} min")

        return StepResult.NEXT

    def _validate_non_negative(self, value: str) -> bool | str:
        """Valida entrada no negativa."""
        try:
            v = float(value)
            if v < 0:
                return "No puede ser negativo"
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
