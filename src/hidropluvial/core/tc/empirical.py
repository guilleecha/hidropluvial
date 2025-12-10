"""
Métodos empíricos para tiempo de concentración.

Incluye:
- Témez (España/Latinoamérica)
- California Culverts Practice
- FAA Formula
- Desbordes (DINAGUA Uruguay)
"""


def temez(length_km: float, slope: float) -> float:
    """
    Calcula Tc usando fórmula Témez (España/Latinoamérica).

    tc = 0.3 × (L / S^0.25)^0.76  [tc: hr, L: km, S: m/m]

    Válido para cuencas de 1-3000 km².

    Args:
        length_km: Longitud del cauce principal en km
        slope: Pendiente media (m/m)

    Returns:
        Tiempo de concentración en horas
    """
    if length_km <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")

    tc_hr = 0.3 * ((length_km / (slope ** 0.25)) ** 0.76)
    return tc_hr


def california_culverts(length_km: float, elevation_diff_m: float) -> float:
    """
    Calcula Tc usando fórmula California Culverts Practice.

    tc = 60 × (11.9 × L³ / H)^0.385  [tc: min, L: mi, H: ft]

    Args:
        length_km: Longitud del cauce en km
        elevation_diff_m: Diferencia de elevación (m)

    Returns:
        Tiempo de concentración en horas
    """
    if length_km <= 0:
        raise ValueError("Longitud debe ser > 0")
    if elevation_diff_m <= 0:
        raise ValueError("Diferencia de elevación debe ser > 0")

    # Convertir unidades
    length_mi = length_km * 0.621371
    h_ft = elevation_diff_m * 3.28084

    tc_min = 60 * ((11.9 * (length_mi ** 3) / h_ft) ** 0.385)
    return tc_min / 60.0


def faa_formula(length_m: float, slope_pct: float, c: float) -> float:
    """
    Calcula Tc usando fórmula FAA.

    tc = 1.8 × (1.1 - C) × L^0.5 / S^0.333  [tc: min, L: ft, S: %]

    Args:
        length_m: Longitud del flujo en metros
        slope_pct: Pendiente en porcentaje (%)
        c: Coeficiente de escorrentía (método racional)

    Returns:
        Tiempo de concentración en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope_pct <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")

    length_ft = length_m * 3.28084
    tc_min = 1.8 * (1.1 - c) * (length_ft ** 0.5) / (slope_pct ** 0.333)

    return tc_min / 60.0


def desbordes(
    area_ha: float,
    slope_pct: float,
    c: float,
    t0_min: float = 5.0,
) -> float:
    """
    Calcula Tc usando Método de los Desbordes (DINAGUA Uruguay).

    Tc = T0 + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)  [Tc: min]

    Recomendado en el "Manual de Diseño para Sistemas de Drenaje de
    Aguas Pluviales Urbanas" de DINAGUA.

    Args:
        area_ha: Área de la cuenca en hectáreas
        slope_pct: Pendiente media de la cuenca en porcentaje (%)
        c: Coeficiente de escorrentía (método racional, 0-1)
        t0_min: Tiempo de entrada inicial en minutos (default: 5 min)

    Returns:
        Tiempo de concentración en horas
    """
    if area_ha <= 0:
        raise ValueError("Área debe ser > 0")
    if slope_pct <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")
    if t0_min < 0:
        raise ValueError("Tiempo de entrada T0 debe ser >= 0")

    tc_min = t0_min + 6.625 * (area_ha ** 0.3) * (slope_pct ** -0.39) * (c ** -0.45)
    return tc_min / 60.0  # Convertir a horas
