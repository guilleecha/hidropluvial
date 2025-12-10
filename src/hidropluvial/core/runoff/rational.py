"""
Método Racional para escorrentía.

Calcula caudal pico para cuencas pequeñas usando
la fórmula racional Q = C × i × A.
"""


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


def rational_peak_flow(
    c: float,
    intensity_mmhr: float,
    area_ha: float,
) -> float:
    """
    Calcula caudal pico usando método racional.

    Q = 0.00278 × C × i × A  [Q: m³/s, i: mm/hr, A: ha]

    El coeficiente C debe incluir el ajuste por período de retorno.
    Las tablas de C (ej: Ven Te Chow, DINAGUA) proporcionan valores
    diferentes según el Tr.

    Args:
        c: Coeficiente de escorrentía (0-1), ya ajustado por Tr
        intensity_mmhr: Intensidad de lluvia en mm/hr
        area_ha: Área de la cuenca en hectáreas

    Returns:
        Caudal pico en m³/s
    """
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")
    if intensity_mmhr <= 0:
        raise ValueError("Intensidad debe ser > 0")
    if area_ha <= 0:
        raise ValueError("Área debe ser > 0")

    # Q = 0.00278 × C × i × A
    Q = 0.00278 * c * intensity_mmhr * area_ha

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
