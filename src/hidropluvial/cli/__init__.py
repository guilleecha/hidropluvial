"""
CLI de HidroPluvial - Herramienta de Cálculos Hidrológicos.

Este módulo organiza los comandos CLI en sub-aplicaciones temáticas:
- idf: Análisis de curvas IDF
- storm: Generación de tormentas de diseño
- tc: Cálculo de tiempo de concentración
- runoff: Cálculo de escorrentía
- hydrograph: Generación de hidrogramas
- report: Generación de reportes LaTeX
- export: Exportación de datos
- project: Gestión de proyectos
- basin: Gestión de cuencas (export, report, preview)
- wizard: Asistente interactivo
- commands: Lista de comandos disponibles
"""

import typer

# Crear aplicación principal
app = typer.Typer(
    name="hidropluvial",
    help="Herramienta de cálculos hidrológicos con generación de reportes LaTeX.",
    no_args_is_help=True,
)


def _register_subapps():
    """Registra sub-aplicaciones de forma diferida."""
    from hidropluvial.cli.export import export_app
    from hidropluvial.cli.hydrograph import hydrograph_app
    from hidropluvial.cli.idf import idf_app
    from hidropluvial.cli.report import report_app
    from hidropluvial.cli.runoff import runoff_app
    from hidropluvial.cli.project import project_app
    from hidropluvial.cli.basin import basin_app
    from hidropluvial.cli.storm import storm_app
    from hidropluvial.cli.tc import tc_app

    app.add_typer(idf_app, name="idf")
    app.add_typer(storm_app, name="storm")
    app.add_typer(tc_app, name="tc")
    app.add_typer(runoff_app, name="runoff")
    app.add_typer(hydrograph_app, name="hydrograph")
    app.add_typer(report_app, name="report")
    app.add_typer(export_app, name="export")
    app.add_typer(project_app, name="project")
    app.add_typer(basin_app, name="basin")


@app.command()
def commands():
    """Muestra todos los comandos disponibles con ejemplos."""
    from hidropluvial.cli.commands import show_commands
    show_commands()


@app.command()
def wizard():
    """Asistente interactivo para análisis hidrológicos."""
    from hidropluvial.cli.wizard import wizard_main
    wizard_main()


_subapps_registered = False


@app.callback()
def main():
    """
    HidroPluvial - Cálculos hidrológicos para Uruguay.

    Utiliza las curvas IDF de DINAGUA y metodologías adaptadas
    para drenaje urbano y pluvial.
    """
    global _subapps_registered
    if not _subapps_registered:
        _register_subapps()
        _subapps_registered = True


def get_app():
    """Obtiene la app con todas las sub-aplicaciones registradas."""
    global _subapps_registered
    if not _subapps_registered:
        _register_subapps()
        _subapps_registered = True
    return app


# Exportar para uso externo
__all__ = [
    "app",
    "get_app",
]
