"""
Pasos del wizard con navegación hacia atrás.

El paquete está organizado en módulos:
- base: Clases base (StepResult, WizardState, WizardStep, WizardNavigator)
- datos_cuenca: Pasos para nombre, datos y longitud de cuenca
- escorrentia: Paso para método de escorrentía (C y CN)
- tc_tormenta: Pasos para tiempo de concentración, tormenta y salida
- config_analisis_form: Formulario unificado de configuración de análisis
"""

# Re-exportar todo para mantener compatibilidad

# Desde base
from hidropluvial.cli.wizard.steps.base import (
    StepResult,
    WizardState,
    WizardStep,
    WizardNavigator,
)

# Desde datos_cuenca
from hidropluvial.cli.wizard.steps.datos_cuenca import (
    StepNombre,
    StepDatosCuenca,
    StepLongitud,
)

# Desde datos_cuenca_form (formulario interactivo)
from hidropluvial.cli.wizard.steps.datos_cuenca_form import (
    StepDatosCuencaForm,
)

# Desde config_analisis_form (formulario unificado)
from hidropluvial.cli.wizard.steps.config_analisis_form import (
    StepConfigAnalisisForm,
)

# Desde escorrentia
from hidropluvial.cli.wizard.steps.escorrentia import (
    StepMetodoEscorrentia,
)

# Desde tc_tormenta
from hidropluvial.cli.wizard.steps.tc_tormenta import (
    StepMetodosTc,
    StepTormenta,
    StepSalida,
)

__all__ = [
    # base
    "StepResult",
    "WizardState",
    "WizardStep",
    "WizardNavigator",
    # datos_cuenca
    "StepNombre",
    "StepDatosCuenca",
    "StepLongitud",
    # datos_cuenca_form
    "StepDatosCuencaForm",
    # config_analisis_form
    "StepConfigAnalisisForm",
    # escorrentia
    "StepMetodoEscorrentia",
    # tc_tormenta
    "StepMetodosTc",
    "StepTormenta",
    "StepSalida",
]
