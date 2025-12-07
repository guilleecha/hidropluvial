"""
Comandos CLI para gestión de cuencas (basins) dentro de proyectos.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.cli.project.base import get_project_manager
from hidropluvial.cli.theme import (
    print_basin_info, print_success, print_error, print_info, print_section,
    print_basins_detail_table, get_console, get_palette,
)
from rich.text import Text


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
        print_error(f"Proyecto '{project_id}' no encontrado.")
        raise typer.Exit(1)

    # Validar parámetros obligatorios
    if area is None or slope is None or p3_10 is None:
        print_error("Faltan parámetros obligatorios.")
        print_info("Uso: hp project basin-add <proyecto> <nombre> --area X --slope Y --p3_10 Z")
        print_info("Opciones adicionales: --c, --cn, --length")
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

    print_success(f"Cuenca agregada al proyecto '{project.name}'")
    print_basin_info(
        basin_name=basin.name,
        basin_id=basin.id,
        project_name=project.name,
        area_ha=basin.area_ha,
        slope_pct=basin.slope_pct,
        c=basin.c,
        cn=basin.cn,
        n_analyses=0,
    )


def basin_list(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
) -> None:
    """
    Lista las cuencas de un proyecto.
    """
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        print_error(f"Proyecto '{project_id}' no encontrado.")
        raise typer.Exit(1)

    if not project.basins:
        print_info(f"El proyecto '{project.name}' no tiene cuencas.")
        print_info(f"Usa 'hp project basin-add {project.id}' para agregar una.")
        return

    console = get_console()
    console.print()
    print_basins_detail_table(project.basins, title=f"Cuencas del Proyecto: {project.name}")
    console.print()


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
        print_error(f"Proyecto '{project_id}' no encontrado.")
        raise typer.Exit(1)

    basin = project.get_basin(basin_id)

    if basin is None:
        print_error(f"Cuenca '{basin_id}' no encontrada en el proyecto.")
        raise typer.Exit(1)

    console = get_console()
    p = get_palette()
    console.print()

    # Panel principal con info de cuenca
    trs = None
    if basin.analyses:
        trs = sorted(set(a.storm.return_period for a in basin.analyses))

    print_basin_info(
        basin_name=basin.name,
        basin_id=basin.id,
        project_name=project.name,
        area_ha=basin.area_ha,
        slope_pct=basin.slope_pct,
        n_analyses=len(basin.analyses),
        return_periods=trs,
        c=basin.c,
        cn=basin.cn,
    )

    # Detalles adicionales
    print_section("Parámetros físicos")
    print_info(f"P3,10: {basin.p3_10} mm")
    if basin.length_m:
        print_info(f"Longitud cauce: {basin.length_m} m")

    # Coeficientes con info de ponderación
    if basin.c is not None and basin.c_weighted:
        print_info(f"C ponderado con {len(basin.c_weighted.items)} coberturas")
    if basin.cn is not None and basin.cn_weighted:
        print_info(f"CN ponderado con {len(basin.cn_weighted.items)} coberturas")

    # Tiempos de concentración
    if basin.tc_results:
        print_section(f"Tiempos de Concentración ({len(basin.tc_results)})")
        for tc in basin.tc_results:
            text = Text()
            text.append(f"  {tc.method.capitalize()}: ", style=p.label)
            text.append(f"{tc.tc_min:.1f}", style=f"bold {p.number}")
            text.append(" min", style=p.unit)
            text.append(f" ({tc.tc_hr:.3f} hr)", style=p.muted)
            console.print(text)

    # Análisis
    if basin.analyses:
        print_section(f"Análisis ({len(basin.analyses)})")
        for a in basin.analyses:
            x_str = f" X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else ""
            text = Text()
            text.append(f"  [{a.id[:8]}] ", style=p.muted)
            text.append(f"{a.tc.method}", style=p.secondary)
            text.append(f" {a.storm.type.upper()} ", style=p.label)
            text.append(f"Tr{a.storm.return_period}", style=p.secondary)
            text.append(x_str, style=p.muted)
            text.append(f" → Qp=", style=p.label)
            text.append(f"{a.hydrograph.peak_flow_m3s:.3f}", style=f"bold {p.accent}")
            text.append(" m³/s", style=p.unit)
            console.print(text)

    if basin.notes:
        print_section("Notas")
        console.print(f"  {basin.notes}", style=p.muted)

    console.print()


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
