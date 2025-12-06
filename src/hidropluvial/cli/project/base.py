"""
Comandos base para gestión de proyectos.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.project import ProjectManager, Project
from hidropluvial.cli.theme import (
    print_project_info, print_basin_info, print_success, print_error,
    print_info, print_projects_table, print_basins_detail_table,
    get_console,
)


# Instancia global del gestor de proyectos
_project_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """Obtiene el gestor de proyectos (singleton)."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager


def project_create(
    name: Annotated[str, typer.Argument(help="Nombre del proyecto")],
    description: Annotated[Optional[str], typer.Option("--desc", "-d", help="Descripción")] = "",
    author: Annotated[Optional[str], typer.Option("--author", "-a", help="Autor")] = "",
    location: Annotated[Optional[str], typer.Option("--location", "-l", help="Ubicación geográfica")] = "",
) -> None:
    """
    Crea un nuevo proyecto hidrológico.

    Un proyecto agrupa múltiples cuencas (basins) para análisis conjunto,
    útil para estudios que involucran varias subcuencas.

    Ejemplo:
        hp project create "Estudio Arroyo Miguelete" --desc "Drenaje pluvial zona norte"
    """
    manager = get_project_manager()

    project = manager.create_project(
        name=name,
        description=description or "",
        author=author or "",
        location=location or "",
    )

    print_success("Proyecto creado")
    print_project_info(
        project_name=project.name,
        project_id=project.id,
        description=project.description,
        author=project.author,
        location=project.location,
        n_basins=0,
        n_analyses=0,
    )
    print_info(f"Usa 'hp project basin-add {project.id}' para agregar cuencas.")


def project_list() -> None:
    """
    Lista todos los proyectos disponibles.

    Muestra ID, nombre, número de cuencas y total de análisis.
    """
    manager = get_project_manager()
    projects = manager.list_projects()

    if not projects:
        print_info("No hay proyectos guardados.")
        print_info("Usa 'hp project create <nombre>' para crear uno nuevo.")
        return

    console = get_console()
    console.print()
    print_projects_table(projects, title=f"Proyectos Disponibles ({len(projects)})")
    console.print()


def project_show(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto (parcial o completo)")],
) -> None:
    """
    Muestra detalles de un proyecto.

    Incluye información del proyecto y listado de cuencas.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        print_error(f"Proyecto '{project_id}' no encontrado.")
        raise typer.Exit(1)

    console = get_console()
    console.print()

    print_project_info(
        project_name=project.name,
        project_id=project.id,
        n_basins=project.n_basins,
        n_analyses=project.total_analyses,
        description=project.description,
        author=project.author,
        location=project.location,
    )

    if project.basins:
        console.print()
        print_basins_detail_table(project.basins, title=f"Cuencas ({project.n_basins})")
    else:
        print_info("(sin cuencas)")

    console.print()


def project_delete(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto a eliminar")],
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
) -> None:
    """
    Elimina un proyecto y todas sus cuencas.

    Esta acción es irreversible.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    if not force:
        msg = f"¿Eliminar proyecto '{project.name}' ({project.n_basins} cuencas)? [y/N]: "
        if not typer.confirm(msg, default=False):
            typer.echo("  Cancelado.\n")
            return

    if manager.delete_project(project.id):
        typer.echo(f"\n  Proyecto '{project.name}' eliminado.\n")
    else:
        typer.echo(f"\n  Error al eliminar proyecto.\n")
        raise typer.Exit(1)


def project_edit(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Nuevo nombre")] = None,
    description: Annotated[Optional[str], typer.Option("--desc", "-d", help="Nueva descripción")] = None,
    author: Annotated[Optional[str], typer.Option("--author", "-a", help="Nuevo autor")] = None,
    location: Annotated[Optional[str], typer.Option("--location", "-l", help="Nueva ubicación")] = None,
    notes: Annotated[Optional[str], typer.Option("--notes", help="Notas")] = None,
) -> None:
    """
    Edita metadatos de un proyecto.

    Solo modifica los campos especificados.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    changes = []

    if name is not None and name != project.name:
        project.name = name
        changes.append(f"Nombre → {name}")

    if description is not None and description != project.description:
        project.description = description
        changes.append(f"Descripción → {description}")

    if author is not None and author != project.author:
        project.author = author
        changes.append(f"Autor → {author}")

    if location is not None and location != project.location:
        project.location = location
        changes.append(f"Ubicación → {location}")

    if notes is not None and notes != project.notes:
        project.notes = notes
        changes.append(f"Notas → {notes}")

    if not changes:
        typer.echo("\n  No se realizaron cambios.\n")
        return

    manager.save_project(project)

    typer.echo(f"\n  Proyecto actualizado:")
    for change in changes:
        typer.echo(f"    - {change}")
    typer.echo("")
