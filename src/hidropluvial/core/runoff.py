"""
Módulo de cálculo de escorrentía.

Implementa métodos para calcular escorrentía superficial:
- Método Racional
- Método SCS Curve Number (CN)
"""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import (
    AntecedentMoistureCondition,
    HydrologicSoilGroup,
    RunoffResult,
)


_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_cn_tables() -> dict:
    """Carga tablas de CN desde JSON."""
    with open(_DATA_DIR / "cn_tables.json") as f:
        return json.load(f)


# ============================================================================
# Método SCS Curve Number
# ============================================================================

def scs_potential_retention(cn: int | float) -> float:
    """
    Calcula retención potencial máxima S.

    S = (25400 / CN) - 254  [mm]

    Args:
        cn: Número de curva (30-100)

    Returns:
        Retención potencial S en mm
    """
    if not 30 <= cn <= 100:
        raise ValueError("CN debe estar entre 30 y 100")

    return (25400 / cn) - 254


def scs_initial_abstraction(s_mm: float, lambda_coef: float = 0.2) -> float:
    """
    Calcula abstracción inicial Ia.

    Ia = λ × S

    Args:
        s_mm: Retención potencial S en mm
        lambda_coef: Coeficiente λ (0.20 tradicional, 0.05 Hawkins 2002)

    Returns:
        Abstracción inicial en mm
    """
    return lambda_coef * s_mm


def scs_runoff(
    rainfall_mm: float | NDArray[np.floating],
    cn: int | float,
    lambda_coef: float = 0.2,
) -> float | NDArray[np.floating]:
    """
    Calcula escorrentía directa usando método SCS-CN.

    Q = (P - Ia)² / (P - Ia + S)  para P > Ia
    Q = 0  para P ≤ Ia

    Args:
        rainfall_mm: Precipitación en mm (escalar o array)
        cn: Número de curva (30-100)
        lambda_coef: Coeficiente λ para Ia (default 0.2)

    Returns:
        Escorrentía directa en mm
    """
    P = np.asarray(rainfall_mm)
    S = scs_potential_retention(cn)
    Ia = scs_initial_abstraction(S, lambda_coef)

    # Calcular escorrentía
    Q = np.where(
        P > Ia,
        ((P - Ia) ** 2) / (P - Ia + S),
        0.0
    )

    if np.isscalar(rainfall_mm):
        return float(Q)
    return Q


def adjust_cn_for_amc(
    cn_ii: int | float,
    amc: AntecedentMoistureCondition,
) -> float:
    """
    Ajusta CN para condición antecedente de humedad.

    CN_I = CN_II / (2.281 - 0.01281 × CN_II)   [AMC II → I (seco)]
    CN_III = CN_II / (0.427 + 0.00573 × CN_II) [AMC II → III (húmedo)]

    Args:
        cn_ii: CN para condiciones promedio (AMC II)
        amc: Condición antecedente de humedad

    Returns:
        CN ajustado
    """
    if not 30 <= cn_ii <= 100:
        raise ValueError("CN debe estar entre 30 y 100")

    if amc == AntecedentMoistureCondition.AVERAGE:
        return float(cn_ii)
    elif amc == AntecedentMoistureCondition.DRY:
        cn_i = cn_ii / (2.281 - 0.01281 * cn_ii)
        return max(30.0, min(100.0, cn_i))
    elif amc == AntecedentMoistureCondition.WET:
        cn_iii = cn_ii / (0.427 + 0.00573 * cn_ii)
        return max(30.0, min(100.0, cn_iii))
    else:
        raise ValueError(f"AMC inválido: {amc}")


def composite_cn(
    areas: list[float],
    cns: list[int | float],
) -> float:
    """
    Calcula CN compuesto para cuenca con múltiples coberturas.

    CN_compuesto = Σ(CNᵢ × Aᵢ) / Σ(Aᵢ)

    Args:
        areas: Lista de áreas parciales (cualquier unidad consistente)
        cns: Lista de CN para cada área

    Returns:
        CN compuesto
    """
    if len(areas) != len(cns):
        raise ValueError("Las listas de áreas y CN deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("Área total no puede ser cero")

    weighted_sum = sum(a * cn for a, cn in zip(areas, cns))
    return weighted_sum / total_area


def get_cn_from_table(
    cover_type: str,
    soil_group: HydrologicSoilGroup,
) -> int:
    """
    Obtiene CN desde tablas TR-55.

    Args:
        cover_type: Tipo de cobertura (ver cn_tables.json)
        soil_group: Grupo hidrológico de suelo (A, B, C, D)

    Returns:
        Número de curva
    """
    tables = _load_cn_tables()

    if cover_type not in tables["cover_types"]:
        raise ValueError(f"Tipo de cobertura desconocido: {cover_type}")

    cover_data = tables["cover_types"][cover_type]
    return cover_data[soil_group.value]


def calculate_scs_runoff(
    rainfall_mm: float,
    cn: int,
    lambda_coef: float = 0.2,
    amc: AntecedentMoistureCondition = AntecedentMoistureCondition.AVERAGE,
) -> RunoffResult:
    """
    Calcula escorrentía SCS-CN con resultado detallado.

    Args:
        rainfall_mm: Precipitación total en mm
        cn: Número de curva (AMC II)
        lambda_coef: Coeficiente λ (default 0.2)
        amc: Condición antecedente de humedad

    Returns:
        RunoffResult con todos los parámetros
    """
    # Ajustar CN si es necesario
    cn_adjusted = adjust_cn_for_amc(cn, amc)

    # Calcular parámetros
    S = scs_potential_retention(cn_adjusted)
    Ia = scs_initial_abstraction(S, lambda_coef)
    Q = scs_runoff(rainfall_mm, cn_adjusted, lambda_coef)

    return RunoffResult(
        rainfall_mm=rainfall_mm,
        runoff_mm=Q,
        initial_abstraction_mm=Ia,
        retention_mm=S,
        cn_used=int(round(cn_adjusted)),
        method=f"SCS-CN (λ={lambda_coef}, AMC={amc.value})",
    )


def rainfall_excess_series(
    cumulative_rainfall_mm: NDArray[np.floating],
    cn: int | float,
    lambda_coef: float = 0.2,
) -> NDArray[np.floating]:
    """
    Calcula serie temporal de exceso de lluvia (precipitación efectiva).

    Para cada paso de tiempo, calcula la escorrentía acumulada y luego
    obtiene el incremento.

    Args:
        cumulative_rainfall_mm: Array de precipitación acumulada (mm)
        cn: Número de curva
        lambda_coef: Coeficiente λ

    Returns:
        Array de exceso de lluvia incremental (mm)
    """
    # Escorrentía acumulada para cada valor de precipitación acumulada
    cumulative_runoff = scs_runoff(cumulative_rainfall_mm, cn, lambda_coef)

    # Exceso incremental
    excess = np.zeros_like(cumulative_runoff)
    excess[0] = cumulative_runoff[0]
    excess[1:] = np.diff(cumulative_runoff)

    return excess


# ============================================================================
# Método Racional
# ============================================================================

# Factores de ajuste por período de retorno (Cf)
RATIONAL_CF = {
    2: 1.00,
    5: 1.00,
    10: 1.00,
    25: 1.10,
    50: 1.20,
    100: 1.25,
}


def rational_peak_flow(
    c: float,
    intensity_mmhr: float,
    area_ha: float,
    return_period_yr: int = 10,
) -> float:
    """
    Calcula caudal pico usando método racional.

    Q = 0.00278 × Cf × C × i × A  [Q: m³/s, i: mm/hr, A: ha]

    Args:
        c: Coeficiente de escorrentía (0-1)
        intensity_mmhr: Intensidad de lluvia en mm/hr
        area_ha: Área de la cuenca en hectáreas
        return_period_yr: Período de retorno en años

    Returns:
        Caudal pico en m³/s
    """
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")
    if intensity_mmhr <= 0:
        raise ValueError("Intensidad debe ser > 0")
    if area_ha <= 0:
        raise ValueError("Área debe ser > 0")

    # Obtener factor Cf
    cf = RATIONAL_CF.get(return_period_yr, 1.0)
    if return_period_yr > 100:
        cf = 1.25

    # Asegurar que Cf × C ≤ 1.0
    c_effective = min(cf * c, 1.0)

    # Q = 0.00278 × C × i × A
    Q = 0.00278 * c_effective * intensity_mmhr * area_ha

    return Q


def composite_c(
    areas: list[float],
    cs: list[float],
) -> float:
    """
    Calcula coeficiente C compuesto para cuenca con múltiples coberturas.

    C_compuesto = Σ(Cᵢ × Aᵢ) / Σ(Aᵢ)

    Args:
        areas: Lista de áreas parciales
        cs: Lista de coeficientes C para cada área

    Returns:
        Coeficiente C compuesto
    """
    if len(areas) != len(cs):
        raise ValueError("Las listas de áreas y C deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("Área total no puede ser cero")

    weighted_sum = sum(a * c for a, c in zip(areas, cs))
    return weighted_sum / total_area


# Coeficientes de escorrentía típicos (HEC-22)
RATIONAL_C = {
    "downtown_commercial": (0.70, 0.95),
    "neighborhood_commercial": (0.50, 0.70),
    "residential_single_family": (0.30, 0.50),
    "residential_multi_units": (0.40, 0.60),
    "residential_apartments": (0.60, 0.75),
    "industrial_light": (0.50, 0.80),
    "industrial_heavy": (0.60, 0.90),
    "parks_cemeteries": (0.10, 0.25),
    "playgrounds": (0.20, 0.35),
    "railroad_yards": (0.20, 0.40),
    "asphalt": (0.70, 0.95),
    "concrete": (0.80, 0.95),
    "brick": (0.70, 0.85),
    "roofs": (0.75, 0.95),
    "lawns_sandy_flat": (0.05, 0.10),
    "lawns_sandy_steep": (0.15, 0.20),
    "lawns_clay_flat": (0.13, 0.17),
    "lawns_clay_steep": (0.25, 0.35),
}


def get_rational_c(
    land_use: str,
    condition: str = "average",
) -> float:
    """
    Obtiene coeficiente C desde tablas HEC-22.

    Args:
        land_use: Tipo de uso de suelo
        condition: 'low', 'average', o 'high'

    Returns:
        Coeficiente de escorrentía C
    """
    if land_use not in RATIONAL_C:
        raise ValueError(f"Uso de suelo desconocido: {land_use}")

    c_low, c_high = RATIONAL_C[land_use]

    if condition == "low":
        return c_low
    elif condition == "high":
        return c_high
    else:  # average
        return (c_low + c_high) / 2
