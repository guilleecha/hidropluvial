"""
Módulo de distribuciones temporales de lluvia.

Implementa métodos para generar hietogramas de diseño:
- Método de Bloques Alternantes (con soporte DINAGUA Uruguay)
- Tormenta de Diseño Chicago (Keifer & Chu 1957)
- Distribuciones SCS 24h (Tipos I, IA, II, III)
- Curvas Huff (1967)
- Tormentas Bimodales
"""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import (
    HyetographResult,
    ShermanCoefficients,
    StormMethod,
)
from hidropluvial.core.idf import (
    depth_from_intensity,
    get_intensity,
    dinagua_intensity_simple,
    dinagua_depth,
)


# Cargar datos de distribuciones
_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_scs_distributions() -> dict:
    """Carga distribuciones SCS desde JSON."""
    with open(_DATA_DIR / "scs_distributions.json") as f:
        return json.load(f)


def _load_huff_curves() -> dict:
    """Carga curvas Huff desde JSON."""
    with open(_DATA_DIR / "huff_curves.json") as f:
        return json.load(f)


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

    # Ordenar incrementos de mayor a menor
    sorted_indices = np.argsort(increments)[::-1]
    sorted_increments = increments[sorted_indices]

    # Distribuir alternando alrededor del pico
    peak_index = int(peak_position * n_intervals)
    result_depths = np.zeros(n_intervals)

    left = peak_index
    right = peak_index + 1
    toggle = True  # True = izquierda, False = derecha

    for inc in sorted_increments:
        if toggle and left >= 0:
            result_depths[left] = inc
            left -= 1
        elif not toggle and right < n_intervals:
            result_depths[right] = inc
            right += 1
        elif left >= 0:
            result_depths[left] = inc
            left -= 1
        elif right < n_intervals:
            result_depths[right] = inc
            right += 1
        toggle = not toggle

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


def scs_distribution(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    storm_type: StormMethod,
) -> HyetographResult:
    """
    Genera hietograma usando distribución SCS 24 horas.

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración (normalmente 24 hr para SCS estándar)
        dt_min: Intervalo de tiempo en minutos
        storm_type: Tipo de tormenta SCS (I, IA, II, III)

    Returns:
        HyetographResult con el hietograma generado
    """
    # Mapear tipo de tormenta a clave JSON
    type_map = {
        StormMethod.SCS_TYPE_I: "scs_type_i",
        StormMethod.SCS_TYPE_IA: "scs_type_ia",
        StormMethod.SCS_TYPE_II: "scs_type_ii",
        StormMethod.SCS_TYPE_III: "scs_type_iii",
    }

    if storm_type not in type_map:
        raise ValueError(f"Tipo de tormenta inválido: {storm_type}")

    # Cargar distribución
    distributions = _load_scs_distributions()
    dist_data = distributions[type_map[storm_type]]

    time_hr_ref = np.array(dist_data["time_hr"])
    ratio_ref = np.array(dist_data["ratio"])

    # Interpolar a intervalos dt_min
    n_intervals = int(duration_hr * 60 / dt_min)
    time_hr_interp = np.linspace(0, duration_hr, n_intervals + 1)

    # Escalar tiempo de referencia si duración != 24hr
    time_hr_scaled = time_hr_ref * duration_hr / 24.0

    # Interpolar ratios acumulados
    cumulative_ratio = np.interp(time_hr_interp, time_hr_scaled, ratio_ref)

    # Calcular profundidades incrementales
    cumulative_depth = cumulative_ratio * total_depth_mm
    incremental_depth = np.diff(cumulative_depth)

    # Tiempos centrales de cada intervalo
    time_centers_hr = (time_hr_interp[:-1] + time_hr_interp[1:]) / 2
    time_centers_min = time_centers_hr * 60

    # Intensidades
    intensities = incremental_depth * 60 / dt_min

    return HyetographResult(
        time_min=time_centers_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=incremental_depth.tolist(),
        cumulative_mm=cumulative_depth[1:].tolist(),
        method=storm_type.value,
        total_depth_mm=float(np.sum(incremental_depth)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )


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
    huff_data = _load_huff_curves()
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


# ============================================================================
# Métodos con IDF DINAGUA Uruguay
# ============================================================================

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

    # Ordenar incrementos de mayor a menor
    sorted_indices = np.argsort(increments)[::-1]
    sorted_increments = increments[sorted_indices]

    # Distribuir alternando alrededor del pico
    peak_index = int(peak_position * n_intervals)
    result_depths = np.zeros(n_intervals)

    left = peak_index
    right = peak_index + 1
    toggle = True

    for inc in sorted_increments:
        if toggle and left >= 0:
            result_depths[left] = inc
            left -= 1
        elif not toggle and right < n_intervals:
            result_depths[right] = inc
            right += 1
        elif left >= 0:
            result_depths[left] = inc
            left -= 1
        elif right < n_intervals:
            result_depths[right] = inc
            right += 1
        toggle = not toggle

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


# ============================================================================
# Tormentas Bimodales
# ============================================================================

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

    Útil para:
    - Cuencas urbanas con impermeabilidad mixta
    - Regiones costeras tropicales
    - Tormentas frontales de larga duración

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


# ============================================================================
# Función principal extendida
# ============================================================================

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
