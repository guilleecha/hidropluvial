"""
Tormentas personalizadas y funciones principales extendidas.

Incluye:
- custom_depth_storm: Genera hietograma desde precipitación total personalizada
- custom_hyetograph: Crea hietograma desde datos medidos
- generate_hyetograph: Dispatcher principal para todos los métodos
- generate_hyetograph_dinagua: Dispatcher para métodos DINAGUA
"""

import numpy as np

from hidropluvial.config import HyetographResult, ShermanCoefficients, StormMethod
from hidropluvial.core.idf import dinagua_depth

from .base import distribute_alternating_blocks
from .blocks import alternating_blocks, alternating_blocks_dinagua
from .chicago import chicago_storm
from .scs import scs_distribution
from .huff import huff_distribution


def custom_depth_storm(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    distribution: str = "alternating_blocks",
    peak_position: float = 0.5,
    huff_quartile: int = 2,
) -> HyetographResult:
    """
    Genera hietograma desde precipitación total personalizada.

    Permite usar una precipitación acumulada conocida (ej: evento real)
    y distribuirla temporalmente con el método seleccionado.

    Args:
        total_depth_mm: Precipitación total en mm
        duration_hr: Duración total en horas
        dt_min: Intervalo de tiempo en minutos
        distribution: Método de distribución temporal:
            - 'alternating_blocks': Bloques alternantes (pico al centro o posición custom)
            - 'uniform': Distribución uniforme
            - 'triangular': Distribución triangular (pico al centro)
            - 'scs_type_ii': Distribución SCS Tipo II
            - 'huff_q1' a 'huff_q4': Curvas Huff por cuartil
        peak_position: Posición del pico (0-1) para bloques alternantes
        huff_quartile: Cuartil para distribución Huff (1-4)

    Returns:
        HyetographResult con el hietograma generado
    """
    n_intervals = int(duration_hr * 60 / dt_min)
    time_min = np.arange(0, n_intervals) * dt_min + dt_min / 2

    if distribution == "uniform":
        # Distribución uniforme
        depth_per_interval = total_depth_mm / n_intervals
        depths = np.full(n_intervals, depth_per_interval)

    elif distribution == "triangular":
        # Distribución triangular centrada
        peak_idx = n_intervals // 2

        # Crear triángulo
        depths = np.zeros(n_intervals)
        for i in range(n_intervals):
            if i <= peak_idx:
                depths[i] = i / peak_idx if peak_idx > 0 else 1
            else:
                depths[i] = (n_intervals - 1 - i) / (n_intervals - 1 - peak_idx)

        # Normalizar para que sume total_depth_mm
        depths = depths * total_depth_mm / np.sum(depths)

    elif distribution == "alternating_blocks":
        # Usar curva IDF sintética basada en relación duración-profundidad típica
        # Asumimos que la intensidad sigue: i = a / (t + b)^n con valores típicos
        # Generar profundidades acumuladas sintéticas usando relación potencial
        # P(d) = P_total * (d/D)^0.6 (relación típica)
        cumulative_depths = np.zeros(n_intervals)
        for i in range(n_intervals):
            d_ratio = (i + 1) / n_intervals
            cumulative_depths[i] = total_depth_mm * (d_ratio ** 0.6)

        # Calcular incrementos
        increments = np.zeros(n_intervals)
        increments[0] = cumulative_depths[0]
        for i in range(1, n_intervals):
            increments[i] = cumulative_depths[i] - cumulative_depths[i - 1]

        # Ordenar y distribuir alternando
        sorted_increments = np.sort(increments)[::-1]
        depths = distribute_alternating_blocks(sorted_increments, n_intervals, peak_position)

    elif distribution == "scs_type_ii":
        result = scs_distribution(total_depth_mm, duration_hr, dt_min, StormMethod.SCS_TYPE_II)
        return HyetographResult(
            time_min=result.time_min,
            intensity_mmhr=result.intensity_mmhr,
            depth_mm=result.depth_mm,
            cumulative_mm=result.cumulative_mm,
            method="custom_scs_type_ii",
            total_depth_mm=result.total_depth_mm,
            peak_intensity_mmhr=result.peak_intensity_mmhr,
        )

    elif distribution.startswith("huff"):
        quartile = huff_quartile
        if "_q" in distribution:
            quartile = int(distribution.split("_q")[1])
        result = huff_distribution(total_depth_mm, duration_hr, dt_min, quartile=quartile)
        return HyetographResult(
            time_min=result.time_min,
            intensity_mmhr=result.intensity_mmhr,
            depth_mm=result.depth_mm,
            cumulative_mm=result.cumulative_mm,
            method=f"custom_huff_q{quartile}",
            total_depth_mm=result.total_depth_mm,
            peak_intensity_mmhr=result.peak_intensity_mmhr,
        )

    else:
        raise ValueError(f"Distribución desconocida: {distribution}")

    # Calcular intensidades y acumulado
    intensities = depths * 60 / dt_min
    cumulative = np.cumsum(depths)

    return HyetographResult(
        time_min=time_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=depths.tolist(),
        cumulative_mm=cumulative.tolist(),
        method=f"custom_{distribution}",
        total_depth_mm=float(np.sum(depths)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )


def custom_hyetograph(
    time_min: list[float],
    depth_mm: list[float],
) -> HyetographResult:
    """
    Crea HyetographResult desde datos de hietograma personalizados.

    Útil para evaluar eventos de precipitación reales medidos.

    Args:
        time_min: Lista de tiempos centrales de cada intervalo (minutos)
        depth_mm: Lista de profundidades por intervalo (mm)

    Returns:
        HyetographResult con el hietograma personalizado
    """
    if len(time_min) != len(depth_mm):
        raise ValueError("time_min y depth_mm deben tener la misma longitud")

    if len(time_min) < 2:
        raise ValueError("Se necesitan al menos 2 intervalos")

    time_arr = np.array(time_min)
    depth_arr = np.array(depth_mm)

    # Calcular dt asumiendo intervalos regulares
    dt_min = time_arr[1] - time_arr[0]

    # Calcular intensidades
    intensities = depth_arr * 60 / dt_min

    # Calcular acumulado
    cumulative = np.cumsum(depth_arr)

    return HyetographResult(
        time_min=time_arr.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=depth_arr.tolist(),
        cumulative_mm=cumulative.tolist(),
        method="custom_event",
        total_depth_mm=float(np.sum(depth_arr)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )


def generate_hyetograph(
    method: StormMethod,
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float = 5.0,
    idf_method: str | None = None,
    idf_coeffs: ShermanCoefficients | None = None,
    return_period_yr: float = 100,
    advancement_coef: float = 0.375,
    huff_quartile: int = 2,
    huff_probability: int = 50,
) -> HyetographResult:
    """
    Función principal para generar hietogramas.

    Args:
        method: Método de distribución temporal
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración en horas
        dt_min: Intervalo de tiempo en minutos
        idf_method: Método IDF (requerido para bloques alternantes)
        idf_coeffs: Coeficientes IDF (requerido para bloques alternantes y Chicago)
        return_period_yr: Período de retorno en años
        advancement_coef: Coeficiente de avance para Chicago
        huff_quartile: Cuartil para Huff
        huff_probability: Probabilidad para Huff

    Returns:
        HyetographResult
    """
    if method == StormMethod.ALTERNATING_BLOCKS:
        if idf_method is None or idf_coeffs is None:
            raise ValueError("Se requiere idf_method e idf_coeffs para bloques alternantes")
        return alternating_blocks(
            total_depth_mm, duration_hr, dt_min,
            idf_method, idf_coeffs, return_period_yr
        )

    elif method == StormMethod.CHICAGO:
        if idf_coeffs is None:
            raise ValueError("Se requiere idf_coeffs para tormenta Chicago")
        return chicago_storm(
            total_depth_mm, duration_hr, dt_min,
            idf_coeffs, return_period_yr, advancement_coef
        )

    elif method in [StormMethod.SCS_TYPE_I, StormMethod.SCS_TYPE_IA,
                    StormMethod.SCS_TYPE_II, StormMethod.SCS_TYPE_III]:
        return scs_distribution(total_depth_mm, duration_hr, dt_min, method)

    elif method in [StormMethod.HUFF_Q1, StormMethod.HUFF_Q2,
                    StormMethod.HUFF_Q3, StormMethod.HUFF_Q4]:
        quartile = int(method.value[-1])
        return huff_distribution(
            total_depth_mm, duration_hr, dt_min,
            quartile, huff_probability
        )

    else:
        raise ValueError(f"Método desconocido: {method}")


def generate_hyetograph_dinagua(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    dt_min: float = 5.0,
    method: str = "alternating_blocks",
    area_km2: float | None = None,
    peak_position: float = 0.5,
) -> HyetographResult:
    """
    Genera hietograma usando método DINAGUA Uruguay.

    Args:
        p3_10: Precipitación P3,10 base (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración en horas
        dt_min: Intervalo de tiempo en minutos
        method: 'alternating_blocks' o 'scs_type_ii'
        area_km2: Área de cuenca para corrección
        peak_position: Posición del pico para bloques alternantes

    Returns:
        HyetographResult
    """
    # Calcular precipitación total usando DINAGUA
    total_depth = dinagua_depth(p3_10, return_period_yr, duration_hr, area_km2)

    if method == "alternating_blocks":
        return alternating_blocks_dinagua(
            p3_10, return_period_yr, duration_hr, dt_min, area_km2, peak_position
        )
    elif method == "scs_type_ii":
        return scs_distribution(total_depth, duration_hr, dt_min, StormMethod.SCS_TYPE_II)
    elif method == "scs_type_i":
        return scs_distribution(total_depth, duration_hr, dt_min, StormMethod.SCS_TYPE_I)
    elif method == "huff_q2":
        return huff_distribution(total_depth, duration_hr, dt_min, quartile=2)
    else:
        raise ValueError(f"Método desconocido: {method}")
