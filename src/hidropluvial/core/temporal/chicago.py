"""
Tormenta de Diseño Chicago (Keifer & Chu 1957).

La tormenta Chicago genera un hietograma sintético basado en
la curva IDF, con control sobre la posición del pico.
"""

import numpy as np

from hidropluvial.config import HyetographResult, ShermanCoefficients


def chicago_storm(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    idf_coeffs: ShermanCoefficients,
    return_period_yr: float,
    advancement_coef: float = 0.375,
) -> HyetographResult:
    """
    Genera hietograma usando método de tormenta Chicago (Keifer & Chu 1957).

    Requiere IDF en forma Sherman: i = a / (t + b)^c

    Antes del pico (t_b medido hacia atrás):
        i_b = a[(1-c)(t_b/r) + b] / [(t_b/r) + b]^(c+1)

    Después del pico (t_a medido hacia adelante):
        i_a = a[(1-c)(t_a/(1-r)) + b] / [(t_a/(1-r)) + b]^(c+1)

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        idf_coeffs: Coeficientes Sherman (k→a, c→b, n→c para duración fija)
        return_period_yr: Período de retorno en años
        advancement_coef: Coeficiente de avance r (típico 0.3-0.5, default 0.375)

    Returns:
        HyetographResult con el hietograma generado
    """
    duration_min = duration_hr * 60
    n_intervals = int(duration_min / dt_min)
    r = advancement_coef

    # Parámetros Sherman: i = k*T^m / (t+c)^n
    # Para Chicago usamos: a = k*T^m, b = c, c_exp = n
    a = idf_coeffs.k * (return_period_yr ** idf_coeffs.m)
    b = idf_coeffs.c
    c_exp = idf_coeffs.n

    # Tiempo del pico
    t_peak = r * duration_min

    intensities = np.zeros(n_intervals)
    time_centers = np.arange(0, n_intervals) * dt_min + dt_min / 2

    for i, t in enumerate(time_centers):
        if t <= t_peak:
            # Antes del pico
            t_b = t_peak - t
            if r > 0:
                t_scaled = t_b / r
                num = a * ((1 - c_exp) * t_scaled + b)
                den = (t_scaled + b) ** (c_exp + 1)
                intensities[i] = num / den
            else:
                intensities[i] = 0
        else:
            # Después del pico
            t_a = t - t_peak
            if r < 1:
                t_scaled = t_a / (1 - r)
                num = a * ((1 - c_exp) * t_scaled + b)
                den = (t_scaled + b) ** (c_exp + 1)
                intensities[i] = num / den
            else:
                intensities[i] = 0

    # Calcular profundidades y escalar
    depths = intensities * dt_min / 60
    current_total = np.sum(depths)

    if current_total > 0:
        scale = total_depth_mm / current_total
        depths *= scale
        intensities *= scale

    cumulative = np.cumsum(depths)

    return HyetographResult(
        time_min=time_centers.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="chicago",
        total_depth_mm=float(np.sum(depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )
