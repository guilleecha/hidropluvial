"""
Configuración de parámetros para tormentas bimodales.

Permite configurar interactivamente los parámetros de la tormenta bimodal:
- Duración de la tormenta
- Posición de los picos
- Distribución del volumen
- Ancho de los picos

Incluye presets predefinidos para escenarios típicos.
"""

from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class BimodalPreset:
    """Preset de configuración bimodal."""
    name: str
    description: str
    duration_hr: float
    peak1: float  # Posición pico 1 (0-1)
    peak2: float  # Posición pico 2 (0-1)
    vol_split: float  # Fracción volumen en pico 1
    peak_width: float  # Ancho de cada pico


# Presets predefinidos para escenarios típicos
BIMODAL_PRESETS = {
    "estandar": BimodalPreset(
        name="Estándar",
        description="Dos eventos similares, distribución simétrica",
        duration_hr=6.0,
        peak1=0.25,
        peak2=0.75,
        vol_split=0.50,
        peak_width=0.15,
    ),
    "adelantada": BimodalPreset(
        name="Adelantada",
        description="Evento temprano + refuerzo posterior",
        duration_hr=6.0,
        peak1=0.15,
        peak2=0.50,
        vol_split=0.50,
        peak_width=0.15,
    ),
    "tardia": BimodalPreset(
        name="Tardía",
        description="Evento inicial + pico tardío dominante",
        duration_hr=6.0,
        peak1=0.50,
        peak2=0.85,
        vol_split=0.50,
        peak_width=0.15,
    ),
    "pico1_fuerte": BimodalPreset(
        name="Primer pico fuerte",
        description="70% del volumen en el primer evento",
        duration_hr=6.0,
        peak1=0.25,
        peak2=0.75,
        vol_split=0.70,
        peak_width=0.15,
    ),
    "frente_tormenta": BimodalPreset(
        name="Frente de tormenta",
        description="Típico de tormentas frontales",
        duration_hr=6.0,
        peak1=0.20,
        peak2=0.60,
        vol_split=0.65,
        peak_width=0.12,
    ),
    "pico2_fuerte": BimodalPreset(
        name="Segundo pico fuerte",
        description="30/70% - evento creciente",
        duration_hr=6.0,
        peak1=0.25,
        peak2=0.75,
        vol_split=0.30,
        peak_width=0.15,
    ),
    "tormenta_creciente": BimodalPreset(
        name="Tormenta creciente",
        description="Intensificación gradual hacia el final",
        duration_hr=6.0,
        peak1=0.30,
        peak2=0.80,
        vol_split=0.35,
        peak_width=0.18,
    ),
    "larga_duracion": BimodalPreset(
        name="Larga duración (12h)",
        description="Evento extendido de 12 horas",
        duration_hr=12.0,
        peak1=0.25,
        peak2=0.75,
        vol_split=0.50,
        peak_width=0.12,
    ),
}


@dataclass
class BimodalConfig:
    """Configuración resultante de tormenta bimodal."""
    duration_hr: float
    peak1: float
    peak2: float
    vol_split: float
    peak_width: float

    @classmethod
    def from_preset(cls, preset: BimodalPreset) -> "BimodalConfig":
        """Crea configuración desde un preset."""
        return cls(
            duration_hr=preset.duration_hr,
            peak1=preset.peak1,
            peak2=preset.peak2,
            vol_split=preset.vol_split,
            peak_width=preset.peak_width,
        )

    @classmethod
    def default(cls) -> "BimodalConfig":
        """Configuración por defecto."""
        return cls.from_preset(BIMODAL_PRESETS["estandar"])


class BimodalConfigurator:
    """Configurador interactivo de tormenta bimodal."""

    def __init__(self, menu, current_config: Optional[BimodalConfig] = None):
        """
        Args:
            menu: Instancia del menú padre (para usar echo, select, etc.)
            current_config: Configuración actual (opcional)
        """
        self.menu = menu
        self.config = current_config or BimodalConfig.default()

    def configure(self) -> Optional[BimodalConfig]:
        """
        Configura parámetros de tormenta bimodal interactivamente.

        Returns:
            BimodalConfig si se configuró exitosamente, None si se canceló.
        """
        self._show_header()

        # Mostrar configuración actual
        self._show_current_config()

        # Menú principal
        while True:
            choices = [
                "Usar preset predefinido",
                "Configuración manual",
            ]
            if self._is_valid_config():
                choices.append("Aceptar configuración actual")
            choices.append("← Cancelar")

            choice = self.menu.select("¿Cómo deseas configurar la tormenta?", choices)

            if choice is None or "Cancelar" in choice:
                return None
            elif "preset" in choice.lower():
                if self._configure_from_preset():
                    self._show_summary()
                    return self.config
            elif "manual" in choice.lower():
                if self._configure_manual():
                    self._show_summary()
                    return self.config
            elif "Aceptar" in choice:
                self._show_summary()
                return self.config

    def _show_header(self) -> None:
        """Muestra encabezado explicativo."""
        self.menu.echo("\n  ┌─────────────────────────────────────────────────────────────┐")
        self.menu.echo("  │           TORMENTA BIMODAL (DOBLE PICO)                     │")
        self.menu.echo("  ├─────────────────────────────────────────────────────────────┤")
        self.menu.echo("  │  Simula tormentas con dos eventos de precipitación:        │")
        self.menu.echo("  │                                                             │")
        self.menu.echo("  │       ▲            ▲                                        │")
        self.menu.echo("  │      /│\\          /│\\                                       │")
        self.menu.echo("  │     / │ \\        / │ \\                                      │")
        self.menu.echo("  │    /  │  \\──────/  │  \\                                     │")
        self.menu.echo("  │   ────┴───────────┴────                                     │")
        self.menu.echo("  │       ↑            ↑                                        │")
        self.menu.echo("  │    Pico 1       Pico 2                                      │")
        self.menu.echo("  │                                                             │")
        self.menu.echo("  │  Útil para: tormentas frontales, regiones costeras,         │")
        self.menu.echo("  │  cuencas urbanas con respuesta rápida.                      │")
        self.menu.echo("  └─────────────────────────────────────────────────────────────┘")

    def _show_current_config(self) -> None:
        """Muestra configuración actual."""
        self.menu.echo("\n  Configuración actual:")
        self.menu.echo(f"    • Duración: {self.config.duration_hr:.1f} h")
        self.menu.echo(f"    • Pico 1: {self.config.peak1*100:.0f}% de la duración")
        self.menu.echo(f"    • Pico 2: {self.config.peak2*100:.0f}% de la duración")
        self.menu.echo(f"    • Volumen pico 1: {self.config.vol_split*100:.0f}%")
        self.menu.echo(f"    • Ancho de picos: {self.config.peak_width*100:.0f}%")

    def _configure_from_preset(self) -> bool:
        """Configura desde un preset predefinido."""
        self.menu.echo("\n  ── PRESETS DISPONIBLES ──")

        # Construir opciones con descripciones
        preset_choices = []
        for key, preset in BIMODAL_PRESETS.items():
            label = f"{preset.name} - {preset.description}"
            preset_choices.append(label)
        preset_choices.append("← Volver")

        choice = self.menu.select("Selecciona un preset:", preset_choices)

        if choice is None or "Volver" in choice:
            return False

        # Buscar preset seleccionado
        for key, preset in BIMODAL_PRESETS.items():
            if preset.name in choice:
                self.config = BimodalConfig.from_preset(preset)
                self.menu.success(f"Preset '{preset.name}' aplicado")
                self._show_current_config()

                # Preguntar si desea ajustar duración
                if self._ask_adjust_duration():
                    return True

                # Confirmar
                confirm = self.menu.select(
                    "¿Confirmar esta configuración?",
                    ["Sí, usar esta configuración", "No, elegir otro preset", "← Cancelar"]
                )
                if confirm and "Sí" in confirm:
                    return True
                elif "Cancelar" in (confirm or ""):
                    return False
                else:
                    return self._configure_from_preset()

        return False

    def _ask_adjust_duration(self) -> bool:
        """Pregunta si desea ajustar la duración."""
        duration_choices = [
            f"Mantener {self.config.duration_hr:.0f}h",
            "3 horas - Tormenta corta",
            "6 horas - Duración estándar",
            "12 horas - Tormenta extendida",
            "24 horas - Evento de larga duración",
            "Ingresar valor personalizado",
        ]

        choice = self.menu.select("¿Ajustar duración?", duration_choices)

        if choice is None or "Mantener" in choice:
            return False

        if "3 horas" in choice:
            self.config.duration_hr = 3.0
        elif "6 horas" in choice:
            self.config.duration_hr = 6.0
        elif "12 horas" in choice:
            self.config.duration_hr = 12.0
        elif "24 horas" in choice:
            self.config.duration_hr = 24.0
        elif "personalizado" in choice.lower():
            val = self.menu.text("Duración (horas, 1-48):", default="6")
            if val:
                try:
                    duration = float(val)
                    if 1 <= duration <= 48:
                        self.config.duration_hr = duration
                    else:
                        self.menu.warning("Duración debe estar entre 1 y 48 horas")
                        return False
                except ValueError:
                    self.menu.error("Valor inválido")
                    return False

        self.menu.success(f"Duración: {self.config.duration_hr:.1f} h")
        return False  # Continuar con el flujo normal

    def _configure_manual(self) -> bool:
        """Configura manualmente todos los parámetros."""
        self.menu.echo("\n  ── CONFIGURACIÓN MANUAL ──")
        self.menu.echo("  Ingresa cada parámetro de la tormenta bimodal.")

        # 1. Duración
        self.menu.echo("\n  1. DURACIÓN DE LA TORMENTA")
        duration_choices = [
            "3 horas - Tormenta corta",
            "6 horas - Duración estándar",
            "12 horas - Tormenta extendida",
            "24 horas - Evento de larga duración",
            "Ingresar valor personalizado",
            "← Cancelar configuración",
        ]
        choice = self.menu.select("Duración:", duration_choices)

        if choice is None or "Cancelar" in choice:
            return False

        if "3 horas" in choice:
            self.config.duration_hr = 3.0
        elif "6 horas" in choice:
            self.config.duration_hr = 6.0
        elif "12 horas" in choice:
            self.config.duration_hr = 12.0
        elif "24 horas" in choice:
            self.config.duration_hr = 24.0
        else:
            val = self.menu.text("Duración (horas, 1-48):", default="6")
            if not val:
                return False
            try:
                self.config.duration_hr = float(val)
                if not 1 <= self.config.duration_hr <= 48:
                    self.menu.warning("Duración debe estar entre 1 y 48 horas")
                    return False
            except ValueError:
                self.menu.error("Valor inválido")
                return False

        # 2. Posición Pico 1
        self.menu.echo("\n  2. POSICIÓN DEL PRIMER PICO")
        self.menu.echo("     (% de la duración donde ocurre el primer pico)")
        peak1_choices = [
            "15% - Muy temprano",
            "20% - Temprano",
            "25% - Primer cuarto (estándar)",
            "30% - Moderado",
            "40% - Cerca del centro",
            "Ingresar valor personalizado",
            "← Cancelar configuración",
        ]
        choice = self.menu.select("Posición pico 1:", peak1_choices)

        if choice is None or "Cancelar" in choice:
            return False

        peak1_values = {"15%": 0.15, "20%": 0.20, "25%": 0.25, "30%": 0.30, "40%": 0.40}
        for label, val in peak1_values.items():
            if label in choice:
                self.config.peak1 = val
                break
        else:
            val = self.menu.text("Posición pico 1 (0.05-0.45):", default="0.25")
            if not val:
                return False
            try:
                self.config.peak1 = float(val)
                if not 0.05 <= self.config.peak1 <= 0.45:
                    self.menu.warning("Posición debe estar entre 0.05 y 0.45")
                    return False
            except ValueError:
                self.menu.error("Valor inválido")
                return False

        # 3. Posición Pico 2
        self.menu.echo("\n  3. POSICIÓN DEL SEGUNDO PICO")
        self.menu.echo("     (% de la duración donde ocurre el segundo pico)")
        peak2_choices = [
            "60% - Después del centro",
            "70% - Moderado",
            "75% - Tercer cuarto (estándar)",
            "80% - Tardío",
            "85% - Muy tardío",
            "Ingresar valor personalizado",
            "← Cancelar configuración",
        ]
        choice = self.menu.select("Posición pico 2:", peak2_choices)

        if choice is None or "Cancelar" in choice:
            return False

        peak2_values = {"60%": 0.60, "70%": 0.70, "75%": 0.75, "80%": 0.80, "85%": 0.85}
        for label, val in peak2_values.items():
            if label in choice:
                self.config.peak2 = val
                break
        else:
            val = self.menu.text("Posición pico 2 (0.50-0.95):", default="0.75")
            if not val:
                return False
            try:
                self.config.peak2 = float(val)
                if not 0.50 <= self.config.peak2 <= 0.95:
                    self.menu.warning("Posición debe estar entre 0.50 y 0.95")
                    return False
            except ValueError:
                self.menu.error("Valor inválido")
                return False

        # Validar que peak2 > peak1
        if self.config.peak2 <= self.config.peak1:
            self.menu.warning("El pico 2 debe estar después del pico 1")
            return False

        # 4. Distribución del volumen
        self.menu.echo("\n  4. DISTRIBUCIÓN DEL VOLUMEN")
        self.menu.echo("     (% del volumen total que cae en el primer pico)")
        vol_choices = [
            "30% - Primer pico menor",
            "40% - Primer pico moderado",
            "50% - Distribución equitativa (estándar)",
            "60% - Primer pico mayor",
            "70% - Primer pico dominante",
            "Ingresar valor personalizado",
            "← Cancelar configuración",
        ]
        choice = self.menu.select("Volumen en pico 1:", vol_choices)

        if choice is None or "Cancelar" in choice:
            return False

        vol_values = {"30%": 0.30, "40%": 0.40, "50%": 0.50, "60%": 0.60, "70%": 0.70}
        for label, val in vol_values.items():
            if label in choice:
                self.config.vol_split = val
                break
        else:
            val = self.menu.text("Fracción en pico 1 (0.20-0.80):", default="0.50")
            if not val:
                return False
            try:
                self.config.vol_split = float(val)
                if not 0.20 <= self.config.vol_split <= 0.80:
                    self.menu.warning("Fracción debe estar entre 0.20 y 0.80")
                    return False
            except ValueError:
                self.menu.error("Valor inválido")
                return False

        # 5. Ancho de picos
        self.menu.echo("\n  5. ANCHO DE LOS PICOS")
        self.menu.echo("     (% de la duración que ocupa cada pico)")
        width_choices = [
            "10% - Picos muy puntiagudos (intensos)",
            "15% - Ancho estándar",
            "20% - Picos moderados",
            "25% - Picos anchos (menos intensos)",
            "Ingresar valor personalizado",
            "← Cancelar configuración",
        ]
        choice = self.menu.select("Ancho de picos:", width_choices)

        if choice is None or "Cancelar" in choice:
            return False

        width_values = {"10%": 0.10, "15%": 0.15, "20%": 0.20, "25%": 0.25}
        for label, val in width_values.items():
            if label in choice:
                self.config.peak_width = val
                break
        else:
            val = self.menu.text("Ancho de picos (0.05-0.30):", default="0.15")
            if not val:
                return False
            try:
                self.config.peak_width = float(val)
                if not 0.05 <= self.config.peak_width <= 0.30:
                    self.menu.warning("Ancho debe estar entre 0.05 y 0.30")
                    return False
            except ValueError:
                self.menu.error("Valor inválido")
                return False

        return True

    def _is_valid_config(self) -> bool:
        """Verifica si la configuración actual es válida."""
        return (
            1.0 <= self.config.duration_hr <= 48.0
            and 0.05 <= self.config.peak1 <= 0.45
            and 0.50 <= self.config.peak2 <= 0.95
            and self.config.peak2 > self.config.peak1
            and 0.20 <= self.config.vol_split <= 0.80
            and 0.05 <= self.config.peak_width <= 0.30
        )

    def _show_summary(self) -> None:
        """Muestra resumen de la configuración."""
        self.menu.echo("\n  ═══════════════════════════════════════════")
        self.menu.echo("  RESUMEN TORMENTA BIMODAL")
        self.menu.echo("  ───────────────────────────────────────────")
        self.menu.echo(f"  Duración total: {self.config.duration_hr:.1f} horas")
        self.menu.echo(f"  Primer pico:  {self.config.peak1*100:.0f}% ({self.config.peak1*self.config.duration_hr:.1f}h)")
        self.menu.echo(f"  Segundo pico: {self.config.peak2*100:.0f}% ({self.config.peak2*self.config.duration_hr:.1f}h)")
        self.menu.echo(f"  Vol. pico 1:  {self.config.vol_split*100:.0f}%")
        self.menu.echo(f"  Vol. pico 2:  {(1-self.config.vol_split)*100:.0f}%")
        self.menu.echo(f"  Ancho picos:  {self.config.peak_width*100:.0f}%")
        self.menu.echo("  ═══════════════════════════════════════════")
