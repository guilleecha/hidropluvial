"""
Método NRCS/TR-55 para tiempo de concentración.

Incluye componentes para flujo laminar (sheet flow),
flujo concentrado superficial (shallow flow) y flujo en canal.
"""

from hidropluvial.config import (
    ChannelFlowSegment,
    ShallowFlowSegment,
    SheetFlowSegment,
    TCSegment,
)

from .constants import SHALLOW_FLOW_K


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
