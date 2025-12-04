"""
Comandos CLI para generación de hidrogramas.
"""

from typing import Annotated, Optional

import numpy as np
import typer

from hidropluvial.core import (
    alternating_blocks_dinagua,
    calculate_scs_runoff,
    convolve_uh,
    dinagua_intensity,
    kirpich,
    rainfall_excess_series,
    scs_curvilinear_uh,
    scs_triangular_uh,
    temez,
)

# Crear sub-aplicación
hydrograph_app = typer.Typer(help="Generación de hidrogramas")


@hydrograph_app.command("scs")
def hydrograph_scs(
    area: Annotated[float, typer.Option("--area", "-a", help="Área de la cuenca en km2")],
    length: Annotated[float, typer.Option("--length", "-l", help="Longitud del cauce en metros")],
    slope: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media (m/m o decimal)")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    cn: Annotated[int, typer.Option("--cn", help="Número de curva (30-100)")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno en años")] = 25,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    method: Annotated[str, typer.Option("--method", "-m", help="Método UH: triangular, curvilinear")] = "triangular",
    tc_method: Annotated[str, typer.Option("--tc-method", help="Método Tc: kirpich, temez, desbordes")] = "kirpich",
    c_escorrentia: Annotated[Optional[float], typer.Option("--c", help="Coef. escorrentía para desbordes (0-1)")] = None,
    lambda_coef: Annotated[float, typer.Option("--lambda", help="Coeficiente lambda para Ia")] = 0.2,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo CSV de salida")] = None,
):
    """
    Genera hidrograma completo usando método SCS.

    Integra: Tc -> IDF -> Hietograma -> Escorrentía -> Hidrograma

    Ejemplo:
        hidropluvial hydrograph scs --area 1 --length 1000 --slope 0.0223 --p3_10 83 --cn 81 --tr 25
    """
    # Convertir pendiente si viene en porcentaje
    if slope > 1:
        slope = slope / 100

    # PASO 1: Tiempo de concentración
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
            # Estimación aproximada: C ≈ 1 - (S/(S+25.4)) donde S = 25400/CN - 254
            s_mm = 25400 / cn - 254
            c_escorrentia = 1 - (s_mm / (s_mm + 25.4))
        tc_hr = desbordes(area_ha, slope_pct, c_escorrentia)
    else:
        typer.echo(f"Error: Método Tc desconocido: {tc_method}", err=True)
        raise typer.Exit(1)

    tc_min = tc_hr * 60

    # PASO 2: IDF - Precipitación de diseño
    # Duración = Tc (redondeado a múltiplo de dt)
    duration_hr = max(tc_hr, dt / 60)  # Mínimo un intervalo

    idf_result = dinagua_intensity(p3_10, return_period, duration_hr, area if area > 1 else None)
    precip_mm = idf_result.depth_mm
    intensity_mmhr = idf_result.intensity_mmhr

    # PASO 3: Hietograma
    dt_hr = dt / 60
    hyetograph = alternating_blocks_dinagua(
        p3_10, return_period, duration_hr, dt, area if area > 1 else None
    )

    # PASO 4: Escorrentía SCS-CN
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
        typer.echo(f"Error: Método UH desconocido: {method}", err=True)
        raise typer.Exit(1)

    # PASO 6: Convolución
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
    typer.echo(f"  HIDROGRAMA SCS - ANÁLISIS COMPLETO")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n  DATOS DE ENTRADA:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Área de cuenca:        {area:>12.2f} km2")
    typer.echo(f"  Longitud cauce:        {length:>12.0f} m")
    typer.echo(f"  Pendiente:             {slope*100:>12.2f} %")
    typer.echo(f"  P3,10:                 {p3_10:>12.1f} mm")
    typer.echo(f"  Período retorno:       {return_period:>12} años")
    typer.echo(f"  CN:                    {cn:>12}")
    typer.echo(f"  Método Tc:             {tc_method:>12}")
    typer.echo(f"  Método UH:             {method:>12}")

    typer.echo(f"\n  RESULTADOS INTERMEDIOS:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Tc:                    {tc_hr:>12.2f} hr ({tc_min:.1f} min)")
    typer.echo(f"  Duración tormenta:     {duration_hr:>12.2f} hr")
    typer.echo(f"  Intensidad:            {intensity_mmhr:>12.2f} mm/hr")
    typer.echo(f"  Precipitación total:   {precip_mm:>12.2f} mm")
    typer.echo(f"  Retención S:           {runoff_result.retention_mm:>12.2f} mm")
    typer.echo(f"  Abstracción Ia:        {runoff_result.initial_abstraction_mm:>12.2f} mm")
    typer.echo(f"  Escorrentía Q:         {runoff_mm:>12.2f} mm")
    typer.echo(f"  Coef. escorrentía:     {runoff_mm/precip_mm*100:>12.1f} %")

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
    area_ha: Annotated[float, typer.Option("--area", "-a", help="Área de la cuenca en hectáreas")],
    slope_pct: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media en porcentaje (%)")],
    c: Annotated[float, typer.Option("--c", help="Coeficiente de escorrentía (0-1)")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    return_period: Annotated[int, typer.Option("--tr", "-t", help="Período de retorno en años")] = 2,
    x_factor: Annotated[float, typer.Option("--x", help="Factor X morfológico (1.0-5.5)")] = 1.0,
    dt: Annotated[float, typer.Option("--dt", help="Intervalo en minutos")] = 5.0,
    t0: Annotated[float, typer.Option("--t0", help="Tiempo entrada Tc en minutos")] = 5.0,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo CSV de salida")] = None,
):
    """
    Genera hidrograma completo usando método GZ.

    Metodología adaptada para drenaje urbano Uruguay:
    - Tc: Método de los Desbordes (DINAGUA)
    - IDF: Curvas DINAGUA Uruguay
    - Hietograma: 6 horas, bloques alternantes, pico en 1ra hora
    - Escorrentía: Coeficiente C (método racional)
    - Hidrograma: Triangular con factor X ajustable

    Valores típicos de X:
        1.00 - Áreas urbanas internas
        1.25 - Áreas urbanas (gran pendiente)
        1.67 - Método NRCS/SCS estándar
        2.25 - Uso mixto rural/urbano

    Ejemplo:
        hidropluvial hydrograph gz --area 100 --slope 2.23 --c 0.62 --p3_10 83 --tr 2 --x 1.0
    """
    from hidropluvial.core import desbordes, triangular_uh_x

    # PASO 1: Tiempo de concentración (Método Desbordes)
    tc_hr = desbordes(area_ha, slope_pct, c, t0)
    tc_min = tc_hr * 60

    # PASO 2: Hietograma de 6 horas con pico adelantado
    duration_hr = 6.0
    peak_position = 1.0 / 6.0  # Pico en la primera hora

    hyetograph = alternating_blocks_dinagua(
        p3_10, return_period, duration_hr, dt, None, peak_position
    )

    precip_mm = hyetograph.total_depth_mm

    # PASO 3: Escorrentía con coeficiente C
    # Pe = C × P (para cada intervalo)
    depths = np.array(hyetograph.depth_mm)
    excess_mm = c * depths
    total_runoff_mm = float(np.sum(excess_mm))

    # PASO 4: Hidrograma unitario triangular con factor X
    dt_hr = dt / 60
    uh_time, uh_flow = triangular_uh_x(area_ha, tc_hr, dt_hr, x_factor)

    # PASO 5: Convolución
    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
    n_total = len(hydrograph_flow)
    hydrograph_time = np.arange(n_total) * dt_hr

    # Calcular resultados
    peak_idx = np.argmax(hydrograph_flow)
    peak_flow = float(hydrograph_flow[peak_idx])
    time_to_peak = float(hydrograph_time[peak_idx])
    volume_m3 = float(np.trapz(hydrograph_flow, hydrograph_time * 3600))

    # Calcular Tp y Tb teóricos
    tp_teorico = 0.5 * dt_hr + 0.6 * tc_hr
    tb_teorico = (1 + x_factor) * tp_teorico

    # Mostrar resultados
    typer.echo(f"\n{'='*60}")
    typer.echo(f"  HIDROGRAMA GZ - ANÁLISIS COMPLETO")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n  DATOS DE ENTRADA:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Área de cuenca:        {area_ha:>12.2f} ha")
    typer.echo(f"  Pendiente:             {slope_pct:>12.2f} %")
    typer.echo(f"  Coef. escorrentía C:   {c:>12.2f}")
    typer.echo(f"  P3,10:                 {p3_10:>12.1f} mm")
    typer.echo(f"  Período retorno:       {return_period:>12} años")
    typer.echo(f"  Factor X:              {x_factor:>12.2f}")

    typer.echo(f"\n  RESULTADOS INTERMEDIOS:")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Tc (Desbordes):        {tc_hr:>12.2f} hr ({tc_min:.1f} min)")
    typer.echo(f"  Tp teórico:            {tp_teorico:>12.2f} hr ({tp_teorico*60:.1f} min)")
    typer.echo(f"  Tb teórico:            {tb_teorico:>12.2f} hr ({tb_teorico*60:.1f} min)")
    typer.echo(f"  Duración tormenta:     {duration_hr:>12.1f} hr")
    typer.echo(f"  Precipitación total:   {precip_mm:>12.2f} mm")
    typer.echo(f"  Escorrentía (C*P):     {total_runoff_mm:>12.2f} mm")

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
