"""
Comandos CLI para gestión de cuencas (basins) dentro de proyectos.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.cli.project.base import get_project_manager


def basin_add(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
    name: Annotated[str, typer.Argument(help="Nombre de la cuenca")],
    area: Annotated[float, typer.Option("--area", "-a", help="Área en hectáreas")] = None,
    slope: Annotated[float, typer.Option("--slope", "-s", help="Pendiente en %")] = None,
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P(3h, Tr=10) en mm")] = None,
    c: Annotated[Optional[float], typer.Option("--c", help="Coeficiente C (método racional)")] = None,
    cn: Annotated[Optional[int], typer.Option("--cn", help="Curve Number")] = None,
    length: Annotated[Optional[float], typer.Option("--length", "-l", help="Longitud cauce (m)")] = None,
) -> None:
    """
    Agrega una cuenca a un proyecto.

    Los parámetros obligatorios (area, slope, p3_10) definen las características
    físicas de la cuenca. C y/o CN son necesarios para el cálculo de escorrentía.

    Ejemplo:
        hp project basin-add abc123 "Subcuenca Norte" --area 50 --slope 2.5 --p3_10 80 --c 0.55
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    # Validar parámetros obligatorios
    if area is None or slope is None or p3_10 is None:
        typer.echo("\n  Error: Faltan parámetros obligatorios.")
        typer.echo("  Uso: hp project basin-add <proyecto> <nombre> --area X --slope Y --p3_10 Z")
        typer.echo("\n  Opciones adicionales: --c, --cn, --length\n")
        raise typer.Exit(1)

    basin = manager.create_basin(
        project=project,
        name=name,
        area_ha=area,
        slope_pct=slope,
        p3_10=p3_10,
        c=c,
        cn=cn,
        length_m=length,
    )

    typer.echo(f"\n  Cuenca agregada al proyecto '{project.name}':")
    typer.echo(f"    ID:        {basin.id}")
    typer.echo(f"    Nombre:    {basin.name}")
    typer.echo(f"    Área:      {basin.area_ha} ha")
    typer.echo(f"    Pendiente: {basin.slope_pct} %")
    typer.echo(f"    P3,10:     {basin.p3_10} mm")
    if basin.c is not None:
        typer.echo(f"    C:         {basin.c}")
    if basin.cn is not None:
        typer.echo(f"    CN:        {basin.cn}")
    if basin.length_m is not None:
        typer.echo(f"    Longitud:  {basin.length_m} m")
    typer.echo("")


def basin_list(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
) -> None:
    """
    Lista las cuencas de un proyecto.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    if not project.basins:
        typer.echo(f"\n  El proyecto '{project.name}' no tiene cuencas.")
        typer.echo(f"  Usa 'hp project basin-add {project.id}' para agregar una.\n")
        return

    typer.echo(f"\n{'='*70}")
    typer.echo(f"  CUENCAS DEL PROYECTO: {project.name}")
    typer.echo(f"{'='*70}")
    typer.echo(f"  {'ID':<10} {'Nombre':<22} {'Área(ha)':>9} {'Pend(%)':>8} {'C':>6} {'CN':>4} {'Análisis':>9}")
    typer.echo(f"  {'-'*65}")

    for basin in project.basins:
        name = basin.name[:21] if len(basin.name) > 21 else basin.name
        c_str = f"{basin.c:.2f}" if basin.c else "-"
        cn_str = str(basin.cn) if basin.cn else "-"
        typer.echo(
            f"  {basin.id:<10} {name:<22} {basin.area_ha:>9.1f} {basin.slope_pct:>8.1f} "
            f"{c_str:>6} {cn_str:>4} {len(basin.analyses):>9}"
        )

    typer.echo(f"{'='*70}\n")


def basin_show(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
) -> None:
    """
    Muestra detalles de una cuenca específica.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    basin = project.get_basin(basin_id)

    if basin is None:
        typer.echo(f"\n  Error: Cuenca '{basin_id}' no encontrada en el proyecto.\n")
        raise typer.Exit(1)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  CUENCA: {basin.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"  ID:          {basin.id}")
    typer.echo(f"  Proyecto:    {project.name}")
    typer.echo(f"  Creada:      {basin.created_at[:10]}")
    typer.echo(f"  Modificada:  {basin.updated_at[:10]}")

    typer.echo(f"\n  PARÁMETROS FÍSICOS:")
    typer.echo(f"    Área:      {basin.area_ha} ha ({basin.area_ha/100:.2f} km²)")
    typer.echo(f"    Pendiente: {basin.slope_pct} %")
    typer.echo(f"    P3,10:     {basin.p3_10} mm")
    if basin.length_m:
        typer.echo(f"    Longitud:  {basin.length_m} m")

    typer.echo(f"\n  COEFICIENTES DE ESCORRENTÍA:")
    if basin.c is not None:
        c_str = f"{basin.c:.3f}"
        if basin.c_weighted:
            c_str += " (ponderado)"
        typer.echo(f"    C:  {c_str}")
    if basin.cn is not None:
        cn_str = str(basin.cn)
        if basin.cn_weighted:
            cn_str += " (ponderado)"
        typer.echo(f"    CN: {cn_str}")

    if basin.tc_results:
        typer.echo(f"\n  TIEMPOS DE CONCENTRACIÓN ({len(basin.tc_results)}):")
        for tc in basin.tc_results:
            typer.echo(f"    {tc.method.capitalize()}: {tc.tc_min:.1f} min ({tc.tc_hr:.3f} hr)")

    if basin.analyses:
        typer.echo(f"\n  ANÁLISIS ({len(basin.analyses)}):")
        for a in basin.analyses:
            x_str = f" X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else ""
            typer.echo(
                f"    [{a.id}] {a.tc.method} + {a.storm.type.upper()} "
                f"Tr{a.storm.return_period}{x_str} → Qp={a.hydrograph.peak_flow_m3s:.3f} m³/s"
            )

    if basin.notes:
        typer.echo(f"\n  Notas: {basin.notes}")

    typer.echo(f"{'='*60}\n")


def basin_delete(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
) -> None:
    """
    Elimina una cuenca de un proyecto.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    basin = project.get_basin(basin_id)

    if basin is None:
        typer.echo(f"\n  Error: Cuenca '{basin_id}' no encontrada en el proyecto.\n")
        raise typer.Exit(1)

    if not force:
        msg = f"¿Eliminar cuenca '{basin.name}' ({len(basin.analyses)} análisis)? [y/N]: "
        if not typer.confirm(msg, default=False):
            typer.echo("  Cancelado.\n")
            return

    if project.remove_basin(basin.id):
        manager.save_project(project)
        typer.echo(f"\n  Cuenca '{basin.name}' eliminada del proyecto.\n")
    else:
        typer.echo(f"\n  Error al eliminar cuenca.\n")
        raise typer.Exit(1)


def basin_import(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto destino")],
    session_id: Annotated[str, typer.Argument(help="ID de la sesión a importar")],
) -> None:
    """
    Importa una sesión existente como cuenca en un proyecto.

    Permite migrar sesiones legacy al nuevo formato de proyectos.
    La sesión original no se elimina.

    Ejemplo:
        hp project basin-import abc123 xyz789
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        typer.echo(f"\n  Error: Proyecto '{project_id}' no encontrado.\n")
        raise typer.Exit(1)

    basin = manager.import_session_as_basin(project, session_id)

    if basin is None:
        typer.echo(f"\n  Error: Sesión '{session_id}' no encontrada.\n")
        raise typer.Exit(1)

    typer.echo(f"\n  Sesión importada como cuenca:")
    typer.echo(f"    Proyecto:  {project.name}")
    typer.echo(f"    ID cuenca: {basin.id}")
    typer.echo(f"    Nombre:    {basin.name}")
    typer.echo(f"    Análisis:  {len(basin.analyses)}")
    typer.echo(f"\n  La sesión original no fue modificada.\n")
