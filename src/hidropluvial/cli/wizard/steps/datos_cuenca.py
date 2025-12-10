"""
Pasos del wizard para datos básicos de la cuenca.
"""

from hidropluvial.cli.wizard.styles import validate_positive_float
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult


class StepNombre(WizardStep):
    """Paso: Nombre de la cuenca."""

    @property
    def title(self) -> str:
        return "Nombre de la Cuenca"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, result = self.text(
            "Nombre de la cuenca:",
            validate=lambda x: len(x) > 0 or "El nombre no puede estar vacío",
            default=self.state.nombre,
            back_option=False,
        )

        if res != StepResult.NEXT or result is None:
            return StepResult.CANCEL

        self.state.nombre = result
        return StepResult.NEXT


class StepDatosCuenca(WizardStep):
    """Paso: Datos básicos de la cuenca (área, pendiente, P3,10)."""

    @property
    def title(self) -> str:
        return "Datos de la Cuenca"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        # Área
        self.suggestion("Típico: 1-50 ha (urbano), 50-500 ha (subcuenca)")
        default_area = str(self.state.area_ha) if self.state.area_ha > 0 else ""
        res, area = self.text(
            "Área de la cuenca (ha):",
            validate=validate_positive_float,
            default=default_area,
            back_option=True,
        )
        if res != StepResult.NEXT:
            return res
        self.state.area_ha = float(area)

        # Pendiente
        self.suggestion("Típico: 0.5-2% (llano), 2-5% (ondulado), >5% (pronunciado)")
        default_slope = str(self.state.slope_pct) if self.state.slope_pct > 0 else ""
        res, slope = self.text(
            "Pendiente media (%):",
            validate=validate_positive_float,
            default=default_slope,
            back_option=True,
        )
        if res == StepResult.BACK:
            # Volver al inicio de este paso (área)
            return self.execute()
        if res != StepResult.NEXT:
            return res
        self.state.slope_pct = float(slope)

        # P3,10
        self.suggestion("Consulta la tabla IDF de DINAGUA. Montevideo: ~55mm")
        default_p3 = str(self.state.p3_10) if self.state.p3_10 > 0 else ""
        res, p3_10 = self.text(
            "Precipitación P(3h, Tr=10) en mm:",
            validate=validate_positive_float,
            default=default_p3,
            back_option=True,
        )
        if res == StepResult.BACK:
            return self.execute()
        if res != StepResult.NEXT:
            return res
        self.state.p3_10 = float(p3_10)

        return StepResult.NEXT


class StepLongitud(WizardStep):
    """Paso: Longitud del cauce (opcional)."""

    @property
    def title(self) -> str:
        return "Longitud del Cauce"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, tiene = self.confirm("¿Conoces la longitud del cauce principal?", default=True)

        if res != StepResult.NEXT:
            return res

        if tiene:
            self.suggestion("Típico: 200-2000m (urbano), 1-10km (rural)")
            default_length = str(int(self.state.length_m)) if self.state.length_m else ""
            res, length = self.text(
                "Longitud del cauce (m):",
                validate=validate_positive_float,
                default=default_length,
            )
            if res == StepResult.BACK:
                return self.execute()
            if res != StepResult.NEXT:
                return res
            if length:
                self.state.length_m = float(length)
        else:
            self.state.length_m = None

        return StepResult.NEXT
