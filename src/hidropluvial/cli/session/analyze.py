"""
Comando de análisis de sesión.
"""

from typing import Annotated

import numpy as np
import typer

from hidropluvial.core import (
    alternating_blocks_dinagua,
    rainfall_excess_series,
    scs_triangular_uh,
)
from hidropluvial.cli.session.base import get_session_manager


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

    from hidropluvial.core import convolve_uh, desbordes, kirpich, temez, triangular_uh_x

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

    # Calcular tp del hidrograma unitario SCS: Tp = ΔD/2 + 0.6×Tc
    from hidropluvial.core import scs_time_to_peak
    tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

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
    volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

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
        tp_unit_hr=tp_unit_hr,
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

    # Calcular tb (tiempo base) = 2.67 × tp
    tb_hr = 2.67 * tp_unit_hr
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    typer.echo(f"\n  HIDROGRAMA UNITARIO:")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Tc:                {tc_hr*60:>12.1f} min")
    typer.echo(f"  tp:                {tp_unit_hr*60:>12.1f} min")
    if storm_type == "gz":
        typer.echo(f"  X:                 {x_factor:>12.2f}")
    typer.echo(f"  tb:                {tb_hr*60:>12.1f} min")

    typer.echo(f"\n  TORMENTA:")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  P:                 {hyetograph.total_depth_mm:>12.1f} mm")
    typer.echo(f"  Pe:                {runoff_mm:>12.1f} mm")

    typer.echo(f"\n  RESULTADOS:")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Qp:                {format_flow(peak_flow):>12} m³/s")
    typer.echo(f"  Tp:                {time_to_peak*60:>12.1f} min")
    typer.echo(f"  Vol:               {format_volume_hm3(volume_m3):>12} hm³")
    typer.echo(f"{'='*60}\n")
