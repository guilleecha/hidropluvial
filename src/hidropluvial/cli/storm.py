"""
Comandos CLI para generación de tormentas de diseño.
"""

import json
from typing import Annotated, Optional

import typer

from hidropluvial.config import ShermanCoefficients, StormMethod
from hidropluvial.core import (
    alternating_blocks_dinagua,
    bimodal_storm,
    generate_hyetograph,
    generate_hyetograph_dinagua,
)
from hidropluvial.cli.theme import print_header, print_field, print_separator, print_error
from hidropluvial.cli.validators import (
    validate_p310, validate_duration, validate_return_period, validate_area,
)

# Crear sub-aplicación
storm_app = typer.Typer(help="Generación de tormentas de diseño")


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

    Ejemplo:
        hp storm uruguay 83 2 --tr 100
        hp storm uruguay 83 2 --tr 100 --area 25
        hp storm uruguay 78 6 --tr 50 -m scs -o hietograma.json
    """
    # Validar entradas
    validate_p310(p3_10)
    validate_duration(duration)
    if area is not None:
        validate_area(area)

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
        print_header("HIETOGRAMA DINAGUA URUGUAY")
        print_field("P3,10 base", f"{p3_10:.1f}", "mm")
        print_field("Periodo retorno", f"{return_period}", "anos")
        print_field("Duracion", f"{duration:.2f}", "hr")
        print_field("Intervalo dt", f"{dt:.1f}", "min")
        if area:
            print_field("Area cuenca", f"{area:.1f}", "km2")
        print_field("Metodo", result.method)
        print_separator()
        print_field("Precipitacion", f"{result.total_depth_mm:.2f}", "mm")
        print_field("Intensidad pico", f"{result.peak_intensity_mmhr:.2f}", "mm/hr")
        print_field("Intervalos", f"{len(result.time_min)}")
        print_separator()


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

    Ejemplo:
        hp storm bimodal 80
        hp storm bimodal 100 --duration 4 --peak1 0.3 --peak2 0.7
    """
    # Validar entradas
    if depth <= 0:
        print_error(f"La profundidad debe ser positiva (recibido: {depth})")
        raise typer.Exit(1)
    validate_duration(duration)

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
        hp storm bimodal-uy 83 --tr 2
        hp storm bimodal-uy 83 --tr 20 --peak1 0.3 --peak2 0.7
    """
    # Validar entradas
    validate_p310(p3_10)
    validate_duration(duration)
    if area is not None:
        validate_area(area)

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
        print_header("HIETOGRAMA BIMODAL DINAGUA")
        print_field("P3,10 base", f"{p3_10:.1f}", "mm")
        print_field("Periodo retorno", f"{return_period}", "anos")
        print_field("Duracion", f"{duration:.1f}", "hr")
        print_field("Intervalo dt", f"{dt:.1f}", "min")
        print_field("Pico 1", f"{peak1*100:.0f}", "%")
        print_field("Pico 2", f"{peak2*100:.0f}", "%")
        print_field("Split volumen", f"{split*100:.0f}% / {(1-split)*100:.0f}%")
        if area:
            print_field("Area cuenca", f"{area:.1f}", "km2")
        print_separator()
        print_field("Precipitacion", f"{result.total_depth_mm:.2f}", "mm")
        print_field("Intensidad pico", f"{result.peak_intensity_mmhr:.2f}", "mm/hr")
        print_field("Intervalos", f"{len(result.time_min)}")
        print_separator()


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
        hp storm gz 83 --tr 2
        hp storm gz 83 --tr 20
        hp storm gz 83 --tr 100
    """
    # Validar entradas
    validate_p310(p3_10)
    validate_duration(duration)
    if area is not None:
        validate_area(area)

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
        print_header("HIETOGRAMA GZ - TORMENTA 6 HORAS (PICO ADELANTADO)")
        print_field("P3,10 base", f"{p3_10:.1f}", "mm")
        print_field("Periodo retorno", f"{return_period}", "anos")
        print_field("Duracion", f"{duration:.1f}", "hr")
        print_field("Intervalo dt", f"{dt:.1f}", "min")
        print_field("Pico en", "1ra hora")
        if area:
            print_field("Area cuenca", f"{area:.1f}", "km2")
        print_separator()
        print_field("Precipitacion", f"{result.total_depth_mm:.2f}", "mm")
        print_field("Intensidad pico", f"{result.peak_intensity_mmhr:.2f}", "mm/hr")
        print_field("Intervalos", f"{len(result.time_min)}")
        print_separator()


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
    """
    Genera hietograma usando distribución SCS.

    Ejemplo:
        hp storm scs 100
        hp storm scs 80 --storm-type III --duration 12
    """
    # Validar entradas
    if depth <= 0:
        print_error(f"La profundidad debe ser positiva (recibido: {depth})")
        raise typer.Exit(1)
    validate_duration(duration)

    type_map = {
        "I": StormMethod.SCS_TYPE_I,
        "IA": StormMethod.SCS_TYPE_IA,
        "II": StormMethod.SCS_TYPE_II,
        "III": StormMethod.SCS_TYPE_III,
    }

    if storm_type.upper() not in type_map:
        print_error(f"Tipo inválido: {storm_type}. Use: I, IA, II, III")
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
    """
    Genera hietograma usando método de tormenta Chicago.

    Ejemplo:
        hp storm chicago 100
        hp storm chicago 80 --duration 3 --return-period 50
    """
    # Validar entradas
    if depth <= 0:
        print_error(f"La profundidad debe ser positiva (recibido: {depth})")
        raise typer.Exit(1)
    validate_duration(duration)
    validate_return_period(return_period)

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
