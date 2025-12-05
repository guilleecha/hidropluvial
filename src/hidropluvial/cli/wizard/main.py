"""
Punto de entrada principal del wizard.
"""

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
                "2. Continuar proyecto/cuenca existente",
                "3. Gestionar proyectos y cuencas",
                "4. Ver comandos disponibles",
                "5. Salir",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "5." in choice:
            typer.echo("\nHasta pronto!\n")
            raise typer.Exit()

        try:
            if "1." in choice:
                _new_basin()
            elif "2." in choice:
                continue_project_menu()
            elif "3." in choice:
                manage_projects_menu()
            elif "4." in choice:
                from hidropluvial.cli.commands import show_commands
                show_commands()
        except SystemExit:
            # Capturar typer.Exit para volver al menu principal
            pass


def _new_basin() -> None:
    """Ejecuta el flujo de nueva cuenca."""
    # Recolectar configuracion
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

    # Ejecutar
    typer.echo("\n" + "=" * 60)
    typer.echo("  EJECUTANDO ANALISIS")
    typer.echo("=" * 60 + "\n")

    runner = AnalysisRunner(config)
    project, basin = runner.run()

    # Menu post-ejecucion
    menu = PostExecutionMenu(project, basin, config.c, config.cn, config.length_m)
    menu.show()
