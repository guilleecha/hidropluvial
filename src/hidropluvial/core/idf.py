"""
Módulo de curvas Intensidad-Duración-Frecuencia (IDF).

Implementa métodos para calcular intensidades de lluvia:
- Uruguay/DINAGUA (Rodríguez Fontal 1980) - MÉTODO PRINCIPAL
- Sherman (1931)
- Bernard (Power Law)
- Koutsoyiannis (1998)
"""

import math
import warnings
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import (
    BernardCoefficients,
    KoutsoyiannisCoefficients,
    ShermanCoefficients,
)


# ============================================================================
# Método Uruguay/DINAGUA - MÉTODO PRINCIPAL
# ============================================================================

# Valores de P3,10 por departamento (mm)
P3_10_URUGUAY = {
    "montevideo": 78,
    "canelones": 75,
    "maldonado": 76,
    "rocha": 77,
    "colonia": 73,
    "san_jose": 74,
    "florida": 76,
    "lavalleja": 78,
    "treinta_y_tres": 80,
    "cerro_largo": 82,
    "rivera": 84,
    "tacuarembo": 82,
    "durazno": 78,
    "flores": 75,
    "soriano": 74,
    "rio_negro": 76,
    "paysandu": 79,
    "salto": 81,
    "artigas": 83,
}


@dataclass
class UruguayIDFResult:
    """Resultado del cálculo IDF Uruguay."""
    intensity_mmhr: float
    depth_mm: float
    ct: float
    ca: float
    p3_10: float
    return_period_yr: float
    duration_hr: float
    area_km2: float | None


def dinagua_ct(return_period_yr: float) -> float:
    """
    Factor de corrección por período de retorno (CT).

    CT(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]

    Args:
        return_period_yr: Período de retorno en años (>= 2)

    Returns:
        Factor CT (adimensional)
    """
    if return_period_yr < 2:
        raise ValueError("Período de retorno debe ser >= 2 años")

    Tr = return_period_yr
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))


def dinagua_ca(area_km2: float, duration_hr: float) -> float:
    """
    Factor de corrección por área de cuenca (CA).

    CA(Ac,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × Ac))

    Args:
        area_km2: Área de la cuenca en km²
        duration_hr: Duración de la tormenta en horas

    Returns:
        Factor CA (adimensional, <= 1.0)
    """
    if area_km2 <= 1.0:
        return 1.0

    if area_km2 > 300:
        warnings.warn(
            f"Área {area_km2} km² > 300 km²: verificar con estudios regionales",
            UserWarning
        )

    d = max(duration_hr, 0.083)  # Mínimo 5 minutos
    ca = 1.0 - (0.3549 * (d ** -0.4272)) * (1.0 - math.exp(-0.005792 * area_km2))

    return min(ca, 1.0)


def dinagua_intensity(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> UruguayIDFResult:
    """
    Calcula intensidad de lluvia usando método DINAGUA Uruguay.

    Para d < 3 horas:
        I(d) = [P₃,₁₀ × CT(Tr)] × 0.6208 / (d + 0.0137)^0.5639

    Para d ≥ 3 horas:
        I(d) = [P₃,₁₀ × CT(Tr)] × 1.0287 / (d + 1.0293)^0.8083

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        area_km2: Área de cuenca (km²), opcional para corrección por área

    Returns:
        UruguayIDFResult con intensidad, profundidad y factores
    """
    # Validaciones
    if p3_10 < 50 or p3_10 > 120:
        warnings.warn(
            f"P3_10={p3_10}mm fuera del rango típico Uruguay (50-120mm)",
            UserWarning
        )

    if duration_hr <= 0:
        raise ValueError("Duración debe ser > 0")

    # Calcular factores
    ct = dinagua_ct(return_period_yr)
    ca = dinagua_ca(area_km2, duration_hr) if area_km2 else 1.0

    # Precipitación corregida por período de retorno
    p_corr = p3_10 * ct

    # Intensidad según duración
    d = duration_hr
    if d < 3.0:
        intensity = p_corr * 0.6208 / ((d + 0.0137) ** 0.5639)
    else:
        intensity = p_corr * 1.0287 / ((d + 1.0293) ** 0.8083)

    # Aplicar corrección por área
    intensity *= ca

    # Precipitación total
    depth = intensity * duration_hr

    return UruguayIDFResult(
        intensity_mmhr=round(intensity, 2),
        depth_mm=round(depth, 2),
        ct=round(ct, 4),
        ca=round(ca, 4),
        p3_10=p3_10,
        return_period_yr=return_period_yr,
        duration_hr=duration_hr,
        area_km2=area_km2,
    )


def dinagua_intensity_simple(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> float:
    """
    Versión simplificada que retorna solo la intensidad.

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        area_km2: Área de cuenca (km²), opcional

    Returns:
        Intensidad en mm/hr
    """
    result = dinagua_intensity(p3_10, return_period_yr, duration_hr, area_km2)
    return result.intensity_mmhr


def dinagua_depth(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> float:
    """
    Calcula profundidad de lluvia usando método DINAGUA.

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        return_period_yr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        area_km2: Área de cuenca (km²), opcional

    Returns:
        Profundidad en mm
    """
    result = dinagua_intensity(p3_10, return_period_yr, duration_hr, area_km2)
    return result.depth_mm


def generate_dinagua_idf_table(
    p3_10: float,
    durations_hr: list[float] | None = None,
    return_periods_yr: list[int] | None = None,
    area_km2: float | None = None,
) -> dict:
    """
    Genera tabla completa de curvas IDF usando método DINAGUA.

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        durations_hr: Lista de duraciones en horas (default: estándar)
        return_periods_yr: Lista de períodos de retorno (default: estándar)
        area_km2: Área de cuenca para corrección (opcional)

    Returns:
        Diccionario con durations, return_periods, intensities, depths
    """
    if durations_hr is None:
        durations_hr = [0.083, 0.167, 0.25, 0.5, 1, 2, 3, 6, 12, 24]  # 5min a 24hr

    if return_periods_yr is None:
        return_periods_yr = [2, 5, 10, 25, 50, 100]

    n_periods = len(return_periods_yr)
    n_durations = len(durations_hr)

    intensities = np.zeros((n_periods, n_durations))
    depths = np.zeros((n_periods, n_durations))

    for i, Tr in enumerate(return_periods_yr):
        for j, d in enumerate(durations_hr):
            result = dinagua_intensity(p3_10, Tr, d, area_km2)
            intensities[i, j] = result.intensity_mmhr
            depths[i, j] = result.depth_mm

    return {
        "p3_10": p3_10,
        "area_km2": area_km2,
        "durations_hr": np.array(durations_hr),
        "return_periods_yr": np.array(return_periods_yr),
        "intensities_mmhr": intensities,
        "depths_mm": depths,
    }


def get_p3_10(departamento: str) -> float:
    """
    Obtiene P3,10 de referencia para un departamento de Uruguay.

    Args:
        departamento: Nombre del departamento (minúsculas, sin tildes)

    Returns:
        P3,10 en mm
    """
    key = departamento.lower().replace(" ", "_")
    if key not in P3_10_URUGUAY:
        available = ", ".join(sorted(P3_10_URUGUAY.keys()))
        raise ValueError(
            f"Departamento '{departamento}' no encontrado. "
            f"Disponibles: {available}"
        )
    return P3_10_URUGUAY[key]


# ============================================================================
# Métodos Internacionales (Sherman, Bernard, Koutsoyiannis)
# ============================================================================


def sherman_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: ShermanCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuación Sherman.

    i = k * T^m / (t + c)^n

    Args:
        duration_min: Duración en minutos (escalar o array)
        return_period_yr: Período de retorno en años
        coeffs: Coeficientes Sherman (k, m, c, n)

    Returns:
        Intensidad en mm/hr
    """
    t = np.asarray(duration_min)
    T = return_period_yr

    intensity = coeffs.k * (T ** coeffs.m) / ((t + coeffs.c) ** coeffs.n)
    return float(intensity) if np.isscalar(duration_min) else intensity


def bernard_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: BernardCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuación Bernard (Power Law).

    i = a * T^m / t^n

    Args:
        duration_min: Duración en minutos (escalar o array)
        return_period_yr: Período de retorno en años
        coeffs: Coeficientes Bernard (a, m, n)

    Returns:
        Intensidad en mm/hr
    """
    t = np.asarray(duration_min)
    T = return_period_yr

    # Evitar división por cero
    t = np.maximum(t, 0.1)

    intensity = coeffs.a * (T ** coeffs.m) / (t ** coeffs.n)
    return float(intensity) if np.isscalar(duration_min) else intensity


def koutsoyiannis_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: KoutsoyiannisCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando método Koutsoyiannis (1998).

    I(T,d) = a(T) / (d + theta)^eta

    donde:
        a(T) = mu + sigma * {0.5772 + ln[ln(T/(T-1))]}

    Args:
        duration_min: Duración en minutos (escalar o array)
        return_period_yr: Período de retorno en años
        coeffs: Coeficientes Koutsoyiannis (mu, sigma, theta, eta)

    Returns:
        Intensidad en mm/hr
    """
    d = np.asarray(duration_min)
    T = return_period_yr

    # Constante de Euler-Mascheroni
    euler = 0.5772156649

    # Factor de frecuencia Gumbel
    if T <= 1:
        raise ValueError("Período de retorno debe ser > 1 año")

    # a(T) usando distribución Gumbel
    y_T = -np.log(-np.log(1 - 1 / T))  # Variable reducida Gumbel
    a_T = coeffs.mu + coeffs.sigma * y_T

    intensity = a_T / ((d + coeffs.theta) ** coeffs.eta)
    return float(intensity) if np.isscalar(duration_min) else intensity


def depth_from_intensity(
    intensity_mmhr: float | NDArray[np.floating],
    duration_min: float | NDArray[np.floating],
) -> float | NDArray[np.floating]:
    """
    Convierte intensidad a profundidad de lluvia.

    P = i * t / 60

    Args:
        intensity_mmhr: Intensidad en mm/hr
        duration_min: Duración en minutos

    Returns:
        Profundidad en mm
    """
    i = np.asarray(intensity_mmhr)
    t = np.asarray(duration_min)
    depth = i * t / 60.0
    result = float(depth) if np.isscalar(intensity_mmhr) and np.isscalar(duration_min) else depth
    return result


def intensity_from_depth(
    depth_mm: float | NDArray[np.floating],
    duration_min: float | NDArray[np.floating],
) -> float | NDArray[np.floating]:
    """
    Convierte profundidad de lluvia a intensidad.

    i = P * 60 / t

    Args:
        depth_mm: Profundidad en mm
        duration_min: Duración en minutos

    Returns:
        Intensidad en mm/hr
    """
    P = np.asarray(depth_mm)
    t = np.asarray(duration_min)
    t = np.maximum(t, 0.1)  # Evitar división por cero
    intensity = P * 60.0 / t
    result = float(intensity) if np.isscalar(depth_mm) and np.isscalar(duration_min) else intensity
    return result


def generate_idf_table(
    durations_min: list[float],
    return_periods_yr: list[int],
    method: str,
    coeffs: ShermanCoefficients | BernardCoefficients | KoutsoyiannisCoefficients,
) -> dict[str, NDArray[np.floating]]:
    """
    Genera tabla completa de curvas IDF.

    Args:
        durations_min: Lista de duraciones en minutos
        return_periods_yr: Lista de períodos de retorno en años
        method: Método ('sherman', 'bernard', 'koutsoyiannis')
        coeffs: Coeficientes del método

    Returns:
        Diccionario con:
            - 'durations': array de duraciones
            - 'return_periods': array de períodos
            - 'intensities': matriz [n_periods x n_durations] de intensidades
            - 'depths': matriz [n_periods x n_durations] de profundidades
    """
    durations = np.array(durations_min)
    periods = np.array(return_periods_yr)

    n_periods = len(periods)
    n_durations = len(durations)

    intensities = np.zeros((n_periods, n_durations))
    depths = np.zeros((n_periods, n_durations))

    # Seleccionar función según método
    if method == "sherman":
        if not isinstance(coeffs, ShermanCoefficients):
            raise TypeError("Se requieren ShermanCoefficients")
        calc_func = lambda d, T: sherman_intensity(d, T, coeffs)
    elif method == "bernard":
        if not isinstance(coeffs, BernardCoefficients):
            raise TypeError("Se requieren BernardCoefficients")
        calc_func = lambda d, T: bernard_intensity(d, T, coeffs)
    elif method == "koutsoyiannis":
        if not isinstance(coeffs, KoutsoyiannisCoefficients):
            raise TypeError("Se requieren KoutsoyiannisCoefficients")
        calc_func = lambda d, T: koutsoyiannis_intensity(d, T, coeffs)
    else:
        raise ValueError(f"Método desconocido: {method}")

    for i, T in enumerate(periods):
        intensities[i, :] = calc_func(durations, T)
        depths[i, :] = depth_from_intensity(intensities[i, :], durations)

    return {
        "durations": durations,
        "return_periods": periods,
        "intensities": intensities,
        "depths": depths,
    }


def fit_sherman_coefficients(
    durations_min: NDArray[np.floating],
    intensities_mmhr: NDArray[np.floating],
    return_period_yr: float,
    initial_guess: tuple[float, float, float] = (1000.0, 10.0, 0.7),
) -> ShermanCoefficients:
    """
    Ajusta coeficientes Sherman a datos observados (para un período de retorno fijo).

    i = k / (t + c)^n  (simplificado, T fijo)

    Args:
        durations_min: Array de duraciones observadas
        intensities_mmhr: Array de intensidades observadas
        return_period_yr: Período de retorno de los datos
        initial_guess: Valores iniciales (k, c, n)

    Returns:
        ShermanCoefficients ajustados
    """
    from scipy.optimize import curve_fit

    def sherman_simple(t: NDArray, k: float, c: float, n: float) -> NDArray:
        return k / ((t + c) ** n)

    popt, _ = curve_fit(
        sherman_simple,
        durations_min,
        intensities_mmhr,
        p0=initial_guess,
        bounds=([0, 0, 0.1], [np.inf, 60, 2.0]),
        maxfev=5000,
    )

    k_fitted, c_fitted, n_fitted = popt

    # Para el modelo completo, asumimos m=0.2 (valor típico)
    # y ajustamos k para que k_total = k_fitted cuando T=return_period
    m_assumed = 0.2
    k_total = k_fitted / (return_period_yr ** m_assumed)

    return ShermanCoefficients(k=k_total, m=m_assumed, c=c_fitted, n=n_fitted)


def get_intensity(
    duration_min: float,
    return_period_yr: float,
    method: str,
    coeffs: ShermanCoefficients | BernardCoefficients | KoutsoyiannisCoefficients,
) -> float:
    """
    Función de conveniencia para obtener una intensidad.

    Args:
        duration_min: Duración en minutos
        return_period_yr: Período de retorno en años
        method: Método ('sherman', 'bernard', 'koutsoyiannis')
        coeffs: Coeficientes del método

    Returns:
        Intensidad en mm/hr
    """
    if method == "sherman":
        if not isinstance(coeffs, ShermanCoefficients):
            raise TypeError("Se requieren ShermanCoefficients")
        return sherman_intensity(duration_min, return_period_yr, coeffs)
    elif method == "bernard":
        if not isinstance(coeffs, BernardCoefficients):
            raise TypeError("Se requieren BernardCoefficients")
        return bernard_intensity(duration_min, return_period_yr, coeffs)
    elif method == "koutsoyiannis":
        if not isinstance(coeffs, KoutsoyiannisCoefficients):
            raise TypeError("Se requieren KoutsoyiannisCoefficients")
        return koutsoyiannis_intensity(duration_min, return_period_yr, coeffs)
    else:
        raise ValueError(f"Método desconocido: {method}")


def get_depth(
    duration_min: float,
    return_period_yr: float,
    method: str,
    coeffs: ShermanCoefficients | BernardCoefficients | KoutsoyiannisCoefficients,
) -> float:
    """
    Función de conveniencia para obtener profundidad de lluvia.

    Args:
        duration_min: Duración en minutos
        return_period_yr: Período de retorno en años
        method: Método ('sherman', 'bernard', 'koutsoyiannis')
        coeffs: Coeficientes del método

    Returns:
        Profundidad en mm
    """
    intensity = get_intensity(duration_min, return_period_yr, method, coeffs)
    return depth_from_intensity(intensity, duration_min)
