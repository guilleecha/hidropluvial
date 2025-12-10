"""
Visor interactivo de cuencas de un proyecto.

Permite navegar entre cuencas usando:
- Flechas arriba/abajo: cambiar cuenca seleccionada
- Espacio: marcar/desmarcar para eliminacion multiple
- i: invertir seleccion
- d: eliminar marcados (o actual si no hay marcados)
- e: editar cuenca (area, pendiente, C, CN)
- Enter: ver analisis de la cuenca
- a: agregar cuenca (nueva o importar)
- q/ESC: volver a proyectos
"""

from typing import Optional, Set

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.project import ProjectManager, Project, Basin


def build_basins_table(
    basins: list[Basin],
    selected_idx: int,
    marked_indices: Set[int] = None,
    project_name: str = "",
) -> Table:
    """
    Construye tabla de cuencas con fila seleccionada destacada.
    """
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()

    table = Table(
        title=f"CUENCAS - {project_name}",
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas - solo datos físicos de la cuenca (C, CN, Tc dependen del análisis)
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("ID", justify="left", width=8)
    table.add_column("Nombre", justify="left", min_width=20)
    table.add_column("Área (ha)", justify="right", width=10)
    table.add_column("Pend (%)", justify="right", width=9)
    table.add_column("Long (m)", justify="right", width=9)
    table.add_column("Análisis", justify="right", width=9)

    for idx, basin in enumerate(basins):
        is_selected = idx == selected_idx
        is_marked = idx in marked_indices

        mark = "x" if is_marked else ""

        # Valores - solo datos físicos
        basin_id = basin.id[:8]
        name = basin.name[:22] if len(basin.name) > 22 else basin.name
        area = f"{basin.area_ha:.2f}" if basin.area_ha else "-"
        slope = f"{basin.slope_pct:.2f}" if basin.slope_pct else "-"
        length = f"{basin.length_m:.0f}" if basin.length_m else "-"
        n_analyses = len(basin.analyses) if basin.analyses else 0

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style=f"bold {p.marked} reverse" if is_marked else row_style)
            idx_text = Text(f">{idx}", style=row_style)
            id_text = Text(basin_id, style=row_style)
            name_text = Text(name, style=row_style)
            area_text = Text(area, style=row_style)
            slope_text = Text(slope, style=row_style)
            length_text = Text(length, style=row_style)
            analyses_text = Text(str(n_analyses), style=row_style)
        elif is_marked:
            mark_text = Text(mark, style=f"bold {p.marked}")
            idx_text = Text(str(idx), style=p.marked)
            id_text = Text(basin_id, style=p.marked)
            name_text = Text(name, style=p.marked)
            area_text = Text(area, style=p.marked)
            slope_text = Text(slope, style=p.marked)
            length_text = Text(length, style=p.marked)
            analyses_text = Text(str(n_analyses), style=p.marked)
        else:
            mark_text = Text(mark)
            idx_text = Text(str(idx), style=p.muted)
            id_text = Text(basin_id, style=p.muted)
            name_text = Text(name)
            area_text = Text(area, style=p.number)
            slope_text = Text(slope, style=p.number)
            length_text = Text(length, style=p.number if length != "-" else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)

        table.add_row(
            mark_text, idx_text, id_text, name_text,
            area_text, slope_text, length_text, analyses_text,
        )

    return table


def build_basins_display(
    project: Project,
    current_idx: int,
    max_visible_rows: int,
    marked_indices: Set[int] = None,
    confirm_delete: bool = False,
    delete_count: int = 0,
) -> Group:
    """Construye el display completo para Live update."""
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()
    basins = project.basins or []
    n_basins = len(basins)

    # Calcular ventana visible
    if n_basins <= max_visible_rows:
        start_idx = 0
        end_idx = n_basins
    else:
        half = max_visible_rows // 2
        start_idx = current_idx - half
        end_idx = start_idx + max_visible_rows

        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible_rows
        elif end_idx > n_basins:
            end_idx = n_basins
            start_idx = end_idx - max_visible_rows

    visible_basins = basins[start_idx:end_idx]
    selected_in_visible = current_idx - start_idx

    # Ajustar marked_indices para la vista
    visible_marked = {i - start_idx for i in marked_indices if start_idx <= i < end_idx}

    # Encabezado
    header_text = Text()
    header_text.append(f"  Proyecto: {project.name} ", style=f"bold {p.secondary}")
    if n_basins > 0:
        header_text.append(f"({current_idx + 1}/{n_basins} cuencas)", style=p.muted)
    else:
        header_text.append("(sin cuencas)", style=p.muted)
    if n_basins > max_visible_rows:
        header_text.append(f" [mostrando {start_idx + 1}-{end_idx}]", style=f"dim {p.muted}")
    if marked_indices:
        header_text.append(f" [{len(marked_indices)} marcadas]", style=f"bold {p.marked}")

    # Tabla (o mensaje si no hay cuencas)
    if n_basins > 0:
        table = build_basins_table(visible_basins, selected_in_visible, visible_marked, project.name)
    else:
        table = Text("\n  No hay cuencas en este proyecto.\n  Presiona [a] para agregar una cuenca.\n", style=p.muted)

    # Info del seleccionado
    info_text = Text()
    if n_basins > 0:
        basin = basins[current_idx]
        info_text.append("  Seleccionada: ", style=p.muted)
        info_text.append(f"[{current_idx}] ", style=f"bold {p.primary}")
        info_text.append(f"{basin.name} ", style="bold")
        n_analyses = len(basin.analyses) if basin.analyses else 0
        info_text.append(f"({n_analyses} analisis)")
        if basin.notes:
            note_preview = basin.notes[:40] + "..." if len(basin.notes) > 40 else basin.notes
            info_text.append(f" - {note_preview}", style=f"italic {p.muted}")

    # Navegacion
    nav_text = Text()
    if confirm_delete:
        nav_text.append(f"  Eliminar {delete_count} cuenca(s)? ", style=f"bold {p.warning}")
        nav_text.append("[", style=p.muted)
        nav_text.append("s/y", style=f"bold {p.nav_confirm}")
        nav_text.append("] Confirmar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n/Esc", style=f"bold {p.nav_cancel}")
        nav_text.append("] Cancelar", style=p.muted)
    else:
        nav_text.append("  [", style=p.muted)
        nav_text.append("^^v", style=f"bold {p.primary}")
        nav_text.append("] Navegar  ", style=p.muted)
        if n_basins > 0:
            nav_text.append("[", style=p.muted)
            nav_text.append("Espacio", style=f"bold {p.primary}")
            nav_text.append("] Marcar  ", style=p.muted)
            nav_text.append("[", style=p.muted)
            nav_text.append("d", style=f"bold {p.primary}")
            nav_text.append("] Eliminar  ", style=p.muted)
            nav_text.append("[", style=p.muted)
            nav_text.append("e", style=f"bold {p.primary}")
            nav_text.append("] Editar  ", style=p.muted)
            nav_text.append("[", style=p.muted)
            nav_text.append("Enter", style=f"bold {p.primary}")
            nav_text.append("] Analisis  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("a", style=f"bold {p.primary}")
        nav_text.append("] Agregar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Volver", style=p.muted)

    return Group(
        Text(""),
        header_text,
        Text(""),
        table,
        Text(""),
        info_text,
        nav_text,
    )


def interactive_basin_viewer(
    project_manager: ProjectManager,
    project: Project,
    max_visible_rows: int = 20,
) -> None:
    """
    Visor interactivo de cuencas de un proyecto.

    Navegacion:
    - Flechas arriba/abajo: cambiar cuenca seleccionada
    - Espacio: marcar/desmarcar para eliminacion
    - i: invertir seleccion
    - d: eliminar marcados (o actual si no hay marcados)
    - e: editar cuenca
    - Enter: ver analisis de la cuenca
    - a: agregar cuenca (nueva o importar)
    - q/ESC: volver a proyectos
    """
    console = get_console()
    p = get_palette()

    current_idx = 0
    pending_delete = False
    marked_indices: Set[int] = set()

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_basins_display(
            project, current_idx, max_visible_rows,
            marked_indices=marked_indices,
        )
        live.update(display, refresh=True)

        while True:
            key = get_key()
            basins = project.basins or []
            n_basins = len(basins)

            # Modo confirmacion de eliminacion
            if pending_delete:
                if key in ('s', 'y'):
                    indices_to_delete = sorted(marked_indices if marked_indices else [current_idx], reverse=True)

                    for idx in indices_to_delete:
                        if idx < len(basins):
                            basin_id = basins[idx].id
                            project_manager.delete_basin(project, basin_id)

                    # Recargar proyecto
                    project = project_manager.get_project(project.id)
                    marked_indices.clear()
                    n_basins = len(project.basins) if project.basins else 0
                    if current_idx >= n_basins:
                        current_idx = max(0, n_basins - 1)
                    pending_delete = False

                elif key in ('n', 'esc'):
                    pending_delete = False
                else:
                    continue
            else:
                # Navegacion normal
                if key in ('q', 'esc'):
                    break
                elif key == 'up' and n_basins > 0:
                    current_idx = (current_idx - 1) % n_basins
                elif key == 'down' and n_basins > 0:
                    current_idx = (current_idx + 1) % n_basins
                elif key == 'space' and n_basins > 0:
                    if current_idx in marked_indices:
                        marked_indices.remove(current_idx)
                    else:
                        marked_indices.add(current_idx)
                elif key == 'i' and n_basins > 0:
                    all_indices = set(range(n_basins))
                    marked_indices = all_indices - marked_indices
                elif key == 'd' and n_basins > 0:
                    pending_delete = True
                elif key == 'e' and n_basins > 0:
                    # Editar cuenca
                    live.stop()
                    basin = basins[current_idx]
                    _edit_basin(project_manager, project, basin)
                    project = project_manager.get_project(project.id)
                    clear_screen()
                    live.start()
                elif key == 'a':
                    # Agregar cuenca
                    live.stop()
                    _add_basin_menu(project_manager, project)
                    project = project_manager.get_project(project.id)
                    clear_screen()
                    live.start()
                elif key == 'enter' and n_basins > 0:
                    # Ver analisis de la cuenca
                    live.stop()
                    basin = basins[current_idx]
                    _view_basin_analyses(project_manager, project, basin)
                    project = project_manager.get_project(project.id)
                    clear_screen()
                    live.start()
                else:
                    continue

            # Ajustar indice
            basins = project.basins or []
            n_basins = len(basins)
            if n_basins > 0 and current_idx >= n_basins:
                current_idx = n_basins - 1

            delete_count = len(marked_indices) if marked_indices else 1

            display = build_basins_display(
                project, current_idx, max_visible_rows,
                marked_indices=marked_indices,
                confirm_delete=pending_delete,
                delete_count=delete_count,
            )
            live.update(display, refresh=True)

    clear_screen()


def _edit_basin(project_manager: ProjectManager, project: Project, basin: Basin) -> None:
    """Edita una cuenca usando CuencaEditor."""
    from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor

    clear_screen()
    editor = CuencaEditor(basin, project_manager)
    editor.edit()


def _add_basin_menu(project_manager: ProjectManager, project: Project) -> None:
    """Menu para agregar cuenca: nueva o importar."""
    from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

    clear_screen()

    items = [
        MenuItem(key="n", label="Nueva cuenca", value="new", hint="Configurar desde cero"),
        MenuItem(key="i", label="Importar cuenca", value="import", hint="Desde otro proyecto"),
    ]

    choice = menu_panel(
        title="Agregar Cuenca",
        items=items,
        subtitle=f"Proyecto: {project.name}",
        allow_back=True,
    )

    if choice is None:
        return

    if choice == "new":
        _create_new_basin(project_manager, project)
    elif choice == "import":
        _import_basin(project_manager, project)


def _create_new_basin(project_manager: ProjectManager, project: Project) -> None:
    """Crea una nueva cuenca."""
    from hidropluvial.cli.wizard.config import WizardConfig
    from hidropluvial.cli.wizard.runner import AnalysisRunner
    from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
    from hidropluvial.cli.theme import print_section, print_header
    from hidropluvial.cli.viewer.panel_input import panel_confirm

    clear_screen()
    print_section(f"Configurar cuenca en: {project.name}")

    config = WizardConfig.from_wizard()
    if config is None:
        return

    config.print_summary()

    if not panel_confirm(title="Ejecutar analisis?", default=True):
        return

    print_header("EJECUTANDO ANALISIS")

    runner = AnalysisRunner(config, project_id=project.id)
    updated_project, basin = runner.run()

    print(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

    # Menu post-ejecucion
    menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
    menu.show()


def _import_basin(project_manager: ProjectManager, target_project: Project) -> None:
    """Importa una cuenca desde otro proyecto."""
    from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
    from hidropluvial.cli.viewer.panel_input import panel_text
    from hidropluvial.cli.theme import print_info, print_success

    clear_screen()

    # Obtener proyectos con cuencas (excluyendo el actual)
    other_projects = [
        p for p in project_manager.list_projects()
        if p['id'] != target_project.id and p['n_basins'] > 0
    ]

    if not other_projects:
        print_info("No hay otros proyectos con cuencas disponibles.")
        return

    # Construir items para seleccion de proyecto
    items = []
    for idx, p in enumerate(other_projects):
        key = chr(ord('a') + idx) if idx < 26 else str(idx)
        items.append(MenuItem(
            key=key,
            label=p['name'],
            value=p['id'],
            hint=f"{p['n_basins']} cuencas",
        ))

    choice = menu_panel(
        title="Seleccionar Proyecto Origen",
        items=items,
        subtitle=f"Importar cuenca a: {target_project.name}",
        allow_back=True,
    )

    if choice is None:
        return

    source_project = project_manager.get_project(choice)

    if not source_project or not source_project.basins:
        print_info("Proyecto sin cuencas.")
        return

    # Construir items para seleccion de cuenca
    basin_items = []
    for idx, b in enumerate(source_project.basins):
        key = chr(ord('a') + idx) if idx < 26 else str(idx)
        n_analyses = len(b.analyses) if b.analyses else 0
        basin_items.append(MenuItem(
            key=key,
            label=b.name,
            value=b.id,
            hint=f"{n_analyses} analisis",
        ))

    basin_choice = menu_panel(
        title="Seleccionar Cuenca",
        items=basin_items,
        subtitle=f"Desde: {source_project.name}",
        allow_back=True,
    )

    if basin_choice is None:
        return

    source_basin = source_project.get_basin(basin_choice)

    if not source_basin:
        print_info("Cuenca no encontrada.")
        return

    # Preguntar nombre para la copia
    new_name = panel_text(
        title="Nombre para la cuenca importada",
        default=source_basin.name,
    )

    if not new_name:
        return

    # Crear nueva cuenca con los datos
    new_basin = project_manager.create_basin(
        project=target_project,
        name=new_name,
        area_ha=source_basin.area_ha,
        slope_pct=source_basin.slope_pct,
        p3_10=source_basin.p3_10,
        c=source_basin.c,
        cn=source_basin.cn,
        length_m=source_basin.length_m,
    )

    print_success(f"Cuenca '{new_name}' importada exitosamente")
    print_info(f"Nueva ID: {new_basin.id}")
    print_info("Los analisis no se copian. Usa 'Agregar analisis' para crear nuevos.")


def _view_basin_analyses(project_manager: ProjectManager, project: Project, basin: Basin) -> None:
    """Muestra el menu de trabajo con la cuenca (analisis)."""
    from hidropluvial.cli.wizard.menus.continue_project import ContinueProjectMenu

    # Usar el menu existente pero configurado para esta cuenca
    # single_basin_mode=True hace que "Volver" regrese al visor interactivo
    menu = ContinueProjectMenu()
    menu.project = project
    menu.basin = basin
    menu._show_basin_menu(single_basin_mode=True)
