"""
Comandos CLI para gestión de cuencas (basins).

Este módulo reemplaza a 'session' con una interfaz más clara.
Los comandos operan sobre cuencas dentro de proyectos.
"""

import typer

from hidropluvial.cli.basin.commands import (
    basin_list,
    basin_show,
    basin_export,
    basin_report,
    basin_preview,
    basin_compare,
    analysis_list,
    analysis_delete,
    analysis_clear,
    analysis_note,
)

# Crear sub-aplicación
basin_app = typer.Typer(help="Gestión de cuencas hidrológicas")

# Registrar comandos de cuenca
basin_app.command("list")(basin_list)
basin_app.command("show")(basin_show)
basin_app.command("export")(basin_export)
basin_app.command("report")(basin_report)
basin_app.command("preview")(basin_preview)
basin_app.command("compare")(basin_compare)

# Registrar comandos de análisis
basin_app.command("analysis-list")(analysis_list)
basin_app.command("analysis-delete")(analysis_delete)
basin_app.command("analysis-clear")(analysis_clear)
basin_app.command("analysis-note")(analysis_note)

__all__ = ["basin_app"]
