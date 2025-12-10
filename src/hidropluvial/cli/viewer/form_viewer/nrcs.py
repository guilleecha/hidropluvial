"""
Funciones para la calculadora NRCS (TR-55) integrada en el formulario.
"""

from typing import Any, List, Optional, Callable

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_icons

from .models import FormState


def calc_segment_tc(seg: Any, p2_mm: float) -> float:
    """Calcula Tc de un segmento en horas."""
    from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment
    from hidropluvial.core.tc import (
        nrcs_sheet_flow, nrcs_shallow_flow, nrcs_channel_flow
    )

    try:
        if isinstance(seg, SheetFlowSegment):
            p2 = seg.p2_mm if seg.p2_mm else p2_mm
            return nrcs_sheet_flow(seg.length_m, seg.n, seg.slope, p2)
        elif isinstance(seg, ShallowFlowSegment):
            return nrcs_shallow_flow(seg.length_m, seg.slope, seg.surface)
        elif isinstance(seg, ChannelFlowSegment):
            return nrcs_channel_flow(seg.length_m, seg.n, seg.slope, seg.hydraulic_radius_m)
    except Exception:
        pass
    return 0.0


def format_segment_type(seg: Any) -> str:
    """Formatea el tipo de segmento."""
    from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment

    if isinstance(seg, SheetFlowSegment):
        return "Laminar"
    elif isinstance(seg, ShallowFlowSegment):
        return "Concentrado"
    elif isinstance(seg, ChannelFlowSegment):
        return "Canal"
    return "?"


def format_segment_params(seg: Any) -> str:
    """Formatea los parámetros del segmento."""
    from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment

    if isinstance(seg, SheetFlowSegment):
        return f"n={seg.n:.3f}"
    elif isinstance(seg, ShallowFlowSegment):
        return seg.surface
    elif isinstance(seg, ChannelFlowSegment):
        return f"n={seg.n:.3f} R={seg.hydraulic_radius_m:.2f}m"
    return ""


def build_nrcs_calculator_panel(state: FormState) -> Panel:
    """Construye el panel de la calculadora NRCS."""
    p = get_palette()
    icons = get_icons()

    elements = []

    # Cabecera P2
    header = Text()
    header.append(f"  Precipitación P₂ (2 años, 24h): ", style=p.muted)
    header.append(f"{state.nrcs_p2_mm:.0f} mm", style=f"bold {p.primary}")
    header.append("         ", style="")
    header.append("[p]", style=f"bold {p.accent}")
    header.append(" Cambiar", style=p.muted)
    elements.append(header)
    elements.append(Text(""))

    # Tabla de segmentos
    if state.nrcs_segments:
        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style=f"bold {p.primary}",
            padding=(0, 1),
            expand=False,
        )
        table.add_column("#", style=p.muted, width=3)
        table.add_column("Tipo", width=12)
        table.add_column("Long(m)", justify="right", width=8)
        table.add_column("Pend(%)", justify="right", width=8)
        table.add_column("Parámetros", width=18)
        table.add_column("T(min)", justify="right", width=7)

        for i, seg in enumerate(state.nrcs_segments):
            is_selected = i == state.nrcs_selected_idx
            prefix = ">" if is_selected else " "
            style = f"bold {p.primary}" if is_selected else ""

            tc_seg = calc_segment_tc(seg, state.nrcs_p2_mm)
            tc_min = tc_seg * 60

            table.add_row(
                f"{prefix}{i+1}",
                format_segment_type(seg),
                f"{seg.length_m:.0f}",
                f"{seg.slope * 100:.2f}",
                format_segment_params(seg),
                f"{tc_min:.1f}",
                style=style,
            )

        elements.append(table)

        # Tc total
        tc_total_hr = sum(calc_segment_tc(s, state.nrcs_p2_mm) for s in state.nrcs_segments)
        tc_total_min = tc_total_hr * 60

        elements.append(Text(""))
        total_text = Text()
        total_text.append("  Tc Total = ", style="bold")
        total_text.append(f"{tc_total_min:.1f} min", style=f"bold {p.success}")
        total_text.append(f" ({tc_total_hr:.3f} hr)", style=p.muted)
        elements.append(total_text)
    else:
        no_seg = Text("  (sin segmentos - agrega al menos uno)", style=p.muted)
        elements.append(no_seg)

    elements.append(Text(""))

    # Acciones
    actions = Text()
    actions.append("  [", style=p.muted)
    actions.append("a", style=f"bold {p.accent}")
    actions.append("] Agregar   ", style=p.muted)

    if state.nrcs_segments:
        actions.append("[", style=p.muted)
        actions.append("d", style=f"bold {p.accent}")
        actions.append("] Eliminar", style=p.muted)

    elements.append(actions)

    # Navegación
    nav = Text()
    nav.append("  [", style=p.muted)
    nav.append("↑↓", style=f"bold {p.accent}")
    nav.append("] Seleccionar   ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Enter", style=f"bold {p.nav_confirm}")
    nav.append("] Confirmar   ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Esc", style=f"bold {p.nav_cancel}")
    nav.append("] Cancelar", style=p.muted)
    elements.append(nav)

    # Mensaje de estado
    if state.nrcs_message:
        elements.append(Text(""))
        elements.append(Text(f"  {icons.info} {state.nrcs_message}", style=f"{p.info}"))

    return Panel(
        Group(*elements),
        title=f"[bold {p.primary}] Calculadora NRCS (TR-55) [/]",
        border_style=p.border,
        padding=(1, 2),
    )


