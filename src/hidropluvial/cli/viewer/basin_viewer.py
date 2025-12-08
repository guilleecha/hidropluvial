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

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box

from hidropluvial.cli.theme import get_palette
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

    # Columnas
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("ID", justify="left", width=8)
    table.add_column("Nombre", justify="left", min_width=18)
    table.add_column("Area", justify="right", width=8)
    table.add_column("Pend", justify="right", width=6)
    table.add_column("C", justify="right", width=5)
    table.add_column("CN", justify="right", width=4)
    table.add_column("Long", justify="right", width=8)
    table.add_column("Tc", justify="right", width=6)
    table.add_column("Analisis", justify="right", width=9)

    for idx, basin in enumerate(basins):
        is_selected = idx == selected_idx
        is_marked = idx in marked_indices

        mark = "x" if is_marked else ""

        # Valores
        basin_id = basin.id[:8]
        name = basin.name[:20]
        area = f"{basin.area_ha:.1f}" if basin.area_ha else "-"
        slope = f"{basin.slope_pct:.1f}" if basin.slope_pct else "-"
        c_val = f"{basin.c:.2f}" if basin.c else "-"
        cn_val = f"{basin.cn:.0f}" if basin.cn else "-"
        length = f"{basin.length_m:.0f}" if basin.length_m else "-"

        # Obtener Tc de los resultados si existe
        tc_val = "-"
        if basin.tc_results:
            # Usar el primer Tc disponible
            first_tc = basin.tc_results[0]
            tc_val = f"{first_tc.tc_min:.0f}"

        n_analyses = len(basin.analyses) if basin.analyses else 0

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style="bold red reverse" if is_marked else row_style)
            idx_text = Text(f">{idx}", style=row_style)
            id_text = Text(basin_id, style=row_style)
            name_text = Text(name, style=row_style)
            area_text = Text(area, style=row_style)
            slope_text = Text(slope, style=row_style)
            c_text = Text(c_val, style=row_style)
            cn_text = Text(cn_val, style=row_style)
            length_text = Text(length, style=row_style)
            tc_text = Text(tc_val, style=row_style)
            analyses_text = Text(str(n_analyses), style=row_style)
        elif is_marked:
            mark_text = Text(mark, style="bold red")
            idx_text = Text(str(idx), style="red")
            id_text = Text(basin_id, style="red")
            name_text = Text(name, style="red")
            area_text = Text(area, style="red")
            slope_text = Text(slope, style="red")
            c_text = Text(c_val, style="red")
            cn_text = Text(cn_val, style="red")
            length_text = Text(length, style="red")
            tc_text = Text(tc_val, style="red")
            analyses_text = Text(str(n_analyses), style="red")
        else:
            mark_text = Text(mark)
            idx_text = Text(str(idx), style=p.muted)
            id_text = Text(basin_id, style=p.muted)
            name_text = Text(name)
            area_text = Text(area, style=p.number)
            slope_text = Text(slope, style=p.number)
            c_text = Text(c_val, style=p.number if c_val != "-" else p.muted)
            cn_text = Text(cn_val, style=p.number if cn_val != "-" else p.muted)
            length_text = Text(length, style=p.number if length != "-" else p.muted)
            tc_text = Text(tc_val, style=p.number if tc_val != "-" else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)

        table.add_row(
            mark_text, idx_text, id_text, name_text,
            area_text, slope_text, c_text, cn_text,
            length_text, tc_text, analyses_text,
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
        header_text.append(f" [{len(marked_indices)} marcadas]", style="bold red")

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
        nav_text.append(f"  Eliminar {delete_count} cuenca(s)? ", style=f"bold {p.accent}")
        nav_text.append("[", style=p.muted)
        nav_text.append("s/y", style="bold green")
        nav_text.append("] Confirmar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n/Esc", style="bold red")
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
    console = Console()
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
    import questionary
    from hidropluvial.cli.wizard.styles import get_select_kwargs

    clear_screen()
    print(f"\n  Agregar cuenca al proyecto: {project.name}\n")

    choice = questionary.select(
        "Como deseas agregar la cuenca?",
        choices=[
            "Crear nueva cuenca (wizard completo)",
            "Importar desde otro proyecto",
            "<- Cancelar",
        ],
        **get_select_kwargs(),
    ).ask()

    if choice is None or "Cancelar" in choice:
        return

    if "Crear nueva" in choice:
        _create_new_basin(project_manager, project)
    elif "Importar" in choice:
        _import_basin(project_manager, project)


def _create_new_basin(project_manager: ProjectManager, project: Project) -> None:
    """Crea una nueva cuenca usando el wizard completo."""
    from hidropluvial.cli.wizard.config import WizardConfig
    from hidropluvial.cli.wizard.runner import AnalysisRunner
    from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
    import questionary
    from hidropluvial.cli.wizard.styles import get_confirm_kwargs

    clear_screen()
    print(f"\n  Configurando nueva cuenca para: {project.name}\n")

    config = WizardConfig.from_wizard()
    if config is None:
        return

    config.print_summary()

    if not questionary.confirm(
        "\nEjecutar analisis?",
        default=True,
        **get_confirm_kwargs(),
    ).ask():
        return

    print("\n" + "=" * 60)
    print("  EJECUTANDO ANALISIS")
    print("=" * 60 + "\n")

    runner = AnalysisRunner(config, project_id=project.id)
    updated_project, basin = runner.run()

    print(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

    # Menu post-ejecucion
    menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
    menu.show()


def _import_basin(project_manager: ProjectManager, target_project: Project) -> None:
    """Importa una cuenca desde otro proyecto."""
    import questionary
    from hidropluvial.cli.wizard.styles import get_select_kwargs, get_text_kwargs

    clear_screen()

    # Obtener proyectos con cuencas (excluyendo el actual)
    other_projects = [
        p for p in project_manager.list_projects()
        if p['id'] != target_project.id and p['n_basins'] > 0
    ]

    if not other_projects:
        print("\n  No hay otros proyectos con cuencas disponibles.\n")
        questionary.press_any_key_to_continue("Presiona cualquier tecla...").ask()
        return

    # Seleccionar proyecto origen
    choices = [
        f"{p['id'][:8]} - {p['name']} ({p['n_basins']} cuencas)"
        for p in other_projects
    ]
    choices.append("<- Cancelar")

    print(f"\n  Importar cuenca al proyecto: {target_project.name}\n")

    choice = questionary.select(
        "Selecciona proyecto origen:",
        choices=choices,
        **get_select_kwargs(),
    ).ask()

    if choice is None or "Cancelar" in choice:
        return

    source_id = choice.split(" - ")[0]
    source_project = project_manager.get_project(source_id)

    if not source_project or not source_project.basins:
        print("\n  Proyecto sin cuencas.\n")
        return

    # Seleccionar cuenca
    basin_choices = [
        f"{b.id[:8]} - {b.name} ({len(b.analyses) if b.analyses else 0} analisis)"
        for b in source_project.basins
    ]
    basin_choices.append("<- Cancelar")

    basin_choice = questionary.select(
        "Selecciona cuenca a importar:",
        choices=basin_choices,
        **get_select_kwargs(),
    ).ask()

    if basin_choice is None or "Cancelar" in basin_choice:
        return

    basin_id = basin_choice.split(" - ")[0]
    source_basin = source_project.get_basin(basin_id)

    if not source_basin:
        print("\n  Cuenca no encontrada.\n")
        return

    # Preguntar nombre para la copia
    new_name = questionary.text(
        "Nombre para la cuenca importada:",
        default=source_basin.name,
        **get_text_kwargs(),
    ).ask()

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

    print(f"\n  Cuenca '{new_name}' importada exitosamente.")
    print(f"  Nueva ID: {new_basin.id}")
    print(f"\n  Nota: Los analisis no se copian. Usa 'Agregar analisis' para crear nuevos.\n")
    questionary.press_any_key_to_continue("Presiona cualquier tecla...").ask()


def _view_basin_analyses(project_manager: ProjectManager, project: Project, basin: Basin) -> None:
    """Muestra el menu de trabajo con la cuenca (analisis)."""
    from hidropluvial.cli.wizard.menus.continue_project import ContinueProjectMenu

    # Usar el menu existente pero configurado para esta cuenca
    # single_basin_mode=True hace que "Volver" regrese al visor interactivo
    menu = ContinueProjectMenu()
    menu.project = project
    menu.basin = basin
    menu._show_basin_menu(single_basin_mode=True)
