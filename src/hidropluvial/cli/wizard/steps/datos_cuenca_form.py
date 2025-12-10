"""
Paso del wizard para datos de cuenca usando formulario interactivo.
"""

from typing import Optional

from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult
from hidropluvial.cli.viewer.form_viewer import (
    interactive_form,
    FormField,
    FieldType,
    FormResult,
)


class StepDatosCuencaForm(WizardStep):
    """Paso: Datos de la cuenca en formulario interactivo."""

    @property
    def title(self) -> str:
        return "Datos de la Cuenca"

    def execute(self) -> StepResult:
        # Definir campos del formulario
        fields = [
            FormField(
                key="nombre",
                label="Nombre de la cuenca",
                field_type=FieldType.TEXT,
                required=True,
                default=self.state.nombre if self.state.nombre else None,
                hint="Identificador único para esta cuenca",
            ),
            FormField(
                key="area_ha",
                label="Área",
                field_type=FieldType.FLOAT,
                required=True,
                unit="ha",
                default=self.state.area_ha if self.state.area_ha > 0 else None,
                min_value=0.01,
                max_value=10000,
                hint="Área total de la cuenca en hectáreas",
            ),
            FormField(
                key="slope_pct",
                label="Pendiente media",
                field_type=FieldType.FLOAT,
                required=True,
                unit="%",
                default=self.state.slope_pct if self.state.slope_pct > 0 else None,
                min_value=0.01,
                max_value=100,
                hint="Pendiente promedio del terreno",
            ),
            FormField(
                key="p3_10",
                label="Precipitación P(3h, Tr=10)",
                field_type=FieldType.FLOAT,
                required=True,
                unit="mm",
                default=self.state.p3_10 if self.state.p3_10 > 0 else None,
                min_value=1,
                max_value=500,
                hint="Consulta tabla IDF de DINAGUA para tu estación",
            ),
            FormField(
                key="length_m",
                label="Longitud del cauce",
                field_type=FieldType.FLOAT,
                required=False,
                unit="m",
                default=self.state.length_m if self.state.length_m else None,
                min_value=1,
                max_value=100000,
                hint="Longitud del cauce principal (opcional)",
            ),
        ]

        # Mostrar formulario interactivo
        result = interactive_form(
            title="Datos de la Cuenca",
            fields=fields,
            allow_back=True,
        )

        if result is None:
            return StepResult.CANCEL

        # Verificar si el usuario quiere volver
        if result.get("_result") == FormResult.BACK:
            return StepResult.BACK

        # Guardar valores en el estado
        self.state.nombre = result.get("nombre", "")
        self.state.area_ha = result.get("area_ha", 0)
        self.state.slope_pct = result.get("slope_pct", 0)
        self.state.p3_10 = result.get("p3_10", 0)
        self.state.length_m = result.get("length_m")

        return StepResult.NEXT
