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
- session: Gestión de sesiones de análisis
"""

import typer

from hidropluvial.cli.export import export_app
from hidropluvial.cli.hydrograph import hydrograph_app
from hidropluvial.cli.idf import idf_app
from hidropluvial.cli.report import report_app
from hidropluvial.cli.runoff import runoff_app
from hidropluvial.cli.session import session_app  # Importa desde subpaquete
from hidropluvial.cli.storm import storm_app
from hidropluvial.cli.tc import tc_app

# Crear aplicación principal
app = typer.Typer(
    name="hidropluvial",
    help="Herramienta de cálculos hidrológicos con generación de reportes LaTeX.",
    no_args_is_help=True,
)

# Registrar sub-aplicaciones
app.add_typer(idf_app, name="idf")
app.add_typer(storm_app, name="storm")
app.add_typer(tc_app, name="tc")
app.add_typer(runoff_app, name="runoff")
app.add_typer(hydrograph_app, name="hydrograph")
app.add_typer(report_app, name="report")
app.add_typer(export_app, name="export")
app.add_typer(session_app, name="session")


@app.callback()
def main():
    """
    HidroPluvial - Cálculos hidrológicos para Uruguay.

    Utiliza las curvas IDF de DINAGUA y metodologías adaptadas
    para drenaje urbano y pluvial.
    """
    pass


# Exportar para uso externo
__all__ = [
    "app",
    "idf_app",
    "storm_app",
    "tc_app",
    "runoff_app",
    "hydrograph_app",
    "report_app",
    "export_app",
    "session_app",
]
