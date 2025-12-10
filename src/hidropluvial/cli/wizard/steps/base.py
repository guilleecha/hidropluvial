"""
Clases base y utilidades para los pasos del wizard.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.cli.theme import (
    print_step, print_info, print_warning, print_error, print_note,
    print_suggestion,
)
from hidropluvial.cli.viewer.panel_input import (
    panel_select,
    panel_checkbox,
    panel_text,
    panel_confirm,
    PanelOption,
)


class StepResult(Enum):
    """Resultado de un paso del wizard."""
    NEXT = "next"       # Continuar al siguiente paso
    BACK = "back"       # Volver al paso anterior
    CANCEL = "cancel"   # Cancelar wizard


@dataclass
class WizardState:
    """Estado compartido del wizard."""
    # Datos de cuenca
    nombre: str = ""
    area_ha: float = 0.0
    slope_pct: float = 0.0
    p3_10: float = 0.0
    c: Optional[float] = None
    cn: Optional[int] = None
    length_m: Optional[float] = None

    # Datos de ponderación
    c_weighted_data: Optional[dict] = None

    # Parámetros avanzados
    amc: str = "II"  # Condición de humedad antecedente: I, II, III
    lambda_coef: float = 0.2  # Coeficiente lambda para abstracción inicial
    t0_min: float = 5.0  # Tiempo de entrada inicial para Desbordes

    # Parámetros de análisis
    tc_methods: list[str] = field(default_factory=list)
    storm_codes: list[str] = field(default_factory=lambda: ["gz"])
    return_periods: list[int] = field(default_factory=list)
    x_factors: list[float] = field(default_factory=lambda: [1.0])
    dt_min: float = 5.0  # Intervalo de tiempo del hietograma (minutos)

    # Parámetros de tormenta bimodal
    bimodal_duration_hr: float = 6.0  # Duración de la tormenta bimodal (horas)
    bimodal_peak1: float = 0.25  # Posición del primer pico (0-1)
    bimodal_peak2: float = 0.75  # Posición del segundo pico (0-1)
    bimodal_vol_split: float = 0.5  # Fracción del volumen en el primer pico
    bimodal_peak_width: float = 0.15  # Ancho de cada pico (fracción de duración)

    # Parámetros de tormenta personalizada
    custom_depth_mm: Optional[float] = None  # Precipitación total personalizada (mm)
    custom_duration_hr: float = 6.0  # Duración de tormenta personalizada (horas)
    custom_distribution: str = "alternating_blocks"  # Distribución temporal
    custom_hyetograph_time: Optional[list[float]] = None  # Tiempos del hietograma (min)
    custom_hyetograph_depth: Optional[list[float]] = None  # Profundidades del hietograma (mm)

    # Parámetros NRCS (método de velocidades)
    nrcs_segments: list = field(default_factory=list)  # Lista de segmentos TCSegment
    p2_mm: Optional[float] = None  # Precipitación 2 años, 24h (mm) para flujo laminar

    # Salida
    output_name: Optional[str] = None


class WizardStep(ABC):
    """Paso base del wizard."""

    def __init__(self, state: WizardState):
        self.state = state

    @property
    @abstractmethod
    def title(self) -> str:
        """Título del paso."""
        pass

    @abstractmethod
    def execute(self) -> StepResult:
        """Ejecuta el paso y retorna el resultado."""
        pass

    def echo(self, msg: str) -> None:
        """Imprime mensaje."""
        typer.echo(msg)

    def error(self, msg: str) -> None:
        """Imprime mensaje de error con estilo."""
        print_error(msg)

    def suggestion(self, msg: str) -> None:
        """Imprime sugerencia/recomendación con estilo."""
        print_suggestion(msg)

    def select(self, message: str, choices: list[str], back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """
        Muestra panel de selección con shortcuts de teclado.

        Returns:
            Tupla (resultado, valor_seleccionado)
        """
        options = [PanelOption(label=c, value=c) for c in choices]

        result = panel_select(
            title=message,
            options=options,
        )

        if result is None:
            if back_option:
                return StepResult.BACK, None
            return StepResult.CANCEL, None
        return StepResult.NEXT, result

    def checkbox(self, message: str, choices: list, back_option: bool = True) -> tuple[StepResult, Optional[list]]:
        """Muestra panel de checkbox con shortcuts de teclado."""
        # Convertir choices a PanelOption
        options = []
        for c in choices:
            if isinstance(c, dict):
                options.append(PanelOption(
                    label=c.get("name", str(c.get("value", ""))),
                    value=c.get("value"),
                    checked=c.get("checked", False),
                ))
            elif hasattr(c, 'title'):  # questionary.Choice
                options.append(PanelOption(
                    label=c.title,
                    value=c.title,
                    checked=getattr(c, 'checked', False),
                ))
            else:
                options.append(PanelOption(label=str(c), value=str(c)))

        result = panel_checkbox(
            title=message,
            options=options,
            min_selections=0 if back_option else 1,
        )

        if result is None:
            if back_option:
                return StepResult.BACK, None
            return StepResult.CANCEL, None
        if not result and back_option:
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def text(self, message: str, validate=None, default: str = "", back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """Muestra panel de entrada de texto."""
        result = panel_text(
            title=message,
            default=default,
            validator=validate,
        )

        if result is None:
            if back_option:
                return StepResult.BACK, None
            return StepResult.CANCEL, None
        if result == "" and back_option and default == "":
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def confirm(self, message: str, default: bool = True) -> tuple[StepResult, bool]:
        """Muestra panel de confirmación Sí/No."""
        result = panel_confirm(
            title=message,
            default=default,
        )

        if result is None:
            return StepResult.CANCEL, False
        return StepResult.NEXT, result


class WizardNavigator:
    """Controlador de navegación del wizard."""

    def __init__(self, steps: list[WizardStep] = None, state: WizardState = None):
        self.state = state or WizardState()
        self.steps: list[WizardStep] = steps if steps is not None else self._default_steps()
        self.current_step = 0

    def _default_steps(self) -> list[WizardStep]:
        """Crea los pasos por defecto del wizard."""
        from hidropluvial.cli.wizard.steps.datos_cuenca_form import StepDatosCuencaForm
        from hidropluvial.cli.wizard.steps.config_analisis_form import StepConfigAnalisisForm
        from hidropluvial.cli.wizard.steps.tc_tormenta import StepSalida

        return [
            StepDatosCuencaForm(self.state),  # Formulario interactivo: datos de cuenca
            StepConfigAnalisisForm(self.state),  # Formulario interactivo: configuración
            StepSalida(self.state),  # Configuración de salida
        ]

    def run(self) -> Optional[WizardState]:
        """Ejecuta el wizard con navegación."""
        while 0 <= self.current_step < len(self.steps):
            step = self.steps[self.current_step]

            # Mostrar progreso con estilo
            print_step(self.current_step + 1, len(self.steps), step.title)

            result = step.execute()

            if result == StepResult.NEXT:
                self.current_step += 1
            elif result == StepResult.BACK:
                if self.current_step > 0:
                    self.current_step -= 1
                    print_info("<< Volviendo al paso anterior...")
                else:
                    print_note("Ya estás en el primer paso")
            elif result == StepResult.CANCEL:
                # Cancelar directamente (la confirmación ya se hizo en el formulario)
                print_warning("Wizard cancelado")
                return None

        if self.current_step >= len(self.steps):
            return self.state
        return None
