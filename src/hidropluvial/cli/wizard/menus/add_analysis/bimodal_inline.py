"""
Configuración inline de tormenta bimodal para el formulario de análisis.

Muestra la configuración en un popup del formulario, permitiendo:
- Ver presets predefinidos
- Configurar duración, picos y volumen
- Todo sin salir de la vista principal
"""

from typing import Optional, List, TYPE_CHECKING, Callable
from dataclasses import dataclass

from hidropluvial.cli.theme import get_palette, get_icons

if TYPE_CHECKING:
    from hidropluvial.cli.viewer.form_viewer import FormState


# Presets predefinidos
BIMODAL_PRESETS = {
    "estandar": {
        "name": "Estándar",
        "description": "Dos eventos similares, 50/50%",
        "duration_hr": 6.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.50,
        "peak_width": 0.15,
    },
    "adelantada": {
        "name": "Adelantada",
        "description": "Evento temprano + refuerzo",
        "duration_hr": 6.0,
        "peak1": 0.15,
        "peak2": 0.50,
        "vol_split": 0.50,
        "peak_width": 0.15,
    },
    "tardia": {
        "name": "Tardía",
        "description": "Pico tardío dominante",
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
        "description": "Evento de 12 horas",
        "duration_hr": 12.0,
        "peak1": 0.25,
        "peak2": 0.75,
        "vol_split": 0.50,
        "peak_width": 0.12,
    },
}


@dataclass
class BimodalPopupState:
    """Estado del popup bimodal."""
    duration_hr: float = 6.0
    peak1: float = 0.25
    peak2: float = 0.75
    vol_split: float = 0.50
    peak_width: float = 0.15
    preset_name: Optional[str] = None  # Nombre del preset usado
    is_configured: bool = False  # Si ya se configuró


# Estado global para el popup bimodal
_bimodal_state: Optional[BimodalPopupState] = None


def get_bimodal_state() -> BimodalPopupState:
    """Obtiene el estado actual del popup bimodal."""
    global _bimodal_state
    if _bimodal_state is None:
        _bimodal_state = BimodalPopupState()
    return _bimodal_state


def reset_bimodal_state() -> None:
    """Reinicia el estado del popup bimodal."""
    global _bimodal_state
    _bimodal_state = None


def set_bimodal_state(
    duration_hr: float,
    peak1: float,
    peak2: float,
    vol_split: float,
    peak_width: float,
    preset_name: str = None,
) -> None:
    """Establece el estado del popup bimodal."""
    global _bimodal_state
    _bimodal_state = BimodalPopupState(
        duration_hr=duration_hr,
        peak1=peak1,
        peak2=peak2,
        vol_split=vol_split,
        peak_width=peak_width,
        preset_name=preset_name,
        is_configured=True,
    )


def build_bimodal_summary() -> str:
    """Construye un resumen de la configuración bimodal."""
    state = get_bimodal_state()
    if not state.is_configured:
        return "Sin configurar"

    return (
        f"{state.duration_hr:.0f}h, "
        f"picos {state.peak1*100:.0f}%/{state.peak2*100:.0f}%, "
        f"vol {state.vol_split*100:.0f}/{(1-state.vol_split)*100:.0f}"
    )


def build_bimodal_popup_options(
    form_state: "FormState",
    on_config_changed: Callable[[], None] = None,
) -> List[dict]:
    """
    Construye las opciones del popup bimodal para el formulario.

    Args:
        form_state: Estado del formulario
        on_config_changed: Callback cuando cambia la configuración

    Returns:
        Lista de opciones para el popup
    """
    p = get_palette()
    icons = get_icons()
    state = get_bimodal_state()

    options = []

    # ─── Presets ───
    options.append({
        "separator": True,
        "title": "Presets",
    })

    preset_keys = ["estandar", "adelantada", "tardia", "pico1_fuerte", "pico2_fuerte", "frente_tormenta", "larga_12h"]

    for preset_key in preset_keys:
        preset = BIMODAL_PRESETS[preset_key]
        is_selected = (state.preset_name == preset_key and state.is_configured)

        def make_apply_preset(pk):
            def apply_preset():
                pr = BIMODAL_PRESETS[pk]
                set_bimodal_state(
                    duration_hr=pr["duration_hr"],
                    peak1=pr["peak1"],
                    peak2=pr["peak2"],
                    vol_split=pr["vol_split"],
                    peak_width=pr["peak_width"],
                    preset_name=pk,
                )
                if on_config_changed:
                    on_config_changed()
                return "__reload__"
            return apply_preset

        options.append({
            "key": "",
            "label": f"{icons.check if is_selected else ' '} {preset['name']}",
            "hint": preset["description"],
            "action": make_apply_preset(preset_key),
        })

    # ─── Configuración actual ───
    options.append({
        "separator": True,
        "title": f"Configuración ({build_bimodal_summary()})",
    })

    # Duración
    options.append({
        "key": "d",
        "label": f"Duración: {state.duration_hr:.1f}h",
        "hint": "Cambiar",
        "action": lambda: _show_duration_submenu(form_state, on_config_changed),
    })

    # Picos
    options.append({
        "key": "p",
        "label": f"Picos: {state.peak1*100:.0f}% / {state.peak2*100:.0f}%",
        "hint": "Posiciones temporales",
        "action": lambda: _show_peaks_form(form_state, on_config_changed),
    })

    # Volumen
    options.append({
        "key": "v",
        "label": f"Volumen: {state.vol_split*100:.0f}% / {(1-state.vol_split)*100:.0f}%",
        "hint": "Distribución entre picos",
        "action": lambda: _show_volume_submenu(form_state, on_config_changed),
    })

    # Ancho de picos
    options.append({
        "key": "a",
        "label": f"Ancho picos: {state.peak_width*100:.0f}%",
        "hint": "Intensidad vs duración",
        "action": lambda: _show_width_submenu(form_state, on_config_changed),
    })

    return options


def _show_duration_submenu(form_state: "FormState", on_config_changed: Callable = None):
    """Muestra el submenú para seleccionar duración."""
    state = get_bimodal_state()

    submenu_options = [
        {"label": "3 horas", "description": "Tormenta corta", "value": 3.0},
        {"label": "6 horas", "description": "Duración estándar", "value": 6.0},
        {"label": "12 horas", "description": "Tormenta extendida", "value": 12.0},
        {"label": "24 horas", "description": "Evento largo", "value": 24.0},
        {"label": "Otro valor", "description": "Ingresar manualmente", "value": "custom"},
    ]

    def on_duration_selected(opt):
        s = get_bimodal_state()
        if opt.get("value") == "custom":
            form_state.inline_input_label = "Duración"
            form_state.inline_input_hint = "Duración de la tormenta bimodal (horas)"
            form_state.inline_input_fields = [
                {"label": "Duración", "type": "float", "unit": "h", "value": s.duration_hr, "required": True},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = str(s.duration_hr)
            form_state.inline_input_callback = lambda fields: _on_duration_input(fields, on_config_changed)
            form_state.mode = "popup_inline_input"
        else:
            s.duration_hr = opt.get("value", 6.0)
            s.preset_name = None
            s.is_configured = True
            if on_config_changed:
                on_config_changed()
            form_state.mode = "popup"
            return "__reload__"

    form_state.submenu_title = "Duración de tormenta"
    form_state.submenu_options = submenu_options
    form_state.submenu_idx = 0
    form_state.submenu_callback = on_duration_selected
    form_state.mode = "popup_submenu"

    return None


def _on_duration_input(fields: List[dict], on_config_changed: Callable = None):
    """Callback cuando se ingresa duración manualmente."""
    state = get_bimodal_state()
    if fields and fields[0].get("value"):
        val = fields[0]["value"]
        if 1.0 <= val <= 48.0:
            state.duration_hr = val
            state.preset_name = None
            state.is_configured = True
            if on_config_changed:
                on_config_changed()
    return "__reload__"


def _show_peaks_form(form_state: "FormState", on_config_changed: Callable = None):
    """Muestra el formulario para configurar posiciones de picos."""
    state = get_bimodal_state()

    form_state.inline_input_label = "Posición de picos"
    form_state.inline_input_hint = "Pico 1: 5-45%, Pico 2: 50-95%"
    form_state.inline_input_fields = [
        {"label": "Pico 1", "type": "float", "unit": "%", "value": state.peak1 * 100, "required": True, "key": "peak1"},
        {"label": "Pico 2", "type": "float", "unit": "%", "value": state.peak2 * 100, "required": True, "key": "peak2"},
    ]
    form_state.inline_input_idx = 0
    form_state.input_buffer = str(int(state.peak1 * 100))

    def on_peaks_input(fields):
        s = get_bimodal_state()
        peak1 = None
        peak2 = None
        for f in fields:
            if f.get("key") == "peak1":
                peak1 = f.get("value")
            elif f.get("key") == "peak2":
                peak2 = f.get("value")

        if peak1 is not None and peak2 is not None:
            # Convertir de % a fracción
            p1 = peak1 / 100
            p2 = peak2 / 100
            if 0.05 <= p1 <= 0.45 and 0.50 <= p2 <= 0.95 and p2 > p1:
                s.peak1 = p1
                s.peak2 = p2
                s.preset_name = None
                s.is_configured = True
                if on_config_changed:
                    on_config_changed()
        return "__reload__"

    form_state.inline_input_callback = on_peaks_input
    form_state.mode = "popup_inline_input"

    return None


def _show_volume_submenu(form_state: "FormState", on_config_changed: Callable = None):
    """Muestra el submenú para seleccionar distribución de volumen."""
    state = get_bimodal_state()

    submenu_options = [
        {"label": "30% / 70%", "description": "Segundo pico dominante", "value": 0.30},
        {"label": "40% / 60%", "description": "Segundo pico mayor", "value": 0.40},
        {"label": "50% / 50%", "description": "Distribución equitativa", "value": 0.50},
        {"label": "60% / 40%", "description": "Primer pico mayor", "value": 0.60},
        {"label": "70% / 30%", "description": "Primer pico dominante", "value": 0.70},
        {"label": "Otro valor", "description": "Ingresar manualmente", "value": "custom"},
    ]

    def on_volume_selected(opt):
        s = get_bimodal_state()
        if opt.get("value") == "custom":
            form_state.inline_input_label = "Distribución de volumen"
            form_state.inline_input_hint = "% del volumen total en el primer pico (20-80)"
            form_state.inline_input_fields = [
                {"label": "Vol. pico 1", "type": "float", "unit": "%", "value": s.vol_split * 100, "required": True},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = str(int(s.vol_split * 100))
            form_state.inline_input_callback = lambda fields: _on_volume_input(fields, on_config_changed)
            form_state.mode = "popup_inline_input"
        else:
            s.vol_split = opt.get("value", 0.50)
            s.preset_name = None
            s.is_configured = True
            if on_config_changed:
                on_config_changed()
            form_state.mode = "popup"
            return "__reload__"

    form_state.submenu_title = "Distribución de volumen"
    form_state.submenu_options = submenu_options
    form_state.submenu_idx = 0
    form_state.submenu_callback = on_volume_selected
    form_state.mode = "popup_submenu"

    return None


def _on_volume_input(fields: List[dict], on_config_changed: Callable = None):
    """Callback cuando se ingresa volumen manualmente."""
    state = get_bimodal_state()
    if fields and fields[0].get("value"):
        val = fields[0]["value"] / 100  # Convertir % a fracción
        if 0.20 <= val <= 0.80:
            state.vol_split = val
            state.preset_name = None
            state.is_configured = True
            if on_config_changed:
                on_config_changed()
    return "__reload__"


def _show_width_submenu(form_state: "FormState", on_config_changed: Callable = None):
    """Muestra el submenú para seleccionar ancho de picos."""
    state = get_bimodal_state()

    submenu_options = [
        {"label": "10%", "description": "Picos muy puntiagudos", "value": 0.10},
        {"label": "15%", "description": "Ancho estándar", "value": 0.15},
        {"label": "20%", "description": "Picos moderados", "value": 0.20},
        {"label": "25%", "description": "Picos anchos", "value": 0.25},
    ]

    def on_width_selected(opt):
        s = get_bimodal_state()
        s.peak_width = opt.get("value", 0.15)
        s.preset_name = None
        s.is_configured = True
        if on_config_changed:
            on_config_changed()
        form_state.mode = "popup"
        return "__reload__"

    form_state.submenu_title = "Ancho de picos"
    form_state.submenu_options = submenu_options
    form_state.submenu_idx = 0
    form_state.submenu_callback = on_width_selected
    form_state.mode = "popup_submenu"

    return None


def get_bimodal_parameters() -> Optional[dict]:
    """
    Obtiene los parámetros bimodales para usar en el runner.

    Returns:
        Dict con duration_hr, peak1, peak2, vol_split, peak_width o None
    """
    state = get_bimodal_state()

    if not state.is_configured:
        return None

    return {
        "duration_hr": state.duration_hr,
        "peak1": state.peak1,
        "peak2": state.peak2,
        "vol_split": state.vol_split,
        "peak_width": state.peak_width,
        "preset_name": state.preset_name,
    }
