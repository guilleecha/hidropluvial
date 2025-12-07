"""
Comandos para gestión de cuencas (basins).

Estos comandos trabajan con cuencas dentro de proyectos,
reemplazando los comandos legacy de 'session'.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial.project import get_project_manager, Basin, Project


def _find_basin(basin_id: str) -> tuple[Project, Basin]:
    """
    Busca una cuenca por ID en todos los proyectos.

    Returns:
        Tupla (proyecto, cuenca)

    Raises:
        typer.Exit si no se encuentra
    """
    manager = get_project_manager()

    # Buscar en todos los proyectos
    for project_info in manager.list_projects():
        project = manager.get_project(project_info["id"])
        if project:
            basin = project.get_basin(basin_id)
            if basin:
                return project, basin

    typer.echo(f"Error: Cuenca '{basin_id}' no encontrada.")
    typer.echo("Use 'hp basin list' para ver cuencas disponibles.")
    raise typer.Exit(1)


def basin_list(
    project_id: Annotated[Optional[str], typer.Argument(help="ID del proyecto (opcional, muestra todas si no se especifica)")] = None,
) -> None:
    """
    Lista cuencas disponibles.

    Sin argumentos: lista todas las cuencas de todos los proyectos.
    Con project_id: lista solo las cuencas de ese proyecto.
    """
    from hidropluvial.cli.theme import print_header, get_console
    from rich.table import Table

    manager = get_project_manager()
    console = get_console()

    if project_id:
        # Listar cuencas de un proyecto específico
        project = manager.get_project(project_id)
        if not project:
            typer.echo(f"Error: Proyecto '{project_id}' no encontrado.")
            raise typer.Exit(1)

        print_header(f"Cuencas del Proyecto: {project.name}")

        if not project.basins:
            typer.echo("  No hay cuencas en este proyecto.")
            return

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Nombre")
        table.add_column("Área (ha)", justify="right")
        table.add_column("Pendiente (%)", justify="right")
        table.add_column("Análisis", justify="right")

        for basin in project.basins:
            table.add_row(
                basin.id,
                basin.name,
                f"{basin.area_ha:.1f}",
                f"{basin.slope_pct:.2f}",
                str(len(basin.analyses)),
            )

        console.print(table)
    else:
        # Listar todas las cuencas de todos los proyectos
        print_header("Todas las Cuencas")

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Cuenca")
        table.add_column("Proyecto", style="dim")
        table.add_column("Área (ha)", justify="right")
        table.add_column("Análisis", justify="right")

        total_basins = 0
        for project_info in manager.list_projects():
            project = manager.get_project(project_info["id"])
            if project:
                for basin in project.basins:
                    table.add_row(
                        basin.id,
                        basin.name,
                        project.name[:20],
                        f"{basin.area_ha:.1f}",
                        str(len(basin.analyses)),
                    )
                    total_basins += 1

        if total_basins == 0:
            typer.echo("  No hay cuencas. Use 'hp wizard' para crear una.")
            return

        console.print(table)
        typer.echo(f"\n  Total: {total_basins} cuencas")


def basin_show(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
) -> None:
    """
    Muestra detalles de una cuenca.

    Incluye: datos físicos, coeficientes, Tc calculados, resumen de análisis.
    """
    from hidropluvial.cli.theme import (
        print_header, print_subheader, print_field,
        print_analyses_summary_table, get_console,
    )

    project, basin = _find_basin(basin_id)

    print_header(f"Cuenca: {basin.name}")
    typer.echo(f"  Proyecto: {project.name}")
    typer.echo(f"  ID: {basin.id}")
    typer.echo()

    print_subheader("Datos Físicos")
    print_field("Área", f"{basin.area_ha:.2f} ha ({basin.area_ha/100:.4f} km²)")
    print_field("Pendiente", f"{basin.slope_pct:.2f} %")
    if basin.length_m:
        print_field("Longitud cauce", f"{basin.length_m:.0f} m")
    print_field("P₃,₁₀", f"{basin.p3_10:.1f} mm")

    if basin.c or basin.cn:
        typer.echo()
        print_subheader("Coeficientes")
        if basin.c:
            print_field("Coef. C", f"{basin.c:.3f}")
        if basin.cn:
            print_field("Curve Number", str(basin.cn))

    if basin.tc_results:
        typer.echo()
        print_subheader("Tiempos de Concentración")
        for tc in basin.tc_results:
            print_field(tc.method.title(), f"{tc.tc_min:.1f} min ({tc.tc_hr:.3f} hr)")

    if basin.analyses:
        typer.echo()
        print_subheader(f"Análisis ({len(basin.analyses)})")

        # Convertir a Session para usar la función existente
        session = basin.to_session()
        print_analyses_summary_table(session)
    else:
        typer.echo()
        typer.echo("  No hay análisis. Use 'hp wizard' para agregar.")


def basin_export(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo de salida")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Formato: xlsx, csv")] = "xlsx",
) -> None:
    """
    Exporta los resultados de una cuenca a Excel o CSV.

    Genera un archivo con la tabla resumen de todos los análisis,
    incluyendo datos de la cuenca y parámetros.
    """
    # Reutilizar la lógica de session.export
    from hidropluvial.cli.session.export import _export_to_excel, _export_to_csv

    project, basin = _find_basin(basin_id)
    session = basin.to_session()

    # Determinar nombre de salida
    if output is None:
        output = basin.name.lower().replace(" ", "_")

    # Agregar extensión si no tiene
    if not output.endswith(f".{format}"):
        output = f"{output}.{format}"

    output_path = Path(output)

    if format == "xlsx":
        _export_to_excel(session, output_path)
    elif format == "csv":
        _export_to_csv(session, output_path)
    else:
        typer.echo(f"Error: Formato '{format}' no soportado. Use 'xlsx' o 'csv'.")
        raise typer.Exit(1)

    typer.echo(f"Exportado: {output_path.absolute()}")


def basin_report(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Nombre del directorio de salida")] = None,
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
    pdf: Annotated[bool, typer.Option("--pdf", help="Compilar automáticamente a PDF")] = False,
    clean: Annotated[bool, typer.Option("--clean/--no-clean", help="Limpiar archivos auxiliares")] = True,
    palette: Annotated[str, typer.Option("--palette", "-p", help="Paleta de colores")] = "default",
) -> None:
    """
    Genera reporte LaTeX con gráficos TikZ para cada análisis.

    Crea estructura en output/<nombre_cuenca>/:
    - Archivo principal (.tex)
    - hietogramas/*.tex
    - hidrogramas/*.tex

    Con --pdf: Compila automáticamente el documento a PDF.
    """
    # Importar la función de reporte de session y reutilizarla
    from hidropluvial.cli.session.report import session_report as _session_report
    from hidropluvial.cli.session.base import get_session_manager

    project, basin = _find_basin(basin_id)

    # Convertir Basin a Session para compatibilidad
    session = basin.to_session()

    # Guardar temporalmente en el session manager
    session_manager = get_session_manager()
    session_manager.save(session)

    try:
        # Llamar a la función de reporte existente
        _session_report(
            session_id=session.id,
            output=output,
            author=author,
            template_dir=None,
            pdf=pdf,
            clean=clean,
            fig_width=r"0.9\textwidth",
            fig_height="6cm",
            palette=palette,
        )
    finally:
        # Limpiar la sesión temporal
        session_manager.delete(session.id)


def basin_preview(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Modo interactivo con navegación")] = True,
    analysis_id: Annotated[Optional[str], typer.Option("--analysis", "-a", help="ID de análisis específico")] = None,
) -> None:
    """
    Visualiza hidrogramas e hietogramas en la terminal.

    Modo interactivo: navega con flechas ←/→, q para salir.
    """
    from hidropluvial.cli.session.preview import session_preview as _session_preview
    from hidropluvial.cli.session.base import get_session_manager

    project, basin = _find_basin(basin_id)
    session = basin.to_session()

    # Guardar temporalmente
    session_manager = get_session_manager()
    session_manager.save(session)

    try:
        _session_preview(
            session_id=session.id,
            interactive=interactive,
            analysis_id=analysis_id,
            compare=False,
        )
    finally:
        session_manager.delete(session.id)


def basin_compare(
    basin_ids: Annotated[list[str], typer.Argument(help="IDs de cuencas a comparar (mínimo 2)")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo Excel de salida")] = None,
    tr: Annotated[Optional[int], typer.Option("--tr", help="Filtrar por período de retorno")] = None,
) -> None:
    """
    Compara resultados de múltiples cuencas lado a lado.

    Genera una tabla comparativa con los caudales pico de cada cuenca
    para los mismos períodos de retorno.
    """
    from hidropluvial.cli.session.export import compare_sessions as _compare_sessions
    from hidropluvial.cli.session.base import get_session_manager

    if len(basin_ids) < 2:
        typer.echo("Error: Necesitas al menos 2 cuencas para comparar.")
        raise typer.Exit(1)

    session_manager = get_session_manager()
    temp_session_ids = []

    try:
        # Convertir cada basin a session temporal
        for basin_id in basin_ids:
            project, basin = _find_basin(basin_id)
            session = basin.to_session()
            session_manager.save(session)
            temp_session_ids.append(session.id)

        # Usar la función de comparación existente
        _compare_sessions(
            session_ids=temp_session_ids,
            output=output,
            tr=tr,
        )
    finally:
        # Limpiar sesiones temporales
        for sid in temp_session_ids:
            session_manager.delete(sid)
