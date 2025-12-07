"""
Comandos CLI para gestión de proyectos hidrológicos.

Un proyecto agrupa múltiples cuencas (basins) para análisis conjunto.
"""

import typer

from hidropluvial.cli.project.base import (
    get_project_manager,
    project_create,
    project_list,
    project_show,
    project_delete,
    project_edit,
)
from hidropluvial.cli.project.basin import (
    basin_add,
    basin_list,
    basin_show,
    basin_delete,
    basin_import,
)
from hidropluvial.cli.project.migrate import (
    migrate_sessions,
)
from hidropluvial.cli.project.report import (
    project_report,
)

# Crear sub-aplicación
project_app = typer.Typer(help="Gestión de proyectos hidrológicos")

# Comandos de proyecto
project_app.command("create")(project_create)
project_app.command("list")(project_list)
project_app.command("show")(project_show)
project_app.command("delete")(project_delete)
project_app.command("edit")(project_edit)

# Comandos de cuencas (basin)
project_app.command("basin-add")(basin_add)
project_app.command("basin-list")(basin_list)
project_app.command("basin-show")(basin_show)
project_app.command("basin-delete")(basin_delete)
project_app.command("basin-import")(basin_import)

# Comandos de migración
project_app.command("migrate")(migrate_sessions)

# Comandos de reporte
project_app.command("report")(project_report)

__all__ = ["project_app", "get_project_manager"]
