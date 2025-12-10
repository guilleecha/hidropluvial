"""
Hidrograma Unitario de Clark.

Método basado en curva tiempo-área y routing a través
de un reservorio lineal para simular almacenamiento.
"""

import numpy as np
from numpy.typing import NDArray


def clark_time_area(
    t_tc: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Calcula relación tiempo-área por defecto (forma de diamante).

    A(t) = 1.414 × (t/Tc)^1.5           para t/Tc ≤ 0.5
    A(t) = 1 - 1.414 × (1 - t/Tc)^1.5   para t/Tc > 0.5

    Args:
        t_tc: Array de t/Tc (tiempo normalizado)

    Returns:
        Array de A/A_total (área acumulada normalizada)
    """
    a_at = np.zeros_like(t_tc)

    mask_rise = t_tc <= 0.5
    a_at[mask_rise] = 1.414 * (t_tc[mask_rise] ** 1.5)
    a_at[~mask_rise] = 1 - 1.414 * ((1 - t_tc[~mask_rise]) ** 1.5)

    return np.clip(a_at, 0, 1)


def clark_uh(
    area_km2: float,
    tc_hr: float,
    r_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario Clark (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca (km²)
        tc_hr: Tiempo de concentración (hr)
        r_hr: Coeficiente de almacenamiento R (hr)
        dt_hr: Intervalo de tiempo (hr)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    # Coeficientes de routing lineal
    c1 = dt_hr / (2 * r_hr + dt_hr)
    c2 = c1
    c0 = (2 * r_hr - dt_hr) / (2 * r_hr + dt_hr)

    # Tiempo base (aproximado)
    tb = tc_hr + 5 * r_hr
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Calcular entrada al reservorio desde curva tiempo-área
    t_tc = time / tc_hr
    area_cum = clark_time_area(np.minimum(t_tc, 1.0))

    # Área incremental (histograma de entrada)
    area_incr = np.zeros(n_points)
    area_incr[1:] = np.diff(area_cum)
    area_incr[0] = area_cum[0]

    # Inflow al reservorio (mm/hr × área → m³/s)
    # Para 1 mm de escorrentía distribuido uniformemente en tc
    inflow = area_incr * area_km2 * 1000 / (dt_hr * 3600)  # m³/s

    # Routing a través del reservorio lineal
    outflow = np.zeros(n_points)
    for i in range(1, n_points):
        outflow[i] = c1 * inflow[i] + c2 * inflow[i-1] + c0 * outflow[i-1]

    return time, outflow
