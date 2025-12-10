"""
Funciones para la calculadora de tormenta bimodal integrada en el formulario.
"""

from rich.console import Group
from rich.text import Text
from rich.panel import Panel

from hidropluvial.cli.theme import get_palette, get_icons

from .models import FormState


# Presets bimodales
BIMODAL_PRESETS = {
    "estandar": {
        "name": "Estándar",
        "description": "Dos eventos similares",
    },
    "adelantada": {
        "name": "Adelantada",
        "description": "Evento temprano",
    },
    "tardia": {
        "name": "Tardía",
        "description": "Pico tardío",
    },
    "pico1_fuerte": {
        "name": "Pico 1 fuerte",
        "description": "70% en primer evento",
    },
    "pico2_fuerte": {
        "name": "Pico 2 fuerte",
        "description": "70% en segundo evento",
    },
    "frente_tormenta": {
        "name": "Frente de tormenta",
        "description": "Típico frontal",
    },
    "larga_12h": {
        "name": "Larga duración",
        "description": "12 horas",
    },
}


def build_bimodal_calculator_panel(state: FormState) -> Panel:
    """Construye el panel de la calculadora de tormenta bimodal."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    p = get_palette()
    icons = get_icons()
    bimodal_state = get_bimodal_state()

    elements = []

    # Título con configuración actual
    header = Text()
    header.append("  Configuración actual: ", style=p.muted)
    if bimodal_state.preset_name:
        preset = BIMODAL_PRESETS.get(bimodal_state.preset_name, {})
        header.append(preset.get("name", bimodal_state.preset_name), style=f"bold {p.primary}")
    else:
        header.append("Personalizada", style=f"bold {p.accent}")
    elements.append(header)
    elements.append(Text(""))

    # Lista de presets (sin tabla para evitar flickering)
    preset_keys = list(BIMODAL_PRESETS.keys())
    n_presets = len(preset_keys)

    for i, preset_key in enumerate(preset_keys):
        preset = BIMODAL_PRESETS[preset_key]
        is_selected = i == state.bimodal_selected_idx
        is_current = bimodal_state.preset_name == preset_key

        line = Text()
        line.append("  ", style="")
        line.append(">" if is_selected else " ", style=f"bold {p.primary}" if is_selected else "")
        line.append(f" {i+1}. ", style=p.muted)
        line.append(icons.check if is_current else " ", style=f"bold {p.success}" if is_current else "")
        line.append(f" {preset['name']:<18}", style=f"bold {p.primary}" if is_selected else "")
        line.append(f" {preset['description']}", style=p.muted)
        elements.append(line)

    elements.append(Text(""))

    # Configuración actual
    config_header = Text()
    config_header.append("  ── Parámetros ──", style=f"bold {p.secondary}")
    elements.append(config_header)
    elements.append(Text(""))

    # Línea 1: Duración y Picos
    line1 = Text()
    is_duration_selected = state.bimodal_selected_idx == n_presets
    dur_style = f"bold {p.primary}" if is_duration_selected else ""
    line1.append("  ", style="")
    line1.append(">" if is_duration_selected else " ", style=dur_style)
    line1.append(" [d] ", style=f"bold {p.accent}")
    line1.append(f"Duración: {bimodal_state.duration_hr:.1f}h", style=dur_style or "")
    line1.append("     ", style="")

    is_peaks_selected = state.bimodal_selected_idx == n_presets + 1
    peaks_style = f"bold {p.primary}" if is_peaks_selected else ""
    line1.append(">" if is_peaks_selected else " ", style=peaks_style)
    line1.append(" [p] ", style=f"bold {p.accent}")
    line1.append(f"Picos: {bimodal_state.peak1*100:.0f}% / {bimodal_state.peak2*100:.0f}%", style=peaks_style or "")
    elements.append(line1)

    # Línea 2: Volumen y Ancho
    line2 = Text()
    is_vol_selected = state.bimodal_selected_idx == n_presets + 2
    vol_style = f"bold {p.primary}" if is_vol_selected else ""
    line2.append("  ", style="")
    line2.append(">" if is_vol_selected else " ", style=vol_style)
    line2.append(" [v] ", style=f"bold {p.accent}")
    vol_pct = bimodal_state.vol_split * 100
    line2.append(f"Volumen: {vol_pct:.0f}% / {100-vol_pct:.0f}%", style=vol_style or "")
    line2.append("   ", style="")

    is_width_selected = state.bimodal_selected_idx == n_presets + 3
    width_style = f"bold {p.primary}" if is_width_selected else ""
    line2.append(">" if is_width_selected else " ", style=width_style)
    line2.append(" [a] ", style=f"bold {p.accent}")
    line2.append(f"Ancho: {bimodal_state.peak_width*100:.0f}%", style=width_style or "")
    elements.append(line2)

    elements.append(Text(""))

    # Navegación
    nav = Text()
    nav.append("  [", style=p.muted)
    nav.append("↑↓", style=f"bold {p.accent}")
    nav.append("] Seleccionar   ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Espacio", style=f"bold {p.accent}")
    nav.append("] Aplicar   ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Enter", style=f"bold {p.nav_confirm}")
    nav.append("] Confirmar   ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Esc", style=f"bold {p.nav_cancel}")
    nav.append("] Cancelar", style=p.muted)
    elements.append(nav)

    return Panel(
        Group(*elements),
        title=f"[bold {p.primary}] Calculadora Tormenta Bimodal [/]",
        border_style=p.border,
        padding=(1, 2),
    )
