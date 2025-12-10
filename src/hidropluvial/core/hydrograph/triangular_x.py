"""
Hidrograma Triangular con Factor X (Método GZ / Porto).

Permite ajustar la forma del hidrograma triangular mediante
un factor morfológico X que controla la relación entre
tiempo de ascenso y tiempo de recesión.
"""

import numpy as np
from numpy.typing import NDArray


def triangular_uh_x(
    area_ha: float,
    tc_hr: float,
    dt_hr: float,
    x_factor: float = 1.0,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario triangular con factor X ajustable.

    Fórmulas (adaptadas de Porto):
        Tp = 0.5 × Du + 0.6 × Tc
        qp = 0.278 × A / Tp × 2 / (1 + X)   [A: ha, Tp: hr, qp: m³/s]
        Tb = (1 + X) × Tp

    Valores típicos de X:
        - 1.00: Método racional / áreas urbanas internas
        - 1.25: Áreas urbanas (gran pendiente)
        - 1.67: Método NRCS (SCS estándar)
        - 2.25: Uso mixto (rural/urbano)
        - 3.33: Área rural sinuosa
        - 5.50: Área rural (pendiente baja)

    Args:
        area_ha: Área de la cuenca en hectáreas
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas (Du)
        x_factor: Factor morfológico X (default 1.0)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario (1 mm)
    """
    if area_ha <= 0:
        raise ValueError("Área debe ser > 0")
    if tc_hr <= 0:
        raise ValueError("Tc debe ser > 0")
    if dt_hr <= 0:
        raise ValueError("dt debe ser > 0")
    if x_factor < 1.0:
        raise ValueError("Factor X debe ser >= 1.0")

    # Tiempo al pico
    tp = 0.5 * dt_hr + 0.6 * tc_hr

    # Caudal pico para 1 mm de escorrentía
    # Fórmula original usa km², para ha dividir por 100
    # qp = 0.278 × A[km²] / Tp × 2 / (1 + X)
    # qp = 0.00278 × A[ha] / Tp × 2 / (1 + X)
    area_km2 = area_ha / 100
    qp = 0.278 * area_km2 / tp * 2 / (1 + x_factor)

    # Tiempo base
    tb = (1 + x_factor) * tp

    # Tiempo de recesión
    tr = tb - tp  # = X × Tp

    # Generar tiempos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Generar ordenadas del triángulo
    flow = np.zeros_like(time)
    for i, t in enumerate(time):
        if t <= tp:
            # Rama ascendente
            flow[i] = qp * t / tp if tp > 0 else 0
        else:
            # Rama descendente
            flow[i] = qp * (tb - t) / tr if tr > 0 else 0

    flow = np.maximum(flow, 0)

    return time, flow
