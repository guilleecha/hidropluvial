"""
Módulo de tiempo de concentración (Tc).

Implementa múltiples métodos para calcular el tiempo de concentración:
- Kirpich (1940)
- NRCS Velocity Method (TR-55)
- Témez (España/Latinoamérica)
- California Culverts Practice
- FAA Formula
- Kinematic Wave
"""

from hidropluvial.config import (
    ChannelFlowSegment,
    ShallowFlowSegment,
    SheetFlowSegment,
    TCSegment,
)


# Constantes para flujo concentrado superficial (shallow flow)
SHALLOW_FLOW_K = {
    "paved": 6.196,      # k = 20.3 ft/s convertido a m/s (×0.3048)
    "unpaved": 4.918,    # k = 16.1 ft/s
    "grassed": 4.572,    # k = 15.0 ft/s
    "short_grass": 2.134,  # k = 7.0 ft/s
}

# Coeficientes de Manning para flujo laminar (sheet flow)
SHEET_FLOW_N = {
    "smooth": 0.011,
    "fallow": 0.05,
    "short_grass": 0.15,
    "dense_grass": 0.24,
    "light_woods": 0.40,
    "dense_woods": 0.80,
}


def kirpich(
    length_m: float,
    slope: float,
    surface_type: str = "natural",
) -> float:
    """
    Calcula Tc usando fórmula Kirpich (1940).

    tc = 0.0195 × L^0.77 × S^(-0.385)  [tc: min, L: m, S: m/m]

    Args:
        length_m: Longitud del cauce principal en metros
        slope: Pendiente media del cauce (m/m)
        surface_type: Tipo de superficie para ajuste
            - 'natural': sin ajuste (×1.0)
            - 'grassy': canales con pasto (×2.0)
            - 'concrete': superficies de concreto/asfalto (×0.4)
            - 'concrete_channel': canales de concreto (×0.2)

    Returns:
        Tiempo de concentración en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")

    # Factores de ajuste
    adjustment_factors = {
        "natural": 1.0,
        "grassy": 2.0,
        "concrete": 0.4,
        "concrete_channel": 0.2,
    }

    factor = adjustment_factors.get(surface_type, 1.0)

    # Fórmula Kirpich (resultado en minutos)
    tc_min = 0.0195 * (length_m ** 0.77) * (slope ** -0.385)
    tc_min *= factor

    return tc_min / 60.0  # Convertir a horas


def nrcs_sheet_flow(
    length_m: float,
    n: float,
    slope: float,
    p2_mm: float,
) -> float:
    """
    Calcula tiempo de viaje para flujo laminar (sheet flow).

    Tt = 0.091 × (n × L)^0.8 / (P2^0.5 × S^0.4)  [Tt: hr, L: m, P2: mm]

    Args:
        length_m: Longitud del flujo laminar (máx ~100m)
        n: Coeficiente de Manning para flujo laminar
        slope: Pendiente (m/m)
        p2_mm: Precipitación de 2 años, 24 horas (mm)

    Returns:
        Tiempo de viaje en horas
    """
    if length_m <= 0 or length_m > 100:
        raise ValueError("Longitud de flujo laminar debe ser 0-100 m")
    if n <= 0:
        raise ValueError("Coeficiente n debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if p2_mm <= 0:
        raise ValueError("P2 debe ser > 0")

    # Convertir P2 de mm a pulgadas para la fórmula original
    p2_in = p2_mm / 25.4
    # Convertir longitud de m a ft
    length_ft = length_m * 3.28084

    # Fórmula TR-55 (resultado en horas)
    tt_hr = 0.007 * ((n * length_ft) ** 0.8) / ((p2_in ** 0.5) * (slope ** 0.4))

    return tt_hr


def nrcs_shallow_flow(
    length_m: float,
    slope: float,
    surface: str = "unpaved",
) -> float:
    """
    Calcula tiempo de viaje para flujo concentrado superficial.

    V = k × S^0.5  [V: m/s, S: m/m]
    Tt = L / (V × 3600)  [Tt: hr]

    Args:
        length_m: Longitud del tramo en metros
        slope: Pendiente (m/m)
        surface: Tipo de superficie ('paved', 'unpaved', 'grassed', 'short_grass')

    Returns:
        Tiempo de viaje en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")

    k = SHALLOW_FLOW_K.get(surface, SHALLOW_FLOW_K["unpaved"])
    velocity = k * (slope ** 0.5)  # m/s

    tt_hr = length_m / (velocity * 3600)
    return tt_hr


def nrcs_channel_flow(
    length_m: float,
    n: float,
    slope: float,
    hydraulic_radius_m: float,
) -> float:
    """
    Calcula tiempo de viaje para flujo en canal usando Manning.

    V = (1/n) × R^(2/3) × S^(1/2)  [V: m/s, R: m, S: m/m]
    Tt = L / (V × 3600)  [Tt: hr]

    Args:
        length_m: Longitud del canal en metros
        n: Coeficiente de Manning del canal
        slope: Pendiente del canal (m/m)
        hydraulic_radius_m: Radio hidráulico (m)

    Returns:
        Tiempo de viaje en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if n <= 0:
        raise ValueError("Coeficiente n debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if hydraulic_radius_m <= 0:
        raise ValueError("Radio hidráulico debe ser > 0")

    velocity = (1 / n) * (hydraulic_radius_m ** (2/3)) * (slope ** 0.5)
    tt_hr = length_m / (velocity * 3600)

    return tt_hr


def nrcs_velocity_method(segments: list[TCSegment], p2_mm: float = 50.0) -> float:
    """
    Calcula Tc total usando método de velocidades NRCS (TR-55).

    Tc = Tt_sheet + Tt_shallow + Tt_channel

    Args:
        segments: Lista de segmentos de flujo
        p2_mm: Precipitación 2 años, 24h para flujo laminar (mm)

    Returns:
        Tiempo de concentración total en horas
    """
    tc_total = 0.0

    for segment in segments:
        if isinstance(segment, SheetFlowSegment):
            p2 = segment.p2_mm if segment.p2_mm else p2_mm
            tc_total += nrcs_sheet_flow(
                segment.length_m, segment.n, segment.slope, p2
            )
        elif isinstance(segment, ShallowFlowSegment):
            tc_total += nrcs_shallow_flow(
                segment.length_m, segment.slope, segment.surface
            )
        elif isinstance(segment, ChannelFlowSegment):
            tc_total += nrcs_channel_flow(
                segment.length_m, segment.n, segment.slope, segment.hydraulic_radius_m
            )

    return tc_total


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


def kinematic_wave(
    length_m: float,
    n: float,
    slope: float,
    intensity_mmhr: float,
    max_iterations: int = 20,
    tolerance: float = 0.01,
) -> float:
    """
    Calcula Tc usando onda cinemática (método iterativo).

    tc = 6.99 × (n × L)^0.6 / (i^0.4 × S^0.3)  [tc: min, L: m, i: mm/hr]

    Args:
        length_m: Longitud del flujo en metros
        n: Coeficiente de Manning
        slope: Pendiente (m/m)
        intensity_mmhr: Intensidad de lluvia inicial (mm/hr)
        max_iterations: Máximo de iteraciones
        tolerance: Tolerancia para convergencia (horas)

    Returns:
        Tiempo de concentración en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if n <= 0:
        raise ValueError("Coeficiente n debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if intensity_mmhr <= 0:
        raise ValueError("Intensidad debe ser > 0")

    # Valor inicial
    i = intensity_mmhr
    tc_prev = 0.0

    for _ in range(max_iterations):
        # Fórmula de onda cinemática (resultado en minutos)
        tc_min = 6.99 * ((n * length_m) ** 0.6) / ((i ** 0.4) * (slope ** 0.3))
        tc_hr = tc_min / 60.0

        if abs(tc_hr - tc_prev) < tolerance:
            return tc_hr

        tc_prev = tc_hr
        # La intensidad podría actualizarse aquí si se tiene curva IDF

    return tc_hr


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
