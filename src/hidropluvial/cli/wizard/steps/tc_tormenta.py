"""
Pasos del wizard para tiempo de concentración y tormentas.
"""

import questionary

from hidropluvial.cli.wizard.styles import validate_positive_float
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult


class StepMetodosTc(WizardStep):
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

        return StepResult.NEXT

    def _collect_x_factors(self) -> StepResult:
        """Recolecta factores X morfológicos."""
        self.echo("\n  Factor X morfológico (forma del hidrograma triangular):")
        self.echo("    X=1.00  Método racional (respuesta rápida)")
        self.echo("    X=1.25  Áreas urbanas con pendiente")
        self.echo("    X=1.67  Método SCS/NRCS")
        self.echo("    X=2.25+ Cuencas rurales/mixtas\n")

        x_choices = [
            questionary.Choice("1.00 - Método racional", checked=True),
            questionary.Choice("1.25 - Urbano con pendiente", checked=True),
            questionary.Choice("1.67 - SCS/NRCS", checked=False),
            questionary.Choice("2.25 - Uso mixto rural/urbano", checked=False),
        ]

        res, x_selected = self.checkbox("Valores de X a analizar:", x_choices)

        if res != StepResult.NEXT:
            return res

        if x_selected:
            self.state.x_factors = [float(x.split(" - ")[0]) for x in x_selected]
        else:
            self.state.x_factors = [1.0]

        return StepResult.NEXT


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
