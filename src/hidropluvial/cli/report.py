"""
Comandos CLI para generación de reportes LaTeX.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial.core import alternating_blocks_dinagua, generate_dinagua_idf_table
from hidropluvial.reports import ReportGenerator
from hidropluvial.reports.charts import generate_hyetograph_tikz

# Crear sub-aplicación
report_app = typer.Typer(help="Generación de reportes LaTeX")


@report_app.command("idf")
def report_idf(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    output: Annotated[str, typer.Option("--output", "-o", help="Archivo de salida .tex")] = "idf_report.tex",
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
):
    """
    Genera reporte LaTeX de curvas IDF DINAGUA.

    Ejemplo:
        hidropluvial report idf 78 -o montevideo_idf.tex --author "Ing. Pérez"
    """
    # Generar tabla IDF
    result = generate_dinagua_idf_table(p3_10, area_km2=area)

    generator = ReportGenerator()

    # Crear tabla LaTeX
    idf_table = generator.generate_idf_table_latex(
        durations_hr=result["durations_hr"].tolist(),
        return_periods_yr=result["return_periods_yr"].tolist(),
        intensities_mmhr=result["intensities_mmhr"].tolist(),
        caption=f"Tabla IDF DINAGUA ($P_{{3,10}}$ = {p3_10} mm)",
        label="tab:idf",
    )

    # Crear contenido del reporte
    content = f"""
\\section{{Datos de Entrada}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Parámetro & Valor \\\\
\\midrule
Método & DINAGUA Uruguay \\\\
$P_{{3,10}}$ base & {p3_10} mm \\\\
{"Área de cuenca & " + str(area) + " km² \\\\" if area else ""}
\\bottomrule
\\end{{tabular}}
\\caption{{Parámetros de entrada}}
\\label{{tab:input}}
\\end{{table}}

\\section{{Tabla de Intensidades}}

{idf_table}

\\section{{Fórmulas Utilizadas}}

\\subsection{{Factor por Período de Retorno ($C_T$)}}

\\begin{{equation}}
C_T(T_r) = 0.5786 - 0.4312 \\times \\log_{{10}}\\left[\\ln\\left(\\frac{{T_r}}{{T_r - 1}}\\right)\\right]
\\end{{equation}}

\\subsection{{Factor por Área de Cuenca ($C_A$)}}

\\begin{{equation}}
C_A(A_c, d) = 1.0 - 0.3549 \\times d^{{-0.4272}} \\times \\left(1.0 - e^{{-0.005792 \\times A_c}}\\right)
\\end{{equation}}

\\subsection{{Intensidad}}

Para $d < 3$ horas:
\\begin{{equation}}
I(d) = \\frac{{P_{{3,10}} \\times C_T(T_r) \\times C_A \\times 0.6208}}{{(d + 0.0137)^{{0.5639}}}}
\\end{{equation}}

Para $d \\geq 3$ horas:
\\begin{{equation}}
I(d) = \\frac{{P_{{3,10}} \\times C_T(T_r) \\times C_A \\times 1.0287}}{{(d + 1.0293)^{{0.8083}}}}
\\end{{equation}}
"""

    # Generar documento completo
    doc = generator.generate_standalone_document(
        content=content,
        title="Memoria de Cálculo: Curvas IDF DINAGUA",
        author=author,
        include_tikz=True,
    )

    # Guardar
    Path(output).write_text(doc, encoding="utf-8")
    typer.echo(f"Reporte generado: {output}")


@report_app.command("storm")
def report_storm(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    duration: Annotated[float, typer.Argument(help="Duración en horas")],
    output: Annotated[str, typer.Option("--output", "-o", help="Archivo de salida .tex")] = "storm_report.tex",
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 10,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
):
    """
    Genera reporte LaTeX de hietograma de diseño.

    Ejemplo:
        hidropluvial report storm 78 3 --tr 25 -o storm_montevideo.tex
    """
    # Generar hietograma
    result = alternating_blocks_dinagua(p3_10, return_period, duration, dt, area)

    generator = ReportGenerator()

    # Generar figura TikZ
    figure_tikz = generate_hyetograph_tikz(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        caption=f"Hietograma de diseño - $T_r$ = {return_period} años",
        label="fig:hyetograph",
        title="",
    )

    # Generar tabla de datos
    table = generator.generate_hyetograph_table_latex(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        caption="Datos del hietograma",
        label="tab:hyetograph",
    )

    # Contenido
    content = f"""
\\section{{Datos de Entrada}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Parámetro & Valor \\\\
\\midrule
Método & Bloques Alternantes DINAGUA \\\\
$P_{{3,10}}$ base & {p3_10} mm \\\\
Período de retorno & {return_period} años \\\\
Duración de tormenta & {duration} horas \\\\
Intervalo $\\Delta t$ & {dt} minutos \\\\
{"Área de cuenca & " + str(area) + " km² \\\\" if area else ""}
\\bottomrule
\\end{{tabular}}
\\caption{{Parámetros de entrada}}
\\label{{tab:input}}
\\end{{table}}

\\section{{Resultados}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Resultado & Valor \\\\
\\midrule
Precipitación total & {result.total_depth_mm:.2f} mm \\\\
Intensidad pico & {result.peak_intensity_mmhr:.2f} mm/hr \\\\
Número de intervalos & {len(result.time_min)} \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Resumen de resultados}}
\\label{{tab:results}}
\\end{{table}}

\\section{{Hietograma}}

{figure_tikz}

\\section{{Datos Tabulados}}

{table}
"""

    # Documento completo
    doc = generator.generate_standalone_document(
        content=content,
        title="Memoria de Cálculo: Hietograma de Diseño",
        author=author,
        include_tikz=True,
    )

    Path(output).write_text(doc, encoding="utf-8")
    typer.echo(f"Reporte generado: {output}")
