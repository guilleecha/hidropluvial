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

        # Usar directamente los análisis del basin
        print_analyses_summary_table(basin.analyses)
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
    from hidropluvial.cli.basin.export import export_to_excel, export_to_csv

    project, basin = _find_basin(basin_id)

    # Determinar nombre de salida
    if output is None:
        output = basin.name.lower().replace(" ", "_")

    # Agregar extensión si no tiene
    if not output.endswith(f".{format}"):
        output = f"{output}.{format}"

    output_path = Path(output)

    if format == "xlsx":
        export_to_excel(basin, output_path)
    elif format == "csv":
        export_to_csv(basin, output_path)
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
    methodology: Annotated[bool, typer.Option("--methodology", "-m", help="Incluir textos explicativos sobre metodologías")] = False,
) -> None:
    """
    Genera reporte LaTeX con gráficos TikZ para cada análisis.

    Crea estructura en output/<nombre_cuenca>/:
    - Archivo principal (.tex)
    - hietogramas/*.tex
    - hidrogramas/*.tex

    Con --pdf: Compila automáticamente el documento a PDF.
    Con --methodology: Incluye sección de marco teórico con fórmulas y explicaciones.
    """
    from hidropluvial.cli.basin.report import generate_basin_report

    project, basin = _find_basin(basin_id)

    output_dir = Path(output) if output else None

    try:
        result_dir = generate_basin_report(
            basin=basin,
            output_dir=output_dir,
            author=author,
            pdf=pdf,
            clean=clean,
            palette=palette,
            methodology=methodology,
        )
        typer.echo(f"Reporte generado en: {result_dir}")
    except ValueError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def basin_preview(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Modo interactivo con navegación")] = True,
    analysis_id: Annotated[Optional[str], typer.Option("--analysis", "-a", help="ID de análisis específico")] = None,
) -> None:
    """
    Visualiza hidrogramas e hietogramas en la terminal.

    Modo interactivo: navega con flechas ←/→, q para salir.
    """
    from hidropluvial.cli.basin.preview import basin_preview_interactive, basin_preview_table

    project, basin = _find_basin(basin_id)

    if not basin.analyses:
        typer.echo("  No hay análisis en esta cuenca.")
        typer.echo("  Use 'hp wizard' para crear análisis.")
        return

    if interactive:
        basin_preview_interactive(basin)
    else:
        basin_preview_table(basin)


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
    from hidropluvial.cli.basin.export import compare_basins
    import pandas as pd

    if len(basin_ids) < 2:
        typer.echo("Error: Necesitas al menos 2 cuencas para comparar.")
        raise typer.Exit(1)

    basins = []
    for basin_id in basin_ids:
        project, basin = _find_basin(basin_id)
        basins.append(basin)

    # Generar comparación
    comparison_df = compare_basins(basins, tr_filter=tr)

    if comparison_df is None or comparison_df.empty:
        typer.echo("No hay datos comparables entre las cuencas.")
        raise typer.Exit(1)

    # Mostrar en consola
    typer.echo("\n" + "=" * 70)
    typer.echo("  COMPARACIÓN DE CUENCAS")
    typer.echo("=" * 70 + "\n")

    for basin in basins:
        typer.echo(f"  [{basin.id}] {basin.name}")
        typer.echo(f"         Área: {basin.area_ha} ha, Pendiente: {basin.slope_pct}%")

    typer.echo("\n" + "-" * 70)
    typer.echo(comparison_df.to_string(index=False))
    typer.echo("-" * 70)

    # Exportar si se especifica
    if output:
        if not output.endswith(".xlsx"):
            output = f"{output}.xlsx"

        output_path = Path(output)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            comparison_df.to_excel(writer, sheet_name="Comparacion", index=False)

            cuencas_data = []
            for basin in basins:
                cuencas_data.append({
                    "ID": basin.id,
                    "Nombre": basin.name,
                    "Área (ha)": basin.area_ha,
                    "Pendiente (%)": basin.slope_pct,
                    "P3,10 (mm)": basin.p3_10,
                    "C": basin.c if basin.c else "-",
                    "CN": basin.cn if basin.cn else "-",
                })
            pd.DataFrame(cuencas_data).to_excel(writer, sheet_name="Datos Cuencas", index=False)

        typer.echo(f"\nExportado: {output_path.absolute()}")


def analysis_list(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
) -> None:
    """
    Lista todos los análisis de una cuenca con detalles.

    Muestra: ID, método Tc, tipo tormenta, TR, caudal pico, nota.
    """
    from hidropluvial.cli.theme import print_header, get_console
    from rich.table import Table

    project, basin = _find_basin(basin_id)
    console = get_console()

    print_header(f"Análisis de: {basin.name}")
    typer.echo(f"  Proyecto: {project.name}")
    typer.echo()

    if not basin.analyses:
        typer.echo("  No hay análisis en esta cuenca.")
        typer.echo("  Use 'hp wizard' para crear análisis.")
        return

    table = Table(show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Tc (método)")
    table.add_column("Tormenta")
    table.add_column("TR", justify="right")
    table.add_column("Qpeak (m³/s)", justify="right", style="bold")
    table.add_column("Vol (hm³)", justify="right")
    table.add_column("Nota", max_width=30)

    for analysis in basin.analyses:
        note_text = analysis.note or ""
        if len(note_text) > 30:
            note_text = note_text[:27] + "..."

        table.add_row(
            analysis.id,
            analysis.tc.method.title(),
            analysis.storm.type.upper(),
            str(analysis.storm.return_period),
            f"{analysis.hydrograph.peak_flow_m3s:.3f}",
            f"{analysis.hydrograph.volume_m3 / 1_000_000:.4f}",
            note_text,
        )

    console.print(table)
    typer.echo(f"\n  Total: {len(basin.analyses)} análisis")


def analysis_delete(
    analysis_id: Annotated[str, typer.Argument(help="ID del análisis a eliminar")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Eliminar sin confirmación")] = False,
) -> None:
    """
    Elimina un análisis específico.

    Requiere confirmación a menos que use --force.
    """
    from hidropluvial.database import get_database

    db = get_database()

    # Verificar que existe
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        typer.echo(f"Error: Análisis '{analysis_id}' no encontrado.")
        raise typer.Exit(1)

    # Confirmar eliminación
    if not force:
        info = f"Tc={analysis['tc']['method']}, TR={analysis['storm']['return_period']}, Qpeak={analysis['hydrograph']['peak_flow_m3s']:.3f} m³/s"
        typer.echo(f"Análisis: {analysis_id}")
        typer.echo(f"  {info}")
        confirm = typer.confirm("¿Está seguro de eliminar este análisis?")
        if not confirm:
            typer.echo("Operación cancelada.")
            raise typer.Exit(0)

    # Eliminar
    success = db.delete_analysis(analysis_id)
    if success:
        typer.echo(f"Análisis '{analysis_id}' eliminado.")
    else:
        typer.echo("Error: No se pudo eliminar el análisis.")
        raise typer.Exit(1)


def analysis_clear(
    basin_id: Annotated[str, typer.Argument(help="ID de la cuenca")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Eliminar sin confirmación")] = False,
) -> None:
    """
    Elimina TODOS los análisis de una cuenca.

    ¡CUIDADO! Esta operación no se puede deshacer.
    """
    from hidropluvial.database import get_database

    project, basin = _find_basin(basin_id)
    db = get_database()

    n_analyses = len(basin.analyses)
    if n_analyses == 0:
        typer.echo(f"La cuenca '{basin.name}' no tiene análisis.")
        return

    # Confirmar eliminación
    if not force:
        typer.echo(f"Cuenca: {basin.name} ({basin.id})")
        typer.echo(f"  Cantidad de análisis: {n_analyses}")
        typer.echo()
        typer.echo("¡ATENCIÓN! Esta operación eliminará TODOS los análisis.")
        confirm = typer.confirm(f"¿Está seguro de eliminar los {n_analyses} análisis?")
        if not confirm:
            typer.echo("Operación cancelada.")
            raise typer.Exit(0)

    # Eliminar todos
    deleted = db.clear_basin_analyses(basin.id)
    typer.echo(f"Eliminados {deleted} análisis de la cuenca '{basin.name}'.")


def analysis_note(
    analysis_id: Annotated[str, typer.Argument(help="ID del análisis")],
    note: Annotated[Optional[str], typer.Argument(help="Nueva nota (omitir para ver actual)")] = None,
    clear: Annotated[bool, typer.Option("--clear", "-c", help="Eliminar la nota")] = False,
) -> None:
    """
    Ver o editar la nota de un análisis.

    Ejemplos:
      hp basin analysis-note abc123                  # Ver nota
      hp basin analysis-note abc123 "Escenario base"  # Establecer nota
      hp basin analysis-note abc123 --clear          # Eliminar nota
    """
    from hidropluvial.database import get_database

    db = get_database()

    # Verificar que existe
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        typer.echo(f"Error: Análisis '{analysis_id}' no encontrado.")
        raise typer.Exit(1)

    # Si --clear, eliminar nota
    if clear:
        db.update_analysis_note(analysis_id, None)
        typer.echo(f"Nota eliminada del análisis '{analysis_id}'.")
        return

    # Si no se proporciona nota, mostrar la actual
    if note is None:
        current_note = analysis.get("note")
        if current_note:
            typer.echo(f"Nota del análisis {analysis_id}:")
            typer.echo(f"  {current_note}")
        else:
            typer.echo(f"El análisis '{analysis_id}' no tiene nota.")
        return

    # Establecer nueva nota
    db.update_analysis_note(analysis_id, note)
    typer.echo(f"Nota actualizada para análisis '{analysis_id}'.")
