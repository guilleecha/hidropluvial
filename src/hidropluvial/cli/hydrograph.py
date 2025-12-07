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
from hidropluvial.cli.theme import (
    print_header, print_section, print_separator, print_field,
    print_success, print_error, get_console, get_palette,
)
from hidropluvial.cli.validators import (
    validate_area, validate_length, validate_slope, validate_p310,
    validate_cn, validate_c_coefficient, validate_x_factor, validate_tc_method,
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
        hp hydrograph scs -a 1 -l 1000 -s 0.02 -p 83 --cn 81 --tr 25
        hp hydrograph scs -a 2 -l 2000 -s 0.015 -p 78 --cn 75 --tc-method temez
    """
    # Validar entradas
    validate_area(area)
    validate_length(length)
    validate_slope(slope)
    validate_p310(p3_10)
    validate_cn(cn)
    validate_tc_method(tc_method)
    if c_escorrentia is not None:
        validate_c_coefficient(c_escorrentia)

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
        print_error(f"Método Tc desconocido: {tc_method}")
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
        print_error(f"Método UH desconocido: {method}")
        raise typer.Exit(1)

    # PASO 6: Convolución
    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
    n_total = len(hydrograph_flow)
    hydrograph_time = np.arange(n_total) * dt_hr

    # Calcular resultados
    peak_idx = np.argmax(hydrograph_flow)
    peak_flow = float(hydrograph_flow[peak_idx])
    time_to_peak = float(hydrograph_time[peak_idx])
    volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

    # Mostrar resultados
    print_header("HIDROGRAMA SCS - ANÁLISIS COMPLETO")

    print_section("Datos de Entrada")
    print_field("Área de cuenca", f"{area:.2f}", "km²")
    print_field("Longitud cauce", f"{length:.0f}", "m")
    print_field("Pendiente", f"{slope*100:.2f}", "%")
    print_field("P3,10", f"{p3_10:.1f}", "mm")
    print_field("Período retorno", str(return_period), "años")
    print_field("CN", str(cn))
    print_field("Método Tc", tc_method)
    print_field("Método UH", method)

    print_section("Resultados Intermedios")
    print_field("Tc", f"{tc_hr:.2f} hr ({tc_min:.1f} min)")
    print_field("Duración tormenta", f"{duration_hr:.2f}", "hr")
    print_field("Intensidad", f"{intensity_mmhr:.2f}", "mm/hr")
    print_field("Precipitación total", f"{precip_mm:.2f}", "mm")
    print_field("Retención S", f"{runoff_result.retention_mm:.2f}", "mm")
    print_field("Abstracción Ia", f"{runoff_result.initial_abstraction_mm:.2f}", "mm")
    print_field("Escorrentía Q", f"{runoff_mm:.2f}", "mm")
    print_field("Coef. escorrentía", f"{runoff_mm/precip_mm*100:.1f}", "%")

    print_section("Resultados Finales")
    print_field("CAUDAL PICO", f"{peak_flow:.3f}", "m³/s")
    print_field("TIEMPO AL PICO", f"{time_to_peak:.2f} hr ({time_to_peak*60:.1f} min)")
    print_field("VOLUMEN", f"{volume_m3:.0f}", "m³")

    # Exportar si se solicita
    if output:
        with open(output, 'w') as f:
            f.write("Tiempo_hr,Caudal_m3s\n")
            for t, q in zip(hydrograph_time, hydrograph_flow):
                f.write(f"{t:.4f},{q:.4f}\n")
        print_success(f"Hidrograma exportado a: {output}")


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
        hp hydrograph gz -a 100 -s 2.23 --c 0.62 -p 83 --tr 2 --x 1.0
        hp hydrograph gz -a 50 -s 1.5 --c 0.5 -p 78 --tr 10 --x 1.67
    """
    # Validar entradas
    validate_area(area_ha)
    if slope_pct <= 0:
        print_error(f"La pendiente debe ser positiva (recibido: {slope_pct})")
        raise typer.Exit(1)
    validate_c_coefficient(c)
    validate_p310(p3_10)
    validate_x_factor(x_factor)

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
    volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

    # Calcular Tp y Tb teóricos
    tp_teorico = 0.5 * dt_hr + 0.6 * tc_hr
    tb_teorico = (1 + x_factor) * tp_teorico

    # Mostrar resultados
    print_header("HIDROGRAMA GZ - ANÁLISIS COMPLETO")

    print_section("Datos de Entrada")
    print_field("Área de cuenca", f"{area_ha:.2f}", "ha")
    print_field("Pendiente", f"{slope_pct:.2f}", "%")
    print_field("Coef. escorrentía C", f"{c:.2f}")
    print_field("P3,10", f"{p3_10:.1f}", "mm")
    print_field("Período retorno", str(return_period), "años")
    print_field("Factor X", f"{x_factor:.2f}")

    print_section("Resultados Intermedios")
    print_field("Tc (Desbordes)", f"{tc_hr:.2f} hr ({tc_min:.1f} min)")
    print_field("Tp teórico", f"{tp_teorico:.2f} hr ({tp_teorico*60:.1f} min)")
    print_field("Tb teórico", f"{tb_teorico:.2f} hr ({tb_teorico*60:.1f} min)")
    print_field("Duración tormenta", f"{duration_hr:.1f}", "hr")
    print_field("Precipitación total", f"{precip_mm:.2f}", "mm")
    print_field("Escorrentía (C*P)", f"{total_runoff_mm:.2f}", "mm")

    print_section("Resultados Finales")
    print_field("CAUDAL PICO", f"{peak_flow:.3f}", "m³/s")
    print_field("TIEMPO AL PICO", f"{time_to_peak:.2f} hr ({time_to_peak*60:.1f} min)")
    print_field("VOLUMEN", f"{volume_m3:.0f}", "m³")

    # Exportar si se solicita
    if output:
        with open(output, 'w') as f:
            f.write("Tiempo_hr,Caudal_m3s\n")
            for t, q in zip(hydrograph_time, hydrograph_flow):
                f.write(f"{t:.4f},{q:.4f}\n")
        print_success(f"Hidrograma exportado a: {output}")
