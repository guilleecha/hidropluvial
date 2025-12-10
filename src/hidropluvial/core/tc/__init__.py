"""
Módulo de tiempo de concentración (Tc).

Implementa múltiples métodos para calcular el tiempo de concentración:
- Kirpich (1940)
- NRCS Velocity Method (TR-55)
- Témez (España/Latinoamérica)
- California Culverts Practice
- FAA Formula
- Kinematic Wave
- Desbordes (DINAGUA Uruguay)
"""

from hidropluvial.config import TCSegment

# Constantes
from .constants import (
    SHALLOW_FLOW_K,
    SHEET_FLOW_N,
)

# Kirpich
from .kirpich import kirpich

# NRCS
from .nrcs import (
    nrcs_sheet_flow,
    nrcs_shallow_flow,
    nrcs_channel_flow,
    nrcs_velocity_method,
)

# Métodos empíricos
from .empirical import (
    temez,
    california_culverts,
    faa_formula,
    desbordes,
)

# Onda cinemática
from .kinematic import kinematic_wave


def calculate_tc(
    method: str,
    length_m: float | None = None,
    length_km: float | None = None,
    slope: float | None = None,
    slope_pct: float | None = None,
    elevation_diff_m: float | None = None,
    surface_type: str = "natural",
    segments: list[TCSegment] | None = None,
    p2_mm: float = 50.0,
    c: float | None = None,
    n: float | None = None,
    intensity_mmhr: float | None = None,
    area_ha: float | None = None,
    t0_min: float | None = None,
) -> float:
    """
    Función principal para calcular tiempo de concentración.

    Args:
        method: Método de cálculo ('kirpich', 'nrcs', 'temez', 'california', 'faa', 'kinematic', 'desbordes')
        length_m: Longitud en metros
        length_km: Longitud en kilómetros
        slope: Pendiente (m/m)
        slope_pct: Pendiente (%)
        elevation_diff_m: Diferencia de elevación (m) para California
        surface_type: Tipo de superficie para Kirpich
        segments: Segmentos para NRCS
        p2_mm: P2 para NRCS sheet flow
        c: Coeficiente C para FAA y Desbordes
        n: Coeficiente Manning para kinematic
        intensity_mmhr: Intensidad para kinematic
        area_ha: Área en hectáreas para Desbordes
        t0_min: Tiempo de entrada inicial para Desbordes (default: 5 min)

    Returns:
        Tiempo de concentración en horas
    """
    # Convertir unidades si es necesario
    if length_km is not None and length_m is None:
        length_m = length_km * 1000
    if slope_pct is not None and slope is None:
        slope = slope_pct / 100

    method = method.lower()

    if method == "kirpich":
        if length_m is None or slope is None:
            raise ValueError("Kirpich requiere length_m y slope")
        return kirpich(length_m, slope, surface_type)

    elif method == "nrcs":
        if segments is None:
            raise ValueError("NRCS requiere segments")
        return nrcs_velocity_method(segments, p2_mm)

    elif method == "temez":
        if length_km is None:
            if length_m is not None:
                length_km = length_m / 1000
            else:
                raise ValueError("Témez requiere length_km")
        if slope is None:
            raise ValueError("Témez requiere slope")
        return temez(length_km, slope)

    elif method == "california":
        if length_km is None:
            if length_m is not None:
                length_km = length_m / 1000
            else:
                raise ValueError("California requiere length_km")
        if elevation_diff_m is None:
            raise ValueError("California requiere elevation_diff_m")
        return california_culverts(length_km, elevation_diff_m)

    elif method == "faa":
        if length_m is None or slope_pct is None or c is None:
            raise ValueError("FAA requiere length_m, slope_pct y c")
        return faa_formula(length_m, slope_pct, c)

    elif method == "kinematic":
        if length_m is None or n is None or slope is None or intensity_mmhr is None:
            raise ValueError("Kinematic requiere length_m, n, slope e intensity_mmhr")
        return kinematic_wave(length_m, n, slope, intensity_mmhr)

    elif method == "desbordes":
        if area_ha is None or slope_pct is None or c is None:
            raise ValueError("Desbordes requiere area_ha, slope_pct y c")
        return desbordes(area_ha, slope_pct, c, t0_min if t0_min is not None else 5.0)

    else:
        raise ValueError(f"Método desconocido: {method}")


__all__ = [
    # Constantes
    "SHALLOW_FLOW_K",
    "SHEET_FLOW_N",
    # Kirpich
    "kirpich",
    # NRCS
    "nrcs_sheet_flow",
    "nrcs_shallow_flow",
    "nrcs_channel_flow",
    "nrcs_velocity_method",
    # Empíricos
    "temez",
    "california_culverts",
    "faa_formula",
    "desbordes",
    # Kinematic
    "kinematic_wave",
    # Dispatcher
    "calculate_tc",
]
