"""
Hidrograma Unitario Sintético de Snyder (1938).

Método empírico basado en características morfológicas de la cuenca
desarrollado por Franklin Snyder para cuencas en los Apalaches.
"""

import numpy as np
from numpy.typing import NDArray


def snyder_lag_time(
    length_km: float,
    lc_km: float,
    ct: float = 2.0,
) -> float:
    """
    Calcula tiempo de retardo Snyder.

    tp = Ct × (L × Lc)^0.3  [tp: hr, L/Lc: km]

    Args:
        length_km: Longitud del cauce principal (km)
        lc_km: Distancia desde salida hasta centroide de la cuenca (km)
        ct: Coeficiente Ct (1.8-2.2 típico)

    Returns:
        Tiempo de retardo en horas
    """
    # Convertir a millas para fórmula original
    length_mi = length_km * 0.621371
    lc_mi = lc_km * 0.621371

    return ct * ((length_mi * lc_mi) ** 0.3)


def snyder_peak(
    area_km2: float,
    tp_hr: float,
    cp: float = 0.6,
) -> float:
    """
    Calcula caudal pico Snyder para 1 pulgada de escorrentía.

    Qp = 640 × Cp × A / tp  [Qp: cfs, A: mi²]

    Args:
        area_km2: Área de la cuenca (km²)
        tp_hr: Tiempo de retardo (hr)
        cp: Coeficiente Cp (0.4-0.8 típico)

    Returns:
        Caudal pico en m³/s (para 25.4 mm de escorrentía)
    """
    area_mi2 = area_km2 * 0.386102
    qp_cfs = 640 * cp * area_mi2 / tp_hr
    qp_m3s = qp_cfs * 0.0283168  # Convertir cfs a m³/s

    return qp_m3s


def snyder_widths(qp_m3s: float, area_km2: float) -> tuple[float, float]:
    """
    Calcula anchos del hidrograma Snyder al 50% y 75% del pico.

    W50 = 770 × (Qp/A)^(-1.08)  [hr]
    W75 = 440 × (Qp/A)^(-1.08)  [hr]

    Args:
        qp_m3s: Caudal pico (m³/s)
        area_km2: Área de la cuenca (km²)

    Returns:
        Tupla (W50_hr, W75_hr)
    """
    # Convertir a unidades inglesas
    qp_cfs = qp_m3s / 0.0283168
    area_mi2 = area_km2 * 0.386102

    qp_a = qp_cfs / area_mi2
    w50 = 770 * (qp_a ** -1.08)
    w75 = 440 * (qp_a ** -1.08)

    return w50, w75


def snyder_uh(
    area_km2: float,
    length_km: float,
    lc_km: float,
    dt_hr: float,
    ct: float = 2.0,
    cp: float = 0.6,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario Snyder (25.4 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca (km²)
        length_km: Longitud del cauce principal (km)
        lc_km: Distancia al centroide (km)
        dt_hr: Intervalo de tiempo (hr)
        ct: Coeficiente Ct
        cp: Coeficiente Cp

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = snyder_lag_time(length_km, lc_km, ct)
    qp = snyder_peak(area_km2, tp, cp)
    w50, w75 = snyder_widths(qp, area_km2)

    # Tiempo base aproximado
    tb = tp + 3 * w50

    # Generar forma usando anchos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Puntos clave: 1/3 antes del pico, 2/3 después
    t_rise_50 = tp - w50 / 3
    t_fall_50 = tp + 2 * w50 / 3
    t_rise_75 = tp - w75 / 3
    t_fall_75 = tp + 2 * w75 / 3

    # Interpolar forma del hidrograma
    t_key = np.array([0, t_rise_50, t_rise_75, tp, t_fall_75, t_fall_50, tb])
    q_key = np.array([0, 0.5 * qp, 0.75 * qp, qp, 0.75 * qp, 0.5 * qp, 0])

    # Ordenar y eliminar duplicados
    sorted_idx = np.argsort(t_key)
    t_key = t_key[sorted_idx]
    q_key = q_key[sorted_idx]

    flow = np.interp(time, t_key, q_key)
    flow = np.maximum(flow, 0)

    return time, flow
