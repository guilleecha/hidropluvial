"""
Comandos base para gestión de proyectos.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.project import ProjectManager, Project


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

    typer.echo(f"\n  Proyecto creado:")
    typer.echo(f"    ID:          {project.id}")
    typer.echo(f"    Nombre:      {project.name}")
    if project.description:
        typer.echo(f"    Descripción: {project.description}")
    if project.author:
        typer.echo(f"    Autor:       {project.author}")
    if project.location:
        typer.echo(f"    Ubicación:   {project.location}")
    typer.echo(f"\n  Usa 'hp project basin-add {project.id}' para agregar cuencas.\n")


def project_list() -> None:
    """
    Lista todos los proyectos disponibles.

    Muestra ID, nombre, número de cuencas y total de análisis.
    """
    manager = get_project_manager()
    projects = manager.list_projects()

    if not projects:
        typer.echo("\n  No hay proyectos guardados.")
        typer.echo("  Usa 'hp project create <nombre>' para crear uno nuevo.\n")
        return

    typer.echo(f"\n{'='*70}")
    typer.echo(f"  PROYECTOS DISPONIBLES ({len(projects)})")
    typer.echo(f"{'='*70}")
    typer.echo(f"  {'ID':<10} {'Nombre':<30} {'Cuencas':>8} {'Análisis':>10}")
    typer.echo(f"  {'-'*65}")

    for p in projects:
        name = p['name'][:29] if len(p['name']) > 29 else p['name']
        typer.echo(f"  {p['id']:<10} {name:<30} {p['n_basins']:>8} {p['total_analyses']:>10}")

    typer.echo(f"{'='*70}\n")


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
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    typer.echo(f"\n{'='*70}")
    typer.echo(f"  PROYECTO: {project.name}")
    typer.echo(f"{'='*70}")
    typer.echo(f"  ID:          {project.id}")
    typer.echo(f"  Creado:      {project.created_at[:10]}")
    typer.echo(f"  Modificado:  {project.updated_at[:10]}")

    if project.description:
        typer.echo(f"  Descripción: {project.description}")
    if project.author:
        typer.echo(f"  Autor:       {project.author}")
    if project.location:
        typer.echo(f"  Ubicación:   {project.location}")
    if project.tags:
        typer.echo(f"  Tags:        {', '.join(project.tags)}")
    if project.notes:
        typer.echo(f"  Notas:       {project.notes}")

    typer.echo(f"\n  CUENCAS ({project.n_basins}):")
    typer.echo(f"  {'-'*65}")

    if not project.basins:
        typer.echo("  (sin cuencas)")
    else:
        typer.echo(f"  {'ID':<10} {'Nombre':<25} {'Área(ha)':>10} {'Pend(%)':>8} {'Análisis':>10}")
        typer.echo(f"  {'-'*65}")
        for basin in project.basins:
            name = basin.name[:24] if len(basin.name) > 24 else basin.name
            typer.echo(
                f"  {basin.id:<10} {name:<25} {basin.area_ha:>10.1f} "
                f"{basin.slope_pct:>8.1f} {len(basin.analyses):>10}"
            )

    typer.echo(f"{'='*70}\n")


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
