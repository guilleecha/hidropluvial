"""
Comandos CLI para análisis de curvas IDF.
"""

import json
from typing import Annotated, Optional

import typer

from hidropluvial.config import ShermanCoefficients
from hidropluvial.core import (
    dinagua_intensity,
    generate_dinagua_idf_table,
    generate_idf_table,
    get_depth,
    get_intensity,
    P3_10_URUGUAY,
)
from hidropluvial.cli.theme import (
    print_header, print_separator, print_field, print_note,
    print_success, print_error, get_console, get_palette,
)
from hidropluvial.cli.validators import (
    validate_p310, validate_duration, validate_return_period, validate_area,
)

# Crear sub-aplicación
idf_app = typer.Typer(help="Análisis de curvas IDF")


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
        hp idf uruguay 83 2 --tr 10
        hp idf uruguay 78 3 --tr 100 --area 25
    """
    # Validar entradas
    validate_p310(p3_10)
    validate_duration(duration)
    if area is not None:
        validate_area(area)

    result = dinagua_intensity(p3_10, return_period, duration, area)

    print_header("METODO DINAGUA URUGUAY")
    print_field("P3,10 base", f"{result.p3_10:.1f}", "mm")
    print_field("Periodo retorno", f"{result.return_period_yr:.0f}", "años")
    print_field("Duracion", f"{result.duration_hr:.2f}", "hr")
    if result.area_km2:
        print_field("Area cuenca", f"{result.area_km2:.1f}", "km²")
    print_separator("-", 50)
    print_field("Factor CT", f"{result.ct:.4f}")
    print_field("Factor CA", f"{result.ca:.4f}")
    print_separator("-", 50)
    print_field("INTENSIDAD", f"{result.intensity_mmhr:.2f}", "mm/hr")
    print_field("PRECIPITACION", f"{result.depth_mm:.2f}", "mm")


@idf_app.command("tabla-uy")
def idf_tabla_uruguay(
    p3_10: Annotated[float, typer.Argument(help="P3,10 base en mm")],
    area: Annotated[Optional[float], typer.Option("--area", "-a", help="Área cuenca km²")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo JSON")] = None,
):
    """
    Genera tabla IDF completa usando método DINAGUA Uruguay.

    Ejemplo:
        hp idf tabla-uy 83
        hp idf tabla-uy 83 --area 25
        hp idf tabla-uy 78 -o tabla_idf.json
    """
    # Validar entradas
    validate_p310(p3_10)
    if area is not None:
        validate_area(area)

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
    from rich.table import Table
    from rich import box

    console = get_console()
    p = get_palette()

    table = Table(
        title="P3,10 por Departamento",
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
    )
    table.add_column("Departamento", justify="left")
    table.add_column("P3,10", justify="right", style=p.number)
    table.add_column("", justify="left", style=p.unit)

    for depto, p310 in sorted(P3_10_URUGUAY.items()):
        table.add_row(depto.replace('_', ' ').title(), str(p310), "mm")

    console.print(table)
    print_note("Para proyectos críticos, mayorar 5-10% por cambio climático")


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
    """
    Calcula intensidad de lluvia desde curva IDF (método Sherman).

    Fórmula: i = k * T^m / (d + c)^n

    Ejemplo:
        hp idf sherman 60 10
        hp idf sherman 30 25 --k 1800 --m 0.20
    """
    # Validar entradas
    if duration <= 0:
        print_error(f"La duración debe ser positiva (recibido: {duration})")
        raise typer.Exit(1)
    validate_return_period(return_period)

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
    """
    Genera tabla completa de curvas IDF (método Sherman).

    Ejemplo:
        hp idf table
        hp idf table --k 1800 --m 0.20 -o tabla.json
    """
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
