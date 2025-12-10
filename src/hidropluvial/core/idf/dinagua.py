"""
Método DINAGUA Uruguay para curvas IDF.

Metodología basada en Rodríguez Fontal (1980) que calcula
precipitación acumulada P(d,Tr,A) mediante:

    P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)

Donde:
- P₃,₁₀: Precipitación máxima 3h, Tr=10 años (del mapa de isoyetas)
- Cd(d): Factor de corrección por duración
- Ct(Tr): Factor de corrección por período de retorno
- CA(A,d): Factor de corrección por área de cuenca

La intensidad se deriva como I = P / d
"""

import math
import warnings
from dataclasses import dataclass

import numpy as np


# Valores de P3,10 de referencia por departamento (mm)
# NOTA: Estos son valores orientativos. Para proyectos se debe usar
# el mapa de isoyetas de DINAGUA para obtener el valor exacto de la ubicación.
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
    depth_mm: float           # Precipitación acumulada P(d,Tr,A)
    intensity_mmhr: float     # Intensidad I = P/d
    cd: float                 # Factor de corrección por duración
    ct: float                 # Factor de corrección por período de retorno
    ca: float                 # Factor de corrección por área
    p3_10: float              # Precipitación base P₃,₁₀
    return_period_yr: float   # Período de retorno
    duration_hr: float        # Duración
    area_km2: float | None    # Área de cuenca


def dinagua_cd(duration_hr: float) -> float:
    """
    Factor de corrección por duración (Cd).

    Para d < 3 horas:
        Cd(d) = 0.6208 / (d + 0.0137)^0.5639 × d / 3

    Para d ≥ 3 horas:
        Cd(d) = 1.0287 / (d + 1.0293)^0.8083 × d / 3

    El factor está normalizado para que Cd(3) ≈ 1.0

    Args:
        duration_hr: Duración de la tormenta en horas

    Returns:
        Factor Cd (adimensional)
    """
    if duration_hr <= 0:
        raise ValueError("Duración debe ser > 0")

    d = duration_hr
    if d < 3.0:
        # Factor que convierte intensidad a precipitación y normaliza a d=3h
        cd = 0.6208 / ((d + 0.0137) ** 0.5639) * d / 3.0
    else:
        cd = 1.0287 / ((d + 1.0293) ** 0.8083) * d / 3.0

    return cd


def dinagua_ct(return_period_yr: float) -> float:
    """
    Factor de corrección por período de retorno (Ct).

    Ct(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]

    Normalizado para que Ct(10) ≈ 1.0

    Args:
        return_period_yr: Período de retorno en años (>= 2)

    Returns:
        Factor Ct (adimensional)
    """
    if return_period_yr < 2:
        raise ValueError("Período de retorno debe ser >= 2 años")

    Tr = return_period_yr
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))


def dinagua_ca(area_km2: float, duration_hr: float) -> float:
    """
    Factor de corrección por área de cuenca (CA).

    CA(A,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × A))

    Para A <= 1 km², CA = 1.0 (sin reducción)

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


def dinagua_precipitation(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> UruguayIDFResult:
    """
    Calcula precipitación acumulada usando método DINAGUA Uruguay.

    P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)

    Luego la intensidad se deriva como: I = P / d

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm) del mapa de isoyetas
        return_period_yr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        area_km2: Área de cuenca (km²), opcional para corrección por área

    Returns:
        UruguayIDFResult con precipitación, intensidad y factores
    """
    # Validaciones
    if p3_10 < 50 or p3_10 > 120:
        warnings.warn(
            f"P3_10={p3_10}mm fuera del rango típico Uruguay (50-120mm)",
            UserWarning
        )

    if duration_hr <= 0:
        raise ValueError("Duración debe ser > 0")

    # Calcular factores de corrección
    cd = dinagua_cd(duration_hr)
    ct = dinagua_ct(return_period_yr)
    ca = dinagua_ca(area_km2, duration_hr) if area_km2 else 1.0

    # Precipitación acumulada: P(d,Tr,A) = P₃,₁₀ × Cd × Ct × CA
    depth = p3_10 * cd * ct * ca

    # Intensidad derivada: I = P / d
    intensity = depth / duration_hr

    return UruguayIDFResult(
        depth_mm=round(depth, 2),
        intensity_mmhr=round(intensity, 2),
        cd=round(cd, 4),
        ct=round(ct, 4),
        ca=round(ca, 4),
        p3_10=p3_10,
        return_period_yr=return_period_yr,
        duration_hr=duration_hr,
        area_km2=area_km2,
    )


def dinagua_intensity(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> UruguayIDFResult:
    """
    Calcula intensidad de lluvia usando método DINAGUA Uruguay.

    Esta función es un alias de dinagua_precipitation() para
    compatibilidad con código existente.

    Args:
        p3_10: Precipitación máxima 3hr, Tr=10 años (mm) del mapa de isoyetas
        return_period_yr: Período de retorno en años
        duration_hr: Duración de la tormenta en horas
        area_km2: Área de cuenca (km²), opcional para corrección por área

    Returns:
        UruguayIDFResult con precipitación, intensidad y factores
    """
    return dinagua_precipitation(p3_10, return_period_yr, duration_hr, area_km2)


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
