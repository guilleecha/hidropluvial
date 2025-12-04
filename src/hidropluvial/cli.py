"""
CLI para HidroPluvial - Herramienta de cálculos hidrológicos.

Uso:
    hidropluvial --help
    hidropluvial idf --help
    hidropluvial storm --help
    hidropluvial tc --help
    hidropluvial runoff --help
    hidropluvial hydrograph --help
    hidropluvial report --help
    hidropluvial export --help
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial import __version__
from hidropluvial.config import (
    AntecedentMoistureCondition,
    HydrographMethod,
    ShermanCoefficients,
    StormMethod,
)
from hidropluvial.core import (
    # Uruguay/DINAGUA
    dinagua_intensity,
    generate_dinagua_idf_table,
    get_p3_10,
    P3_10_URUGUAY,
    # Hietogramas
    generate_hyetograph_dinagua,
    alternating_blocks_dinagua,
    bimodal_storm,
    # Otros métodos
    calculate_scs_runoff,
    calculate_tc,
    generate_hyetograph,
    generate_idf_table,
    get_depth,
    get_intensity,
    kirpich,
    rational_peak_flow,
    scs_runoff,
    temez,
    # Hidrogramas
    rainfall_excess_series,
    scs_triangular_uh,
    scs_curvilinear_uh,
    convolve_uh,
    scs_lag_time,
    scs_time_to_peak,
)
from hidropluvial.core.hydrograph import scs_lag_time, scs_time_to_peak
import numpy as np
from hidropluvial.reports import (
    ReportGenerator,
    generate_hyetograph_tikz,
    idf_to_csv,
    hyetograph_to_csv,
)
from hidropluvial.session import SessionManager, Session

app = typer.Typer(
    name="hidropluvial",
    help="Herramienta de cálculos hidrológicos con generación de reportes LaTeX.",
    no_args_is_help=True,
)

# Subcomandos
idf_app = typer.Typer(help="Análisis de curvas IDF")
storm_app = typer.Typer(help="Generación de tormentas de diseño")
tc_app = typer.Typer(help="Cálculo de tiempo de concentración")
runoff_app = typer.Typer(help="Cálculo de escorrentía")
hydrograph_app = typer.Typer(help="Generación de hidrogramas")
report_app = typer.Typer(help="Generación de reportes LaTeX")
export_app = typer.Typer(help="Exportación de datos (CSV, JSON)")
session_app = typer.Typer(help="Gestión de sesiones de análisis")

app.add_typer(idf_app, name="idf")
app.add_typer(storm_app, name="storm")
app.add_typer(tc_app, name="tc")
app.add_typer(runoff_app, name="runoff")
app.add_typer(hydrograph_app, name="hydrograph")
app.add_typer(report_app, name="report")
app.add_typer(export_app, name="export")
app.add_typer(session_app, name="session")


def version_callback(value: bool):
    if value:
        typer.echo(f"hidropluvial v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
):
    """HidroPluvial - Herramienta de cálculos hidrológicos."""
    pass


# ============================================================================
# Comandos IDF - URUGUAY (MÉTODO PRINCIPAL)
# ============================================================================

@idf_app.command("uruguay")
def idf_uruguay(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm (o usar --depto)")],
    duration: Annotated[float, typer.Argument(help="Duración en horas")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 10,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
):
    """
    Calcula intensidad usando método DINAGUA Uruguay.

    Ejemplo:
        hidropluvial idf uruguay 83 2 --tr 100 --area 25
    """
    result = dinagua_intensity(p3_10, return_period, duration, area)

    typer.echo(f"\n{'='*50}")
    typer.echo(f"  METODO DINAGUA URUGUAY")
    typer.echo(f"{'='*50}")
    typer.echo(f"  P3,10 base:        {result.p3_10:>10.1f} mm")
    typer.echo(f"  Periodo retorno:   {result.return_period_yr:>10.0f} anios")
    typer.echo(f"  Duracion:          {result.duration_hr:>10.2f} hr")
    if result.area_km2:
        typer.echo(f"  Area cuenca:       {result.area_km2:>10.1f} km2")
    typer.echo(f"{'='*50}")
    typer.echo(f"  Factor CT:         {result.ct:>10.4f}")
    typer.echo(f"  Factor CA:         {result.ca:>10.4f}")
    typer.echo(f"{'='*50}")
    typer.echo(f"  INTENSIDAD:        {result.intensity_mmhr:>10.2f} mm/hr")
    typer.echo(f"  PRECIPITACION:     {result.depth_mm:>10.2f} mm")
    typer.echo(f"{'='*50}\n")


@idf_app.command("tabla-uy")
def idf_tabla_uruguay(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo JSON")] = None,
):
    """
    Genera tabla IDF completa usando método DINAGUA Uruguay.

    Ejemplo:
        hidropluvial idf tabla-uy 83 --area 25 -o tabla_idf.json
    """
    result = generate_dinagua_idf_table(p3_10, area_km2=area)

    if output:
        data = {
            "p3_10_mm": result["p3_10"],
            "area_km2": result["area_km2"],
            "durations_hr": result["durations_hr"].tolist(),
            "return_periods_yr": result["return_periods_yr"].tolist(),
            "intensities_mmhr": result["intensities_mmhr"].tolist(),
            "depths_mm": result["depths_mm"].tolist(),
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        typer.echo(f"Tabla guardada en {output}")
    else:
        durations = result["durations_hr"]
        periods = result["return_periods_yr"]
        intensities = result["intensities_mmhr"]

        typer.echo(f"\nTabla IDF DINAGUA Uruguay (P3,10 = {p3_10} mm)")
        if area:
            typer.echo(f"Área de cuenca: {area} km²")
        typer.echo(f"\nIntensidades (mm/hr):")

        # Encabezado
        header = f"{'Dur (hr)':>8} |"
        for T in periods:
            header += f" T={T:>3} |"
        typer.echo(header)
        typer.echo("-" * len(header))

        # Filas
        for j, d in enumerate(durations):
            if d < 1:
                dur_str = f"{d*60:.0f}min"
            else:
                dur_str = f"{d:.1f}hr"
            row = f"{dur_str:>8} |"
            for i in range(len(periods)):
                row += f" {intensities[i, j]:>5.1f} |"
            typer.echo(row)


@idf_app.command("departamentos")
def idf_departamentos():
    """Lista valores de P3,10 por departamento de Uruguay."""
    typer.echo("\nValores de P3,10 por departamento (mm):")
    typer.echo("-" * 35)
    for depto, p310 in sorted(P3_10_URUGUAY.items()):
        typer.echo(f"  {depto.replace('_', ' ').title():20} {p310:>5} mm")
    typer.echo("-" * 35)
    typer.echo("\nNota: Para proyectos críticos, mayorar 5-10% por cambio climático.")


# ============================================================================
# Comandos IDF - Métodos Internacionales
# ============================================================================

@idf_app.command("sherman")
def idf_intensity(
    duration: Annotated[float, typer.Argument(help="Duración en minutos")],
    return_period: Annotated[int, typer.Argument(help="Período de retorno en años")],
    k: Annotated[float, typer.Option(help="Coeficiente k")] = 2150.0,
    m: Annotated[float, typer.Option(help="Exponente m")] = 0.22,
    c: Annotated[float, typer.Option(help="Constante c")] = 15.0,
    n: Annotated[float, typer.Option(help="Exponente n")] = 0.75,
):
    """Calcula intensidad de lluvia desde curva IDF (método Sherman)."""
    coeffs = ShermanCoefficients(k=k, m=m, c=c, n=n)
    intensity = get_intensity(duration, return_period, "sherman", coeffs)
    depth = get_depth(duration, return_period, "sherman", coeffs)

    typer.echo(f"Duración: {duration} min")
    typer.echo(f"Período de retorno: {return_period} años")
    typer.echo(f"Intensidad: {intensity:.2f} mm/hr")
    typer.echo(f"Profundidad: {depth:.2f} mm")


@idf_app.command("table")
def idf_table(
    k: Annotated[float, typer.Option(help="Coeficiente k")] = 2150.0,
    m: Annotated[float, typer.Option(help="Exponente m")] = 0.22,
    c: Annotated[float, typer.Option(help="Constante c")] = 15.0,
    n: Annotated[float, typer.Option(help="Exponente n")] = 0.75,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo de salida JSON")] = None,
):
    """Genera tabla completa de curvas IDF (método Sherman)."""
    coeffs = ShermanCoefficients(k=k, m=m, c=c, n=n)
    durations = [5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 360, 720, 1440]
    periods = [2, 5, 10, 25, 50, 100]

    result = generate_idf_table(durations, periods, "sherman", coeffs)

    if output:
        data = {
            "durations_min": result["durations"].tolist(),
            "return_periods_yr": result["return_periods"].tolist(),
            "intensities_mmhr": result["intensities"].tolist(),
            "depths_mm": result["depths"].tolist(),
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        typer.echo(f"Tabla guardada en {output}")
    else:
        typer.echo("\nIntensidades (mm/hr):")
        typer.echo(f"{'Duración':>10} | " + " | ".join(f"T={p:>3}" for p in periods))
        typer.echo("-" * 70)
        for i, d in enumerate(durations):
            row = " | ".join(f"{result['intensities'][j, i]:>6.1f}" for j in range(len(periods)))
            typer.echo(f"{d:>10} | {row}")


# ============================================================================
# Comandos de Tormenta - URUGUAY (MÉTODO PRINCIPAL)
# ============================================================================

@storm_app.command("uruguay")
def storm_uruguay(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    duration: Annotated[float, typer.Argument(help="Duración en horas")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 10,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
    method: Annotated[str, typer.Option("--method", "-m", help="Método: blocks, scs")] = "blocks",
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo JSON")] = None,
):
    """
    Genera hietograma usando método DINAGUA Uruguay.

    Ejemplos:
        hidropluvial storm uruguay 83 2 --tr 100 --area 25
        hidropluvial storm uruguay 78 6 --tr 50 -m scs -o hietograma.json
    """
    if method == "blocks":
        result = alternating_blocks_dinagua(
            p3_10, return_period, duration, dt, area
        )
    else:
        result = generate_hyetograph_dinagua(
            p3_10, return_period, duration, dt, method, area
        )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\n{'='*50}")
        typer.echo(f"  HIETOGRAMA DINAGUA URUGUAY")
        typer.echo(f"{'='*50}")
        typer.echo(f"  P3,10 base:        {p3_10:>10.1f} mm")
        typer.echo(f"  Período retorno:   {return_period:>10} años")
        typer.echo(f"  Duración:          {duration:>10.2f} hr")
        typer.echo(f"  Intervalo dt:      {dt:>10.1f} min")
        if area:
            typer.echo(f"  Área cuenca:       {area:>10.1f} km²")
        typer.echo(f"  Método:            {result.method:>10}")
        typer.echo(f"{'='*50}")
        typer.echo(f"  Precipitación:     {result.total_depth_mm:>10.2f} mm")
        typer.echo(f"  Intensidad pico:   {result.peak_intensity_mmhr:>10.2f} mm/hr")
        typer.echo(f"  Intervalos:        {len(result.time_min):>10}")
        typer.echo(f"{'='*50}\n")


@storm_app.command("bimodal")
def storm_bimodal(
    depth: Annotated[float, typer.Argument(help="Profundidad total en mm")],
    duration: Annotated[float, typer.Option(help="Duración en horas")] = 6.0,
    dt: Annotated[float, typer.Option(help="Intervalo en minutos")] = 5.0,
    peak1: Annotated[float, typer.Option(help="Posición primer pico (0-1)")] = 0.25,
    peak2: Annotated[float, typer.Option(help="Posición segundo pico (0-1)")] = 0.75,
    split: Annotated[float, typer.Option(help="Fracción volumen primer pico")] = 0.5,
    output: Annotated[Optional[str], typer.Option("--output", "-o")] = None,
):
    """
    Genera hietograma bimodal (doble pico).

    Útil para cuencas urbanas mixtas y tormentas frontales.
    """
    result = bimodal_storm(
        depth, duration, dt, peak1, peak2, split
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\nHietograma Bimodal")
        typer.echo(f"Picos en: {peak1*100:.0f}% y {peak2*100:.0f}% de la duración")
        typer.echo(f"Volumen split: {split*100:.0f}% / {(1-split)*100:.0f}%")
        typer.echo(f"Profundidad total: {result.total_depth_mm:.2f} mm")
        typer.echo(f"Intensidad pico: {result.peak_intensity_mmhr:.2f} mm/hr")


@storm_app.command("bimodal-uy")
def storm_bimodal_uy(
    p3_10: Annotated[float, typer.Argument(help="P3,10 en mm")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Periodo de retorno")] = 2,
    duration: Annotated[float, typer.Option("--duration", "-d", help="Duracion en horas")] = 6.0,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    peak1: Annotated[float, typer.Option("--peak1", help="Posicion primer pico (0-1)")] = 0.25,
    peak2: Annotated[float, typer.Option("--peak2", help="Posicion segundo pico (0-1)")] = 0.75,
    split: Annotated[float, typer.Option("--split", help="Fraccion volumen primer pico")] = 0.5,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Area cuenca km2")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo JSON salida")] = None,
):
    """
    Genera hietograma bimodal (doble pico) usando IDF DINAGUA Uruguay.

    Calcula automaticamente la precipitacion total a partir de P3,10
    y el periodo de retorno.

    Ejemplo:
        hidropluvial storm bimodal-uy 83 --tr 2
        hidropluvial storm bimodal-uy 83 --tr 20 --peak1 0.3 --peak2 0.7
    """
    from hidropluvial.core import bimodal_dinagua

    result = bimodal_dinagua(
        p3_10, return_period, duration, dt, area,
        peak1, peak2, split
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\n{'='*55}")
        typer.echo(f"  HIETOGRAMA BIMODAL DINAGUA")
        typer.echo(f"{'='*55}")
        typer.echo(f"  P3,10 base:        {p3_10:>10.1f} mm")
        typer.echo(f"  Periodo retorno:   {return_period:>10} anos")
        typer.echo(f"  Duracion:          {duration:>10.1f} hr")
        typer.echo(f"  Intervalo dt:      {dt:>10.1f} min")
        typer.echo(f"  Pico 1:            {peak1*100:>10.0f} %")
        typer.echo(f"  Pico 2:            {peak2*100:>10.0f} %")
        typer.echo(f"  Split volumen:     {split*100:.0f}% / {(1-split)*100:.0f}%")
        if area:
            typer.echo(f"  Area cuenca:       {area:>10.1f} km2")
        typer.echo(f"{'='*55}")
        typer.echo(f"  Precipitacion:     {result.total_depth_mm:>10.2f} mm")
        typer.echo(f"  Intensidad pico:   {result.peak_intensity_mmhr:>10.2f} mm/hr")
        typer.echo(f"  Intervalos:        {len(result.time_min):>10}")
        typer.echo(f"{'='*55}\n")


@storm_app.command("gz")
def storm_gz(
    p3_10: Annotated[float, typer.Argument(help="P3,10 en mm")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Periodo de retorno")] = 2,
    duration: Annotated[float, typer.Option("--duration", "-d", help="Duracion en horas")] = 6.0,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Area cuenca km2")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo JSON salida")] = None,
):
    """
    Genera hietograma metodo GZ (6 horas, pico en primera hora).

    Metodologia adaptada para drenaje urbano Uruguay:
    - Duracion fija de 6 horas
    - Bloques alternantes con pico adelantado (1ra hora)
    - Curvas IDF DINAGUA

    Ejemplo:
        hidropluvial storm gz 83 --tr 2
        hidropluvial storm gz 83 --tr 20
        hidropluvial storm gz 83 --tr 100
    """
    # Pico en la primera hora: 1/6 = 0.167
    peak_position = 1.0 / 6.0

    result = alternating_blocks_dinagua(
        p3_10, return_period, duration, dt, area, peak_position
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\n{'='*55}")
        typer.echo(f"  HIETOGRAMA GZ - TORMENTA 6 HORAS (PICO ADELANTADO)")
        typer.echo(f"{'='*55}")
        typer.echo(f"  P3,10 base:        {p3_10:>10.1f} mm")
        typer.echo(f"  Periodo retorno:   {return_period:>10} anos")
        typer.echo(f"  Duracion:          {duration:>10.1f} hr")
        typer.echo(f"  Intervalo dt:      {dt:>10.1f} min")
        typer.echo(f"  Pico en:           {'1ra hora':>10}")
        if area:
            typer.echo(f"  Area cuenca:       {area:>10.1f} km2")
        typer.echo(f"{'='*55}")
        typer.echo(f"  Precipitacion:     {result.total_depth_mm:>10.2f} mm")
        typer.echo(f"  Intensidad pico:   {result.peak_intensity_mmhr:>10.2f} mm/hr")
        typer.echo(f"  Intervalos:        {len(result.time_min):>10}")
        typer.echo(f"{'='*55}\n")


# ============================================================================
# Comandos de Tormenta - Internacionales
# ============================================================================

@storm_app.command("scs")
def storm_scs(
    depth: Annotated[float, typer.Argument(help="Profundidad total en mm")],
    duration: Annotated[float, typer.Option(help="Duración en horas")] = 24.0,
    dt: Annotated[float, typer.Option(help="Intervalo en minutos")] = 15.0,
    storm_type: Annotated[str, typer.Option(help="Tipo: I, IA, II, III")] = "II",
    output: Annotated[Optional[str], typer.Option("--output", "-o")] = None,
):
    """Genera hietograma usando distribución SCS."""
    type_map = {
        "I": StormMethod.SCS_TYPE_I,
        "IA": StormMethod.SCS_TYPE_IA,
        "II": StormMethod.SCS_TYPE_II,
        "III": StormMethod.SCS_TYPE_III,
    }

    if storm_type.upper() not in type_map:
        typer.echo(f"Error: Tipo inválido. Use: I, IA, II, III", err=True)
        raise typer.Exit(1)

    result = generate_hyetograph(
        method=type_map[storm_type.upper()],
        total_depth_mm=depth,
        duration_hr=duration,
        dt_min=dt,
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\nHietograma SCS Tipo {storm_type.upper()}")
        typer.echo(f"Profundidad total: {result.total_depth_mm:.2f} mm")
        typer.echo(f"Intensidad pico: {result.peak_intensity_mmhr:.2f} mm/hr")
        typer.echo(f"Intervalos: {len(result.time_min)}")


@storm_app.command("chicago")
def storm_chicago(
    depth: Annotated[float, typer.Argument(help="Profundidad total en mm")],
    duration: Annotated[float, typer.Option(help="Duración en horas")] = 2.0,
    dt: Annotated[float, typer.Option(help="Intervalo en minutos")] = 5.0,
    return_period: Annotated[int, typer.Option(help="Período de retorno")] = 100,
    r: Annotated[float, typer.Option(help="Coeficiente de avance")] = 0.375,
    k: Annotated[float, typer.Option(help="Coeficiente k IDF")] = 2150.0,
    c: Annotated[float, typer.Option(help="Constante c IDF")] = 15.0,
    n: Annotated[float, typer.Option(help="Exponente n IDF")] = 0.75,
    m_coef: Annotated[float, typer.Option(help="Exponente m IDF")] = 0.22,
    output: Annotated[Optional[str], typer.Option("--output", "-o")] = None,
):
    """Genera hietograma usando método de tormenta Chicago."""
    coeffs = ShermanCoefficients(k=k, m=m_coef, c=c, n=n)

    result = generate_hyetograph(
        method=StormMethod.CHICAGO,
        total_depth_mm=depth,
        duration_hr=duration,
        dt_min=dt,
        idf_coeffs=coeffs,
        return_period_yr=return_period,
        advancement_coef=r,
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        typer.echo(f"Hietograma guardado en {output}")
    else:
        typer.echo(f"\nHietograma Chicago (r={r})")
        typer.echo(f"Profundidad total: {result.total_depth_mm:.2f} mm")
        typer.echo(f"Intensidad pico: {result.peak_intensity_mmhr:.2f} mm/hr")


# ============================================================================
# Comandos de Tiempo de Concentración
# ============================================================================

@tc_app.command("kirpich")
def tc_kirpich(
    length: Annotated[float, typer.Argument(help="Longitud del cauce en metros")],
    slope: Annotated[float, typer.Argument(help="Pendiente (m/m)")],
    surface: Annotated[str, typer.Option(help="Tipo: natural, grassy, concrete")] = "natural",
):
    """Calcula Tc usando fórmula Kirpich."""
    tc = kirpich(length, slope, surface)
    typer.echo(f"Longitud: {length} m")
    typer.echo(f"Pendiente: {slope:.4f} m/m ({slope*100:.2f}%)")
    typer.echo(f"Superficie: {surface}")
    typer.echo(f"Tc = {tc:.2f} horas ({tc*60:.1f} minutos)")


@tc_app.command("temez")
def tc_temez(
    length: Annotated[float, typer.Argument(help="Longitud del cauce en km")],
    slope: Annotated[float, typer.Argument(help="Pendiente (m/m)")],
):
    """Calcula Tc usando fórmula Témez."""
    tc = temez(length, slope)
    typer.echo(f"Longitud: {length} km")
    typer.echo(f"Pendiente: {slope:.4f} m/m ({slope*100:.2f}%)")
    typer.echo(f"Tc = {tc:.2f} horas ({tc*60:.1f} minutos)")


@tc_app.command("desbordes")
def tc_desbordes(
    area: Annotated[float, typer.Argument(help="Area de la cuenca en hectareas")],
    slope_pct: Annotated[float, typer.Argument(help="Pendiente media en porcentaje (%)")],
    c: Annotated[float, typer.Argument(help="Coeficiente de escorrentia (0-1)")],
    t0: Annotated[float, typer.Option("--t0", help="Tiempo de entrada inicial en minutos")] = 5.0,
):
    """Calcula Tc usando Metodo de los Desbordes (DINAGUA Uruguay)."""
    from hidropluvial.core import desbordes
    tc = desbordes(area, slope_pct, c, t0)
    typer.echo(f"\n{'='*50}")
    typer.echo(f"  METODO DE LOS DESBORDES (DINAGUA)")
    typer.echo(f"{'='*50}")
    typer.echo(f"  Area:              {area:.2f} ha")
    typer.echo(f"  Pendiente:         {slope_pct:.2f} %")
    typer.echo(f"  Coef. escorrentia: {c:.2f}")
    typer.echo(f"  T0:                {t0:.1f} min")
    typer.echo(f"{'='*50}")
    typer.echo(f"  Tc = {tc:.2f} horas ({tc*60:.1f} minutos)")
    typer.echo(f"{'='*50}")


# ============================================================================
# Comandos de Escorrentía
# ============================================================================

@runoff_app.command("cn")
def runoff_cn(
    rainfall: Annotated[float, typer.Argument(help="Precipitación total en mm")],
    cn: Annotated[int, typer.Argument(help="Número de curva (30-100)")],
    lambda_coef: Annotated[float, typer.Option("--lambda", "-l", help="Coeficiente λ")] = 0.2,
    amc: Annotated[str, typer.Option(help="AMC: I (seco), II (promedio), III (húmedo)")] = "II",
):
    """Calcula escorrentía usando método SCS-CN."""
    amc_map = {
        "I": AntecedentMoistureCondition.DRY,
        "II": AntecedentMoistureCondition.AVERAGE,
        "III": AntecedentMoistureCondition.WET,
    }

    if amc.upper() not in amc_map:
        typer.echo("Error: AMC debe ser I, II o III", err=True)
        raise typer.Exit(1)

    result = calculate_scs_runoff(rainfall, cn, lambda_coef, amc_map[amc.upper()])

    typer.echo(f"\n{'='*40}")
    typer.echo(f"Método SCS Curve Number")
    typer.echo(f"{'='*40}")
    typer.echo(f"Precipitación:     {result.rainfall_mm:>10.2f} mm")
    typer.echo(f"CN (AMC {amc}):        {result.cn_used:>10d}")
    typer.echo(f"Retención S:       {result.retention_mm:>10.2f} mm")
    typer.echo(f"Abstracción Ia:    {result.initial_abstraction_mm:>10.2f} mm")
    typer.echo(f"{'='*40}")
    typer.echo(f"Escorrentía Q:     {result.runoff_mm:>10.2f} mm")
    typer.echo(f"Coef. escorrentía: {result.runoff_mm/result.rainfall_mm:>10.2%}")


@runoff_app.command("rational")
def runoff_rational(
    c: Annotated[float, typer.Argument(help="Coeficiente de escorrentía (0-1)")],
    intensity: Annotated[float, typer.Argument(help="Intensidad en mm/hr")],
    area: Annotated[float, typer.Argument(help="Área en hectáreas")],
    return_period: Annotated[int, typer.Option(help="Período de retorno")] = 10,
):
    """Calcula caudal pico usando método racional."""
    q = rational_peak_flow(c, intensity, area, return_period)

    typer.echo(f"\nMétodo Racional")
    typer.echo(f"C = {c:.2f}")
    typer.echo(f"i = {intensity:.2f} mm/hr")
    typer.echo(f"A = {area:.2f} ha")
    typer.echo(f"T = {return_period} años")
    typer.echo(f"Q = {q:.3f} m³/s")


# ============================================================================
# Comandos de Hidrograma
# ============================================================================

@hydrograph_app.command("scs")
def hydrograph_scs(
    area: Annotated[float, typer.Option("--area", "-a", help="Area de la cuenca en km2")],
    length: Annotated[float, typer.Option("--length", "-l", help="Longitud del cauce en metros")],
    slope: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media (m/m o decimal)")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    cn: Annotated[int, typer.Option("--cn", help="Numero de curva (30-100)")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Periodo de retorno en anos")] = 25,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    method: Annotated[str, typer.Option("--method", "-m", help="Metodo UH: triangular, curvilinear")] = "triangular",
    tc_method: Annotated[str, typer.Option("--tc-method", help="Metodo Tc: kirpich, temez, desbordes")] = "kirpich",
    c_escorrentia: Annotated[Optional[float], typer.Option("--c", help="Coef. escorrentia para desbordes (0-1)")] = None,
    lambda_coef: Annotated[float, typer.Option("--lambda", help="Coeficiente lambda para Ia")] = 0.2,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo CSV de salida")] = None,
):
    """
    Genera hidrograma completo usando metodo SCS.

    Integra: Tc -> IDF -> Hietograma -> Escorrentia -> Hidrograma

    Ejemplo:
        hidropluvial hydrograph scs --area 1 --length 1000 --slope 0.0223 --p3_10 83 --cn 81 --tr 25
    """
    # Convertir pendiente si viene en porcentaje
    if slope > 1:
        slope = slope / 100

    # PASO 1: Tiempo de concentracion
    if tc_method == "kirpich":
        tc_hr = kirpich(length, slope)
    elif tc_method == "temez":
        tc_hr = temez(length / 1000, slope)  # Temez usa km
    elif tc_method == "desbordes":
        from hidropluvial.core import desbordes
        area_ha = area * 100  # km2 a ha
        slope_pct = slope * 100  # m/m a %
        # Si no se proporciona C, estimar desde CN
        if c_escorrentia is None:
            # Estimacion aproximada: C ≈ 1 - (S/(S+25.4)) donde S = 25400/CN - 254
            s_mm = 25400 / cn - 254
            c_escorrentia = 1 - (s_mm / (s_mm + 25.4))
        tc_hr = desbordes(area_ha, slope_pct, c_escorrentia)
    else:
        typer.echo(f"Error: Metodo Tc desconocido: {tc_method}", err=True)
        raise typer.Exit(1)

    tc_min = tc_hr * 60

    # PASO 2: IDF - Precipitacion de diseno
    # Duracion = Tc (redondeado a multiplo de dt)
    duration_hr = max(tc_hr, dt / 60)  # Minimo un intervalo

    idf_result = dinagua_intensity(p3_10, return_period, duration_hr, area if area > 1 else None)
    precip_mm = idf_result.depth_mm
    intensity_mmhr = idf_result.intensity_mmhr

    # PASO 3: Hietograma
    dt_hr = dt / 60
    hyetograph = alternating_blocks_dinagua(
        p3_10, return_period, duration_hr, dt, area if area > 1 else None
    )

    # PASO 4: Escorrentia SCS-CN
    runoff_result = calculate_scs_runoff(precip_mm, cn, lambda_coef)
    runoff_mm = runoff_result.runoff_mm

    # Calcular exceso de lluvia por intervalo
    cumulative_rain = np.array(hyetograph.cumulative_mm)
    excess_mm = rainfall_excess_series(cumulative_rain, cn, lambda_coef)

    # PASO 5: Hidrograma unitario
    if method == "triangular":
        uh_time, uh_flow = scs_triangular_uh(area, tc_hr, dt_hr)
    elif method == "curvilinear":
        uh_time, uh_flow = scs_curvilinear_uh(area, tc_hr, dt_hr)
    else:
        typer.echo(f"Error: Metodo UH desconocido: {method}", err=True)
        raise typer.Exit(1)

    # PASO 6: Convolucion
    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
    n_total = len(hydrograph_flow)
    hydrograph_time = np.arange(n_total) * dt_hr

    # Calcular resultados
    peak_idx = np.argmax(hydrograph_flow)
    peak_flow = float(hydrograph_flow[peak_idx])
    time_to_peak = float(hydrograph_time[peak_idx])
    volume_m3 = float(np.trapz(hydrograph_flow, hydrograph_time * 3600))

    # Mostrar resultados
    typer.echo(f"\n{'='*60}")
    typer.echo(f"  HIDROGRAMA SCS - ANALISIS COMPLETO")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n  DATOS DE ENTRADA:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Area de cuenca:        {area:>12.2f} km2")
    typer.echo(f"  Longitud cauce:        {length:>12.0f} m")
    typer.echo(f"  Pendiente:             {slope*100:>12.2f} %")
    typer.echo(f"  P3,10:                 {p3_10:>12.1f} mm")
    typer.echo(f"  Periodo retorno:       {return_period:>12} anos")
    typer.echo(f"  CN:                    {cn:>12}")
    typer.echo(f"  Metodo Tc:             {tc_method:>12}")
    typer.echo(f"  Metodo UH:             {method:>12}")

    typer.echo(f"\n  RESULTADOS INTERMEDIOS:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Tc:                    {tc_hr:>12.2f} hr ({tc_min:.1f} min)")
    typer.echo(f"  Duracion tormenta:     {duration_hr:>12.2f} hr")
    typer.echo(f"  Intensidad:            {intensity_mmhr:>12.2f} mm/hr")
    typer.echo(f"  Precipitacion total:   {precip_mm:>12.2f} mm")
    typer.echo(f"  Retencion S:           {runoff_result.retention_mm:>12.2f} mm")
    typer.echo(f"  Abstraccion Ia:        {runoff_result.initial_abstraction_mm:>12.2f} mm")
    typer.echo(f"  Escorrentia Q:         {runoff_mm:>12.2f} mm")
    typer.echo(f"  Coef. escorrentia:     {runoff_mm/precip_mm*100:>12.1f} %")

    typer.echo(f"\n  RESULTADOS FINALES:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  CAUDAL PICO:           {peak_flow:>12.3f} m3/s")
    typer.echo(f"  TIEMPO AL PICO:        {time_to_peak:>12.2f} hr ({time_to_peak*60:.1f} min)")
    typer.echo(f"  VOLUMEN:               {volume_m3:>12.0f} m3")
    typer.echo(f"{'='*60}\n")

    # Exportar si se solicita
    if output:
        with open(output, 'w') as f:
            f.write("Tiempo_hr,Caudal_m3s\n")
            for t, q in zip(hydrograph_time, hydrograph_flow):
                f.write(f"{t:.4f},{q:.4f}\n")
        typer.echo(f"Hidrograma exportado a: {output}")


@hydrograph_app.command("gz")
def hydrograph_gz(
    area_ha: Annotated[float, typer.Option("--area", "-a", help="Area de la cuenca en hectareas")],
    slope_pct: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media en porcentaje (%)")],
    c: Annotated[float, typer.Option("--c", help="Coeficiente de escorrentia (0-1)")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Periodo de retorno en anos")] = 2,
    x_factor: Annotated[float, typer.Option("--x", help="Factor X morfologico (1.0-5.5)")] = 1.0,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    t0: Annotated[float, typer.Option("--t0", help="Tiempo entrada Tc en minutos")] = 5.0,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo CSV de salida")] = None,
):
    """
    Genera hidrograma completo usando metodo GZ.

    Metodologia adaptada para drenaje urbano Uruguay:
    - Tc: Metodo de los Desbordes (DINAGUA)
    - IDF: Curvas DINAGUA Uruguay
    - Hietograma: 6 horas, bloques alternantes, pico en 1ra hora
    - Escorrentia: Coeficiente C (metodo racional)
    - Hidrograma: Triangular con factor X ajustable

    Valores tipicos de X:
        1.00 - Areas urbanas internas
        1.25 - Areas urbanas (gran pendiente)
        1.67 - Metodo NRCS/SCS estandar
        2.25 - Uso mixto rural/urbano

    Ejemplo:
        hidropluvial hydrograph gz --area 100 --slope 2.23 --c 0.62 --p3_10 83 --tr 2 --x 1.0
    """
    from hidropluvial.core import desbordes, triangular_uh_x, convolve_uh

    # PASO 1: Tiempo de concentracion (Metodo Desbordes)
    tc_hr = desbordes(area_ha, slope_pct, c, t0)
    tc_min = tc_hr * 60

    # PASO 2: Hietograma de 6 horas con pico adelantado
    duration_hr = 6.0
    peak_position = 1.0 / 6.0  # Pico en la primera hora

    hyetograph = alternating_blocks_dinagua(
        p3_10, return_period, duration_hr, dt, None, peak_position
    )

    precip_mm = hyetograph.total_depth_mm

    # PASO 3: Escorrentia con coeficiente C
    # Pe = C × P (para cada intervalo)
    depths = np.array(hyetograph.depth_mm)
    excess_mm = c * depths
    total_runoff_mm = float(np.sum(excess_mm))

    # PASO 4: Hidrograma unitario triangular con factor X
    dt_hr = dt / 60
    uh_time, uh_flow = triangular_uh_x(area_ha, tc_hr, dt_hr, x_factor)

    # PASO 5: Convolucion
    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
    n_total = len(hydrograph_flow)
    hydrograph_time = np.arange(n_total) * dt_hr

    # Calcular resultados
    peak_idx = np.argmax(hydrograph_flow)
    peak_flow = float(hydrograph_flow[peak_idx])
    time_to_peak = float(hydrograph_time[peak_idx])
    volume_m3 = float(np.trapz(hydrograph_flow, hydrograph_time * 3600))

    # Calcular Tp y Tb teoricos
    tp_teorico = 0.5 * dt_hr + 0.6 * tc_hr
    tb_teorico = (1 + x_factor) * tp_teorico

    # Mostrar resultados
    typer.echo(f"\n{'='*60}")
    typer.echo(f"  HIDROGRAMA GZ - ANALISIS COMPLETO")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n  DATOS DE ENTRADA:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Area de cuenca:        {area_ha:>12.2f} ha")
    typer.echo(f"  Pendiente:             {slope_pct:>12.2f} %")
    typer.echo(f"  Coef. escorrentia C:   {c:>12.2f}")
    typer.echo(f"  P3,10:                 {p3_10:>12.1f} mm")
    typer.echo(f"  Periodo retorno:       {return_period:>12} anos")
    typer.echo(f"  Factor X:              {x_factor:>12.2f}")

    typer.echo(f"\n  RESULTADOS INTERMEDIOS:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Tc (Desbordes):        {tc_hr:>12.2f} hr ({tc_min:.1f} min)")
    typer.echo(f"  Tp teorico:            {tp_teorico:>12.2f} hr ({tp_teorico*60:.1f} min)")
    typer.echo(f"  Tb teorico:            {tb_teorico:>12.2f} hr ({tb_teorico*60:.1f} min)")
    typer.echo(f"  Duracion tormenta:     {duration_hr:>12.1f} hr")
    typer.echo(f"  Precipitacion total:   {precip_mm:>12.2f} mm")
    typer.echo(f"  Escorrentia (C*P):     {total_runoff_mm:>12.2f} mm")

    typer.echo(f"\n  RESULTADOS FINALES:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  CAUDAL PICO:           {peak_flow:>12.3f} m3/s")
    typer.echo(f"  TIEMPO AL PICO:        {time_to_peak:>12.2f} hr ({time_to_peak*60:.1f} min)")
    typer.echo(f"  VOLUMEN:               {volume_m3:>12.0f} m3")
    typer.echo(f"{'='*60}\n")

    # Exportar si se solicita
    if output:
        with open(output, 'w') as f:
            f.write("Tiempo_hr,Caudal_m3s\n")
            for t, q in zip(hydrograph_time, hydrograph_flow):
                f.write(f"{t:.4f},{q:.4f}\n")
        typer.echo(f"Hidrograma exportado a: {output}")


# ============================================================================
# Comandos de Reporte
# ============================================================================

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


# ============================================================================
# Comandos de Exportación
# ============================================================================

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


# ============================================================================
# Comandos de Sesión
# ============================================================================

# Instancia global del gestor de sesiones
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtiene o crea el gestor de sesiones."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


@session_app.command("create")
def session_create(
    name: Annotated[str, typer.Argument(help="Nombre de la sesión")],
    area_ha: Annotated[float, typer.Option("--area", "-a", help="Área en hectáreas")],
    slope_pct: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media en %")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    c: Annotated[Optional[float], typer.Option("--c", help="Coef. escorrentía (0-1)")] = None,
    cn: Annotated[Optional[int], typer.Option("--cn", help="Curve Number (30-100)")] = None,
    length_m: Annotated[Optional[float], typer.Option("--length", "-l", help="Longitud cauce en m")] = None,
    cuenca_nombre: Annotated[str, typer.Option("--cuenca", help="Nombre de la cuenca")] = "",
):
    """
    Crea una nueva sesión de análisis.

    Ejemplo:
        hidropluvial session create "Proyecto Norte" --area 62 --slope 3.41 --p3_10 83 --c 0.62 --cn 81
    """
    manager = get_session_manager()

    session = manager.create(
        name=name,
        area_ha=area_ha,
        slope_pct=slope_pct,
        p3_10=p3_10,
        c=c,
        cn=cn,
        length_m=length_m,
        cuenca_nombre=cuenca_nombre,
    )

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  SESION CREADA")
    typer.echo(f"{'='*55}")
    typer.echo(f"  ID:                {session.id}")
    typer.echo(f"  Nombre:            {session.name}")
    typer.echo(f"  Cuenca:            {session.cuenca.nombre}")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Área:              {session.cuenca.area_ha:>10.2f} ha")
    typer.echo(f"  Pendiente:         {session.cuenca.slope_pct:>10.2f} %")
    typer.echo(f"  P3,10:             {session.cuenca.p3_10:>10.1f} mm")
    if session.cuenca.c:
        typer.echo(f"  Coef. C:           {session.cuenca.c:>10.2f}")
    if session.cuenca.cn:
        typer.echo(f"  CN:                {session.cuenca.cn:>10}")
    if session.cuenca.length_m:
        typer.echo(f"  Longitud cauce:    {session.cuenca.length_m:>10.0f} m")
    typer.echo(f"{'='*55}")
    typer.echo(f"\n  Usa 'session tc {session.id}' para calcular Tc")
    typer.echo(f"  Usa 'session analyze {session.id}' para análisis completo\n")


@session_app.command("list")
def session_list():
    """Lista todas las sesiones disponibles."""
    manager = get_session_manager()
    sessions = manager.list_sessions()

    if not sessions:
        typer.echo("\nNo hay sesiones guardadas.")
        typer.echo("Usa 'session create' para crear una nueva.\n")
        return

    typer.echo(f"\n{'='*75}")
    typer.echo(f"  SESIONES DISPONIBLES")
    typer.echo(f"{'='*75}")
    typer.echo(f"  {'ID':8} | {'Nombre':20} | {'Cuenca':15} | {'Análisis':>8} | {'Actualizado':19}")
    typer.echo(f"  {'-'*71}")

    for s in sessions:
        updated = s["updated_at"][:19].replace("T", " ")
        typer.echo(f"  {s['id']:8} | {s['name'][:20]:20} | {s['cuenca'][:15]:15} | {s['n_analyses']:>8} | {updated}")

    typer.echo(f"{'='*75}\n")


@session_app.command("show")
def session_show(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """Muestra detalles de una sesión."""
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  SESION: {session.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"  ID:                {session.id}")
    typer.echo(f"  Creada:            {session.created_at[:19].replace('T', ' ')}")
    typer.echo(f"  Actualizada:       {session.updated_at[:19].replace('T', ' ')}")

    typer.echo(f"\n  CUENCA: {session.cuenca.nombre}")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Área:              {session.cuenca.area_ha:>12.2f} ha")
    typer.echo(f"  Pendiente:         {session.cuenca.slope_pct:>12.2f} %")
    typer.echo(f"  P3,10:             {session.cuenca.p3_10:>12.1f} mm")
    if session.cuenca.c:
        typer.echo(f"  Coef. C:           {session.cuenca.c:>12.2f}")
    if session.cuenca.cn:
        typer.echo(f"  CN:                {session.cuenca.cn:>12}")
    if session.cuenca.length_m:
        typer.echo(f"  Longitud cauce:    {session.cuenca.length_m:>12.0f} m")

    # Mostrar Tc calculados
    if session.tc_results:
        typer.echo(f"\n  TIEMPOS DE CONCENTRACION:")
        typer.echo(f"  {'-'*45}")
        for tc in session.tc_results:
            typer.echo(f"  {tc.method:15} Tc = {tc.tc_min:>8.1f} min ({tc.tc_hr:.2f} hr)")

    # Mostrar análisis
    if session.analyses:
        typer.echo(f"\n  ANALISIS REALIZADOS: {len(session.analyses)}")
        typer.echo(f"  {'-'*45}")
        for a in session.analyses:
            x_str = f"X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else ""
            typer.echo(f"  [{a.id}] {a.tc.method} + {a.storm.type} Tr{a.storm.return_period} {x_str}")
            typer.echo(f"          Qp = {a.hydrograph.peak_flow_m3s:.3f} m³/s, Tp = {a.hydrograph.time_to_peak_min:.1f} min")

    typer.echo(f"{'='*60}\n")


@session_app.command("tc")
def session_tc(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    methods: Annotated[str, typer.Option("--methods", "-m", help="Métodos: kirpich,temez,desbordes")] = "desbordes",
):
    """
    Calcula tiempo de concentración con múltiples métodos.

    Ejemplo:
        hidropluvial session tc abc123 --methods "kirpich,desbordes"
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    from hidropluvial.core import kirpich, temez, desbordes

    method_list = [m.strip().lower() for m in methods.split(",")]

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  CALCULO DE TIEMPOS DE CONCENTRACION")
    typer.echo(f"  Sesión: {session.name} [{session.id}]")
    typer.echo(f"{'='*55}")

    for method in method_list:
        tc_hr = None
        params = {}

        if method == "kirpich":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            tc_hr = kirpich(session.cuenca.length_m, slope_mm)
            params = {"length_m": session.cuenca.length_m, "slope_mm": slope_mm}

        elif method == "temez":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            length_km = session.cuenca.length_m / 1000
            tc_hr = temez(length_km, slope_mm)
            params = {"length_km": length_km, "slope_mm": slope_mm}

        elif method == "desbordes":
            if not session.cuenca.c:
                typer.echo(f"  {method}: ERROR - Requiere coeficiente C", err=True)
                continue
            tc_hr = desbordes(
                session.cuenca.area_ha,
                session.cuenca.slope_pct,
                session.cuenca.c,
            )
            params = {
                "area_ha": session.cuenca.area_ha,
                "slope_pct": session.cuenca.slope_pct,
                "c": session.cuenca.c,
            }

        else:
            typer.echo(f"  {method}: ERROR - Método desconocido", err=True)
            continue

        if tc_hr:
            result = manager.add_tc_result(session, method, tc_hr, **params)
            typer.echo(f"  {method:15} Tc = {result.tc_min:>8.1f} min ({result.tc_hr:.2f} hr)")

    typer.echo(f"{'='*55}\n")


@session_app.command("analyze")
def session_analyze(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    tc_method: Annotated[str, typer.Option("--tc", help="Método Tc a usar")] = "desbordes",
    storm_type: Annotated[str, typer.Option("--storm", "-s", help="Tipo de tormenta: gz, blocks, bimodal")] = "gz",
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno")] = 2,
    x_factor: Annotated[float, typer.Option("--x", help="Factor X (solo para gz)")] = 1.0,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
):
    """
    Ejecuta un análisis completo (Tc + Tormenta + Hidrograma).

    Ejemplo:
        hidropluvial session analyze abc123 --tc desbordes --storm gz --tr 2 --x 1.0
        hidropluvial session analyze abc123 --tc kirpich --storm blocks --tr 25
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    from hidropluvial.core import kirpich, temez, desbordes, triangular_uh_x, convolve_uh

    # PASO 1: Obtener Tc
    tc_hr = None
    tc_result = next((tc for tc in session.tc_results if tc.method == tc_method), None)

    if tc_result:
        tc_hr = tc_result.tc_hr
    else:
        # Calcular si no existe
        if tc_method == "desbordes" and session.cuenca.c:
            tc_hr = desbordes(session.cuenca.area_ha, session.cuenca.slope_pct, session.cuenca.c)
        elif tc_method == "kirpich" and session.cuenca.length_m:
            tc_hr = kirpich(session.cuenca.length_m, session.cuenca.slope_pct / 100)
        elif tc_method == "temez" and session.cuenca.length_m:
            tc_hr = temez(session.cuenca.length_m / 1000, session.cuenca.slope_pct / 100)
        else:
            typer.echo(f"Error: No se puede calcular Tc con método '{tc_method}'", err=True)
            raise typer.Exit(1)

        # Guardar para futuras referencias
        manager.add_tc_result(session, tc_method, tc_hr)

    # PASO 2: Generar hietograma
    duration_hr = 6.0 if storm_type == "gz" else max(tc_hr, 1.0)

    if storm_type == "gz":
        peak_position = 1.0 / 6.0
        hyetograph = alternating_blocks_dinagua(
            session.cuenca.p3_10, return_period, duration_hr, dt, None, peak_position
        )
    elif storm_type == "blocks":
        hyetograph = alternating_blocks_dinagua(
            session.cuenca.p3_10, return_period, duration_hr, dt, None
        )
    elif storm_type == "bimodal":
        from hidropluvial.core import bimodal_dinagua
        hyetograph = bimodal_dinagua(
            session.cuenca.p3_10, return_period, duration_hr, dt
        )
    else:
        typer.echo(f"Error: Tipo de tormenta desconocido: {storm_type}", err=True)
        raise typer.Exit(1)

    # PASO 3: Calcular escorrentía
    depths = np.array(hyetograph.depth_mm)

    if session.cuenca.c:
        # Método coeficiente C
        excess_mm = session.cuenca.c * depths
        runoff_mm = float(np.sum(excess_mm))
    elif session.cuenca.cn:
        # Método SCS-CN
        cumulative = np.array(hyetograph.cumulative_mm)
        excess_mm = rainfall_excess_series(cumulative, session.cuenca.cn)
        runoff_mm = float(np.sum(excess_mm))
    else:
        typer.echo("Error: Se requiere C o CN para calcular escorrentía", err=True)
        raise typer.Exit(1)

    # PASO 4: Generar hidrograma
    dt_hr = dt / 60

    if storm_type == "gz" or session.cuenca.c:
        # Usar hidrograma triangular con X
        uh_time, uh_flow = triangular_uh_x(session.cuenca.area_ha, tc_hr, dt_hr, x_factor)
    else:
        # Usar SCS triangular estándar (X=1.67)
        uh_time, uh_flow = scs_triangular_uh(session.cuenca.area_ha / 100, tc_hr, dt_hr)
        x_factor = 1.67

    # Convolución
    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
    n_total = len(hydrograph_flow)
    hydrograph_time = np.arange(n_total) * dt_hr

    # Resultados
    peak_idx = np.argmax(hydrograph_flow)
    peak_flow = float(hydrograph_flow[peak_idx])
    time_to_peak = float(hydrograph_time[peak_idx])
    volume_m3 = float(np.trapz(hydrograph_flow, hydrograph_time * 3600))

    # Guardar análisis
    analysis = manager.add_analysis(
        session=session,
        tc_method=tc_method,
        tc_hr=tc_hr,
        storm_type=storm_type,
        return_period=return_period,
        duration_hr=duration_hr,
        total_depth_mm=hyetograph.total_depth_mm,
        peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
        n_intervals=len(hyetograph.time_min),
        peak_flow_m3s=peak_flow,
        time_to_peak_hr=time_to_peak,
        volume_m3=volume_m3,
        runoff_mm=runoff_mm,
        x_factor=x_factor if storm_type == "gz" else None,
        # Series temporales para gráficos
        storm_time_min=list(hyetograph.time_min),
        storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
        hydrograph_time_hr=[float(t) for t in hydrograph_time],
        hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
    )

    # Mostrar resultados
    typer.echo(f"\n{'='*60}")
    typer.echo(f"  ANALISIS COMPLETADO [{analysis.id}]")
    typer.echo(f"  Sesión: {session.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n  PARAMETROS:")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Método Tc:         {tc_method:>15}")
    typer.echo(f"  Tipo tormenta:     {storm_type:>15}")
    typer.echo(f"  Período retorno:   {return_period:>15} años")
    if storm_type == "gz":
        typer.echo(f"  Factor X:          {x_factor:>15.2f}")

    typer.echo(f"\n  RESULTADOS:")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Tc:                {tc_hr:>12.2f} hr ({tc_hr*60:.1f} min)")
    typer.echo(f"  Precipitación:     {hyetograph.total_depth_mm:>12.2f} mm")
    typer.echo(f"  Escorrentía:       {runoff_mm:>12.2f} mm")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  CAUDAL PICO:       {peak_flow:>12.3f} m³/s")
    typer.echo(f"  TIEMPO AL PICO:    {time_to_peak:>12.2f} hr ({time_to_peak*60:.1f} min)")
    typer.echo(f"  VOLUMEN:           {volume_m3:>12.0f} m³")
    typer.echo(f"{'='*60}\n")


@session_app.command("summary")
def session_summary(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """
    Muestra tabla comparativa de todos los análisis.

    Ejemplo:
        hidropluvial session summary abc123
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo(f"\nNo hay análisis en la sesión '{session.name}'.")
        typer.echo("Usa 'session analyze' para ejecutar análisis.\n")
        return

    rows = manager.get_summary_table(session)

    typer.echo(f"\n{'='*100}")
    typer.echo(f"  RESUMEN COMPARATIVO - {session.name}")
    typer.echo(f"{'='*100}")
    typer.echo(f"  {'ID':8} | {'Tc':12} | {'Tc(min)':>8} | {'Tormenta':10} | {'Tr':>4} | {'X':>5} | {'P(mm)':>7} | {'Q(mm)':>7} | {'Qp(m³/s)':>9} | {'Tp(min)':>8}")
    typer.echo(f"  {'-'*96}")

    for r in rows:
        x_str = f"{r['x']:.2f}" if r['x'] else "-"
        typer.echo(
            f"  {r['id']:8} | {r['tc_method']:12} | {r['tc_min']:>8.1f} | {r['storm']:10} | "
            f"{r['tr']:>4} | {x_str:>5} | {r['depth_mm']:>7.1f} | {r['runoff_mm']:>7.1f} | "
            f"{r['qpeak_m3s']:>9.3f} | {r['tp_min']:>8.1f}"
        )

    typer.echo(f"{'='*100}\n")

    # Mostrar máximos/mínimos
    if len(rows) > 1:
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])

        typer.echo(f"  Caudal máximo: {max_q['qpeak_m3s']:.3f} m³/s ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")
        typer.echo(f"  Caudal mínimo: {min_q['qpeak_m3s']:.3f} m³/s ({min_q['tc_method']} + {min_q['storm']} Tr{min_q['tr']})")
        typer.echo(f"  Variación: {(max_q['qpeak_m3s'] - min_q['qpeak_m3s']) / min_q['qpeak_m3s'] * 100:.1f}%\n")


@session_app.command("delete")
def session_delete(
    session_id: Annotated[str, typer.Argument(help="ID de la sesión a eliminar")],
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
):
    """Elimina una sesión."""
    manager = get_session_manager()

    if not force:
        confirm = typer.confirm(f"¿Eliminar sesión '{session_id}'?")
        if not confirm:
            typer.echo("Cancelado.")
            raise typer.Exit(0)

    if manager.delete(session_id):
        typer.echo(f"Sesión '{session_id}' eliminada.")
    else:
        typer.echo(f"Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)


@session_app.command("batch")
def session_batch(
    config_file: Annotated[str, typer.Argument(help="Archivo YAML de configuración")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo LaTeX de salida")] = None,
):
    """
    Ejecuta análisis batch desde archivo YAML.

    Formato del archivo YAML:
    ```yaml
    session:
      name: "Cuenca Norte"
      cuenca:
        nombre: "Arroyo Las Piedras"
        area_ha: 62
        slope_pct: 3.41
        p3_10: 83
        c: 0.62
        cn: 81
        length_m: 800

    tc_methods:
      - kirpich
      - desbordes

    analyses:
      - storm: gz
        tr: [2, 10, 25]
        x: [1.0, 1.25]
      - storm: blocks
        tr: [10, 25]
    ```

    Ejemplo:
        hidropluvial session batch cuenca.yaml -o reporte.tex
    """
    import yaml

    config_path = Path(config_file)
    if not config_path.exists():
        typer.echo(f"Error: Archivo no encontrado: {config_file}", err=True)
        raise typer.Exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    manager = get_session_manager()

    # Crear sesión
    session_cfg = config.get("session", {})
    cuenca_cfg = session_cfg.get("cuenca", {})

    session = manager.create(
        name=session_cfg.get("name", "Batch Session"),
        area_ha=cuenca_cfg.get("area_ha"),
        slope_pct=cuenca_cfg.get("slope_pct"),
        p3_10=cuenca_cfg.get("p3_10"),
        c=cuenca_cfg.get("c"),
        cn=cuenca_cfg.get("cn"),
        length_m=cuenca_cfg.get("length_m"),
        cuenca_nombre=cuenca_cfg.get("nombre", ""),
    )

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  BATCH: Sesión creada [{session.id}]")
    typer.echo(f"{'='*55}")

    # Calcular Tc con todos los métodos
    from hidropluvial.core import kirpich, temez, desbordes

    tc_methods = config.get("tc_methods", ["desbordes"])

    typer.echo(f"\n  Calculando Tc...")
    for method in tc_methods:
        tc_hr = None
        if method == "kirpich" and session.cuenca.length_m:
            tc_hr = kirpich(session.cuenca.length_m, session.cuenca.slope_pct / 100)
        elif method == "temez" and session.cuenca.length_m:
            tc_hr = temez(session.cuenca.length_m / 1000, session.cuenca.slope_pct / 100)
        elif method == "desbordes" and session.cuenca.c:
            tc_hr = desbordes(session.cuenca.area_ha, session.cuenca.slope_pct, session.cuenca.c)

        if tc_hr:
            result = manager.add_tc_result(session, method, tc_hr)
            typer.echo(f"    {method:15} Tc = {result.tc_min:>6.1f} min")

    # Ejecutar análisis
    analyses_cfg = config.get("analyses", [])
    n_analyses = 0

    typer.echo(f"\n  Ejecutando análisis...")

    for analysis_cfg in analyses_cfg:
        storm_type = analysis_cfg.get("storm", "gz")
        return_periods = analysis_cfg.get("tr", [2])
        x_factors = analysis_cfg.get("x", [1.0])
        dt = analysis_cfg.get("dt", 5.0)

        # Normalizar a listas
        if not isinstance(return_periods, list):
            return_periods = [return_periods]
        if not isinstance(x_factors, list):
            x_factors = [x_factors]

        # Para cada combinación de Tc method
        for tc_result in session.tc_results:
            for tr in return_periods:
                for x in x_factors:
                    # Solo usar X para tormenta gz
                    if storm_type != "gz":
                        x = None

                    # Ejecutar análisis (silencioso)
                    from hidropluvial.core import triangular_uh_x, convolve_uh, bimodal_dinagua

                    tc_hr = tc_result.tc_hr

                    # Determinar duración y dt según tipo de tormenta
                    if storm_type == "gz":
                        duration_hr = 6.0
                        storm_dt = dt  # 5 min por defecto
                    elif storm_type == "blocks24":
                        duration_hr = 24.0
                        storm_dt = 10.0  # 10 min para tormentas de 24h
                    else:  # blocks, bimodal
                        duration_hr = max(tc_hr, 1.0)
                        storm_dt = dt

                    if storm_type == "gz":
                        peak_position = 1.0 / 6.0
                        hyetograph = alternating_blocks_dinagua(
                            session.cuenca.p3_10, tr, duration_hr, storm_dt, None, peak_position
                        )
                    elif storm_type in ("blocks", "blocks24"):
                        hyetograph = alternating_blocks_dinagua(
                            session.cuenca.p3_10, tr, duration_hr, storm_dt, None
                        )
                    elif storm_type == "bimodal":
                        hyetograph = bimodal_dinagua(session.cuenca.p3_10, tr, duration_hr, storm_dt)
                    else:
                        continue

                    depths = np.array(hyetograph.depth_mm)

                    if session.cuenca.c:
                        excess_mm = session.cuenca.c * depths
                        runoff_mm = float(np.sum(excess_mm))
                    elif session.cuenca.cn:
                        cumulative = np.array(hyetograph.cumulative_mm)
                        excess_mm = rainfall_excess_series(cumulative, session.cuenca.cn)
                        runoff_mm = float(np.sum(excess_mm))
                    else:
                        continue

                    dt_hr = storm_dt / 60
                    x_val = x if x else 1.0

                    if storm_type == "gz" or session.cuenca.c:
                        uh_time, uh_flow = triangular_uh_x(session.cuenca.area_ha, tc_hr, dt_hr, x_val)
                    else:
                        uh_time, uh_flow = scs_triangular_uh(session.cuenca.area_ha / 100, tc_hr, dt_hr)
                        x_val = 1.67

                    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
                    n_total = len(hydrograph_flow)
                    hydrograph_time = np.arange(n_total) * dt_hr

                    peak_idx = np.argmax(hydrograph_flow)
                    peak_flow = float(hydrograph_flow[peak_idx])
                    time_to_peak = float(hydrograph_time[peak_idx])
                    volume_m3 = float(np.trapz(hydrograph_flow, hydrograph_time * 3600))

                    manager.add_analysis(
                        session=session,
                        tc_method=tc_result.method,
                        tc_hr=tc_hr,
                        storm_type=storm_type,
                        return_period=tr,
                        duration_hr=duration_hr,
                        total_depth_mm=hyetograph.total_depth_mm,
                        peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
                        n_intervals=len(hyetograph.time_min),
                        peak_flow_m3s=peak_flow,
                        time_to_peak_hr=time_to_peak,
                        volume_m3=volume_m3,
                        runoff_mm=runoff_mm,
                        x_factor=x if storm_type == "gz" else None,
                        # Series temporales para gráficos
                        storm_time_min=list(hyetograph.time_min),
                        storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
                        hydrograph_time_hr=[float(t) for t in hydrograph_time],
                        hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
                    )

                    n_analyses += 1
                    x_str = f"X={x:.2f}" if x else ""
                    typer.echo(f"    {tc_result.method} + {storm_type} Tr{tr} {x_str} -> Qp={peak_flow:.3f} m³/s")

                    # Si no es gz, salir del bucle de x
                    if storm_type != "gz":
                        break

    typer.echo(f"\n  Total: {n_analyses} análisis completados")
    typer.echo(f"{'='*55}")

    # Mostrar resumen
    rows = manager.get_summary_table(session)
    if rows:
        typer.echo(f"\n  RESUMEN:")
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])
        typer.echo(f"    Caudal máximo: {max_q['qpeak_m3s']:.3f} m³/s ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")
        typer.echo(f"    Caudal mínimo: {min_q['qpeak_m3s']:.3f} m³/s ({min_q['tc_method']} + {min_q['storm']} Tr{min_q['tr']})")

    typer.echo(f"\n  Sesión guardada: {session.id}")
    typer.echo(f"  Usa 'session summary {session.id}' para ver tabla completa")
    typer.echo(f"  Usa 'session report {session.id}' para generar reporte LaTeX\n")


@session_app.command("report")
def session_report(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    output: Annotated[str, typer.Option("--output", "-o", help="Directorio de salida")] = "report",
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
    template_dir: Annotated[Optional[str], typer.Option("--template", "-t", help="Directorio con template Pablo Pizarro")] = None,
):
    """
    Genera reporte LaTeX con graficos TikZ para cada analisis.

    Crea un directorio con:
    - Archivo principal (.tex)
    - Graficos de hietogramas (hietograma_*.tex)
    - Graficos de hidrogramas (hidrograma_*.tex)

    Con --template: Genera documento compatible con template Pablo Pizarro
    y copia los archivos del template al directorio de salida.

    Ejemplo:
        hidropluvial session report abc123 -o reporte_cuenca --author "Ing. Perez"
        hidropluvial session report abc123 -o reporte --template examples/
    """
    import shutil
    from hidropluvial.reports.charts import (
        generate_hyetograph_tikz,
        generate_hydrograph_tikz,
        HydrographSeries,
    )

    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo(f"Error: No hay análisis en la sesión.", err=True)
        raise typer.Exit(1)

    # Crear directorio de salida
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = ReportGenerator()
    rows = manager.get_summary_table(session)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  GENERANDO REPORTE - {session.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"  Directorio: {output_dir.absolute()}")

    # =========================================================================
    # GENERAR GRÁFICOS TIKZ
    # =========================================================================
    generated_files = {"hyetographs": [], "hydrographs": []}

    typer.echo(f"\n  Generando gráficos TikZ...")

    for i, analysis in enumerate(session.analyses):
        # Verificar si hay datos de series temporales
        has_storm_data = len(analysis.storm.time_min) > 0 and len(analysis.storm.intensity_mmhr) > 0
        has_hydro_data = len(analysis.hydrograph.time_hr) > 0 and len(analysis.hydrograph.flow_m3s) > 0

        # Identificador único para el análisis
        x_str = f"_X{analysis.hydrograph.x_factor:.2f}".replace(".", "") if analysis.hydrograph.x_factor else ""
        file_id = f"{analysis.tc.method}_{analysis.storm.type}_Tr{analysis.storm.return_period}{x_str}"

        # -----------------------------------------------------------------
        # Generar hietograma
        # -----------------------------------------------------------------
        if has_storm_data:
            hyeto_filename = f"hietograma_{file_id}.tex"
            hyeto_path = output_dir / hyeto_filename

            hyeto_caption = (
                f"Hietograma - {analysis.storm.type.upper()} "
                f"$T_r$={analysis.storm.return_period} años "
                f"(P={analysis.storm.total_depth_mm:.1f} mm)"
            )

            hyeto_tikz = generate_hyetograph_tikz(
                time_min=analysis.storm.time_min,
                intensity_mmhr=analysis.storm.intensity_mmhr,
                caption=hyeto_caption,
                label=f"fig:hyeto_{file_id}",
                width=r"0.9\textwidth",
                height="6cm",
            )

            hyeto_path.write_text(hyeto_tikz, encoding="utf-8")
            generated_files["hyetographs"].append(hyeto_filename)
            typer.echo(f"    + {hyeto_filename}")

        # -----------------------------------------------------------------
        # Generar hidrograma
        # -----------------------------------------------------------------
        if has_hydro_data:
            hydro_filename = f"hidrograma_{file_id}.tex"
            hydro_path = output_dir / hydro_filename

            # Convertir tiempo de horas a minutos para el gráfico
            time_min_hydro = [t * 60 for t in analysis.hydrograph.time_hr]

            hydro_caption = (
                f"Hidrograma - {analysis.tc.method.title()} + {analysis.storm.type.upper()} "
                f"$T_r$={analysis.storm.return_period} años "
                r"($Q_p$=" + f"{analysis.hydrograph.peak_flow_m3s:.3f}" + r" m$^3$/s)"
            )

            x_label = f" X={analysis.hydrograph.x_factor:.2f}" if analysis.hydrograph.x_factor else ""
            series_label = f"{analysis.tc.method.title()}{x_label}"

            series = [
                HydrographSeries(
                    time_min=time_min_hydro,
                    flow_m3s=analysis.hydrograph.flow_m3s,
                    label=series_label,
                    color="blue",
                    style="solid",
                )
            ]

            hydro_tikz = generate_hydrograph_tikz(
                series=series,
                caption=hydro_caption,
                label=f"fig:hydro_{file_id}",
                width=r"0.9\textwidth",
                height="6cm",
            )

            hydro_path.write_text(hydro_tikz, encoding="utf-8")
            generated_files["hydrographs"].append(hydro_filename)
            typer.echo(f"    + {hydro_filename}")

    # =========================================================================
    # GENERAR ARCHIVOS DE SECCIONES SEPARADOS
    # =========================================================================

    # --- sec_cuenca.tex: Datos de la cuenca ---
    cuenca_content = f"""% Seccion: Datos de la Cuenca
% Generado automaticamente por HidroPluvial

\\section{{Datos de la Cuenca}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Parámetro & Valor \\\\
\\midrule
Nombre & {session.cuenca.nombre or session.name} \\\\
Área & {session.cuenca.area_ha:.2f} ha \\\\
Pendiente & {session.cuenca.slope_pct:.2f} \\% \\\\
$P_{{3,10}}$ & {session.cuenca.p3_10:.1f} mm \\\\
"""
    if session.cuenca.c:
        cuenca_content += f"Coef. escorrentía C & {session.cuenca.c:.2f} \\\\\n"
    if session.cuenca.cn:
        cuenca_content += f"Curve Number CN & {session.cuenca.cn} \\\\\n"
    if session.cuenca.length_m:
        cuenca_content += f"Longitud cauce & {session.cuenca.length_m:.0f} m \\\\\n"

    cuenca_content += """\\bottomrule
\\end{tabular}
\\caption{Características de la cuenca}
\\label{tab:cuenca}
\\end{table}
"""

    # --- sec_tc.tex: Tiempos de concentración ---
    tc_content = """% Seccion: Tiempos de Concentracion
% Generado automaticamente por HidroPluvial

\\section{Tiempos de Concentración}

\\begin{table}[H]
\\centering
\\begin{tabular}{lrr}
\\toprule
Método & $T_c$ (hr) & $T_c$ (min) \\\\
\\midrule
"""
    for tc in session.tc_results:
        tc_content += f"{tc.method.title()} & {tc.tc_hr:.3f} & {tc.tc_min:.1f} \\\\\n"

    tc_content += """\\bottomrule
\\end{tabular}
\\caption{Tiempos de concentración calculados}
\\label{tab:tc}
\\end{table}
"""

    # --- sec_resultados.tex: Tabla de resultados ---
    results_content = f"""% Seccion: Resultados de Analisis
% Generado automaticamente por HidroPluvial

\\section{{Resultados de Análisis}}

Se realizaron {len(rows)} combinaciones de análisis variando:
\\begin{{itemize}}
    \\item Métodos de tiempo de concentración
    \\item Tipos de tormenta de diseño
    \\item Períodos de retorno
    \\item Factor morfológico X (para tormentas GZ)
\\end{{itemize}}

\\begin{{table}}[H]
\\centering
\\footnotesize
\\begin{{tabular}}{{lccccccc}}
\\toprule
Método $T_c$ & Tormenta & $T_r$ & X & P (mm) & Q (mm) & $Q_p$ (m$^3$/s) & Vol (m$^3$) \\\\
\\midrule
"""
    for r in rows:
        x_str = f"{r['x']:.2f}" if r['x'] else "-"
        results_content += (
            f"{r['tc_method']} & {r['storm']} & {r['tr']} & {x_str} & "
            f"{r['depth_mm']:.1f} & {r['runoff_mm']:.1f} & {r['qpeak_m3s']:.3f} & {r['vol_m3']:.0f} \\\\\n"
        )

    results_content += """\\bottomrule
\\end{tabular}
\\caption{Tabla comparativa de análisis}
\\label{tab:results}
\\end{table}
"""

    # --- sec_estadisticas.tex: Resumen estadístico ---
    stats_content = ""
    if len(rows) > 1:
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])
        avg_q = sum(r['qpeak_m3s'] for r in rows) / len(rows)
        variation = (max_q['qpeak_m3s'] - min_q['qpeak_m3s']) / min_q['qpeak_m3s'] * 100

        stats_content = f"""% Seccion: Resumen Estadistico
% Generado automaticamente por HidroPluvial

\\section{{Resumen Estadístico}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Estadístico & Valor \\\\
\\midrule
Número de análisis & {len(rows)} \\\\
Caudal pico máximo & {max_q['qpeak_m3s']:.3f} m$^3$/s ({max_q['tc_method']} + {max_q['storm']} $T_r$={max_q['tr']}) \\\\
Caudal pico mínimo & {min_q['qpeak_m3s']:.3f} m$^3$/s ({min_q['tc_method']} + {min_q['storm']} $T_r$={min_q['tr']}) \\\\
Caudal pico promedio & {avg_q:.3f} m$^3$/s \\\\
Variación máx/mín & {variation:.1f}\\% \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Resumen estadístico de caudales pico}}
\\label{{tab:summary}}
\\end{{table}}

\\subsection{{Observaciones}}

\\begin{{itemize}}
    \\item La variación entre métodos es del {variation:.1f}\\%, lo que indica {"alta" if variation > 50 else "moderada" if variation > 20 else "baja"} sensibilidad a la metodología empleada.
    \\item El caudal de diseño recomendado depende del nivel de riesgo aceptable para la obra.
    \\item Para obras de infraestructura crítica, considerar el valor máximo.
    \\item Para drenaje menor, puede utilizarse el valor promedio o el correspondiente al $T_r$ de diseño.
\\end{{itemize}}
"""

    # --- sec_hietogramas.tex: Sección de hietogramas ---
    hyetograph_content = ""
    if generated_files["hyetographs"]:
        hyetograph_content = """% Seccion: Hietogramas de Diseno
% Generado automaticamente por HidroPluvial

\\section{Hietogramas de Diseño}

"""
        for hfile in generated_files["hyetographs"]:
            hyetograph_content += f"\\input{{{hfile}}}\n\n"

    # --- sec_hidrogramas.tex: Sección de hidrogramas ---
    hydrograph_content = ""
    if generated_files["hydrographs"]:
        hydrograph_content = """% Seccion: Hidrogramas de Salida
% Generado automaticamente por HidroPluvial

\\section{Hidrogramas de Salida}

"""
        for hfile in generated_files["hydrographs"]:
            hydrograph_content += f"\\input{{{hfile}}}\n\n"

    # --- sec_metodologia.tex: Metodología ---
    methodology_content = """% Seccion: Metodologia
% Generado automaticamente por HidroPluvial

\\section{Metodología}

\\subsection{Tiempo de Concentración}

\\textbf{Método de Kirpich:}
\\begin{equation}
T_c = 0.0195 \\times L^{0.77} \\times S^{-0.385}
\\end{equation}

donde $L$ es la longitud del cauce principal en metros y $S$ la pendiente media (m/m).

\\textbf{Método de los Desbordes (DINAGUA):}
\\begin{equation}
T_c = T_0 + 6.625 \\times A^{0.3} \\times P^{-0.39} \\times C^{-0.45}
\\end{equation}

donde $A$ es el área en hectáreas, $P$ la pendiente en \\%, $C$ el coeficiente de escorrentía, y $T_0 = 5$ min.

\\subsection{Curvas IDF DINAGUA}

Factor por período de retorno:
\\begin{equation}
C_T(T_r) = 0.5786 - 0.4312 \\times \\log_{10}\\left[\\ln\\left(\\frac{T_r}{T_r - 1}\\right)\\right]
\\end{equation}

Ecuaciones de intensidad:
\\begin{equation}
I(d) = \\frac{P_{3,10} \\times C_T(T_r) \\times 0.6208}{(d + 0.0137)^{0.5639}} \\quad \\text{para } d < 3 \\text{ horas}
\\end{equation}

\\begin{equation}
I(d) = \\frac{P_{3,10} \\times C_T(T_r) \\times 1.0287}{(d + 1.0293)^{0.8083}} \\quad \\text{para } d \\geq 3 \\text{ horas}
\\end{equation}

\\subsection{Hidrograma Unitario Triangular}

\\begin{equation}
T_p = 0.5 \\times \\Delta t + 0.6 \\times T_c
\\end{equation}

\\begin{equation}
q_p = 0.278 \\times \\frac{A}{T_p} \\times \\frac{2}{1 + X}
\\end{equation}

\\begin{equation}
T_b = (1 + X) \\times T_p
\\end{equation}

donde $A$ es el área en km², $T_p$ el tiempo al pico en horas, y $X$ el factor morfológico.
"""

    # Diccionario de secciones para guardar
    sections = {
        "sec_cuenca.tex": cuenca_content,
        "sec_tc.tex": tc_content,
        "sec_resultados.tex": results_content,
        "sec_metodologia.tex": methodology_content,
    }
    if stats_content:
        sections["sec_estadisticas.tex"] = stats_content
    if hyetograph_content:
        sections["sec_hietogramas.tex"] = hyetograph_content
    if hydrograph_content:
        sections["sec_hidrogramas.tex"] = hydrograph_content

    # =========================================================================
    # GENERAR DOCUMENTO PRINCIPAL
    # =========================================================================
    main_filename = f"{session.name.replace(' ', '_').lower()}_memoria.tex"
    main_path = output_dir / main_filename

    if template_dir:
        # Copiar archivos del template al directorio de salida
        template_path = Path(template_dir)
        template_file = template_path / "template.tex"
        config_file = template_path / "template_config.tex"

        if template_file.exists():
            shutil.copy(template_file, output_dir / "template.tex")
            typer.echo(f"    + template.tex")
        else:
            typer.echo(f"  Advertencia: No se encontro template.tex en {template_dir}", err=True)

        if config_file.exists():
            shutil.copy(config_file, output_dir / "template_config.tex")
            typer.echo(f"    + template_config.tex")

        # Copiar carpeta departamentos si existe (para logos)
        dept_dir = template_path / "departamentos"
        if dept_dir.exists() and dept_dir.is_dir():
            import shutil as sh
            dest_dept = output_dir / "departamentos"
            if dest_dept.exists():
                sh.rmtree(dest_dept)
            sh.copytree(dept_dir, dest_dept)
            typer.echo(f"    + departamentos/")

        # Generar documento compatible con template Pablo Pizarro
        safe_title = session.name.replace("_", " ")

        # =====================================================================
        # GUARDAR ARCHIVOS DE SECCIONES SEPARADOS
        # =====================================================================
        typer.echo(f"\n  Generando secciones LaTeX...")
        section_files = []
        for sec_filename, sec_content in sections.items():
            sec_path = output_dir / sec_filename
            sec_path.write_text(sec_content, encoding="utf-8")
            section_files.append(sec_filename)
            typer.echo(f"    + {sec_filename}")

        # =====================================================================
        # GENERAR document.tex (solo imports de secciones)
        # =====================================================================
        document_content = """% Documento de contenido
% Generado automaticamente por HidroPluvial
% Este archivo importa todas las secciones del reporte

"""
        # Orden de secciones
        section_order = [
            "sec_cuenca.tex",
            "sec_tc.tex",
            "sec_resultados.tex",
            "sec_estadisticas.tex",
            "sec_hietogramas.tex",
            "sec_hidrogramas.tex",
            "sec_metodologia.tex",
        ]
        for sec in section_order:
            if sec in sections:
                document_content += f"\\input{{{sec.replace('.tex', '')}}}\n"

        doc_content_file = output_dir / "document.tex"
        doc_content_file.write_text(document_content, encoding="utf-8")
        typer.echo(f"    + document.tex")

        # =====================================================================
        # GENERAR main.tex (archivo principal limpio)
        # =====================================================================
        doc = f"""% Memoria de Calculo Hidrologico
% Generado automaticamente por HidroPluvial
% Template: Informe LaTeX - Pablo Pizarro R.
% Version: 8.3.6

% CREACION DEL DOCUMENTO
\\documentclass[
    spanish,
    letterpaper, oneside
]{{article}}

% INFORMACION DEL DOCUMENTO
\\def\\documenttitle {{{safe_title}}}
\\def\\documentsubtitle {{Memoria de Calculo Hidrologico}}
\\def\\documentsubject {{Analisis de escorrentia y caudales de diseno}}

\\def\\documentauthor {{{author or "HidroPluvial"}}}
\\def\\coursename {{}}
\\def\\coursecode {{}}

\\def\\universityname {{}}
\\def\\universityfaculty {{}}
\\def\\universitydepartment {{}}
\\def\\universitydepartmentimage {{}}
\\def\\universitydepartmentimagecfg {{height=3.5cm}}
\\def\\universitylocation {{Uruguay}}

% INTEGRANTES Y FECHAS
\\def\\authortable {{
    \\begin{{tabular}}{{ll}}
        Autor: & {author or "HidroPluvial"} \\\\
        \\\\
        \\multicolumn{{2}}{{l}}{{Fecha: \\today}} \\\\
        \\multicolumn{{2}}{{l}}{{\\universitylocation}}
    \\end{{tabular}}
}}

% IMPORTACION DEL TEMPLATE
\\input{{template}}

% Paquetes adicionales (no incluidos en template)
\\usepackage{{tabularx}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\usepackage{{makecell}}

% INICIO DE PAGINAS
\\begin{{document}}

% Compresion PDF
\\pdfcompresslevel=9
\\pdfobjcompresslevel=3

% PORTADA
\\templatePortrait

% CONFIGURACION DE PAGINA
\\templatePagecfg

% TABLA DE CONTENIDOS
\\templateIndex

% CONFIGURACIONES FINALES
\\templateFinalcfg

% CONTENIDO
\\input{{document}}

% FIN DEL DOCUMENTO
\\end{{document}}
"""
    else:
        # Generar documento standalone completo (sin template Pablo Pizarro)
        # Combinar todas las secciones en un solo contenido
        content = "\n".join(sections.values())
        doc = generator.generate_standalone_document(
            content=content,
            title=f"Memoria de Calculo: {session.name}",
            author=author,
            include_tikz=True,
        )

    main_path.write_text(doc, encoding="utf-8")

    # =========================================================================
    # RESUMEN
    # =========================================================================
    typer.echo(f"\n  {'='*50}")
    typer.echo(f"  ARCHIVOS GENERADOS:")
    typer.echo(f"  {'='*50}")
    typer.echo(f"  Documento principal: {main_filename}")
    if template_dir:
        typer.echo(f"  Template:            template.tex + template_config.tex")
        typer.echo(f"  Contenido:           document.tex")
        typer.echo(f"  Secciones:           {len(sections)} archivos (sec_*.tex)")
    typer.echo(f"  Hietogramas:         {len(generated_files['hyetographs'])} archivos")
    typer.echo(f"  Hidrogramas:         {len(generated_files['hydrographs'])} archivos")
    typer.echo(f"  {'='*50}")
    typer.echo(f"\n  Para compilar:")
    typer.echo(f"    cd {output_dir.absolute()}")
    typer.echo(f"    pdflatex {main_filename}")
    typer.echo(f"{'='*60}\n")


# ============================================================================
# Punto de entrada
# ============================================================================

if __name__ == "__main__":
    app()
