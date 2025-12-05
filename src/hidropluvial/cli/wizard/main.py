"""
Punto de entrada principal del wizard.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.wizard.runner import AnalysisRunner
from hidropluvial.cli.wizard.menus import (
    PostExecutionMenu,
    continue_project_menu,
    manage_projects_menu,
)
from hidropluvial.project import Project, get_project_manager


def wizard_main() -> None:
    """
    Asistente interactivo para crear analisis hidrologicos.
    """
    typer.echo("""
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Analisis                |
|         Calculos hidrologicos para Uruguay                  |
+-------------------------------------------------------------+
""")

    while True:
        # Menu principal
        choice = questionary.select(
            "Que deseas hacer?",
            choices=[
                "1. Nueva cuenca (analisis guiado)",
                "2. Crear nuevo proyecto",
                "3. Continuar proyecto/cuenca existente",
                "4. Gestionar proyectos y cuencas",
                "5. Ver comandos disponibles",
                "6. Salir",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "6." in choice:
            typer.echo("\nHasta pronto!\n")
            raise typer.Exit()

        try:
            if "1." in choice:
                _new_basin()
            elif "2." in choice:
                _create_project()
            elif "3." in choice:
                continue_project_menu()
            elif "4." in choice:
                manage_projects_menu()
            elif "5." in choice:
                from hidropluvial.cli.commands import show_commands
                show_commands()
        except SystemExit:
            # Capturar typer.Exit para volver al menu principal
            pass


def _new_basin() -> None:
    """Ejecuta el flujo de nueva cuenca."""
    project_manager = get_project_manager()

    # Primero preguntar sobre el proyecto
    project = _select_or_create_project_for_basin()
    if project is None:
        raise typer.Exit()

    typer.echo(f"\n  Proyecto seleccionado: {project.name} [{project.id}]\n")

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
        typer.echo("\nOperacion cancelada.\n")
        raise typer.Exit()

    # Ejecutar con el proyecto seleccionado
    typer.echo("\n" + "=" * 60)
    typer.echo("  EJECUTANDO ANALISIS")
    typer.echo("=" * 60 + "\n")

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
    typer.echo("\n  -- Nuevo Proyecto --\n")

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

    typer.echo(f"\n  Proyecto creado: {project.name} [{project.id}]")
    return project


def _create_project() -> None:
    """Crea un nuevo proyecto y ofrece opciones para agregar cuencas."""
    typer.echo("\n" + "=" * 60)
    typer.echo("  CREAR NUEVO PROYECTO")
    typer.echo("=" * 60 + "\n")

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

    typer.echo(f"\n  Proyecto creado: {project.name} [{project.id}]\n")

    # Menu post-creacion
    _post_project_creation_menu(project)


def _post_project_creation_menu(project: Project) -> None:
    """Menu de opciones despues de crear un proyecto."""
    project_manager = get_project_manager()

    while True:
        choice = questionary.select(
            "Que deseas hacer ahora?",
            choices=[
                "Agregar nueva cuenca al proyecto",
                "Importar cuenca desde otro proyecto",
                "Volver al menu principal (proyecto guardado)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Volver" in choice:
            typer.echo(f"\n  Proyecto '{project.name}' guardado sin cuencas.")
            typer.echo(f"  Puedes agregar cuencas luego desde 'Continuar proyecto'.\n")
            raise typer.Exit()

        if "Agregar nueva" in choice:
            _add_basin_to_project(project)
            # Recargar proyecto
            project = project_manager.get_project(project.id)
        elif "Importar" in choice:
            _import_basin_to_project(project)
            # Recargar proyecto
            project = project_manager.get_project(project.id)


def _add_basin_to_project(project: Project) -> None:
    """Agrega una nueva cuenca al proyecto usando el wizard."""
    typer.echo(f"\n  Agregando cuenca al proyecto: {project.name}\n")

    # Recolectar configuracion
    config = WizardConfig.from_wizard()
    if config is None:
        return

    # Mostrar resumen y confirmar
    config.print_summary()

    confirmar = questionary.confirm(
        "\nEjecutar analisis?",
        default=True,
        style=WIZARD_STYLE,
    ).ask()

    if not confirmar:
        typer.echo("\nOperacion cancelada.\n")
        return

    # Ejecutar con el proyecto existente
    typer.echo("\n" + "=" * 60)
    typer.echo("  EJECUTANDO ANALISIS")
    typer.echo("=" * 60 + "\n")

    runner = AnalysisRunner(config, project_id=project.id)
    updated_project, basin = runner.run()

    typer.echo(f"\n  Cuenca '{basin.name}' agregada al proyecto '{project.name}'.\n")

    # Menu post-ejecucion
    menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
    menu.show()


def _import_basin_to_project(project: Project) -> None:
    """Importa una cuenca desde otro proyecto o sesion legacy."""
    project_manager = get_project_manager()
    from hidropluvial.cli.session.base import get_session_manager
    session_manager = get_session_manager()

    # Listar proyectos y sesiones disponibles
    other_projects = [p for p in project_manager.list_projects() if p['id'] != project.id]
    sessions = session_manager.list_sessions()

    if not other_projects and not sessions:
        typer.echo("\n  No hay otros proyectos ni cuencas disponibles para importar.\n")
        return

    # Construir opciones
    choices = []

    for p in other_projects:
        if p['n_basins'] > 0:
            choices.append(f"[Proyecto] {p['id']} - {p['name']} ({p['n_basins']} cuencas)")

    for s in sessions:
        choices.append(f"[Cuenca legacy] {s['id']} - {s['name']}")

    choices.append("Cancelar")

    choice = questionary.select(
        "Selecciona origen de la cuenca:",
        choices=choices,
        style=WIZARD_STYLE,
    ).ask()

    if choice is None or "Cancelar" in choice:
        return

    if "[Proyecto]" in choice:
        # Seleccionar cuenca del proyecto
        source_id = choice.split(" - ")[0].replace("[Proyecto] ", "")
        source_project = project_manager.get_project(source_id)

        if not source_project or not source_project.basins:
            typer.echo("\n  El proyecto no tiene cuencas.\n")
            return

        basin_choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} analisis)"
            for b in source_project.basins
        ]
        basin_choices.append("Cancelar")

        basin_choice = questionary.select(
            "Selecciona cuenca a importar:",
            choices=basin_choices,
            style=WIZARD_STYLE,
        ).ask()

        if basin_choice is None or "Cancelar" in basin_choice:
            return

        basin_id = basin_choice.split(" - ")[0]
        source_basin = source_project.get_basin(basin_id)

        if source_basin:
            # Copiar la cuenca (crear nueva instancia)
            from hidropluvial.project import Basin
            import json

            # Clonar la cuenca con nuevo ID
            basin_data = source_basin.model_dump()
            basin_data['id'] = None  # Forzar nuevo ID
            new_basin = Basin.model_validate(basin_data)

            project.add_basin(new_basin)
            project_manager.save_project(project)

            typer.echo(f"\n  Cuenca '{new_basin.name}' importada al proyecto '{project.name}'.")
            typer.echo(f"  (Nueva ID: {new_basin.id})\n")

    elif "[Cuenca legacy]" in choice:
        # Importar sesion legacy
        session_id = choice.split(" - ")[0].replace("[Cuenca legacy] ", "")
        session = session_manager.get_session(session_id)

        if session:
            from hidropluvial.project import Basin
            basin = Basin.from_session(session)

            project.add_basin(basin)
            project_manager.save_project(project)

            typer.echo(f"\n  Cuenca '{basin.name}' importada al proyecto '{project.name}'.\n")
