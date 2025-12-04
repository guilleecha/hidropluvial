"""
Comandos CLI para cálculo de tiempo de concentración.
"""

from typing import Annotated

import typer

from hidropluvial.core import kirpich, temez

# Crear sub-aplicación
tc_app = typer.Typer(help="Cálculo de tiempo de concentración")


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
