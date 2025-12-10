"""
Curvas Huff (1967) para distribución temporal de lluvia.

Las curvas Huff clasifican tormentas según el cuartil en que
ocurre la mayor intensidad, con diferentes niveles de probabilidad.
"""

import numpy as np

from hidropluvial.config import HyetographResult

from .base import load_huff_curves


def huff_distribution(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    quartile: int = 2,
    probability: int = 50,
) -> HyetographResult:
    """
    Genera hietograma usando curvas Huff (1967).

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        quartile: Cuartil de Huff (1-4)
        probability: Nivel de probabilidad (10, 50, 90)

    Returns:
        HyetographResult con el hietograma generado
    """
    if quartile not in [1, 2, 3, 4]:
        raise ValueError("Cuartil debe ser 1, 2, 3 o 4")
    if probability not in [10, 50, 90]:
        raise ValueError("Probabilidad debe ser 10, 50 o 90")

    # Cargar curva Huff
    huff_data = load_huff_curves()
    quartile_key = f"huff_q{quartile}"
    prob_key = f"probability_{probability}"

    curve_data = huff_data[quartile_key][prob_key]
    time_pct = np.array(curve_data["time_pct"])
    rain_pct = np.array(curve_data["rain_pct"])

    # Interpolar a intervalos dt_min
    n_intervals = int(duration_hr * 60 / dt_min)
    time_pct_interp = np.linspace(0, 100, n_intervals + 1)

    # Interpolar porcentajes de lluvia acumulada
    cumulative_pct = np.interp(time_pct_interp, time_pct, rain_pct)

    # Convertir a profundidades
    cumulative_depth = cumulative_pct / 100 * total_depth_mm
    incremental_depth = np.diff(cumulative_depth)

    # Tiempos
    time_min = np.linspace(0, duration_hr * 60, n_intervals + 1)
    time_centers_min = (time_min[:-1] + time_min[1:]) / 2

    # Intensidades
    intensities = incremental_depth * 60 / dt_min

    return HyetographResult(
        time_min=time_centers_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=incremental_depth.tolist(),
        cumulative_mm=cumulative_depth[1:].tolist(),
        method=f"huff_q{quartile}_p{probability}",
        total_depth_mm=float(np.sum(incremental_depth)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )
