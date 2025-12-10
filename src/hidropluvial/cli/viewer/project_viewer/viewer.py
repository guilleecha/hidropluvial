"""
Visor interactivo unificado de proyectos y cuencas.

Vista de dos paneles con navegación por Tab:
- Panel superior: Proyectos
- Panel inferior: Cuencas del proyecto seleccionado

Navegación:
- Tab: Cambiar foco entre paneles
- Flechas arriba/abajo: Navegar en el panel activo
- Enter: En proyectos -> ir a cuencas; En cuencas -> ver análisis
- Espacio: Marcar/desmarcar para eliminación múltiple
- d: Eliminar marcados (o actual si no hay marcados)
- e: Editar proyecto o cuenca según panel activo
- n: Nuevo proyecto o cuenca según panel activo
- q/ESC: Salir
"""

from typing import Optional, Set

from rich.text import Text
from rich.live import Live

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.project import ProjectManager, Project

from .state import ActivePanel, PopupMode
from .builders import build_unified_display
from .popups import get_importable_projects
from .actions import (
    edit_project,
    create_new_project,
    edit_basin,
    edit_basin_metadata,
    edit_basin_params,
    create_new_basin,
    do_import_basin,
    view_basin_analyses,
)


def interactive_project_viewer(
    project_manager: ProjectManager,
    max_visible_rows: int = 20,
) -> None:
    """
    Visor interactivo unificado de proyectos y cuencas.

    Navegación:
    - Tab: Cambiar foco entre panel de proyectos y cuencas
    - Flechas arriba/abajo: Navegar en el panel activo
    - Espacio: Marcar/desmarcar para eliminación
    - d: Eliminar marcados (o actual)
    - e: Editar proyecto o cuenca
    - n: Nuevo proyecto o cuenca
    - Enter: Ver análisis (solo cuencas)
    - q/ESC: Salir
    """
    console = get_console()
    p = get_palette()

    projects = project_manager.list_projects()
    if not projects:
        console.print("\n  No hay proyectos.\n", style=p.warning)
        return

    # Estado del visor
    project_idx = 0
    basin_idx = 0
    project_marked: Set[int] = set()
    basin_marked: Set[int] = set()
    active_panel = ActivePanel.PROJECTS
    pending_delete = False
    # Estado del popup multinivel
    popup_mode = PopupMode.NONE
    popup_idx = 0
    import_source_project: Optional[Project] = None

    def load_selected_project() -> Optional[Project]:
        if not projects:
            return None
        proj_id = projects[project_idx]["id"]
        return project_manager.get_project(proj_id)

    selected_project = load_selected_project()

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_unified_display(
            projects, project_idx, project_marked,
            selected_project, basin_idx, basin_marked,
            active_panel,
        )
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_projects = len(projects)
            basins = selected_project.basins if selected_project else []
            n_basins = len(basins)

            if n_projects == 0:
                live.update(Text("\n  No quedan proyectos. Presiona q para salir.\n", style=p.warning), refresh=True)
                if key in ('q', 'esc'):
                    break
                continue

            # Modo popup nivel 1: Agregar cuenca (Nueva / Importar)
            if popup_mode == PopupMode.ADD_BASIN:
                if key == 'esc':
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                elif key == 'up':
                    popup_idx = (popup_idx - 1) % 2
                elif key == 'down':
                    popup_idx = (popup_idx + 1) % 2
                elif key == 'n':
                    # Nueva cuenca
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                    live.stop()
                    create_new_basin(project_manager, selected_project)
                    selected_project = project_manager.get_project(selected_project.id)
                    projects = project_manager.list_projects()
                    live.start()
                elif key == 'i' or (key == 'enter' and popup_idx == 1):
                    # Importar: ir al nivel 2 (seleccionar proyecto)
                    importable = get_importable_projects(projects, selected_project.id)
                    if importable:
                        popup_mode = PopupMode.SELECT_PROJECT
                        popup_idx = 0
                    # Si no hay proyectos, quedarse en este nivel (el popup mostrará mensaje)
                elif key == 'enter' and popup_idx == 0:
                    # Nueva cuenca
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                    live.stop()
                    create_new_basin(project_manager, selected_project)
                    selected_project = project_manager.get_project(selected_project.id)
                    projects = project_manager.list_projects()
                    live.start()

            # Modo popup nivel 2: Seleccionar proyecto de origen
            elif popup_mode == PopupMode.SELECT_PROJECT:
                importable = get_importable_projects(projects, selected_project.id)
                n_importable = len(importable)

                if key == 'esc':
                    # Volver al nivel 1
                    popup_mode = PopupMode.ADD_BASIN
                    popup_idx = 1  # Mantener en "Importar"
                elif key == 'up' and n_importable > 0:
                    popup_idx = (popup_idx - 1) % n_importable
                elif key == 'down' and n_importable > 0:
                    popup_idx = (popup_idx + 1) % n_importable
                elif key == 'enter' and n_importable > 0:
                    # Seleccionar proyecto y pasar al nivel 3
                    source_proj_id = importable[popup_idx]["id"]
                    import_source_project = project_manager.get_project(source_proj_id)
                    if import_source_project and import_source_project.basins:
                        popup_mode = PopupMode.SELECT_BASIN
                        popup_idx = 0

            # Modo popup nivel 3: Seleccionar cuenca a importar
            elif popup_mode == PopupMode.SELECT_BASIN:
                source_basins = import_source_project.basins if import_source_project else []
                n_source_basins = len(source_basins)

                if key == 'esc':
                    # Volver al nivel 2
                    popup_mode = PopupMode.SELECT_PROJECT
                    popup_idx = 0
                    import_source_project = None
                elif key == 'up' and n_source_basins > 0:
                    popup_idx = (popup_idx - 1) % n_source_basins
                elif key == 'down' and n_source_basins > 0:
                    popup_idx = (popup_idx + 1) % n_source_basins
                elif key == 'enter' and n_source_basins > 0:
                    # Importar la cuenca seleccionada
                    basin_to_import = source_basins[popup_idx]
                    do_import_basin(project_manager, selected_project, basin_to_import)
                    # Cerrar popup y actualizar
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                    import_source_project = None
                    selected_project = project_manager.get_project(selected_project.id)
                    projects = project_manager.list_projects()

            # Modo popup: Editar cuenca (Metadatos / Parámetros)
            elif popup_mode == PopupMode.EDIT_BASIN:
                if key == 'esc':
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                elif key == 'up':
                    popup_idx = (popup_idx - 1) % 2
                elif key == 'down':
                    popup_idx = (popup_idx + 1) % 2
                elif key == 'm' or (key == 'enter' and popup_idx == 0):
                    # Editar metadatos - directo al formulario
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                    live.stop()
                    edit_basin_metadata(project_manager, basins[basin_idx])
                    selected_project = project_manager.get_project(selected_project.id)
                    projects = project_manager.list_projects()
                    live.start()
                elif key == 'p' or (key == 'enter' and popup_idx == 1):
                    # Editar parámetros - verificar si hay análisis
                    current_basin = basins[basin_idx]
                    n_analyses = len(current_basin.analyses) if current_basin.analyses else 0
                    if n_analyses > 0:
                        # Mostrar popup de confirmación
                        popup_mode = PopupMode.CONFIRM_EDIT_PARAMS
                    else:
                        # Sin análisis, ir directo al editor
                        popup_mode = PopupMode.NONE
                        popup_idx = 0
                        live.stop()
                        edit_basin_params(project_manager, basins[basin_idx])
                        selected_project = project_manager.get_project(selected_project.id)
                        projects = project_manager.list_projects()
                        live.start()

            # Modo popup: Confirmación para editar parámetros (alerta amarilla)
            elif popup_mode == PopupMode.CONFIRM_EDIT_PARAMS:
                if key in ('s', 'y'):
                    # Confirma - proceder a editar parámetros
                    popup_mode = PopupMode.NONE
                    popup_idx = 0
                    live.stop()
                    edit_basin_params(project_manager, basins[basin_idx])
                    selected_project = project_manager.get_project(selected_project.id)
                    projects = project_manager.list_projects()
                    live.start()
                elif key in ('n', 'esc'):
                    # Cancela - volver al popup de edición
                    popup_mode = PopupMode.EDIT_BASIN
                    popup_idx = 1  # Mantener en "Parámetros"

            # Modo confirmación de eliminación
            elif pending_delete:
                if key in ('s', 'y'):
                    if active_panel == ActivePanel.PROJECTS:
                        # Eliminar proyectos
                        indices = sorted(project_marked if project_marked else [project_idx], reverse=True)
                        for idx in indices:
                            if idx < len(projects):
                                project_manager.delete_project(projects[idx]["id"])
                        projects = project_manager.list_projects()
                        project_marked.clear()
                        if project_idx >= len(projects):
                            project_idx = max(0, len(projects) - 1)
                        selected_project = load_selected_project()
                        basin_idx = 0
                        basin_marked.clear()
                    else:
                        # Eliminar cuencas
                        indices = sorted(basin_marked if basin_marked else [basin_idx], reverse=True)
                        for idx in indices:
                            if idx < n_basins:
                                project_manager.delete_basin(selected_project, basins[idx].id)
                        selected_project = project_manager.get_project(selected_project.id)
                        projects = project_manager.list_projects()
                        basin_marked.clear()
                        basins = selected_project.basins if selected_project else []
                        if basin_idx >= len(basins):
                            basin_idx = max(0, len(basins) - 1)
                    pending_delete = False

                elif key in ('n', 'esc'):
                    pending_delete = False
                else:
                    continue

            else:
                # Navegación normal
                if key in ('q', 'esc'):
                    break

                elif key == 'tab':
                    # Cambiar panel activo
                    if active_panel == ActivePanel.PROJECTS:
                        active_panel = ActivePanel.BASINS
                    else:
                        active_panel = ActivePanel.PROJECTS

                elif key == 'up':
                    if active_panel == ActivePanel.PROJECTS and n_projects > 0:
                        project_idx = (project_idx - 1) % n_projects
                        selected_project = load_selected_project()
                        basin_idx = 0
                        basin_marked.clear()
                    elif active_panel == ActivePanel.BASINS and n_basins > 0:
                        basin_idx = (basin_idx - 1) % n_basins

                elif key == 'down':
                    if active_panel == ActivePanel.PROJECTS and n_projects > 0:
                        project_idx = (project_idx + 1) % n_projects
                        selected_project = load_selected_project()
                        basin_idx = 0
                        basin_marked.clear()
                    elif active_panel == ActivePanel.BASINS and n_basins > 0:
                        basin_idx = (basin_idx + 1) % n_basins

                elif key == 'space':
                    if active_panel == ActivePanel.PROJECTS:
                        if project_idx in project_marked:
                            project_marked.remove(project_idx)
                        else:
                            project_marked.add(project_idx)
                    elif n_basins > 0:
                        if basin_idx in basin_marked:
                            basin_marked.remove(basin_idx)
                        else:
                            basin_marked.add(basin_idx)

                elif key == 'i':
                    if active_panel == ActivePanel.PROJECTS:
                        all_indices = set(range(n_projects))
                        project_marked = all_indices - project_marked
                    elif n_basins > 0:
                        all_indices = set(range(n_basins))
                        basin_marked = all_indices - basin_marked

                elif key == 'd':
                    if active_panel == ActivePanel.PROJECTS and n_projects > 0:
                        pending_delete = True
                    elif active_panel == ActivePanel.BASINS and n_basins > 0:
                        pending_delete = True

                elif key == 'e':
                    if active_panel == ActivePanel.PROJECTS:
                        live.stop()
                        edit_project(project_manager, projects[project_idx]["id"])
                        projects = project_manager.list_projects()
                        selected_project = load_selected_project()
                        live.start()
                    elif n_basins > 0:
                        # Mostrar popup de editar cuenca
                        popup_mode = PopupMode.EDIT_BASIN
                        popup_idx = 0

                elif key == 'n':
                    if active_panel == ActivePanel.PROJECTS:
                        live.stop()
                        create_new_project(project_manager)
                        projects = project_manager.list_projects()
                        selected_project = load_selected_project()
                        live.start()
                    else:
                        # Mostrar popup de agregar cuenca (nivel 1)
                        popup_mode = PopupMode.ADD_BASIN
                        popup_idx = 0

                elif key == 'enter':
                    if active_panel == ActivePanel.PROJECTS:
                        # Ir al panel de cuencas del proyecto seleccionado
                        active_panel = ActivePanel.BASINS
                        basin_idx = 0
                        basin_marked.clear()
                    elif active_panel == ActivePanel.BASINS and n_basins > 0:
                        # Ver análisis de la cuenca
                        live.stop()
                        view_basin_analyses(project_manager, selected_project, basins[basin_idx])
                        selected_project = project_manager.get_project(selected_project.id)
                        projects = project_manager.list_projects()
                        live.start()

                else:
                    continue

            # Calcular delete_count
            if active_panel == ActivePanel.PROJECTS:
                delete_count = len(project_marked) if project_marked else 1
            else:
                delete_count = len(basin_marked) if basin_marked else 1

            display = build_unified_display(
                projects, project_idx, project_marked,
                selected_project, basin_idx, basin_marked,
                active_panel,
                confirm_delete=pending_delete,
                delete_count=delete_count,
                popup_mode=popup_mode,
                popup_idx=popup_idx,
                import_source_project=import_source_project,
            )
            live.update(display, refresh=True)

    clear_screen()
