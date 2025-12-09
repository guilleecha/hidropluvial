"""
Punto de entrada principal del wizard.
"""

from typing import Optional

import typer

from hidropluvial.cli.wizard.styles import print_banner
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.wizard.runner import AnalysisRunner
from hidropluvial.cli.wizard.menus import PostExecutionMenu
from hidropluvial.project import Project, get_project_manager
from hidropluvial.cli.theme import (
    print_header, print_section, print_success, print_warning,
    print_info, print_error,
)
from hidropluvial.cli.viewer.menu_panel import (
    menu_panel, MenuItem, confirm_menu,
)
from hidropluvial.cli.viewer.panel_input import panel_text, panel_confirm


def wizard_main() -> None:
    """
    Asistente interactivo para crear analisis hidrologicos.
    """
    print_banner()

    while True:
        # Menu principal con panel interactivo
        items = [
            MenuItem(key="p", label="Proyectos", value="projects", hint="Ver y gestionar proyectos"),
            MenuItem(key="c", label="Crear proyecto", value="create", hint="Nuevo proyecto vacío"),
            MenuItem(key="n", label="Nueva cuenca", value="basin", hint="Crear cuenca con análisis"),
            MenuItem(key="separator1", label="", separator=True),
            MenuItem(key="?", label="Comandos disponibles", value="help", hint="Ver ayuda"),
            MenuItem(key="q", label="Salir", value="exit"),
        ]

        choice = menu_panel(
            title="HidroPluvial",
            items=items,
            subtitle="Herramienta de cálculos hidrológicos",
            allow_back=False,
        )

        if choice is None or choice == "exit":
            print_info("Hasta pronto!")
            raise typer.Exit()

        try:
            if choice == "projects":
                _projects_menu()
            elif choice == "create":
                _create_project()
            elif choice == "basin":
                _new_basin()
            elif choice == "help":
                from hidropluvial.cli.commands import show_commands
                show_commands()
        except SystemExit:
            # Capturar typer.Exit para volver al menu principal
            pass


def _projects_menu() -> None:
    """Muestra el visor interactivo de proyectos."""
    from hidropluvial.cli.viewer.project_viewer import interactive_project_viewer

    project_manager = get_project_manager()
    projects = project_manager.list_projects()

    if not projects:
        print_info("\n  No hay proyectos guardados.")
        print_info("  Usa 'Crear proyecto' o 'Nueva cuenca' para comenzar.\n")
        return

    interactive_project_viewer(project_manager)


def _new_basin() -> None:
    """Ejecuta el flujo de nueva cuenca."""
    project_manager = get_project_manager()

    # Primero preguntar sobre el proyecto
    project = _select_or_create_project_for_basin()
    if project is None:
        return  # Volver al menú principal

    print_success(f"Proyecto seleccionado: {project.name} [{project.id}]")

    # Recolectar configuracion de la cuenca
    config = WizardConfig.from_wizard()
    if config is None:
        return

    # Mostrar resumen y confirmar
    config.print_summary()

    confirmar = panel_confirm(
        title="¿Ejecutar análisis?",
        default=True,
    )

    if not confirmar:
        print_warning("Operacion cancelada")
        return

    # Ejecutar con el proyecto seleccionado
    print_header("EJECUTANDO ANALISIS")

    runner = AnalysisRunner(config, project_id=project.id)
    project, basin = runner.run()

    # Menu post-ejecucion
    menu = PostExecutionMenu(project, basin, config.c, config.cn, config.length_m)
    menu.show()


def _select_or_create_project_for_basin() -> Optional[Project]:
    """Permite seleccionar un proyecto existente o crear uno nuevo para la cuenca."""
    project_manager = get_project_manager()
    projects = project_manager.list_projects()

    # Construir opciones
    items = [
        MenuItem(key="n", label="Crear nuevo proyecto", value="new"),
    ]

    if projects:
        items.append(MenuItem(key="sep", label="", separator=True))
        for idx, p in enumerate(projects):
            key = chr(ord('a') + idx) if idx < 25 else str(idx)
            items.append(MenuItem(
                key=key,
                label=f"{p['name']}",
                value=p['id'],
                hint=f"{p['n_basins']} cuencas",
            ))

    choice = menu_panel(
        title="Seleccionar Proyecto",
        items=items,
        subtitle="¿Dónde crear la cuenca?",
    )

    if choice is None:
        return None

    if choice == "new":
        return _create_project_quick()

    # Proyecto existente seleccionado
    return project_manager.get_project(choice)


def _create_project_quick() -> Optional[Project]:
    """Crea un proyecto de forma rápida (solo nombre obligatorio)."""
    print_section("Nuevo Proyecto")

    name = panel_text(
        title="Nombre del proyecto",
        hint="Identificador único para este proyecto",
    )

    if not name:
        return None

    # Preguntar si quiere agregar más detalles
    add_details = panel_confirm(
        title="¿Agregar descripción, autor y ubicación?",
        default=False,
    )

    description = ""
    author = ""
    location = ""

    if add_details:
        description = panel_text(
            title="Descripción",
            hint="Opcional",
        ) or ""

        author = panel_text(
            title="Autor",
            hint="Opcional",
        ) or ""

        location = panel_text(
            title="Ubicación",
            hint="Opcional",
        ) or ""

    project_manager = get_project_manager()
    project = project_manager.create_project(
        name=name,
        description=description,
        author=author,
        location=location,
    )

    print_success(f"Proyecto creado: {project.name} [{project.id}]")
    return project


def _create_project() -> None:
    """Crea un nuevo proyecto y ofrece opciones para agregar cuencas."""
    print_header("CREAR NUEVO PROYECTO")

    # Solicitar datos del proyecto
    name = panel_text(
        title="Nombre del proyecto",
        hint="Requerido",
    )

    if not name:
        return

    description = panel_text(
        title="Descripción",
        hint="Opcional",
    ) or ""

    author = panel_text(
        title="Autor",
        hint="Opcional",
    ) or ""

    location = panel_text(
        title="Ubicación",
        hint="Opcional",
    ) or ""

    # Crear el proyecto
    project_manager = get_project_manager()
    project = project_manager.create_project(
        name=name,
        description=description,
        author=author,
        location=location,
    )

    print_success(f"Proyecto creado: {project.name} [{project.id}]")

    # Menu post-creacion
    _post_project_creation_menu(project)


def _post_project_creation_menu(project: Project) -> None:
    """Menu de opciones despues de crear un proyecto."""
    from hidropluvial.cli.wizard.menus.basin_management import BasinManagementMenu

    print_info(f"Proyecto '{project.name}' creado exitosamente")
    print_info("Ahora puedes agregar cuencas al proyecto\n")

    # Usar el menú de gestión de cuencas directamente
    menu = BasinManagementMenu(project)
    menu.show()
