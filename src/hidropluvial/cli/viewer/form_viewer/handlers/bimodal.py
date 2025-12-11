"""
Handlers para la calculadora de tormenta bimodal.
"""

from typing import Any, Optional

from ..models import FormState, FormResult


# Presets bimodales
BIMODAL_PRESETS = {
    "estandar": {
        "name": "Estándar",
        "description": "Dos eventos similares",
        "duration_hr": 6.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.50,
        "peak_width": 0.15,
    },
    "adelantada": {
        "name": "Adelantada",
        "description": "Evento temprano",
        "duration_hr": 6.0,
        "peak1": 0.15,
        "peak2": 0.50,
        "vol_split": 0.50,
        "peak_width": 0.15,
    },
    "tardia": {
        "name": "Tardía",
        "description": "Pico tardío",
        "duration_hr": 6.0,
        "peak1": 0.50,
        "peak2": 0.85,
        "vol_split": 0.50,
        "peak_width": 0.15,
    },
    "pico1_fuerte": {
        "name": "Pico 1 fuerte",
        "description": "70% en primer evento",
        "duration_hr": 6.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.70,
        "peak_width": 0.15,
    },
    "pico2_fuerte": {
        "name": "Pico 2 fuerte",
        "description": "70% en segundo evento",
        "duration_hr": 6.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.30,
        "peak_width": 0.15,
    },
    "frente_tormenta": {
        "name": "Frente de tormenta",
        "description": "Típico frontal",
        "duration_hr": 6.0,
        "peak1": 0.20,
        "peak2": 0.60,
        "vol_split": 0.65,
        "peak_width": 0.12,
    },
    "larga_12h": {
        "name": "Larga duración",
        "description": "12 horas",
        "duration_hr": 12.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.50,
        "peak_width": 0.12,
    },
}


def get_bimodal_config(state: FormState) -> dict:
    """Obtiene la configuración bimodal desde el estado global."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state
    bs = get_bimodal_state()
    return {
        "duration_hr": bs.duration_hr,
        "peak1": bs.peak1,
        "peak2": bs.peak2,
        "vol_split": bs.vol_split,
        "peak_width": bs.peak_width,
        "preset_name": bs.preset_name,
    }


def handle_bimodal_calculator(key: str, state: FormState) -> Optional[dict]:
    """Maneja el modo de calculadora bimodal."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import (
        get_bimodal_state, set_bimodal_state
    )

    bimodal_state = get_bimodal_state()
    preset_keys = list(BIMODAL_PRESETS.keys())
    n_options = len(preset_keys) + 4  # presets + duración + picos + volumen + ancho

    if key == 'esc':
        # Cancelar - volver al popup de tormentas
        state.bimodal_selected_idx = 0
        state.bimodal_callback = None
        state.mode = "popup"

    elif key == 'enter':
        # Confirmar - guardar configuración y volver
        callback = state.bimodal_callback
        config = get_bimodal_config(state)

        # Limpiar estado
        state.bimodal_selected_idx = 0
        state.bimodal_callback = None
        state.mode = "popup"

        if callable(callback):
            result = callback(config)
            if result == "__reload__":
                return {"_result": FormResult.RELOAD}

    elif key == 'up':
        state.bimodal_selected_idx = max(0, state.bimodal_selected_idx - 1)

    elif key == 'down':
        state.bimodal_selected_idx = min(n_options - 1, state.bimodal_selected_idx + 1)

    elif key == ' ':
        # Espacio - seleccionar opción actual
        idx = state.bimodal_selected_idx

        if idx < len(preset_keys):
            # Es un preset
            preset_key = preset_keys[idx]
            preset = BIMODAL_PRESETS[preset_key]
            set_bimodal_state(
                duration_hr=preset["duration_hr"],
                peak1=preset["peak1"],
                peak2=preset["peak2"],
                vol_split=preset["vol_split"],
                peak_width=preset["peak_width"],
                preset_name=preset_key,
            )
        elif idx == len(preset_keys):
            # Duración
            _show_duration_submenu(state)
        elif idx == len(preset_keys) + 1:
            # Picos
            _show_peaks_form(state)
        elif idx == len(preset_keys) + 2:
            # Volumen
            _show_volume_submenu(state)
        elif idx == len(preset_keys) + 3:
            # Ancho
            _show_width_submenu(state)

    # Atajos de teclado para presets
    elif key == '1':
        _apply_preset(state, "estandar")
    elif key == '2':
        _apply_preset(state, "adelantada")
    elif key == '3':
        _apply_preset(state, "tardia")
    elif key == '4':
        _apply_preset(state, "pico1_fuerte")
    elif key == '5':
        _apply_preset(state, "pico2_fuerte")
    elif key == '6':
        _apply_preset(state, "frente_tormenta")
    elif key == '7':
        _apply_preset(state, "larga_12h")

    # Atajos para configuración
    elif key == 'd':
        _show_duration_submenu(state)
    elif key == 'p':
        _show_peaks_form(state)
    elif key == 'v':
        _show_volume_submenu(state)
    elif key == 'a':
        _show_width_submenu(state)

    else:
        # Tecla no reconocida, no actualizar display
        return {"_no_update": True}

    return None


def _apply_preset(state: FormState, preset_key: str) -> None:
    """Aplica un preset bimodal."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import set_bimodal_state

    preset = BIMODAL_PRESETS[preset_key]
    set_bimodal_state(
        duration_hr=preset["duration_hr"],
        peak1=preset["peak1"],
        peak2=preset["peak2"],
        vol_split=preset["vol_split"],
        peak_width=preset["peak_width"],
        preset_name=preset_key,
    )


def _show_duration_submenu(state: FormState) -> None:
    """Muestra submenú para duración."""
    state.submenu_title = "Duración de tormenta"
    state.submenu_options = [
        {"label": "3 horas", "description": "Tormenta corta", "value": 3.0},
        {"label": "6 horas", "description": "Duración estándar", "value": 6.0},
        {"label": "12 horas", "description": "Tormenta extendida", "value": 12.0},
        {"label": "24 horas", "description": "Evento largo", "value": 24.0},
    ]
    state.submenu_idx = 0
    state.submenu_callback = lambda opt: _on_duration_selected(state, opt)
    state.mode = "popup_submenu"


def _on_duration_selected(state: FormState, opt: dict) -> Optional[str]:
    """Callback cuando se selecciona duración."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    bs = get_bimodal_state()
    bs.duration_hr = opt.get("value", 6.0)
    bs.preset_name = None
    bs.is_configured = True
    state.mode = "popup_bimodal_calculator"
    return None


def _show_peaks_form(state: FormState) -> None:
    """Muestra formulario para posiciones de picos."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    bs = get_bimodal_state()
    state.inline_input_label = "Posición de picos"
    state.inline_input_hint = "Pico 1: 5-45%, Pico 2: 50-95%"
    state.inline_input_fields = [
        {"label": "Pico 1", "type": "float", "unit": "%", "value": bs.peak1 * 100, "required": True, "key": "peak1"},
        {"label": "Pico 2", "type": "float", "unit": "%", "value": bs.peak2 * 100, "required": True, "key": "peak2"},
    ]
    state.inline_input_idx = 0
    state.input_buffer = str(int(bs.peak1 * 100))
    state.inline_input_callback = lambda fields: _on_peaks_input(state, fields)
    state.mode = "popup_inline_input"


def _on_peaks_input(state: FormState, fields: list) -> Optional[str]:
    """Callback cuando se ingresan posiciones de picos."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    bs = get_bimodal_state()
    peak1 = None
    peak2 = None
    for f in fields:
        if f.get("key") == "peak1":
            peak1 = f.get("value")
        elif f.get("key") == "peak2":
            peak2 = f.get("value")

    if peak1 is not None and peak2 is not None:
        p1 = peak1 / 100
        p2 = peak2 / 100
        if 0.05 <= p1 <= 0.45 and 0.50 <= p2 <= 0.95 and p2 > p1:
            bs.peak1 = p1
            bs.peak2 = p2
            bs.preset_name = None
            bs.is_configured = True

    state.mode = "popup_bimodal_calculator"
    return None


def _show_volume_submenu(state: FormState) -> None:
    """Muestra submenú para distribución de volumen."""
    state.submenu_title = "Distribución de volumen"
    state.submenu_options = [
        {"label": "30% / 70%", "description": "Segundo pico dominante", "value": 0.30},
        {"label": "40% / 60%", "description": "Segundo pico mayor", "value": 0.40},
        {"label": "50% / 50%", "description": "Distribución equitativa", "value": 0.50},
        {"label": "60% / 40%", "description": "Primer pico mayor", "value": 0.60},
        {"label": "70% / 30%", "description": "Primer pico dominante", "value": 0.70},
    ]
    state.submenu_idx = 0
    state.submenu_callback = lambda opt: _on_volume_selected(state, opt)
    state.mode = "popup_submenu"


def _on_volume_selected(state: FormState, opt: dict) -> Optional[str]:
    """Callback cuando se selecciona volumen."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    bs = get_bimodal_state()
    bs.vol_split = opt.get("value", 0.50)
    bs.preset_name = None
    bs.is_configured = True
    state.mode = "popup_bimodal_calculator"
    return None


def _show_width_submenu(state: FormState) -> None:
    """Muestra submenú para ancho de picos."""
    state.submenu_title = "Ancho de picos"
    state.submenu_options = [
        {"label": "10%", "description": "Picos muy puntiagudos", "value": 0.10},
        {"label": "15%", "description": "Ancho estándar", "value": 0.15},
        {"label": "20%", "description": "Picos moderados", "value": 0.20},
        {"label": "25%", "description": "Picos anchos", "value": 0.25},
    ]
    state.submenu_idx = 0
    state.submenu_callback = lambda opt: _on_width_selected(state, opt)
    state.mode = "popup_submenu"


def _on_width_selected(state: FormState, opt: dict) -> Optional[str]:
    """Callback cuando se selecciona ancho."""
    from hidropluvial.cli.wizard.menus.add_analysis.bimodal_inline import get_bimodal_state

    bs = get_bimodal_state()
    bs.peak_width = opt.get("value", 0.15)
    bs.preset_name = None
    bs.is_configured = True
    state.mode = "popup_bimodal_calculator"
    return None
