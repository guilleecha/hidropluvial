"""
Comandos de migración de sesiones legacy a proyectos.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.cli.project.base import get_project_manager


def migrate_sessions(
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Nombre para el proyecto")] = None,
    delete_sessions: Annotated[bool, typer.Option("--delete", "-d", help="Eliminar sesiones originales")] = False,
) -> None:
    """
    Migra todas las sesiones existentes a un nuevo proyecto.

    Crea un proyecto nuevo conteniendo todas las sesiones como cuencas.
    Por defecto, las sesiones originales se mantienen.

    Ejemplo:
        hp project migrate --name "Proyecto Migrado"
        hp project migrate --delete  # Elimina sesiones originales
    """
    manager = get_project_manager()

    project_name = name or "Sesiones Migradas"

    typer.echo(f"\n  Buscando sesiones para migrar...")

    project = manager.migrate_sessions_to_project(
        project_name=project_name,
        delete_sessions=delete_sessions,
    )

    if project is None:
        typer.echo("  No se encontraron sesiones para migrar.\n")
        return

    typer.echo(f"\n  Migración completada:")
    typer.echo(f"    Proyecto:    {project.name}")
    typer.echo(f"    ID:          {project.id}")
    typer.echo(f"    Cuencas:     {project.n_basins}")
    typer.echo(f"    Análisis:    {project.total_analyses}")

    if delete_sessions:
        typer.echo(f"\n    Las sesiones originales fueron eliminadas.")
    else:
        typer.echo(f"\n    Las sesiones originales se mantienen.")
        typer.echo(f"    Usa --delete para eliminarlas en futuras migraciones.")

    typer.echo(f"\n  Usa 'hp project show {project.id}' para ver detalles.\n")
