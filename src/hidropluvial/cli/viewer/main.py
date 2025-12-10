"""
Visor interactivo principal de fichas de análisis.

Permite navegar entre análisis usando:
- Flechas izquierda/derecha: cambiar análisis secuencialmente
- e: editar nota del análisis actual
- d: eliminar análisis actual
- p: ver tabla de ponderación (si existe)
- q/ESC: salir

Nota: Los filtros se heredan del listado de análisis (table_viewer).
"""

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.viewer.components import build_analysis_list, build_info_panel
from hidropluvial.cli.viewer.filters import format_active_filters
from hidropluvial.cli.viewer.plots import build_combined_plot
from hidropluvial.cli.viewer.detail_view import show_weighted_view


def get_responsive_layout(console: Console) -> dict:
    """
    Calcula layout responsive basado en tamaño del terminal.

    Returns:
        dict con: width, height_hyeto, height_hydro, show_table, max_table_rows
    """
    term_width, term_height = console.size

    # Ancho del gráfico: máximo 90, mínimo 50, dejando margen
    plot_width = max(50, min(90, term_width - 4))

    # Alturas base para cada componente:
    # - Tabla: ~8-10 líneas (con encabezado y borde)
    # - Info panel: ~12 líneas
    # - Hietograma: 8-10 líneas
    # - Hidrograma: 10-14 líneas
    # - Nav bar: 2 líneas
    # Total mínimo: ~40 líneas

    if term_height >= 50:
        # Terminal grande: todo con espacio
        height_hyeto = 10
        height_hydro = 14
        show_table = True
        max_table_rows = 6
    elif term_height >= 42:
        # Terminal mediana: gráficos estándar
        height_hyeto = 8
        height_hydro = 12
        show_table = True
        max_table_rows = 5
    elif term_height >= 35:
        # Terminal pequeña: gráficos compactos, tabla mínima
        height_hyeto = 7
        height_hydro = 10
        show_table = True
        max_table_rows = 3
    else:
        # Terminal muy pequeña: sin tabla, gráficos mínimos
        height_hyeto = 6
        height_hydro = 9
        show_table = False
        max_table_rows = 0

    return {
        "width": plot_width,
        "height_hyeto": height_hyeto,
        "height_hydro": height_hydro,
        "show_table": show_table,
        "max_table_rows": max_table_rows,
    }


def build_viewer_display(
    analysis,
    session_name: str,
    current_idx: int,
    filtered_analyses: list,
    active_filters: dict,
    layout: dict,
    plot_width: int,
    p,
    on_edit_note: callable = None,
    on_delete: callable = None,
    has_weighted_data: bool = False,
) -> Group:
    """
    Construye el display completo del visor como un Group de Rich.

    Returns:
        Group con todos los componentes renderizables
    """
    n_analyses = len(filtered_analyses)
    components = []

    # Lista de análisis (solo si hay más de 1 y cabe en pantalla)
    if n_analyses > 1 and layout["show_table"]:
        filter_info = format_active_filters(active_filters)

        title_text = Text()
        title_text.append(f" {session_name} ", style=f"bold {p.secondary}")
        if active_filters:
            title_text.append(f"({n_analyses} filtrados)", style=f"italic {p.accent}")
        else:
            title_text.append(f"({n_analyses})", style=p.muted)
        if filter_info:
            title_text.append(filter_info, style=f"italic {p.accent}")

        list_table = build_analysis_list(
            filtered_analyses, current_idx, max_visible=layout["max_table_rows"]
        )
        list_panel = Panel(
            list_table,
            title=title_text,
            title_align="left",
            border_style=p.border,
            box=box.ROUNDED,
            padding=(0, 0),
        )
        components.append(list_panel)

    # Panel de información compacto
    info_panel = build_info_panel(analysis, session_name, current_idx, n_analyses)
    components.append(info_panel)

    # Gráficos (como texto plano envuelto en Text)
    plot_text = build_combined_plot(
        analysis,
        width=plot_width,
        height_hyeto=layout["height_hyeto"],
        height_hydro=layout["height_hydro"],
    )
    components.append(Text.from_ansi(plot_text))

    # Instrucciones de navegación
    nav_text = Text()
    nav_text.append("  [", style=p.muted)
    nav_text.append("↑↓←→", style=f"bold {p.primary}")
    nav_text.append("] Navegar  ", style=p.muted)
    if has_weighted_data:
        nav_text.append("[", style=p.muted)
        nav_text.append("p", style=f"bold {p.primary}")
        nav_text.append("] Ponderación  ", style=p.muted)
    if on_edit_note:
        nav_text.append("[", style=p.muted)
        nav_text.append("e", style=f"bold {p.primary}")
        nav_text.append("] Nota  ", style=p.muted)
    if on_delete:
        nav_text.append("[", style=p.muted)
        nav_text.append("d", style=f"bold {p.primary}")
        nav_text.append("] Eliminar  ", style=p.muted)
    nav_text.append("[", style=p.muted)
    nav_text.append("q", style=f"bold {p.nav_cancel}")
    nav_text.append("] Volver", style=p.muted)
    components.append(nav_text)

    return Group(*components)


def interactive_hydrograph_viewer(
    analyses: list,
    session_name: str,
    width: int = None,  # Ahora opcional, se calcula responsive
    height: int = None,  # Deprecated, se ignora
    on_edit_note: callable = None,
    on_delete: callable = None,
    start_index: int = 0,
    basin_id: str = None,
    db=None,
    inherited_filters: dict = None,
) -> list:
    """
    Visor interactivo de fichas de análisis.

    Permite navegar entre análisis con las flechas del teclado.
    Muestra lista de análisis arriba, luego panel de info y gráficos.

    Los filtros se heredan del listado de análisis (table_viewer) y no se
    pueden modificar desde este visor. Para cambiar filtros, volver al listado.

    Navegación:
    - Flechas izquierda/derecha: cambiar análisis secuencialmente
    - Flechas arriba/abajo: cambiar análisis secuencialmente
    - e: editar nota del análisis actual
    - d: eliminar análisis actual
    - p: ver tabla de ponderación (si existe)
    - q/ESC: volver al listado

    Args:
        analyses: Lista de AnalysisRun (ya filtrada si se heredan filtros)
        session_name: Nombre de la sesión/cuenca
        width: Ancho del gráfico
        height: Alto del gráfico (no usado, se usan alturas fijas)
        on_edit_note: Callback(analysis_id, current_note) -> new_note para editar nota
        on_delete: Callback(analysis_id) -> bool para eliminar análisis
        start_index: Índice inicial del análisis a mostrar
        basin_id: ID de la cuenca (para obtener datos de ponderación)
        db: DatabaseConnection (para obtener datos de ponderación)
        inherited_filters: Filtros heredados del listado (solo para mostrar info)

    Returns:
        Lista actualizada de análisis (puede haber cambiado si se eliminaron)
    """
    if not analyses:
        print("  No hay análisis disponibles.")
        return analyses

    console = get_console()
    p = get_palette()

    # Estado del visor - los análisis ya vienen filtrados
    filtered_analyses = list(analyses)  # Copia para poder modificar
    current_idx = min(start_index, len(filtered_analyses) - 1) if filtered_analyses else 0
    active_filters = inherited_filters or {}

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        while True:
            # Calcular layout responsive en cada iteración (por si cambia tamaño)
            layout = get_responsive_layout(console)
            plot_width = width if width else layout["width"]

            n_analyses = len(filtered_analyses)

            # Si no quedan análisis, salir
            if n_analyses == 0:
                break

            # Ajustar índice si está fuera de rango
            if current_idx >= n_analyses:
                current_idx = n_analyses - 1

            analysis = filtered_analyses[current_idx]

            # Verificar si hay datos de ponderación para este análisis
            has_weighted_data = False
            if db and basin_id:
                tc_params = analysis.tc.parameters or {}
                runoff_method = tc_params.get("runoff_method", "")
                if runoff_method == "racional" or "c" in tc_params:
                    weighted = db.get_weighted_coefficient(basin_id, "c")
                    has_weighted_data = bool(weighted and weighted.get("items"))
                elif runoff_method == "scs-cn" or "cn_adjusted" in tc_params:
                    weighted = db.get_weighted_coefficient(basin_id, "cn")
                    has_weighted_data = bool(weighted and weighted.get("items"))

            # Construir y mostrar display completo
            display = build_viewer_display(
                analysis=analysis,
                session_name=session_name,
                current_idx=current_idx,
                filtered_analyses=filtered_analyses,
                active_filters=active_filters,
                layout=layout,
                plot_width=plot_width,
                p=p,
                on_edit_note=on_edit_note,
                on_delete=on_delete,
                has_weighted_data=has_weighted_data,
            )
            live.update(display, refresh=True)

            # Esperar input
            key = get_key()

            if key == 'q' or key == 'esc':
                break
            elif key in ('left', 'up'):
                current_idx = (current_idx - 1) % n_analyses
            elif key in ('right', 'down'):
                current_idx = (current_idx + 1) % n_analyses
            elif key == 'e' and on_edit_note:
                # Editar nota del análisis actual
                live.stop()
                analysis = filtered_analyses[current_idx]
                current_note = getattr(analysis, 'note', None) or ""
                new_note = on_edit_note(analysis.id, current_note)
                if new_note is not None:
                    analysis.note = new_note if new_note else None
                clear_screen()
                live.start()
            elif key == 'd' and on_delete:
                # Eliminar análisis actual
                live.stop()
                analysis = filtered_analyses[current_idx]
                if on_delete(analysis.id):
                    # Eliminar de la lista filtrada
                    filtered_analyses = [a for a in filtered_analyses if a.id != analysis.id]
                    # Ajustar índice
                    if current_idx >= len(filtered_analyses):
                        current_idx = max(0, len(filtered_analyses) - 1)
                    # Si no quedan análisis, salir
                    if not filtered_analyses:
                        console.print("\n  Todos los análisis visibles han sido eliminados.\n")
                        return filtered_analyses
                clear_screen()
                live.start()
            elif key == 'p' and has_weighted_data:
                # Ver tabla de ponderación de C o CN
                live.stop()
                analysis = filtered_analyses[current_idx]
                show_weighted_view(
                    analysis=analysis,
                    basin_id=basin_id,
                    session_name=session_name,
                    db=db,
                )
                clear_screen()
                live.start()

    clear_screen()
    return filtered_analyses
