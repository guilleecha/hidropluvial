"""
Comandos CLI para gestión de sesiones de análisis.
"""

import typer

from hidropluvial.cli.session.base import (
    get_session_manager,
    session_clean,
    session_create,
    session_delete,
    session_edit,
    session_list,
    session_rename,
    session_show,
    session_summary,
    session_tc,
)
from hidropluvial.cli.session.analyze import session_analyze
from hidropluvial.cli.session.batch import session_batch
from hidropluvial.cli.session.report import session_report
from hidropluvial.cli.session.preview import session_preview
from hidropluvial.cli.session.export import session_export, compare_sessions

# Crear sub-aplicación
session_app = typer.Typer(help="Gestión de sesiones de análisis")

# Registrar comandos
session_app.command("create")(session_create)
session_app.command("list")(session_list)
session_app.command("show")(session_show)
session_app.command("tc")(session_tc)
session_app.command("analyze")(session_analyze)
session_app.command("summary")(session_summary)
session_app.command("preview")(session_preview)
session_app.command("edit")(session_edit)
session_app.command("delete")(session_delete)
session_app.command("clean")(session_clean)
session_app.command("rename")(session_rename)
session_app.command("batch")(session_batch)
session_app.command("report")(session_report)
session_app.command("export")(session_export)
session_app.command("compare")(compare_sessions)

__all__ = ["session_app", "get_session_manager"]
