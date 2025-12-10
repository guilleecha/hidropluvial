"""
Método de Bloques Alternantes para distribución temporal de lluvia.

Incluye:
- alternating_blocks: Versión genérica con coeficientes IDF
- alternating_blocks_dinagua: Versión con IDF DINAGUA Uruguay
"""

import numpy as np

from hidropluvial.config import HyetographResult, ShermanCoefficients
from hidropluvial.core.idf import depth_from_intensity, get_intensity, dinagua_depth

from .base import distribute_alternating_blocks


def alternating_blocks(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    idf_method: str,
    idf_coeffs: ShermanCoefficients,
    return_period_yr: float,
    peak_position: float = 0.5,
) -> HyetographResult:
    """
    Genera hietograma usando método de bloques alternantes.

    Algoritmo:
    1. Calcula profundidades acumuladas desde curva IDF
    2. Obtiene incrementos de profundidad
    3. Ordena incrementos de mayor a menor
    4. Coloca alternando alrededor del pico

    Args:
        total_depth_mm: Profundidad total (usado para escalar si difiere de IDF)
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        idf_method: Método IDF ('sherman', 'bernard', 'koutsoyiannis')
        idf_coeffs: Coeficientes del método IDF
        return_period_yr: Período de retorno en años
        peak_position: Posición del pico (0-1), default 0.5 (centro)

    Returns:
        HyetographResult con el hietograma generado
    """
    duration_min = duration_hr * 60
    n_intervals = int(duration_min / dt_min)

    # Calcular profundidades acumuladas desde IDF
    durations = np.arange(1, n_intervals + 1) * dt_min
    cumulative_depths = np.zeros(n_intervals)

    for i, d in enumerate(durations):
        intensity = get_intensity(d, return_period_yr, idf_method, idf_coeffs)
        cumulative_depths[i] = depth_from_intensity(intensity, d)

    # Calcular incrementos de profundidad
    increments = np.zeros(n_intervals)
    increments[0] = cumulative_depths[0]
    for i in range(1, n_intervals):
        increments[i] = cumulative_depths[i] - cumulative_depths[i - 1]

    # Escalar si total_depth_mm difiere del calculado
    idf_total = cumulative_depths[-1]
    if abs(idf_total - total_depth_mm) > 0.01:
        scale_factor = total_depth_mm / idf_total
        increments *= scale_factor

    # Ordenar incrementos de mayor a menor y distribuir
    sorted_increments = np.sort(increments)[::-1]
    result_depths = distribute_alternating_blocks(sorted_increments, n_intervals, peak_position)

    # Calcular tiempos e intensidades
    time_min = np.arange(0, n_intervals) * dt_min + dt_min / 2
    intensities = result_depths * 60 / dt_min
    cumulative = np.cumsum(result_depths)

    return HyetographResult(
        time_min=time_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=result_depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="alternating_blocks",
        total_depth_mm=float(np.sum(result_depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )


def alternating_blocks_dinagua(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    dt_min: float,
    area_km2: float | None = None,
    peak_position: float = 0.5,
) -> HyetographResult:
    """
    Genera hietograma de bloques alternantes usando IDF DINAGUA Uruguay.

    Args:
        p3_10: Precipitación P3,10 base (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        area_km2: Área de cuenca para corrección (opcional)
        peak_position: Posición del pico (0-1), default 0.5 (centro)

    Returns:
        HyetographResult con el hietograma generado
    """
    dt_hr = dt_min / 60
    n_intervals = int(duration_hr / dt_hr)

    # Calcular profundidades acumuladas usando DINAGUA
    cumulative_depths = np.zeros(n_intervals)
    for i in range(n_intervals):
        d_hr = (i + 1) * dt_hr
        cumulative_depths[i] = dinagua_depth(p3_10, return_period_yr, d_hr, area_km2)

    # Calcular incrementos de profundidad
    increments = np.zeros(n_intervals)
    increments[0] = cumulative_depths[0]
    for i in range(1, n_intervals):
        increments[i] = cumulative_depths[i] - cumulative_depths[i - 1]

    # Ordenar incrementos de mayor a menor y distribuir
    sorted_increments = np.sort(increments)[::-1]
    result_depths = distribute_alternating_blocks(sorted_increments, n_intervals, peak_position)

    # Calcular tiempos e intensidades
    time_min = np.arange(0, n_intervals) * dt_min + dt_min / 2
    intensities = result_depths * 60 / dt_min
    cumulative = np.cumsum(result_depths)

    return HyetographResult(
        time_min=time_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=result_depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="alternating_blocks_dinagua",
        total_depth_mm=float(np.sum(result_depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )
