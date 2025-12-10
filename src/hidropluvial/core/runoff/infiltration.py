"""
Tasas de infiltración por grupo hidrológico.

Referencia: HHA - FING UdelaR (2019)
"""

from hidropluvial.config import HydrologicSoilGroup


# Tasa mínima de infiltración fc (mm/h) por grupo hidrológico
# Representa la infiltración a largo plazo cuando el suelo está saturado
MINIMUM_INFILTRATION_RATE = {
    "A": 2.4,   # Suelos con alta infiltración (arena, grava)
    "B": 1.2,   # Suelos con moderada infiltración
    "C": 1.2,   # Suelos con baja infiltración
    "D": 1.2,   # Suelos con muy baja infiltración (arcilla)
}


def get_minimum_infiltration_rate(soil_group: str | HydrologicSoilGroup) -> float:
    """
    Obtiene la tasa mínima de infiltración para un grupo hidrológico.

    Según metodología HHA-FING UdelaR, se debe verificar que el déficit
    (abstracción) en cada intervalo supere esta tasa mínima.

    Args:
        soil_group: Grupo hidrológico (A, B, C, D)

    Returns:
        Tasa mínima de infiltración fc en mm/h
    """
    if isinstance(soil_group, HydrologicSoilGroup):
        key = soil_group.value
    else:
        key = str(soil_group).upper()

    if key not in MINIMUM_INFILTRATION_RATE:
        raise ValueError(f"Grupo hidrológico inválido: {soil_group}")

    return MINIMUM_INFILTRATION_RATE[key]
