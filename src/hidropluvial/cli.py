"""
CLI para HidroPluvial - Herramienta de cálculos hidrológicos.

Uso:
    hidropluvial --help
    hidropluvial idf --help
    hidropluvial storm --help
    hidropluvial tc --help
    hidropluvial runoff --help
    hidropluvial hydrograph --help
"""

import json
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

app.add_typer(idf_app, name="idf")
app.add_typer(storm_app, name="storm")
app.add_typer(tc_app, name="tc")
app.add_typer(runoff_app, name="runoff")
app.add_typer(hydrograph_app, name="hydrograph")


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

        typer.echo(f"\nTabla IDF DINAGUA Uruguay (P₃,₁₀ = {p3_10} mm)")
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
    typer.echo("\nValores de P₃,₁₀ por departamento (mm):")
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
        typer.echo(f"  P₃,₁₀ base:        {p3_10:>10.1f} mm")
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
# Punto de entrada
# ============================================================================

if __name__ == "__main__":
    app()
