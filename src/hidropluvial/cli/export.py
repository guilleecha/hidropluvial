"""
Comandos CLI para exportación de datos.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial.core import alternating_blocks_dinagua, generate_dinagua_idf_table
from hidropluvial.reports.charts import generate_hyetograph_tikz
from hidropluvial.reports.generator import hyetograph_to_csv, idf_to_csv

# Crear sub-aplicación
export_app = typer.Typer(help="Exportación de datos")


@export_app.command("idf-csv")
def export_idf_csv(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    output: Annotated[str, typer.Option("--output", "-o", help="Archivo de salida")] = "idf_table.csv",
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
):
    """
    Exporta tabla IDF a CSV.

    Ejemplo:
        hidropluvial export idf-csv 78 -o montevideo_idf.csv
    """
    result = generate_dinagua_idf_table(p3_10, area_km2=area)

    idf_to_csv(
        durations_hr=result["durations_hr"].tolist(),
        return_periods_yr=result["return_periods_yr"].tolist(),
        intensities_mmhr=result["intensities_mmhr"].tolist(),
        filepath=output,
    )

    typer.echo(f"Tabla IDF exportada a: {output}")


@export_app.command("storm-csv")
def export_storm_csv(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    duration: Annotated[float, typer.Argument(help="Duración en horas")],
    output: Annotated[str, typer.Option("--output", "-o", help="Archivo de salida")] = "hyetograph.csv",
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 10,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
):
    """
    Exporta hietograma a CSV.

    Ejemplo:
        hidropluvial export storm-csv 78 3 --tr 25 -o storm.csv
    """
    result = alternating_blocks_dinagua(p3_10, return_period, duration, dt, area)

    hyetograph_to_csv(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        filepath=output,
    )

    typer.echo(f"Hietograma exportado a: {output}")


@export_app.command("storm-tikz")
def export_storm_tikz(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    duration: Annotated[float, typer.Argument(help="Duración en horas")],
    output: Annotated[str, typer.Option("--output", "-o", help="Archivo de salida")] = "hyetograph.tex",
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 10,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
):
    """
    Exporta hietograma como figura TikZ (para incluir en LaTeX).

    Ejemplo:
        hidropluvial export storm-tikz 78 3 --tr 25 -o hyetograph.tex
    """
    result = alternating_blocks_dinagua(p3_10, return_period, duration, dt, area)

    tikz = generate_hyetograph_tikz(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        caption=f"Hietograma de diseño ($T_r$ = {return_period} años)",
        label="fig:hyetograph",
    )

    Path(output).write_text(tikz, encoding="utf-8")
    typer.echo(f"Figura TikZ exportada a: {output}")
