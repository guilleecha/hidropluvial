"""
Visor interactivo de tabla resumen de análisis.

Permite navegar entre análisis usando:
- Flechas arriba/abajo: cambiar análisis seleccionado
- Espacio: marcar/desmarcar para eliminación múltiple
- i: invertir selección
- d: eliminar marcados (o actual si no hay marcados)
- e: editar nota del análisis actual
- Enter: ver ficha detallada del análisis
- q/ESC: salir
"""

from typing import Callable, Optional, Set

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.preview import sparkline


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
            mark_text = Text(mark, style=f"bold red reverse" if is_marked else row_style)
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
            mark_text = Text(mark, style="bold red")
            idx_text = Text(str(real_idx), style="red")
            tc_method_text = Text(tc.method[:12], style="red")
            tc_text = Text(tc_min, style="red")
            x_text = Text(x_str, style="red")
            abst_text = Text(abst_str, style="red")
            storm_text = Text(storm_type, style="red")
            tr_text = Text(str(storm.return_period), style="red")
            p_text = Text(p_total, style="red")
            pe_text = Text(pe, style="red")
            qp_text = Text(qp_str, style="red")
            spark_text = Text(spark, style="red")
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

    # Encabezado
    header_text = Text()
    header_text.append(f"  {session_name} ", style=f"bold {p.secondary}")
    header_text.append(f"({current_idx + 1}/{n_analyses})", style=p.muted)
    if n_analyses > max_visible_rows:
        header_text.append(f" [mostrando {start_idx + 1}-{end_idx}]", style=f"dim {p.muted}")
    if marked_indices:
        header_text.append(f" [{len(marked_indices)} marcados]", style="bold red")

    # Tabla
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
    if confirm_delete:
        # Modo confirmación de eliminación
        nav_text.append(f"  ¿Eliminar {delete_count} análisis? ", style=f"bold {p.accent}")
        nav_text.append("[", style=p.muted)
        nav_text.append("s/y", style=f"bold green")
        nav_text.append("] Confirmar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n/Esc", style=f"bold red")
        nav_text.append("] Cancelar", style=p.muted)
    else:
        # Navegación normal
        nav_text.append("  [", style=p.muted)
        nav_text.append("↑↓", style=f"bold {p.primary}")
        nav_text.append("] Navegar  ", style=p.muted)
        if on_delete:
            nav_text.append("[", style=p.muted)
            nav_text.append("Espacio", style=f"bold {p.primary}")
            nav_text.append("] Marcar  ", style=p.muted)
            nav_text.append("[", style=p.muted)
            nav_text.append("i", style=f"bold {p.primary}")
            nav_text.append("] Invertir  ", style=p.muted)
            nav_text.append("[", style=p.muted)
            nav_text.append("d", style=f"bold {p.primary}")
            nav_text.append("] Eliminar  ", style=p.muted)
        if on_edit_note:
            nav_text.append("[", style=p.muted)
            nav_text.append("e", style=f"bold {p.primary}")
            nav_text.append("] Nota  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("Enter", style=f"bold {p.primary}")
        nav_text.append("] Ficha  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Salir", style=p.muted)

    return Group(
        Text(""),  # Línea vacía arriba
        header_text,
        Text(""),
        table,
        Text(""),
        info_text,
        nav_text,
    )


def interactive_table_viewer(
    analyses: list,
    session_name: str,
    on_edit_note: Optional[Callable[[str, str], Optional[str]]] = None,
    on_delete: Optional[Callable[[str], bool]] = None,
    on_view_detail: Optional[Callable[[int], None]] = None,
    max_visible_rows: int = 25,
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
    - q/ESC: salir

    Args:
        analyses: Lista de AnalysisRun
        session_name: Nombre de la cuenca/sesión
        on_edit_note: Callback(analysis_id, current_note) -> new_note
        on_delete: Callback(analysis_id) -> bool
        on_view_detail: Callback(index) para ver detalle
        max_visible_rows: Máximo de filas visibles en la tabla

    Returns:
        Lista actualizada de análisis
    """
    if not analyses:
        print("  No hay análisis disponibles.")
        return analyses

    console = Console()
    p = get_palette()

    all_analyses = list(analyses)
    current_idx = 0
    pending_delete = False  # Estado de confirmación de eliminación
    marked_indices: Set[int] = set()  # Índices marcados para eliminación

    clear_screen()

    # auto_refresh=False evita el parpadeo constante - solo actualizamos cuando hay cambios
    with Live(console=console, auto_refresh=False, screen=False) as live:
        # Mostrar display inicial
        display = build_display(
            all_analyses,
            current_idx,
            session_name,
            max_visible_rows,
            on_edit_note is not None,
            on_delete is not None,
            marked_indices=marked_indices,
        )
        live.update(display, refresh=True)

        while True:
            # Esperar input (bloqueante)
            key = get_key()

            n_analyses = len(all_analyses)

            if n_analyses == 0:
                live.update(Text("\n  No quedan análisis. Presiona q para salir.\n", style="yellow"), refresh=True)
                if key == 'q' or key == 'esc':
                    break
                continue

            # Modo confirmación de eliminación
            if pending_delete:
                if key in ('s', 'y') and on_delete:
                    # Confirmar eliminación usando el callback
                    # Determinar qué eliminar
                    if marked_indices:
                        indices_to_delete = sorted(marked_indices, reverse=True)
                    else:
                        indices_to_delete = [current_idx]

                    # Eliminar usando el callback (que persiste en DB)
                    deleted_ids = set()
                    for idx in indices_to_delete:
                        if idx < len(all_analyses):
                            analysis = all_analyses[idx]
                            if on_delete(analysis.id):
                                deleted_ids.add(analysis.id)

                    # Reconstruir lista sin los eliminados
                    all_analyses = [a for a in all_analyses if a.id not in deleted_ids]

                    # Limpiar marcas y ajustar índice
                    marked_indices.clear()
                    n_analyses = len(all_analyses)  # Actualizar contador
                    if current_idx >= n_analyses:
                        current_idx = max(0, n_analyses - 1)
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
                    current_idx = (current_idx - 1) % n_analyses
                elif key == 'down':
                    current_idx = (current_idx + 1) % n_analyses
                elif key == 'space' and on_delete:
                    # Marcar/desmarcar actual
                    if current_idx in marked_indices:
                        marked_indices.remove(current_idx)
                    else:
                        marked_indices.add(current_idx)
                elif key == 'i' and on_delete:
                    # Invertir selección
                    all_indices = set(range(n_analyses))
                    marked_indices = all_indices - marked_indices
                elif key == 'enter' and on_view_detail:
                    live.stop()
                    on_view_detail(current_idx)
                    clear_screen()
                    live.start()
                elif key == 'e' and on_edit_note:
                    live.stop()
                    analysis = all_analyses[current_idx]
                    current_note = getattr(analysis, 'note', None) or ""
                    new_note = on_edit_note(analysis.id, current_note)
                    if new_note is not None:
                        analysis.note = new_note if new_note else None
                    clear_screen()
                    live.start()
                elif key == 'd' and on_delete:
                    # Entrar en modo confirmación
                    pending_delete = True
                else:
                    # Tecla no reconocida, no actualizar
                    continue

            # Ajustar índice si está fuera de rango
            if n_analyses > 0 and current_idx >= n_analyses:
                current_idx = n_analyses - 1

            # Calcular cantidad a eliminar
            delete_count = len(marked_indices) if marked_indices else 1

            # Solo actualizar display después de una acción válida
            display = build_display(
                all_analyses,
                current_idx,
                session_name,
                max_visible_rows,
                on_edit_note is not None,
                on_delete is not None,
                confirm_delete=pending_delete,
                marked_indices=marked_indices,
                delete_count=delete_count,
            )
            live.update(display, refresh=True)

    clear_screen()
    console.print(f"\n  Tabla cerrada. Cuenca: {session_name}\n")

    return all_analyses
