"""
Handlers para la calculadora NRCS (TR-55).
"""

from typing import Any, Optional, List

from ..models import FormState, FormResult


def handle_nrcs_calculator(key: str, state: FormState) -> Optional[dict]:
    """Maneja el modo de calculadora NRCS."""
    n_segments = len(state.nrcs_segments)

    if key == 'esc':
        # Cancelar - volver al popup de Tc sin guardar
        state.nrcs_segments = []
        state.nrcs_selected_idx = 0
        state.nrcs_message = ""
        state.nrcs_callback = None
        state.nrcs_basin = None
        state.mode = "popup"

    elif key == 'enter':
        # Confirmar - guardar segmentos y volver
        if state.nrcs_segments:
            callback = state.nrcs_callback
            segments = list(state.nrcs_segments)
            p2_mm = state.nrcs_p2_mm

            # Limpiar estado
            state.nrcs_selected_idx = 0
            state.nrcs_message = ""
            state.nrcs_callback = None
            state.nrcs_basin = None
            state.mode = "popup"

            if callable(callback):
                result = callback({"segments": segments, "p2_mm": p2_mm})
                if result == "__reload__":
                    return {"_result": FormResult.RELOAD}
        else:
            state.nrcs_message = "Agrega al menos un segmento"

    elif key == 'up' and n_segments > 0:
        state.nrcs_selected_idx = max(0, state.nrcs_selected_idx - 1)

    elif key == 'down' and n_segments > 0:
        state.nrcs_selected_idx = min(n_segments - 1, state.nrcs_selected_idx + 1)

    elif key == 'd' and n_segments > 0:
        # Eliminar segmento seleccionado
        state.nrcs_segments.pop(state.nrcs_selected_idx)
        if state.nrcs_selected_idx >= len(state.nrcs_segments) and state.nrcs_segments:
            state.nrcs_selected_idx = len(state.nrcs_segments) - 1
        state.nrcs_message = "Segmento eliminado"

    elif key == 'a':
        # Agregar segmento - abrir submenú de tipos
        state.submenu_title = "Tipo de segmento"
        state.submenu_options = [
            {"label": "Flujo laminar", "description": "máx 100m, superficie inicial", "value": "sheet"},
            {"label": "Flujo concentrado", "description": "cunetas, zanjas", "value": "shallow"},
            {"label": "Flujo en canal", "description": "arroyos, canales", "value": "channel"},
        ]
        state.submenu_idx = 0
        state.submenu_callback = lambda opt: _handle_nrcs_segment_type(state, opt)
        state.mode = "popup_submenu"

    elif key == 'p':
        # Cambiar P2 - mostrar opciones
        p2_estimated = None
        if state.nrcs_basin and hasattr(state.nrcs_basin, 'p3_10') and state.nrcs_basin.p3_10:
            p2_estimated = state.nrcs_basin.p3_10 * 0.5

        options = []
        if p2_estimated:
            options.append({"label": f"Estimado: {p2_estimated:.1f} mm", "description": "Desde P3,10", "value": p2_estimated})
        options.extend([
            {"label": "50 mm", "description": "Valor típico Uruguay", "value": 50.0},
            {"label": "40 mm", "description": "Zona semiárida", "value": 40.0},
            {"label": "60 mm", "description": "Zona húmeda", "value": 60.0},
            {"label": "Otro valor...", "description": "Ingresar manualmente", "value": "custom"},
        ])

        state.submenu_title = "Precipitación P₂ (2 años, 24h)"
        state.submenu_options = options
        state.submenu_idx = 0
        state.submenu_callback = lambda opt: _handle_nrcs_p2_selection(state, opt)
        state.mode = "popup_submenu"

    else:
        # Tecla no reconocida, no actualizar display
        return {"_no_update": True}

    return None


# ============================================================================
# Helpers para selección de tipo de segmento
# ============================================================================

def _handle_nrcs_segment_type(state: FormState, opt: dict) -> Optional[str]:
    """Maneja la selección de tipo de segmento NRCS."""
    from hidropluvial.core.tc import SHEET_FLOW_N, SHALLOW_FLOW_K

    seg_type = opt.get("value")
    if not seg_type:
        state.mode = "popup_nrcs_calculator"
        return None

    if seg_type == "sheet":
        # Mostrar opciones de superficie para flujo laminar
        surface_options = [
            {"label": f"Superficie lisa (n={SHEET_FLOW_N['smooth']:.3f})", "description": "concreto, asfalto", "value": ("smooth", SHEET_FLOW_N["smooth"])},
            {"label": f"Suelo desnudo (n={SHEET_FLOW_N['fallow']:.2f})", "description": "barbecho", "value": ("fallow", SHEET_FLOW_N["fallow"])},
            {"label": f"Pasto corto (n={SHEET_FLOW_N['short_grass']:.2f})", "description": "", "value": ("short_grass", SHEET_FLOW_N["short_grass"])},
            {"label": f"Pasto denso (n={SHEET_FLOW_N['dense_grass']:.2f})", "description": "", "value": ("dense_grass", SHEET_FLOW_N["dense_grass"])},
            {"label": f"Bosque ralo (n={SHEET_FLOW_N['light_woods']:.2f})", "description": "", "value": ("light_woods", SHEET_FLOW_N["light_woods"])},
            {"label": f"Bosque denso (n={SHEET_FLOW_N['dense_woods']:.2f})", "description": "", "value": ("dense_woods", SHEET_FLOW_N["dense_woods"])},
        ]
        state.submenu_title = "Flujo Laminar - Tipo de superficie"
        state.submenu_options = surface_options
        state.submenu_idx = 0
        state.submenu_callback = lambda o: _handle_nrcs_sheet_surface(state, o)
        state.mode = "popup_submenu"

    elif seg_type == "shallow":
        # Mostrar opciones de superficie para flujo concentrado
        surface_options = [
            {"label": f"Pavimentado (k={SHALLOW_FLOW_K['paved']:.2f} m/s)", "description": "", "value": "paved"},
            {"label": f"Sin pavimentar (k={SHALLOW_FLOW_K['unpaved']:.2f} m/s)", "description": "", "value": "unpaved"},
            {"label": f"Con pasto (k={SHALLOW_FLOW_K['grassed']:.2f} m/s)", "description": "", "value": "grassed"},
            {"label": f"Pasto corto (k={SHALLOW_FLOW_K['short_grass']:.2f} m/s)", "description": "", "value": "short_grass"},
        ]
        state.submenu_title = "Flujo Concentrado - Tipo de superficie"
        state.submenu_options = surface_options
        state.submenu_idx = 0
        state.submenu_callback = lambda o: _handle_nrcs_shallow_surface(state, o)
        state.mode = "popup_submenu"

    elif seg_type == "channel":
        # Mostrar opciones de tipo de canal
        channel_options = [
            {"label": "Canal de concreto liso (n=0.013)", "description": "", "value": 0.013},
            {"label": "Canal de concreto revestido (n=0.017)", "description": "", "value": 0.017},
            {"label": "Canal de tierra limpio (n=0.022)", "description": "", "value": 0.022},
            {"label": "Canal de tierra con vegetación (n=0.030)", "description": "", "value": 0.030},
            {"label": "Arroyo natural limpio (n=0.035)", "description": "", "value": 0.035},
            {"label": "Arroyo con vegetación (n=0.050)", "description": "", "value": 0.050},
            {"label": "Arroyo sinuoso con pozas (n=0.070)", "description": "", "value": 0.070},
        ]
        state.submenu_title = "Flujo en Canal - Tipo"
        state.submenu_options = channel_options
        state.submenu_idx = 0
        state.submenu_callback = lambda o: _handle_nrcs_channel_type(state, o)
        state.mode = "popup_submenu"

    return None


def _handle_nrcs_sheet_surface(state: FormState, opt: dict) -> Optional[str]:
    """Maneja la selección de superficie para flujo laminar."""
    value = opt.get("value")
    if not value:
        state.mode = "popup_nrcs_calculator"
        return None

    _, n_value = value
    default_slope = 0.02
    if state.nrcs_basin and hasattr(state.nrcs_basin, 'slope_pct') and state.nrcs_basin.slope_pct:
        default_slope = state.nrcs_basin.slope_pct / 100

    # Guardar n_value temporalmente en el estado
    state._temp_sheet_n = n_value

    # Pedir longitud y pendiente
    state.inline_input_label = "Flujo Laminar"
    state.inline_input_hint = f"Superficie: n={n_value:.3f}. Máximo 100m."
    state.inline_input_fields = [
        {"label": "Longitud", "type": "float", "unit": "m", "value": 50.0, "required": True, "key": "length"},
        {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
    ]
    state.inline_input_idx = 0
    state.input_buffer = "50"
    state.inline_input_callback = lambda fields: _create_sheet_segment(state, fields, n_value)
    state.mode = "popup_inline_input"

    return None


def _create_sheet_segment(state: FormState, fields: List[dict], n_value: float) -> Optional[str]:
    """Crea un segmento de flujo laminar."""
    from hidropluvial.config import SheetFlowSegment

    length = None
    slope = None
    for f in fields:
        if f.get("key") == "length":
            length = f.get("value")
        elif f.get("key") == "slope":
            slope = f.get("value")

    if length and slope and length <= 100:
        seg = SheetFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            p2_mm=state.nrcs_p2_mm,
        )
        state.nrcs_segments.append(seg)
        state.nrcs_selected_idx = len(state.nrcs_segments) - 1
        state.nrcs_message = "Segmento laminar agregado"
    elif length and length > 100:
        state.nrcs_message = "Error: Longitud máxima 100m para flujo laminar"

    state.mode = "popup_nrcs_calculator"
    return None


def _handle_nrcs_shallow_surface(state: FormState, opt: dict) -> Optional[str]:
    """Maneja la selección de superficie para flujo concentrado."""
    surface = opt.get("value")
    if not surface:
        state.mode = "popup_nrcs_calculator"
        return None

    default_slope = 0.02
    if state.nrcs_basin and hasattr(state.nrcs_basin, 'slope_pct') and state.nrcs_basin.slope_pct:
        default_slope = state.nrcs_basin.slope_pct / 100

    # Pedir longitud y pendiente
    state.inline_input_label = "Flujo Concentrado"
    state.inline_input_hint = f"Superficie: {surface}"
    state.inline_input_fields = [
        {"label": "Longitud", "type": "float", "unit": "m", "value": 200.0, "required": True, "key": "length"},
        {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
    ]
    state.inline_input_idx = 0
    state.input_buffer = "200"
    state.inline_input_callback = lambda fields: _create_shallow_segment(state, fields, surface)
    state.mode = "popup_inline_input"

    return None


def _create_shallow_segment(state: FormState, fields: List[dict], surface: str) -> Optional[str]:
    """Crea un segmento de flujo concentrado."""
    from hidropluvial.config import ShallowFlowSegment

    length = None
    slope = None
    for f in fields:
        if f.get("key") == "length":
            length = f.get("value")
        elif f.get("key") == "slope":
            slope = f.get("value")

    if length and slope:
        seg = ShallowFlowSegment(
            length_m=length,
            slope=slope,
            surface=surface,
        )
        state.nrcs_segments.append(seg)
        state.nrcs_selected_idx = len(state.nrcs_segments) - 1
        state.nrcs_message = "Segmento concentrado agregado"

    state.mode = "popup_nrcs_calculator"
    return None


def _handle_nrcs_channel_type(state: FormState, opt: dict) -> Optional[str]:
    """Maneja la selección de tipo de canal."""
    n_value = opt.get("value")
    if not n_value:
        state.mode = "popup_nrcs_calculator"
        return None

    default_slope = 0.005
    if state.nrcs_basin and hasattr(state.nrcs_basin, 'slope_pct') and state.nrcs_basin.slope_pct:
        default_slope = state.nrcs_basin.slope_pct / 200  # Mitad de la pendiente de la cuenca

    # Pedir longitud, pendiente y radio hidráulico
    state.inline_input_label = "Flujo en Canal"
    state.inline_input_hint = f"Manning n={n_value:.3f}"
    state.inline_input_fields = [
        {"label": "Longitud", "type": "float", "unit": "m", "value": 500.0, "required": True, "key": "length"},
        {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
        {"label": "Radio hidráulico", "type": "float", "unit": "m", "value": 0.5, "required": True, "key": "radius"},
    ]
    state.inline_input_idx = 0
    state.input_buffer = "500"
    state.inline_input_callback = lambda fields: _create_channel_segment(state, fields, n_value)
    state.mode = "popup_inline_input"

    return None


def _create_channel_segment(state: FormState, fields: List[dict], n_value: float) -> Optional[str]:
    """Crea un segmento de flujo en canal."""
    from hidropluvial.config import ChannelFlowSegment

    length = None
    slope = None
    radius = None
    for f in fields:
        if f.get("key") == "length":
            length = f.get("value")
        elif f.get("key") == "slope":
            slope = f.get("value")
        elif f.get("key") == "radius":
            radius = f.get("value")

    if length and slope and radius:
        seg = ChannelFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            hydraulic_radius_m=radius,
        )
        state.nrcs_segments.append(seg)
        state.nrcs_selected_idx = len(state.nrcs_segments) - 1
        state.nrcs_message = "Segmento de canal agregado"

    state.mode = "popup_nrcs_calculator"
    return None


def _handle_nrcs_p2_selection(state: FormState, opt: dict) -> Optional[str]:
    """Maneja la selección de P2."""
    value = opt.get("value")

    if value == "custom":
        # Mostrar input para valor personalizado
        state.inline_input_label = "Precipitación P₂"
        state.inline_input_hint = "Precipitación de 2 años, 24 horas (mm)"
        state.inline_input_fields = [
            {"label": "P₂", "type": "float", "unit": "mm", "value": None, "required": True, "key": "p2"},
        ]
        state.inline_input_idx = 0
        state.input_buffer = str(state.nrcs_p2_mm)
        state.inline_input_callback = lambda fields: _set_nrcs_p2_custom(state, fields)
        state.mode = "popup_inline_input"
    elif value:
        state.nrcs_p2_mm = value
        state.nrcs_message = f"P₂ actualizado a {value:.0f} mm"
        state.mode = "popup_nrcs_calculator"

    return None


def _set_nrcs_p2_custom(state: FormState, fields: List[dict]) -> Optional[str]:
    """Establece P2 desde valor personalizado."""
    for f in fields:
        if f.get("key") == "p2" and f.get("value"):
            state.nrcs_p2_mm = f.get("value")
            state.nrcs_message = f"P₂ actualizado a {state.nrcs_p2_mm:.0f} mm"
            break

    state.mode = "popup_nrcs_calculator"
    return None
