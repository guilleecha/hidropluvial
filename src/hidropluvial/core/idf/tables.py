"""
Generación de tablas IDF y ajuste de coeficientes.

Incluye:
- generate_idf_table: Genera tabla completa de curvas IDF
- fit_sherman_coefficients: Ajusta coeficientes Sherman a datos
- get_intensity/get_depth: Funciones de conveniencia
"""

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import (
    BernardCoefficients,
    KoutsoyiannisCoefficients,
    ShermanCoefficients,
)

from .base import depth_from_intensity
from .international import (
    sherman_intensity,
    bernard_intensity,
    koutsoyiannis_intensity,
)


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
