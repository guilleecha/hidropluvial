"""
Visor interactivo principal de fichas de análisis.

Permite navegar entre análisis usando:
- Flechas izquierda/derecha: cambiar análisis secuencialmente
- f: abrir menú de filtros
- c: limpiar filtros
- q/ESC: salir
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.viewer.components import build_analysis_list, build_info_panel
from hidropluvial.cli.viewer.filters import (
    filter_analyses,
    show_filter_menu,
    format_active_filters,
)
from hidropluvial.cli.viewer.plots import plot_combined


def interactive_hydrograph_viewer(
    analyses: list,
    session_name: str,
    width: int = 75,
    height: int = 16,
) -> None:
    """
    Visor interactivo de fichas de análisis.

    Permite navegar entre análisis con las flechas del teclado.
    Muestra lista de análisis arriba, luego panel de info y gráficos.

    Navegación:
    - Flechas izquierda/derecha: cambiar análisis secuencialmente
    - f: abrir menú de filtros
    - c: limpiar filtros (solo si hay filtros activos)
    - q/ESC: salir

    Args:
        analyses: Lista de AnalysisRun
        session_name: Nombre de la sesión/cuenca
        width: Ancho del gráfico
        height: Alto del gráfico (no usado, se usan alturas fijas)
    """
    if not analyses:
        print("  No hay análisis disponibles.")
        return

    console = Console()
    p = get_palette()

    # Estado del visor
    all_analyses = analyses
    filtered_analyses = analyses
    current_idx = 0
    active_filters = {}

    while True:
        clear_screen()

        n_analyses = len(filtered_analyses)

        # Manejo de filtros vacíos
        if n_analyses == 0:
            console.print("\n  [yellow]No hay análisis que coincidan con los filtros.[/yellow]")
            console.print("  Presiona [bold]f[/bold] para cambiar filtros o [bold]q[/bold] para salir.\n")
            key = get_key()
            if key == 'q' or key == 'esc':
                break
            elif key == 'f':
                active_filters, filtered_analyses = show_filter_menu(
                    console, all_analyses, active_filters
                )
                current_idx = 0
            elif key == 'c' and active_filters:
                active_filters = {}
                filtered_analyses = all_analyses
                current_idx = 0
            continue

        # Ajustar índice si está fuera de rango
        if current_idx >= n_analyses:
            current_idx = n_analyses - 1

        analysis = filtered_analyses[current_idx]

        # PRIMERO: Lista de análisis (compacta, arriba)
        if len(all_analyses) > 1:
            filter_info = format_active_filters(active_filters)

            title_text = Text()
            title_text.append(f" {session_name} ", style=f"bold {p.secondary}")
            title_text.append(f"({n_analyses}/{len(all_analyses)} análisis)", style=p.muted)
            if filter_info:
                title_text.append(filter_info, style=f"italic {p.accent}")

            list_table = build_analysis_list(filtered_analyses, current_idx)
            list_panel = Panel(
                list_table,
                title=title_text,
                title_align="left",
                border_style=p.border,
                box=box.ROUNDED,
                padding=(0, 0),
            )
            console.print(list_panel)

        # SEGUNDO: Panel de información compacto
        info_panel = build_info_panel(analysis, session_name, current_idx, n_analyses)
        console.print(info_panel)

        # TERCERO: Gráficos (reducidos para que quepa todo)
        plot_combined(
            analysis,
            width=width,
            height_hyeto=8,
            height_hydro=12,
        )

        # Instrucciones de navegación
        nav_text = Text()
        nav_text.append("  [", style=p.muted)
        nav_text.append("←→", style=f"bold {p.primary}")
        nav_text.append("] Navegar  [", style=p.muted)
        nav_text.append("f", style=f"bold {p.primary}")
        nav_text.append("] Filtrar  ", style=p.muted)
        if active_filters:
            nav_text.append("[", style=p.muted)
            nav_text.append("c", style=f"bold {p.primary}")
            nav_text.append("] Limpiar filtro  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Salir", style=p.muted)
        console.print(nav_text)

        # Esperar input
        key = get_key()

        if key == 'q' or key == 'esc':
            clear_screen()
            console.print(f"\n  Visor cerrado. Cuenca: {session_name}\n")
            break
        elif key == 'left':
            current_idx = (current_idx - 1) % n_analyses
        elif key == 'right':
            current_idx = (current_idx + 1) % n_analyses
        elif key == 'f':
            active_filters, filtered_analyses = show_filter_menu(
                console, all_analyses, active_filters
            )
            current_idx = 0
        elif key == 'c' and active_filters:
            # Limpiar filtros
            active_filters = {}
            filtered_analyses = all_analyses
            current_idx = 0
