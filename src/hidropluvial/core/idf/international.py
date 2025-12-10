"""
Métodos internacionales para curvas IDF.

Incluye:
- Sherman (1931): i = k * T^m / (t + c)^n
- Bernard (Power Law): i = a * T^m / t^n
- Koutsoyiannis (1998): I(T,d) = a(T) / (d + theta)^eta
"""

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import (
    BernardCoefficients,
    KoutsoyiannisCoefficients,
    ShermanCoefficients,
)


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

    # Factor de frecuencia Gumbel
    if T <= 1:
        raise ValueError("Período de retorno debe ser > 1 año")

    # a(T) usando distribución Gumbel
    y_T = -np.log(-np.log(1 - 1 / T))  # Variable reducida Gumbel
    a_T = coeffs.mu + coeffs.sigma * y_T

    intensity = a_T / ((d + coeffs.theta) ** coeffs.eta)
    return float(intensity) if np.isscalar(duration_min) else intensity
