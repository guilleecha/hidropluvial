"""
Punto de entrada principal del wizard.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE, print_banner
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.wizard.runner import AnalysisRunner
from hidropluvial.cli.wizard.menus import PostExecutionMenu
from hidropluvial.project import Project, get_project_manager
from hidropluvial.cli.theme import (
    print_header, print_section, print_success, print_warning,
    print_info, print_error,
)


def wizard_main() -> None:
    """
    Asistente interactivo para crear analisis hidrologicos.
    """
    print_banner()

    while True:
        # Menu principal
        choice = questionary.select(
            "Que deseas hacer?",
            choices=[
                "1. Proyectos",
                "2. Crear proyecto",
                "3. Nueva cuenca",
                "4. Ver comandos disponibles",
                "5. Salir",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "5." in choice:
            print_info("Hasta pronto!")
            raise typer.Exit()

        try:
            if "1." in choice:
                _projects_menu()
            elif "2." in choice:
                _create_project()
            elif "3." in choice:
                _new_basin()
            elif "4." in choice:
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
        raise typer.Exit()

    print_success(f"Proyecto seleccionado: {project.name} [{project.id}]")

    # Recolectar configuracion de la cuenca
    config = WizardConfig.from_wizard()
    if config is None:
        raise typer.Exit()

    # Mostrar resumen y confirmar
    config.print_summary()

    confirmar = questionary.confirm(
        "\nEjecutar analisis?",
        default=True,
        style=WIZARD_STYLE,
    ).ask()

    if not confirmar:
        print_warning("Operacion cancelada")
        raise typer.Exit()

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
    choices = ["Crear nuevo proyecto"]

    if projects:
        choices.append("--- Proyectos existentes ---")
        for p in projects:
            choices.append(f"{p['id']} - {p['name']} ({p['n_basins']} cuencas)")

    choices.append("← Volver al menu principal")

    choice = questionary.select(
        "Donde deseas crear la cuenca?",
        choices=choices,
        style=WIZARD_STYLE,
    ).ask()

    if choice is None or "Volver" in choice:
        return None

    if "Crear nuevo proyecto" in choice:
        return _create_project_quick()
    elif choice.startswith("---"):
        # Separador, volver a preguntar
        return _select_or_create_project_for_basin()
    else:
        # Proyecto existente seleccionado
        project_id = choice.split(" - ")[0]
        return project_manager.get_project(project_id)


def _create_project_quick() -> Optional[Project]:
    """Crea un proyecto de forma rápida (solo nombre obligatorio)."""
    print_section("Nuevo Proyecto")

    name = questionary.text(
        "Nombre del proyecto:",
        validate=lambda x: len(x.strip()) > 0 or "El nombre no puede estar vacio",
        style=WIZARD_STYLE,
    ).ask()

    if name is None:
        return None

    # Preguntar si quiere agregar más detalles
    add_details = questionary.confirm(
        "Agregar descripcion, autor y ubicacion?",
        default=False,
        style=WIZARD_STYLE,
    ).ask()

    description = ""
    author = ""
    location = ""

    if add_details:
        description = questionary.text(
            "Descripcion (opcional):",
            default="",
            style=WIZARD_STYLE,
        ).ask() or ""

        author = questionary.text(
            "Autor (opcional):",
            default="",
            style=WIZARD_STYLE,
        ).ask() or ""

        location = questionary.text(
            "Ubicacion (opcional):",
            default="",
            style=WIZARD_STYLE,
        ).ask() or ""

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
    name = questionary.text(
        "Nombre del proyecto:",
        validate=lambda x: len(x.strip()) > 0 or "El nombre no puede estar vacio",
        style=WIZARD_STYLE,
    ).ask()

    if name is None:
        raise typer.Exit()

    description = questionary.text(
        "Descripcion (opcional):",
        default="",
        style=WIZARD_STYLE,
    ).ask()

    author = questionary.text(
        "Autor (opcional):",
        default="",
        style=WIZARD_STYLE,
    ).ask()

    location = questionary.text(
        "Ubicacion (opcional):",
        default="",
        style=WIZARD_STYLE,
    ).ask()

    # Crear el proyecto
    project_manager = get_project_manager()
    project = project_manager.create_project(
        name=name,
        description=description or "",
        author=author or "",
        location=location or "",
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
