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

app.add_typer(idf_app, name="idf")
app.add_typer(storm_app, name="storm")
app.add_typer(tc_app, name="tc")
app.add_typer(runoff_app, name="runoff")
app.add_typer(hydrograph_app, name="hydrograph")
app.add_typer(report_app, name="report")
app.add_typer(export_app, name="export")


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
# Punto de entrada
# ============================================================================

if __name__ == "__main__":
    app()
