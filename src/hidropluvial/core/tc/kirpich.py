"""
Método Kirpich (1940) para tiempo de concentración.

Desarrollado para pequeñas cuencas agrícolas en Tennessee.
"""


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
