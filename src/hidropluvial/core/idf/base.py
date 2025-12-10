"""
Tipos base y utilidades para curvas IDF.

Incluye:
- Conversiones entre intensidad y profundidad
"""

import numpy as np
from numpy.typing import NDArray


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
