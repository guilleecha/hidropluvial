"""
Configuración inline de segmentos NRCS para el formulario de análisis.

Muestra los segmentos en un popup del formulario, permitiendo:
- Ver templates guardados
- Agregar/eliminar segmentos
- Guardar configuración como template
- Todo sin salir de la vista principal (sin clear_screen)
"""

from typing import Optional, List, TYPE_CHECKING, Callable
from dataclasses import dataclass, field

from rich.text import Text

from hidropluvial.cli.theme import get_palette, get_icons
from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment
from hidropluvial.core.tc import nrcs_velocity_method, SHEET_FLOW_N, SHALLOW_FLOW_K

if TYPE_CHECKING:
    from hidropluvial.models import Basin
    from hidropluvial.models.basin import NRCSTemplate
    from hidropluvial.cli.viewer.form_viewer import FormState, FormField


@dataclass
class NRCSPopupState:
    """Estado del popup NRCS."""
    segments: List = field(default_factory=list)
    p2_mm: float = 50.0
    template_name: Optional[str] = None  # Nombre del template usado
    template_id: Optional[int] = None  # ID del template usado
    message: str = ""


# Estado global para el popup NRCS (compartido entre callbacks)
_nrcs_state: Optional[NRCSPopupState] = None


def get_nrcs_state() -> NRCSPopupState:
    """Obtiene el estado actual del popup NRCS."""
    global _nrcs_state
    if _nrcs_state is None:
        _nrcs_state = NRCSPopupState()
    return _nrcs_state


def reset_nrcs_state() -> None:
    """Reinicia el estado del popup NRCS."""
    global _nrcs_state
    _nrcs_state = None


def set_nrcs_state(segments: List, p2_mm: float, template_name: str = None, template_id: int = None) -> None:
    """Establece el estado del popup NRCS."""
    global _nrcs_state
    _nrcs_state = NRCSPopupState(
        segments=list(segments) if segments else [],
        p2_mm=p2_mm,
        template_name=template_name,
        template_id=template_id,
    )


def build_nrcs_summary(segments: List, p2_mm: float) -> str:
    """Construye un resumen de la configuración NRCS."""
    if not segments:
        return "Sin configurar"

    tc_hr = nrcs_velocity_method(segments, p2_mm)
    tc_min = tc_hr * 60
    n_segments = len(segments)

    return f"{n_segments} seg, Tc={tc_min:.1f}min"


def format_segment_info(seg, idx: int) -> str:
    """Formatea la información de un segmento para mostrar."""
    if isinstance(seg, SheetFlowSegment):
        return f"#{idx+1} Laminar L={seg.length_m}m n={seg.n:.3f}"
    elif isinstance(seg, ShallowFlowSegment):
        return f"#{idx+1} Concentrado L={seg.length_m}m {seg.surface}"
    elif isinstance(seg, ChannelFlowSegment):
        return f"#{idx+1} Canal L={seg.length_m}m n={seg.n:.3f} R={seg.hydraulic_radius_m}m"
    return f"#{idx+1} ?"


def build_nrcs_popup_options(
    basin: "Basin",
    form_state: "FormState",
    on_segments_changed: Callable[[], None] = None,
) -> List[dict]:
    """
    Construye las opciones del popup NRCS para el formulario.

    Args:
        basin: Cuenca actual
        form_state: Estado del formulario (para modificar modos)
        on_segments_changed: Callback cuando cambian los segmentos

    Returns:
        Lista de opciones para el popup
    """
    p = get_palette()
    icons = get_icons()
    state = get_nrcs_state()

    # Inicializar P2 si no está configurado
    if state.p2_mm is None:
        state.p2_mm = basin.p2_mm or 50.0

    options = []

    # ─── Templates guardados ───
    templates = getattr(basin, 'nrcs_templates', []) or []
    if templates:
        options.append({
            "separator": True,
            "title": "Templates guardados",
        })

        for tmpl in templates:
            tc_summary = build_nrcs_summary(tmpl.segments, tmpl.p2_mm)
            is_selected = (state.template_id == tmpl.id)

            def make_load_template(t):
                def load_template():
                    set_nrcs_state(
                        segments=list(t.segments),
                        p2_mm=t.p2_mm,
                        template_name=t.name,
                        template_id=t.id,
                    )
                    if on_segments_changed:
                        on_segments_changed()
                    return "__reload__"
                return load_template

            options.append({
                "key": "",
                "label": f"{icons.check if is_selected else ' '} {tmpl.name}",
                "hint": tc_summary,
                "action": make_load_template(tmpl),
            })

    # ─── Configuración actual ───
    options.append({
        "separator": True,
        "title": "Configuración actual",
    })

    # P2
    options.append({
        "key": "p",
        "label": f"P₂ = {state.p2_mm:.0f} mm",
        "hint": "Cambiar",
        "action": lambda: _show_p2_submenu(basin, form_state),
    })

    # Segmentos actuales
    if state.segments:
        for idx, seg in enumerate(state.segments):
            seg_info = format_segment_info(seg, idx)

            def make_delete_segment(i):
                def delete_segment():
                    s = get_nrcs_state()
                    if i < len(s.segments):
                        s.segments.pop(i)
                        s.template_name = None  # Ya no es del template
                        s.template_id = None
                        if on_segments_changed:
                            on_segments_changed()
                    return "__reload__"
                return delete_segment

            options.append({
                "key": str(idx + 1),
                "label": seg_info,
                "hint": "[Del] Eliminar",
                "action": make_delete_segment(idx),
            })

        # Mostrar Tc calculado
        tc_hr = nrcs_velocity_method(state.segments, state.p2_mm)
        tc_min = tc_hr * 60
        options.append({
            "separator": True,
            "title": f"Tc = {tc_min:.1f} min ({tc_hr:.3f} hr)",
        })
    else:
        options.append({
            "key": "",
            "label": "(sin segmentos)",
            "hint": "Agrega segmentos abajo",
            "disabled": True,
        })

    # ─── Agregar segmento ───
    options.append({
        "separator": True,
        "title": "Agregar segmento",
    })

    options.append({
        "key": icons.add,
        "label": "Flujo laminar",
        "hint": "máx 100m, superficie inicial",
        "action": lambda: _show_add_segment_form(basin, form_state, "sheet", on_segments_changed),
    })

    options.append({
        "key": icons.add,
        "label": "Flujo concentrado",
        "hint": "cunetas, zanjas",
        "action": lambda: _show_add_segment_form(basin, form_state, "shallow", on_segments_changed),
    })

    options.append({
        "key": icons.add,
        "label": "Flujo en canal",
        "hint": "arroyos, canales",
        "action": lambda: _show_add_segment_form(basin, form_state, "channel", on_segments_changed),
    })

    # ─── Acciones ───
    if state.segments:
        options.append({
            "separator": True,
            "title": "Acciones",
        })

        # Guardar como template
        if not state.template_id:  # Solo si no es un template existente
            options.append({
                "key": "g",
                "label": "Guardar como template",
                "hint": "Reutilizar esta configuración",
                "action": lambda: _show_save_template_form(basin, form_state),
            })

    return options


def _show_p2_submenu(basin: "Basin", form_state: "FormState"):
    """Muestra el submenú para seleccionar P2."""
    state = get_nrcs_state()

    # Estimar P2 desde P3,10 si está disponible
    p2_estimated = None
    if basin.p3_10:
        p2_estimated = basin.p3_10 * 0.5

    submenu_options = []

    if p2_estimated:
        submenu_options.append({
            "label": f"Estimado: {p2_estimated:.1f} mm",
            "description": "Desde P3,10",
            "value": p2_estimated,
        })

    submenu_options.extend([
        {"label": "50 mm", "description": "Valor típico Uruguay", "value": 50.0},
        {"label": "40 mm", "description": "Zona semiárida", "value": 40.0},
        {"label": "60 mm", "description": "Zona húmeda", "value": 60.0},
        {"label": "Otro valor", "description": "Ingresar manualmente", "value": "custom"},
    ])

    def on_p2_selected(opt):
        s = get_nrcs_state()
        if opt.get("value") == "custom":
            # Mostrar input inline
            form_state.inline_input_label = "Precipitación P₂"
            form_state.inline_input_hint = "Precipitación de 2 años, 24 horas (mm)"
            form_state.inline_input_fields = [
                {"label": "P₂", "type": "float", "unit": "mm", "value": None, "required": True},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = ""
            form_state.inline_input_callback = lambda fields: _on_p2_input(fields)
            form_state.mode = "popup_inline_input"
        else:
            s.p2_mm = opt.get("value", 50.0)
            form_state.mode = "popup"
            return "__reload__"

    form_state.submenu_title = "Seleccionar P₂"
    form_state.submenu_options = submenu_options
    form_state.submenu_idx = 0
    form_state.submenu_callback = on_p2_selected
    form_state.mode = "popup_submenu"

    return None


def _on_p2_input(fields: List[dict]):
    """Callback cuando se ingresa P2 manualmente."""
    state = get_nrcs_state()
    if fields and fields[0].get("value"):
        state.p2_mm = fields[0]["value"]
    return "__reload__"


def _show_add_segment_form(
    basin: "Basin",
    form_state: "FormState",
    segment_type: str,
    on_segments_changed: Callable[[], None] = None,
):
    """Muestra el formulario inline para agregar un segmento."""
    state = get_nrcs_state()

    # Definir campos según tipo de segmento
    if segment_type == "sheet":
        form_state.inline_input_label = "Flujo Laminar"
        form_state.inline_input_hint = "Máximo 100m. Típico: 30-100m en superficie inicial"

        # Submenú para superficie primero
        surface_options = [
            {"label": f"Superficie lisa (n={SHEET_FLOW_N['smooth']:.3f})", "description": "concreto, asfalto", "value": SHEET_FLOW_N["smooth"]},
            {"label": f"Suelo desnudo (n={SHEET_FLOW_N['fallow']:.2f})", "description": "barbecho", "value": SHEET_FLOW_N["fallow"]},
            {"label": f"Pasto corto (n={SHEET_FLOW_N['short_grass']:.2f})", "description": "", "value": SHEET_FLOW_N["short_grass"]},
            {"label": f"Pasto denso (n={SHEET_FLOW_N['dense_grass']:.2f})", "description": "", "value": SHEET_FLOW_N["dense_grass"]},
            {"label": f"Bosque ralo (n={SHEET_FLOW_N['light_woods']:.2f})", "description": "", "value": SHEET_FLOW_N["light_woods"]},
            {"label": f"Bosque denso (n={SHEET_FLOW_N['dense_woods']:.2f})", "description": "", "value": SHEET_FLOW_N["dense_woods"]},
        ]

        def on_surface_selected(opt):
            n_value = opt.get("value")
            default_slope = basin.slope_pct / 100 if basin.slope_pct else 0.02

            form_state.inline_input_label = "Flujo Laminar"
            form_state.inline_input_hint = f"Superficie: n={n_value:.3f}"
            form_state.inline_input_fields = [
                {"label": "Longitud", "type": "float", "unit": "m", "value": 50.0, "required": True, "key": "length"},
                {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = "50"

            def on_sheet_input(fields):
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
                        p2_mm=state.p2_mm,
                    )
                    state.segments.append(seg)
                    state.template_name = None
                    state.template_id = None
                    if on_segments_changed:
                        on_segments_changed()
                return "__reload__"

            form_state.inline_input_callback = on_sheet_input
            form_state.mode = "popup_inline_input"

        form_state.submenu_title = "Tipo de superficie"
        form_state.submenu_options = surface_options
        form_state.submenu_idx = 0
        form_state.submenu_callback = on_surface_selected
        form_state.mode = "popup_submenu"

    elif segment_type == "shallow":
        # Submenú para superficie
        surface_options = [
            {"label": f"Pavimentado (k={SHALLOW_FLOW_K['paved']:.2f} m/s)", "description": "", "value": "paved"},
            {"label": f"Sin pavimentar (k={SHALLOW_FLOW_K['unpaved']:.2f} m/s)", "description": "", "value": "unpaved"},
            {"label": f"Con pasto (k={SHALLOW_FLOW_K['grassed']:.2f} m/s)", "description": "", "value": "grassed"},
            {"label": f"Pasto corto (k={SHALLOW_FLOW_K['short_grass']:.2f} m/s)", "description": "", "value": "short_grass"},
        ]

        def on_shallow_surface_selected(opt):
            surface = opt.get("value")
            default_slope = basin.slope_pct / 100 if basin.slope_pct else 0.02

            form_state.inline_input_label = "Flujo Concentrado"
            form_state.inline_input_hint = f"Superficie: {surface}"
            form_state.inline_input_fields = [
                {"label": "Longitud", "type": "float", "unit": "m", "value": 200.0, "required": True, "key": "length"},
                {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = "200"

            def on_shallow_input(fields):
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
                    state.segments.append(seg)
                    state.template_name = None
                    state.template_id = None
                    if on_segments_changed:
                        on_segments_changed()
                return "__reload__"

            form_state.inline_input_callback = on_shallow_input
            form_state.mode = "popup_inline_input"

        form_state.submenu_title = "Tipo de superficie"
        form_state.submenu_options = surface_options
        form_state.submenu_idx = 0
        form_state.submenu_callback = on_shallow_surface_selected
        form_state.mode = "popup_submenu"

    elif segment_type == "channel":
        # Submenú para tipo de canal
        channel_options = [
            {"label": "Canal de concreto liso (n=0.013)", "description": "", "value": 0.013},
            {"label": "Canal de concreto revestido (n=0.017)", "description": "", "value": 0.017},
            {"label": "Canal de tierra limpio (n=0.022)", "description": "", "value": 0.022},
            {"label": "Canal de tierra con vegetación (n=0.030)", "description": "", "value": 0.030},
            {"label": "Arroyo natural limpio (n=0.035)", "description": "", "value": 0.035},
            {"label": "Arroyo con vegetación (n=0.050)", "description": "", "value": 0.050},
            {"label": "Arroyo sinuoso con pozas (n=0.070)", "description": "", "value": 0.070},
        ]

        def on_channel_type_selected(opt):
            n_value = opt.get("value")
            default_slope = basin.slope_pct / 100 if basin.slope_pct else 0.005

            form_state.inline_input_label = "Flujo en Canal"
            form_state.inline_input_hint = f"Manning n={n_value:.3f}"
            form_state.inline_input_fields = [
                {"label": "Longitud", "type": "float", "unit": "m", "value": 500.0, "required": True, "key": "length"},
                {"label": "Pendiente", "type": "float", "unit": "m/m", "value": default_slope, "required": True, "key": "slope"},
                {"label": "Radio hidráulico", "type": "float", "unit": "m", "value": 0.5, "required": True, "key": "radius"},
            ]
            form_state.inline_input_idx = 0
            form_state.input_buffer = "500"

            def on_channel_input(fields):
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
                    state.segments.append(seg)
                    state.template_name = None
                    state.template_id = None
                    if on_segments_changed:
                        on_segments_changed()
                return "__reload__"

            form_state.inline_input_callback = on_channel_input
            form_state.mode = "popup_inline_input"

        form_state.submenu_title = "Tipo de canal"
        form_state.submenu_options = channel_options
        form_state.submenu_idx = 0
        form_state.submenu_callback = on_channel_type_selected
        form_state.mode = "popup_submenu"

    return None


def _show_save_template_form(basin: "Basin", form_state: "FormState"):
    """Muestra el formulario para guardar como template."""
    state = get_nrcs_state()

    form_state.inline_input_label = "Guardar Template"
    form_state.inline_input_hint = "Nombre para identificar esta configuración"
    form_state.inline_input_fields = [
        {"label": "Nombre", "type": "text", "value": None, "required": True, "key": "name"},
    ]
    form_state.inline_input_idx = 0
    form_state.input_buffer = ""

    def on_save_template(fields):
        name = None
        for f in fields:
            if f.get("key") == "name":
                name = f.get("value")

        if name and state.segments:
            from hidropluvial.database import get_database
            from hidropluvial.models.basin import NRCSTemplate

            # Guardar en DB
            db = get_database()
            saved_template = db.create_nrcs_template(
                basin_id=basin.id,
                name=name,
                segments=list(state.segments),
                p2_mm=state.p2_mm,
            )

            if saved_template:
                state.template_name = name
                state.template_id = saved_template.get("id")
                # Crear objeto NRCSTemplate y agregarlo a la lista
                new_template = NRCSTemplate(
                    id=saved_template.get("id"),
                    basin_id=basin.id,
                    name=name,
                    p2_mm=state.p2_mm,
                    segments=list(state.segments),
                )
                if not hasattr(basin, 'nrcs_templates') or basin.nrcs_templates is None:
                    basin.nrcs_templates = []
                basin.nrcs_templates.append(new_template)

        return "__reload__"

    form_state.inline_input_callback = on_save_template
    form_state.mode = "popup_inline_input"

    return None


def get_nrcs_tc_parameters() -> Optional[dict]:
    """
    Obtiene los parámetros NRCS para guardar en tc.parameters.

    Returns:
        Dict con p2_mm, segments, template_name, template_id o None si no hay config
    """
    state = get_nrcs_state()

    if not state.segments:
        return None

    return {
        "p2_mm": state.p2_mm,
        "segments": [
            seg.model_dump() if hasattr(seg, 'model_dump') else seg.__dict__
            for seg in state.segments
        ],
        "template_name": state.template_name,
        "template_id": state.template_id,
    }


def get_nrcs_tc_value() -> Optional[float]:
    """
    Obtiene el valor de Tc calculado con NRCS.

    Returns:
        Tc en horas o None si no hay segmentos
    """
    state = get_nrcs_state()

    if not state.segments:
        return None

    return nrcs_velocity_method(state.segments, state.p2_mm)
