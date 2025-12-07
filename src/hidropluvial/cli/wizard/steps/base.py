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
from hidropluvial.cli.theme import print_step, print_info, print_warning, print_error, print_note


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
    bimodal_peak1: float = 0.25  # Posición del primer pico (0-1)
    bimodal_peak2: float = 0.75  # Posición del segundo pico (0-1)
    bimodal_vol_split: float = 0.5  # Fracción del volumen en el primer pico

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

    def select(self, message: str, choices: list[str], back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """
        Muestra selector con opción de volver atrás.

        Returns:
            Tupla (resultado, valor_seleccionado)
        """
        if back_option:
            choices = choices + ["<< Volver atrás"]

        result = questionary.select(
            message,
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if result == "<< Volver atrás":
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def checkbox(self, message: str, choices: list, back_option: bool = True) -> tuple[StepResult, Optional[list]]:
        """Muestra checkbox con instrucciones para volver."""
        if back_option:
            self.echo("  (Presiona Esc o deja vacío y Enter para volver atrás)\n")

        result = questionary.checkbox(
            message,
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if not result and back_option:
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def text(self, message: str, validate=None, default: str = "", back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """Muestra input de texto con opción de volver."""
        if back_option:
            hint = " (dejar vacío para volver)"
            full_message = message
        else:
            hint = ""
            full_message = message

        result = questionary.text(
            full_message,
            validate=validate if not back_option else lambda x: True if x == "" else (validate(x) if validate else True),
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if result == "" and back_option and default == "":
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def confirm(self, message: str, default: bool = True) -> tuple[StepResult, bool]:
        """Muestra confirmación."""
        result = questionary.confirm(
            message,
            default=default,
            style=WIZARD_STYLE,
        ).ask()

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
        from hidropluvial.cli.wizard.steps.datos_cuenca import (
            StepNombre,
            StepDatosCuenca,
            StepLongitud,
        )
        from hidropluvial.cli.wizard.steps.escorrentia import StepMetodoEscorrentia
        from hidropluvial.cli.wizard.steps.tc_tormenta import (
            StepMetodosTc,
            StepIntervaloTiempo,
            StepTormenta,
            StepSalida,
        )

        return [
            StepNombre(self.state),
            StepDatosCuenca(self.state),
            StepLongitud(self.state),
            StepMetodoEscorrentia(self.state),
            StepMetodosTc(self.state),
            StepIntervaloTiempo(self.state),
            StepTormenta(self.state),
            StepSalida(self.state),
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
                # Confirmar cancelación
                confirm = questionary.confirm(
                    "¿Cancelar el wizard? Se perderán los datos ingresados",
                    default=False,
                    style=WIZARD_STYLE,
                ).ask()
                if confirm:
                    print_warning("Wizard cancelado")
                    return None
                # Si no confirma, continúa en el paso actual

        if self.current_step >= len(self.steps):
            return self.state
        return None
