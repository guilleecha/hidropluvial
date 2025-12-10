"""
Visor interactivo de tabla resumen de análisis.

Permite navegar entre análisis usando:
- Flechas arriba/abajo: cambiar análisis seleccionado
- Espacio: marcar/desmarcar para eliminación múltiple
- i: invertir selección
- u: deseleccionar todo
- d: eliminar marcados (o actual si no hay marcados)
- e: editar nota del análisis actual
- Enter: ver ficha detallada del análisis
- q/ESC: salir
"""

from typing import Callable, Optional, Set

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from rich import box

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.preview import sparkline
from hidropluvial.cli.viewer.filters import filter_analyses
from hidropluvial.cli.viewer.filters_inline import (
    InlineFilterState,
    create_filter_state,
    build_filter_panel,
    handle_filter_key,
)


def get_responsive_table_layout(console: Console) -> dict:
    """
    Calcula layout responsive para la tabla basado en tamaño del terminal.

    Returns:
        dict con: max_rows, sparkline_width, compact_mode
    """
    term_width, term_height = console.size

    # Cada fila de tabla ocupa aproximadamente 1 línea
    # Reservar espacio para header (~4), footer (~4), bordes (~4)
    available_rows = term_height - 12

    # Sparkline width basado en ancho disponible
    if term_width >= 140:
        sparkline_width = 16
    elif term_width >= 120:
        sparkline_width = 12
    elif term_width >= 100:
        sparkline_width = 10
    else:
        sparkline_width = 8

    # Modo compacto para terminales estrechas (oculta algunas columnas)
    compact_mode = term_width < 100

    # Limitar filas visibles (máximo 25 para mejor legibilidad)
    max_rows = max(5, min(25, available_rows))

    return {
        "max_rows": max_rows,
        "sparkline_width": sparkline_width,
        "compact_mode": compact_mode,
    }


def build_interactive_table(
    analyses: list,
    selected_idx: int,
    title: str = "RESUMEN DE ANÁLISIS",
    sparkline_width: int = 12,
    start_offset: int = 0,
    marked_indices: Set[int] = None,
) -> Table:
    """
    Construye tabla resumen con fila seleccionada destacada.

    Args:
        analyses: Lista de AnalysisRun
        selected_idx: Índice de fila seleccionada (relativo a analyses)
        title: Título de la tabla
        sparkline_width: Ancho del sparkline
        start_offset: Offset para mostrar índices correctos
        marked_indices: Conjunto de índices marcados para eliminación

    Returns:
        Rich Table
    """
    from hidropluvial.cli.formatters import format_flow

    if marked_indices is None:
        marked_indices = set()

    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas - agregar columna de marca
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("Método Tc", justify="left")
    table.add_column("Tc", justify="right")
    table.add_column("X", justify="right")
    table.add_column("Abst", justify="left")
    table.add_column("Tormenta", justify="left")
    table.add_column("Tr", justify="right")
    table.add_column("P", justify="right")
    table.add_column("Pe", justify="right")
    table.add_column("Qp", justify="right")
    table.add_column("Hidrograma", justify="left")

    # Encontrar Qp máximo
    max_qp = max(a.hydrograph.peak_flow_m3s for a in analyses) if analyses else 0

    for idx, analysis in enumerate(analyses):
        real_idx = idx + start_offset  # Índice real en la lista completa
        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Formatear valores
        tc_min = f"{tc.tc_min:.0f}" if tc.tc_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"

        # Abstracción
        abst_str = "-"
        params = tc.parameters or {}
        if "c" in params:
            abst_str = f"C={params['c']:.2f}"
        elif "cn_adjusted" in params:
            abst_str = f"CN={params['cn_adjusted']:.0f}"
        elif "cn" in params:
            abst_str = f"CN={params['cn']:.0f}"

        # Tormenta
        storm_type = storm.type.upper()[:6]

        # Precipitación
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"

        # Qp
        qp_val = hydro.peak_flow_m3s
        qp_str = format_flow(qp_val)

        # Sparkline
        spark = sparkline(hydro.flow_m3s, width=sparkline_width) if hydro.flow_m3s else "-"

        # Determinar estilo de la fila
        is_selected = idx == selected_idx
        is_marked = real_idx in marked_indices
        is_max_qp = qp_val == max_qp

        # Marca de selección
        mark = "×" if is_marked else ""

        if is_selected:
            # Fila seleccionada: fondo destacado
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style=f"bold {p.marked} reverse" if is_marked else row_style)
            idx_text = Text(f">{real_idx}", style=row_style)
            tc_method_text = Text(tc.method[:12], style=row_style)
            tc_text = Text(tc_min, style=row_style)
            x_text = Text(x_str, style=row_style)
            abst_text = Text(abst_str, style=row_style)
            storm_text = Text(storm_type, style=row_style)
            tr_text = Text(str(storm.return_period), style=row_style)
            p_text = Text(p_total, style=row_style)
            pe_text = Text(pe, style=row_style)
            qp_text = Text(qp_str, style=row_style)
            spark_text = Text(spark, style=row_style)
        elif is_marked:
            # Fila marcada para eliminación
            mark_text = Text(mark, style=f"bold {p.marked}")
            idx_text = Text(str(real_idx), style=p.marked)
            tc_method_text = Text(tc.method[:12], style=p.marked)
            tc_text = Text(tc_min, style=p.marked)
            x_text = Text(x_str, style=p.marked)
            abst_text = Text(abst_str, style=p.marked)
            storm_text = Text(storm_type, style=p.marked)
            tr_text = Text(str(storm.return_period), style=p.marked)
            p_text = Text(p_total, style=p.marked)
            pe_text = Text(pe, style=p.marked)
            qp_text = Text(qp_str, style=p.marked)
            spark_text = Text(spark, style=p.marked)
        else:
            # Fila normal
            mark_text = Text(mark)
            idx_text = Text(str(real_idx), style=p.muted)
            tc_method_text = Text(tc.method[:12])
            tc_text = Text(tc_min, style=p.number)
            x_text = Text(x_str, style=p.number)
            abst_text = Text(abst_str)
            storm_text = Text(storm_type)
            tr_text = Text(str(storm.return_period), style=p.number)
            p_text = Text(p_total, style=p.number)
            pe_text = Text(pe, style=p.number)
            qp_text = Text(qp_str, style=f"bold {p.accent}" if is_max_qp else p.number)
            spark_text = Text(spark, style=p.info)

        table.add_row(
            mark_text,
            idx_text,
            tc_method_text,
            tc_text,
            x_text,
            abst_text,
            storm_text,
            tr_text,
            p_text,
            pe_text,
            qp_text,
            spark_text,
        )

    return table


def build_display(
    all_analyses: list,
    current_idx: int,
    session_name: str,
    max_visible_rows: int,
    on_edit_note: bool,
    on_delete: bool,
    confirm_delete: bool = False,
    marked_indices: Set[int] = None,
    delete_count: int = 0,
    has_add: bool = False,
    has_export: bool = False,
    has_compare: bool = False,
    has_edit_basin: bool = False,
    basin_info: dict = None,
    active_filters: dict = None,
    total_unfiltered: int = None,
    filter_mode: bool = False,
    filter_state: InlineFilterState = None,
    cached_table: Table = None,
) -> Group:
    """Construye el display completo para Live update."""
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()
    n_analyses = len(all_analyses)

    # Calcular ventana visible centrada en current_idx
    if n_analyses <= max_visible_rows:
        start_idx = 0
        end_idx = n_analyses
    else:
        half = max_visible_rows // 2
        start_idx = current_idx - half
        end_idx = start_idx + max_visible_rows

        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible_rows
        elif end_idx > n_analyses:
            end_idx = n_analyses
            start_idx = end_idx - max_visible_rows

    visible_analyses = all_analyses[start_idx:end_idx]
    selected_in_visible = current_idx - start_idx

    # Info de cuenca (si está disponible) - como tabla compacta
    basin_panel = None
    if basin_info:
        basin_table = Table(
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 1),
            expand=False,
        )
        basin_table.add_column("label", style=p.muted)
        basin_table.add_column("value", style=f"bold {p.number}")
        basin_table.add_column("label2", style=p.muted)
        basin_table.add_column("value2", style=f"bold {p.number}")
        basin_table.add_column("label3", style=p.muted)
        basin_table.add_column("value3", style=f"bold {p.number}")

        # Solo datos físicos de la cuenca (C, CN, Tc dependen del análisis)
        area_val = f"{basin_info['area_ha']:.1f} ha" if basin_info.get('area_ha') else "-"
        slope_val = f"{basin_info['slope_pct']:.1f} %" if basin_info.get('slope_pct') else "-"
        length_val = f"{basin_info['length_m']:.0f} m" if basin_info.get('length_m') else "-"
        basin_table.add_row("Área:", area_val, "Pendiente:", slope_val, "Longitud:", length_val)

        basin_panel = Panel(
            basin_table,
            title=f"[bold {p.primary}]{basin_info.get('name', session_name)}[/]",
            border_style=p.border,
            padding=(0, 1),
        )

    # Encabezado
    header_text = Text()
    header_text.append(f"  {session_name} ", style=f"bold {p.secondary}")
    header_text.append(f"({current_idx + 1}/{n_analyses})", style=p.muted)
    # Mostrar info de filtro si está activo
    if active_filters and total_unfiltered and total_unfiltered != n_analyses:
        header_text.append(f" [filtrado: {n_analyses}/{total_unfiltered}]", style=f"bold {p.accent}")
    if n_analyses > max_visible_rows:
        header_text.append(f" [mostrando {start_idx + 1}-{end_idx}]", style=f"dim {p.muted}")
    if marked_indices:
        header_text.append(f" [{len(marked_indices)} marcados]", style=f"bold {p.marked}")

    # Tabla - usar cache en modo filtro para evitar flickering
    if filter_mode and cached_table is not None:
        table = cached_table
    else:
        table = build_interactive_table(
            visible_analyses,
            selected_in_visible,
            start_offset=start_idx,
            title=f"Tabla Resumen - {session_name}",
            marked_indices=marked_indices,
        )

    # Info del seleccionado
    analysis = all_analyses[current_idx]
    info_text = Text()
    info_text.append("  Seleccionado: ", style=p.muted)
    info_text.append(f"[{current_idx}] ", style=f"bold {p.primary}")
    info_text.append(f"{analysis.hydrograph.tc_method} ", style="bold")
    info_text.append(f"{analysis.storm.type} Tr{analysis.storm.return_period}")
    if analysis.note:
        note_preview = analysis.note[:40] + "..." if len(analysis.note) > 40 else analysis.note
        info_text.append(f" - Nota: {note_preview}", style=f"italic {p.muted}")

    # Navegación
    nav_text = Text()
    nav_text2 = Text()  # Segunda línea para más opciones

    if confirm_delete:
        # Modo confirmación de eliminación
        nav_text.append(f"  ¿Eliminar {delete_count} análisis? ", style=f"bold {p.warning}")
        nav_text.append("[", style=p.muted)
        nav_text.append("s/y", style=f"bold {p.nav_confirm}")
        nav_text.append("] Confirmar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n/Esc", style=f"bold {p.nav_cancel}")
        nav_text.append("] Cancelar", style=p.muted)
    else:
        # Navegación normal - línea 1: navegación básica
        nav_text.append("  [", style=p.muted)
        nav_text.append("↑↓", style=f"bold {p.primary}")
        nav_text.append("] Navegar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("Enter", style=f"bold {p.primary}")
        nav_text.append("] Ficha  ", style=p.muted)
        if on_edit_note:
            nav_text.append("[", style=p.muted)
            nav_text.append("e", style=f"bold {p.primary}")
            nav_text.append("] Nota  ", style=p.muted)
        if on_delete:
            nav_text.append("[", style=p.muted)
            nav_text.append("d", style=f"bold {p.primary}")
            nav_text.append("] Eliminar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Salir", style=p.muted)

        # Línea 2: acciones adicionales
        if has_add or has_export or has_compare or has_edit_basin:
            nav_text2.append("  ", style=p.muted)
            if has_add:
                nav_text2.append("[", style=p.muted)
                nav_text2.append("a", style=f"bold {p.accent}")
                nav_text2.append("] +Análisis  ", style=p.muted)
            if has_compare and marked_indices:
                nav_text2.append("[", style=p.muted)
                nav_text2.append("c", style=f"bold {p.accent}")
                nav_text2.append(f"] Comparar ({len(marked_indices)})  ", style=p.muted)
                nav_text2.append("[", style=p.muted)
                nav_text2.append("u", style=f"bold {p.accent}")
                nav_text2.append("] Desmarcar  ", style=p.muted)
            if has_export:
                nav_text2.append("[", style=p.muted)
                nav_text2.append("x", style=f"bold {p.accent}")
                nav_text2.append("] Exportar  ", style=p.muted)
            if has_edit_basin:
                nav_text2.append("[", style=p.muted)
                nav_text2.append("b", style=f"bold {p.accent}")
                nav_text2.append("] Editar cuenca  ", style=p.muted)
            # Siempre mostrar opción de filtro si hay análisis
            nav_text2.append("[", style=p.muted)
            if active_filters:
                nav_text2.append("f", style=f"bold {p.warning}")
                nav_text2.append("] Filtro ✓", style=p.muted)
            else:
                nav_text2.append("f", style=f"bold {p.accent}")
                nav_text2.append("] Filtrar", style=p.muted)

    elements = [Text("")]  # Línea vacía arriba

    # Info de cuenca si está disponible
    if basin_panel:
        elements.append(basin_panel)

    elements.extend([
        header_text,
        Text(""),
        table,
        Text(""),
    ])

    # Mostrar panel de filtros si está en modo filtro
    if filter_mode and filter_state:
        filter_panel = build_filter_panel(
            filter_state,
            filtered_count=n_analyses,
            total_count=total_unfiltered or n_analyses,
        )
        elements.append(filter_panel)
    else:
        # Mostrar info del seleccionado y navegación solo en modo normal
        elements.append(info_text)
        elements.append(nav_text)

        # Agregar segunda línea de navegación si tiene contenido
        if nav_text2.plain:
            elements.append(nav_text2)

    return Group(*elements)


def interactive_table_viewer(
    analyses: list,
    session_name: str,
    on_edit_note: Optional[Callable[[str, str], Optional[str]]] = None,
    on_delete: Optional[Callable[[str], bool]] = None,
    on_view_detail: Optional[Callable[[int, list, dict], None]] = None,
    on_add_analysis: Optional[Callable[[], None]] = None,
    on_export: Optional[Callable[[], None]] = None,
    on_compare: Optional[Callable[[list], None]] = None,
    on_edit_basin: Optional[Callable[[], None]] = None,
    max_visible_rows: int = 25,
    basin_info: dict = None,
) -> list:
    """
    Visor interactivo de tabla resumen.

    Navegación:
    - Flechas arriba/abajo: cambiar análisis seleccionado
    - Espacio: marcar/desmarcar para eliminación
    - i: invertir selección
    - d: eliminar marcados (o actual si no hay marcados)
    - e: editar nota del análisis actual
    - Enter: ver ficha detallada
    - a: agregar análisis
    - x: exportar resultados
    - c: comparar hidrogramas
    - b: editar cuenca
    - f: filtrar análisis
    - q/ESC: salir

    Args:
        analyses: Lista de AnalysisRun
        session_name: Nombre de la cuenca/sesión
        on_edit_note: Callback(analysis_id, current_note) -> new_note
        on_delete: Callback(analysis_id) -> bool
        on_view_detail: Callback(index, filtered_analyses, active_filters) para ver detalle
        on_add_analysis: Callback() para agregar análisis
        on_export: Callback() para exportar
        on_compare: Callback(analyses_list) para comparar hidrogramas marcados
        on_edit_basin: Callback() para editar cuenca
        max_visible_rows: Máximo de filas visibles en la tabla

    Returns:
        Lista actualizada de análisis
    """
    if not analyses:
        print("  No hay análisis disponibles.")
        return analyses

    console = get_console()
    p = get_palette()

    all_analyses = list(analyses)  # Lista original (sin filtrar)
    filtered_analyses = all_analyses  # Lista filtrada (vista actual)
    current_idx = 0
    pending_delete = False  # Estado de confirmación de eliminación
    marked_indices: Set[int] = set()  # Índices marcados para eliminación
    active_filters: dict = {}  # Filtros activos
    filter_mode = False  # Modo de filtro inline
    filter_state: Optional[InlineFilterState] = None  # Estado del filtro
    cached_table: Optional[Table] = None  # Tabla cacheada para modo filtro

    clear_screen()

    # Flags para opciones adicionales
    has_add = on_add_analysis is not None
    has_export = on_export is not None
    has_compare = on_compare is not None
    has_edit_basin = on_edit_basin is not None
    needs_reload = False  # Flag para indicar si hay que recargar análisis

    # Calcular layout responsive inicial
    layout = get_responsive_table_layout(console)
    effective_max_rows = layout["max_rows"] if max_visible_rows == 25 else max_visible_rows

    # auto_refresh=False evita el parpadeo constante - solo actualizamos cuando hay cambios
    with Live(console=console, auto_refresh=False, screen=False) as live:
        # Mostrar display inicial
        display = build_display(
            filtered_analyses,
            current_idx,
            session_name,
            effective_max_rows,
            on_edit_note is not None,
            on_delete is not None,
            marked_indices=marked_indices,
            has_add=has_add,
            has_export=has_export,
            has_compare=has_compare,
            has_edit_basin=has_edit_basin,
            basin_info=basin_info,
            filter_mode=filter_mode,
            filter_state=filter_state,
            active_filters=active_filters,
            total_unfiltered=len(all_analyses),
        )
        live.update(display, refresh=True)

        while True:
            # Esperar input (bloqueante)
            key = get_key()

            n_filtered = len(filtered_analyses)

            if n_filtered == 0:
                # Si hay filtros activos, ofrecer limpiarlos
                if active_filters:
                    live.update(Text("\n  No hay análisis que coincidan con el filtro. Presiona [f] para modificar filtros o [q] para salir.\n", style=p.warning), refresh=True)
                    if key == 'f':
                        # Entrar en modo filtro inline
                        filter_state = create_filter_state(all_analyses, active_filters)
                        if filter_state.categories:
                            filter_mode = True
                    elif key == 'q' or key == 'esc':
                        break
                    continue
                else:
                    live.update(Text("\n  No quedan análisis. Presiona q para salir.\n", style=p.warning), refresh=True)
                    if key == 'q' or key == 'esc':
                        break
                    # Permitir agregar análisis incluso sin análisis existentes
                    if key == 'a' and on_add_analysis:
                        live.stop()
                        on_add_analysis()
                        needs_reload = True
                        break
                    continue

            # Modo filtro inline
            if filter_mode:
                result = handle_filter_key(key, filter_state)
                if result == "apply":
                    # Aplicar filtros y salir de modo filtro
                    active_filters = filter_state.get_filters_dict()
                    if active_filters:
                        filtered_analyses = filter_analyses(all_analyses, active_filters)
                    else:
                        filtered_analyses = all_analyses
                    current_idx = 0
                    marked_indices.clear()
                    filter_mode = False
                    filter_state = None
                    cached_table = None  # Limpiar cache
                elif result == "cancel":
                    # Cancelar sin aplicar cambios
                    filter_mode = False
                    filter_state = None
                    cached_table = None  # Limpiar cache
                # Si result es None, continuar en modo filtro

            # Modo confirmación de eliminación
            elif pending_delete:
                if key in ('s', 'y') and on_delete:
                    # Confirmar eliminación usando el callback
                    # Determinar qué eliminar (de la lista filtrada)
                    if marked_indices:
                        indices_to_delete = sorted(marked_indices, reverse=True)
                    else:
                        indices_to_delete = [current_idx]

                    # Eliminar usando el callback (que persiste en DB)
                    deleted_ids = set()
                    for idx in indices_to_delete:
                        if idx < len(filtered_analyses):
                            analysis = filtered_analyses[idx]
                            if on_delete(analysis.id):
                                deleted_ids.add(analysis.id)

                    # Reconstruir listas sin los eliminados
                    all_analyses = [a for a in all_analyses if a.id not in deleted_ids]
                    filtered_analyses = [a for a in filtered_analyses if a.id not in deleted_ids]

                    # Limpiar marcas y ajustar índice
                    marked_indices.clear()
                    n_filtered = len(filtered_analyses)
                    if current_idx >= n_filtered:
                        current_idx = max(0, n_filtered - 1)
                    pending_delete = False
                elif key in ('n', 'esc'):
                    # Cancelar eliminación
                    pending_delete = False
                else:
                    # Ignorar otras teclas en modo confirmación
                    continue
            else:
                # Navegación normal
                if key == 'q' or key == 'esc':
                    break
                elif key == 'up':
                    current_idx = (current_idx - 1) % n_filtered
                elif key == 'down':
                    current_idx = (current_idx + 1) % n_filtered
                elif key == 'space' and on_delete:
                    # Marcar/desmarcar actual
                    if current_idx in marked_indices:
                        marked_indices.remove(current_idx)
                    else:
                        marked_indices.add(current_idx)
                elif key == 'i' and on_delete:
                    # Invertir selección
                    all_indices = set(range(n_filtered))
                    marked_indices = all_indices - marked_indices
                elif key == 'u' and on_delete and marked_indices:
                    # Deseleccionar todo
                    marked_indices.clear()
                elif key == 'enter' and on_view_detail:
                    live.stop()
                    # Pasar índice en lista filtrada, la lista filtrada y los filtros activos
                    on_view_detail(current_idx, filtered_analyses, active_filters)
                    clear_screen()
                    live.start()
                elif key == 'e' and on_edit_note:
                    live.stop()
                    analysis = filtered_analyses[current_idx]
                    current_note = getattr(analysis, 'note', None) or ""
                    new_note = on_edit_note(analysis.id, current_note)
                    if new_note is not None:
                        analysis.note = new_note if new_note else None
                    clear_screen()
                    live.start()
                elif key == 'd' and on_delete:
                    # Entrar en modo confirmación
                    pending_delete = True
                elif key == 'a' and on_add_analysis:
                    # Agregar análisis
                    live.stop()
                    on_add_analysis()
                    needs_reload = True
                    break
                elif key == 'x' and on_export:
                    # Exportar
                    live.stop()
                    on_export()
                    clear_screen()
                    live.start()
                elif key == 'c' and on_compare and marked_indices:
                    # Comparar hidrogramas (solo los marcados)
                    live.stop()
                    analyses_to_compare = [filtered_analyses[i] for i in sorted(marked_indices)]
                    on_compare(analyses_to_compare)
                    clear_screen()
                    live.start()
                elif key == 'b' and on_edit_basin:
                    # Editar cuenca
                    live.stop()
                    on_edit_basin()
                    needs_reload = True
                    break
                elif key == 'f':
                    # Entrar en modo filtro inline
                    filter_state = create_filter_state(all_analyses, active_filters)
                    if filter_state.categories:
                        filter_mode = True
                        # Calcular ventana visible para cachear tabla
                        if n_filtered <= effective_max_rows:
                            cache_start, cache_end = 0, n_filtered
                        else:
                            half = effective_max_rows // 2
                            cache_start = max(0, current_idx - half)
                            cache_end = cache_start + effective_max_rows
                            if cache_end > n_filtered:
                                cache_end = n_filtered
                                cache_start = cache_end - effective_max_rows
                        # Cachear la tabla actual para evitar flickering
                        cached_table = build_interactive_table(
                            filtered_analyses[cache_start:cache_end],
                            current_idx - cache_start,
                            start_offset=cache_start,
                            title=f"Tabla Resumen - {session_name}",
                            marked_indices=marked_indices,
                        )
                    # Si no hay categorías para filtrar, no hacer nada
                else:
                    # Tecla no reconocida, no actualizar
                    continue

            # Ajustar índice si está fuera de rango
            if n_filtered > 0 and current_idx >= n_filtered:
                current_idx = n_filtered - 1

            # Recalcular layout responsive (por si cambió tamaño del terminal)
            layout = get_responsive_table_layout(console)
            effective_max_rows = layout["max_rows"] if max_visible_rows == 25 else max_visible_rows

            # Calcular cantidad a eliminar
            delete_count = len(marked_indices) if marked_indices else 1

            # Solo actualizar display después de una acción válida
            display = build_display(
                filtered_analyses,
                current_idx,
                session_name,
                effective_max_rows,
                on_edit_note is not None,
                on_delete is not None,
                confirm_delete=pending_delete,
                marked_indices=marked_indices,
                delete_count=delete_count,
                has_add=has_add,
                has_export=has_export,
                has_compare=has_compare,
                has_edit_basin=has_edit_basin,
                basin_info=basin_info,
                active_filters=active_filters,
                total_unfiltered=len(all_analyses),
                filter_mode=filter_mode,
                filter_state=filter_state,
                cached_table=cached_table,
            )
            live.update(display, refresh=True)

    clear_screen()

    # Retornar tupla con lista actualizada y flag de recarga
    return all_analyses, needs_reload
