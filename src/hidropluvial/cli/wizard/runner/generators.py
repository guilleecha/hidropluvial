"""
Funciones compartidas para generación de análisis hidrológicos.

Este módulo contiene las funciones que se comparten entre AnalysisRunner
y AdditionalAnalysisRunner para evitar duplicación de código.
"""

from typing import Optional, Tuple

import numpy as np

from hidropluvial.config import StormMethod
from hidropluvial.core import (
    alternating_blocks_dinagua,
    bimodal_dinagua,
    rainfall_excess_series,
    adjust_cn_for_amc,
)
from hidropluvial.core.temporal import (
    huff_distribution,
    scs_distribution,
    custom_depth_storm,
    custom_hyetograph,
)
from hidropluvial.core.idf import dinagua_depth
from hidropluvial.models import TcResult, StormResult, HydrographResult

from .helpers import get_amc_enum


def get_storm_duration_and_dt(
    storm_code: str,
    tc_hr: float,
    dt_min: float,
    bimodal_duration_hr: float = 6.0,
    custom_duration_hr: float = 6.0,
) -> Tuple[float, float]:
    """
    Determina la duración de tormenta y el intervalo de tiempo.

    Args:
        storm_code: Código de tormenta (gz, bimodal, custom, blocks24, scs_ii, huff_qN)
        tc_hr: Tiempo de concentración en horas
        dt_min: Intervalo de tiempo configurado
        bimodal_duration_hr: Duración para tormentas bimodales
        custom_duration_hr: Duración para tormentas personalizadas

    Returns:
        Tupla (duration_hr, dt_min)
    """
    dt = dt_min

    if storm_code == "gz":
        duration_hr = 6.0
    elif storm_code == "bimodal":
        duration_hr = bimodal_duration_hr
    elif storm_code == "custom":
        duration_hr = custom_duration_hr
    elif storm_code == "blocks24" or storm_code == "scs_ii":
        duration_hr = 24.0
        if dt < 10.0:
            dt = 10.0
    elif storm_code.startswith("huff"):
        duration_hr = max(tc_hr * 2, 2.0)
    else:
        duration_hr = max(tc_hr, 1.0)

    return duration_hr, dt


def generate_hyetograph(
    storm_code: str,
    p3_10: float,
    tr: int,
    duration_hr: float,
    dt: float,
    bimodal_peak1: float = 0.25,
    bimodal_peak2: float = 0.75,
    bimodal_vol_split: float = 0.5,
    bimodal_peak_width: float = 0.15,
    custom_depth_mm: float = None,
    custom_distribution: str = "alternating_blocks",
    custom_hyetograph_time: list = None,
    custom_hyetograph_depth: list = None,
):
    """
    Genera un hietograma según el código de tormenta.

    Args:
        storm_code: Código de tormenta
        p3_10: Precipitación P3,10 en mm
        tr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        dt: Intervalo de tiempo en minutos
        bimodal_*: Parámetros para tormentas bimodales
        custom_*: Parámetros para tormentas personalizadas

    Returns:
        Objeto HyetographResult
    """
    if storm_code == "gz":
        peak_position = 1.0 / 6.0
        return alternating_blocks_dinagua(
            p3_10, tr, duration_hr, dt, None, peak_position
        )

    elif storm_code == "bimodal":
        return bimodal_dinagua(
            p3_10, tr, duration_hr, dt,
            peak1_position=bimodal_peak1,
            peak2_position=bimodal_peak2,
            volume_split=bimodal_vol_split,
            peak_width_fraction=bimodal_peak_width,
        )

    elif storm_code == "custom":
        if custom_hyetograph_time and custom_hyetograph_depth:
            return custom_hyetograph(
                custom_hyetograph_time,
                custom_hyetograph_depth,
            )
        elif custom_depth_mm:
            distribution = custom_distribution
            peak_pos = 1.0 / 6.0 if distribution == "alternating_blocks_gz" else 0.5
            if distribution == "alternating_blocks_gz":
                distribution = "alternating_blocks"
            return custom_depth_storm(
                custom_depth_mm,
                duration_hr,
                dt,
                distribution=distribution,
                peak_position=peak_pos,
            )
        else:
            return alternating_blocks_dinagua(
                p3_10, tr, duration_hr, dt, None
            )

    elif storm_code.startswith("huff"):
        quartile = int(storm_code.split("_q")[1]) if "_q" in storm_code else 2
        total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
        return huff_distribution(total_depth, duration_hr, dt, quartile=quartile)

    elif storm_code == "scs_ii":
        total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
        return scs_distribution(total_depth, duration_hr, dt, StormMethod.SCS_TYPE_II)

    else:
        return alternating_blocks_dinagua(
            p3_10, tr, duration_hr, dt, None
        )


def calculate_runoff(
    depths: np.ndarray,
    cumulative: np.ndarray,
    runoff_method: str,
    c_adjusted: float = None,
    cn: int = None,
    amc: str = "II",
    lambda_coef: float = 0.2,
) -> Tuple[Optional[np.ndarray], Optional[float], Optional[float]]:
    """
    Calcula la escorrentía según el método seleccionado.

    Args:
        depths: Array de profundidades de lluvia
        cumulative: Array de precipitación acumulada
        runoff_method: 'racional' o 'scs-cn'
        c_adjusted: Coeficiente C ajustado (para método racional)
        cn: Curve Number (para método SCS-CN)
        amc: Condición de humedad antecedente
        lambda_coef: Coeficiente lambda para SCS-CN

    Returns:
        Tupla (excess_mm, runoff_mm, cn_adjusted) o (None, None, None) si falta info
    """
    cn_adjusted = None

    if runoff_method == "racional" and c_adjusted:
        excess_mm = c_adjusted * depths
        runoff_mm = float(np.sum(excess_mm))
    elif runoff_method == "scs-cn" and cn:
        amc_enum = get_amc_enum(amc)
        cn_adjusted = adjust_cn_for_amc(cn, amc_enum)
        excess_mm = rainfall_excess_series(cumulative, cn_adjusted, lambda_coef)
        runoff_mm = float(np.sum(excess_mm))
    else:
        return None, None, None

    return excess_mm, runoff_mm, cn_adjusted


def create_analysis_results(
    tc_method: str,
    tc_hr: float,
    tc_params: dict,
    storm_code: str,
    tr: int,
    duration_hr: float,
    hyetograph,
    x: float,
    peak_flow: float,
    time_to_peak: float,
    tp_unit_hr: float,
    volume_m3: float,
    runoff_mm: float,
    hydrograph_time: np.ndarray,
    hydrograph_flow: np.ndarray,
    bimodal_params: Optional[dict] = None,
) -> Tuple[TcResult, StormResult, HydrographResult]:
    """
    Crea los objetos de resultado del análisis.

    Args:
        tc_method: Nombre del método de Tc
        tc_hr: Tiempo de concentración en horas
        tc_params: Parámetros del método Tc
        storm_code: Código de tormenta
        tr: Período de retorno
        duration_hr: Duración de la tormenta
        hyetograph: Resultado del hietograma
        x: Factor X morfológico
        peak_flow: Caudal pico en m³/s
        time_to_peak: Tiempo al pico en horas
        tp_unit_hr: Tiempo al pico del HU en horas
        volume_m3: Volumen total en m³
        runoff_mm: Escorrentía en mm
        hydrograph_time: Array de tiempos del hidrograma
        hydrograph_flow: Array de caudales del hidrograma

    Returns:
        Tupla (TcResult, StormResult, HydrographResult)
    """
    tc_result_obj = TcResult(
        method=tc_method,
        tc_hr=tc_hr,
        tc_min=tc_hr * 60,
        parameters=tc_params,
    )

    storm_result = StormResult(
        type=storm_code,
        return_period=tr,
        duration_hr=duration_hr,
        total_depth_mm=hyetograph.total_depth_mm,
        peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
        n_intervals=len(hyetograph.time_min),
        time_min=list(hyetograph.time_min),
        intensity_mmhr=list(hyetograph.intensity_mmhr),
        # Parámetros bimodales (solo si es tormenta bimodal)
        bimodal_peak1=bimodal_params.get("peak1") if bimodal_params else None,
        bimodal_peak2=bimodal_params.get("peak2") if bimodal_params else None,
        bimodal_vol_split=bimodal_params.get("vol_split") if bimodal_params else None,
        bimodal_peak_width=bimodal_params.get("peak_width") if bimodal_params else None,
    )

    # Calcular tiempo base: tb = (1 + X) × tp
    tb_hr = None
    tb_min = None
    if tp_unit_hr is not None and x is not None:
        tb_hr = (1 + x) * tp_unit_hr
        tb_min = tb_hr * 60

    hydrograph_result = HydrographResult(
        tc_method=tc_method,
        tc_min=tc_hr * 60,
        storm_type=storm_code,
        return_period=tr,
        x_factor=x,
        peak_flow_m3s=peak_flow,
        time_to_peak_hr=time_to_peak,
        time_to_peak_min=time_to_peak * 60,
        tp_unit_hr=tp_unit_hr,
        tp_unit_min=tp_unit_hr * 60 if tp_unit_hr else None,
        tb_hr=tb_hr,
        tb_min=tb_min,
        volume_m3=volume_m3,
        total_depth_mm=hyetograph.total_depth_mm,
        runoff_mm=runoff_mm,
        time_hr=[float(t) for t in hydrograph_time],
        flow_m3s=[float(q) for q in hydrograph_flow],
    )

    return tc_result_obj, storm_result, hydrograph_result
