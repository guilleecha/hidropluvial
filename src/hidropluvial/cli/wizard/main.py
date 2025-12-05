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
    continue_session_menu,
    manage_sessions_menu,
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

    # Menu principal
    choice = questionary.select(
        "Que deseas hacer?",
        choices=[
            "1. Nuevo analisis completo (guiado)",
            "2. Continuar sesion existente",
            "3. Gestionar sesiones (ver, eliminar, renombrar)",
            "4. Ver comandos disponibles",
            "5. Salir",
        ],
        style=WIZARD_STYLE,
    ).ask()

    if choice is None or "5." in choice:
        typer.echo("\nHasta pronto!\n")
        raise typer.Exit()

    if "1." in choice:
        _new_analysis()
    elif "2." in choice:
        continue_session_menu()
    elif "3." in choice:
        manage_sessions_menu()
    elif "4." in choice:
        from hidropluvial.cli.commands import show_commands
        show_commands()


def _new_analysis() -> None:
    """Ejecuta el flujo de nuevo analisis."""
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
    session = runner.run()

    # Menu post-ejecucion
    menu = PostExecutionMenu(session, config.c, config.cn, config.length_m)
    menu.show()
