"""
Hidrogramas unitarios SCS (Soil Conservation Service).

Incluye:
- SCS Triangular Unit Hydrograph
- SCS Curvilinear (Dimensionless) Unit Hydrograph
- Gamma Unit Hydrograph
"""

import numpy as np
from numpy.typing import NDArray

from .base import scs_time_to_peak, scs_time_base, load_uh_data


def scs_triangular_peak(
    area_km2: float,
    runoff_mm: float,
    tp_hr: float,
) -> float:
    """
    Calcula caudal pico del hidrograma triangular SCS.

    qp = 2.08 × A × Q / Tp  [qp: m³/s, A: km², Q: mm, Tp: hr]

    Args:
        area_km2: Área de la cuenca en km²
        runoff_mm: Escorrentía directa en mm
        tp_hr: Tiempo al pico en horas

    Returns:
        Caudal pico en m³/s
    """
    if area_km2 <= 0:
        raise ValueError("Área debe ser > 0")
    if runoff_mm < 0:
        raise ValueError("Escorrentía no puede ser negativa")
    if tp_hr <= 0:
        raise ValueError("Tiempo al pico debe ser > 0")

    return 2.08 * area_km2 * runoff_mm / tp_hr


def scs_triangular_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario triangular SCS (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)
    tb = scs_time_base(tp)
    tr = 1.67 * tp  # tiempo de recesión

    # Caudal pico para 1 mm de escorrentía
    qp = scs_triangular_peak(area_km2, 1.0, tp)

    # Generar tiempos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Generar ordenadas del triángulo
    flow = np.zeros_like(time)
    for i, t in enumerate(time):
        if t <= tp:
            # Rama ascendente
            flow[i] = qp * t / tp
        else:
            # Rama descendente
            flow[i] = qp * (tb - t) / tr

    flow = np.maximum(flow, 0)  # Asegurar valores no negativos

    return time, flow


def scs_curvilinear_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    prf: int = 484,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario curvilíneo SCS (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas
        prf: Peak Rate Factor (default 484)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)

    # Caudal pico para 1 mm usando PRF
    # qp = PRF × A × Q / Tp  donde PRF=484 es el estándar
    qp = (prf / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    # Cargar hidrograma adimensional
    uh_data = load_uh_data()
    t_tp_std = np.array(uh_data["scs_curvilinear"]["t_Tp"])
    q_qp_std = np.array(uh_data["scs_curvilinear"]["q_qp"])

    # Escalar a valores reales
    tb = t_tp_std[-1] * tp  # tiempo base
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Interpolar ordenadas
    t_tp = time / tp
    flow = qp * np.interp(t_tp, t_tp_std, q_qp_std, right=0)

    return time, flow


def gamma_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    m: float = 3.7,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario usando ecuación Gamma.

    q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp)

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas
        m: Parámetro de forma (3.7 para PRF=484)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)

    # PRF aproximado según m
    prf_approx = 130 * m + 3  # Aproximación lineal
    qp = (prf_approx / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    # Generar tiempos (hasta que el flujo sea ~0)
    tb = 5 * tp  # Tiempo base aproximado
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Ecuación Gamma
    t_tp = time / tp
    t_tp = np.maximum(t_tp, 1e-10)  # Evitar log(0)

    # q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp) = (t/Tp)^m × e^(m × (1 - t/Tp))
    q_qp = (t_tp ** m) * np.exp(m * (1 - t_tp))
    flow = qp * q_qp

    return time, flow
