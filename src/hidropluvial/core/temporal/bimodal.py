"""
Tormentas Bimodales (doble pico).

Útiles para:
- Cuencas urbanas con impermeabilidad mixta
- Regiones costeras tropicales
- Tormentas frontales de larga duración
"""

import numpy as np

from hidropluvial.config import HyetographResult, ShermanCoefficients
from hidropluvial.core.idf import dinagua_depth

from .chicago import chicago_storm


def bimodal_storm(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    peak1_position: float = 0.25,
    peak2_position: float = 0.75,
    volume_split: float = 0.5,
    peak_width_fraction: float = 0.15,
) -> HyetographResult:
    """
    Genera hietograma bimodal (doble pico) usando distribución triangular.

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        peak1_position: Posición del primer pico (0-1), default 0.25
        peak2_position: Posición del segundo pico (0-1), default 0.75
        volume_split: Fracción del volumen en el primer pico (0-1), default 0.5
        peak_width_fraction: Ancho de cada pico como fracción de duración

    Returns:
        HyetographResult con el hietograma generado
    """
    n_intervals = int(duration_hr * 60 / dt_min)
    time_min = np.arange(0, n_intervals) * dt_min + dt_min / 2
    time_normalized = time_min / (duration_hr * 60)

    # Volúmenes de cada pico
    vol1 = total_depth_mm * volume_split
    vol2 = total_depth_mm * (1 - volume_split)

    # Ancho de cada pico
    width = peak_width_fraction

    def triangular_peak(t: np.ndarray, center: float, width: float, volume: float) -> np.ndarray:
        """Genera un pico triangular."""
        result = np.zeros_like(t)
        left = center - width
        right = center + width

        # Rama ascendente
        mask_up = (t >= left) & (t <= center)
        if np.any(mask_up):
            result[mask_up] = (t[mask_up] - left) / (center - left)

        # Rama descendente
        mask_down = (t > center) & (t <= right)
        if np.any(mask_down):
            result[mask_down] = (right - t[mask_down]) / (right - center)

        # Normalizar para que el área sea igual al volumen
        area = np.trapezoid(result, t)
        if area > 0:
            result = result * volume / area

        return result

    # Generar ambos picos
    depths1 = triangular_peak(time_normalized, peak1_position, width, vol1)
    depths2 = triangular_peak(time_normalized, peak2_position, width, vol2)

    # Combinar
    result_depths = depths1 + depths2

    # Escalar para que la suma sea exacta
    current_total = np.sum(result_depths)
    if current_total > 0:
        result_depths *= total_depth_mm / current_total

    intensities = result_depths * 60 / dt_min
    cumulative = np.cumsum(result_depths)

    return HyetographResult(
        time_min=time_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=result_depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="bimodal",
        total_depth_mm=float(np.sum(result_depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )


def bimodal_dinagua(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float = 6.0,
    dt_min: float = 5.0,
    area_km2: float | None = None,
    peak1_position: float = 0.25,
    peak2_position: float = 0.75,
    volume_split: float = 0.5,
    peak_width_fraction: float = 0.15,
) -> HyetographResult:
    """
    Genera hietograma bimodal usando IDF DINAGUA Uruguay.

    Calcula automáticamente la precipitación total a partir de P3,10
    y el período de retorno usando las curvas IDF DINAGUA.

    Args:
        p3_10: Precipitación P3,10 base (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración total en horas (default 6)
        dt_min: Intervalo de tiempo en minutos (default 5)
        area_km2: Área de cuenca para corrección (opcional)
        peak1_position: Posición del primer pico (0-1), default 0.25
        peak2_position: Posición del segundo pico (0-1), default 0.75
        volume_split: Fracción del volumen en el primer pico (0-1)
        peak_width_fraction: Ancho de cada pico como fracción de duración

    Returns:
        HyetographResult con el hietograma generado
    """
    # Calcular precipitación total usando DINAGUA
    total_depth_mm = dinagua_depth(p3_10, return_period_yr, duration_hr, area_km2)

    # Generar hietograma bimodal
    result = bimodal_storm(
        total_depth_mm=total_depth_mm,
        duration_hr=duration_hr,
        dt_min=dt_min,
        peak1_position=peak1_position,
        peak2_position=peak2_position,
        volume_split=volume_split,
        peak_width_fraction=peak_width_fraction,
    )

    # Actualizar método
    return HyetographResult(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        depth_mm=result.depth_mm,
        cumulative_mm=result.cumulative_mm,
        method="bimodal_dinagua",
        total_depth_mm=result.total_depth_mm,
        peak_intensity_mmhr=result.peak_intensity_mmhr,
    )


def bimodal_chicago(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    idf_coeffs: ShermanCoefficients,
    return_period_yr: float,
    peak1_position: float = 0.25,
    peak2_position: float = 0.75,
    volume_split: float = 0.5,
) -> HyetographResult:
    """
    Genera hietograma bimodal superponiendo dos tormentas Chicago.

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        idf_coeffs: Coeficientes Sherman para IDF
        return_period_yr: Período de retorno en años
        peak1_position: Posición del primer pico (0-1)
        peak2_position: Posición del segundo pico (0-1)
        volume_split: Fracción del volumen en el primer pico

    Returns:
        HyetographResult con el hietograma generado
    """
    # Generar cada tormenta Chicago por separado
    vol1 = total_depth_mm * volume_split
    vol2 = total_depth_mm * (1 - volume_split)

    # Primera tormenta (primer pico)
    storm1 = chicago_storm(
        vol1, duration_hr, dt_min, idf_coeffs,
        return_period_yr, advancement_coef=peak1_position
    )

    # Segunda tormenta (segundo pico)
    storm2 = chicago_storm(
        vol2, duration_hr, dt_min, idf_coeffs,
        return_period_yr, advancement_coef=peak2_position
    )

    # Combinar
    depths1 = np.array(storm1.depth_mm)
    depths2 = np.array(storm2.depth_mm)
    result_depths = depths1 + depths2

    # Escalar
    current_total = np.sum(result_depths)
    if current_total > 0:
        result_depths *= total_depth_mm / current_total

    time_min = np.array(storm1.time_min)
    intensities = result_depths * 60 / dt_min
    cumulative = np.cumsum(result_depths)

    return HyetographResult(
        time_min=time_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=result_depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="bimodal_chicago",
        total_depth_mm=float(np.sum(result_depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )
