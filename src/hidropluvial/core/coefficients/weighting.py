"""
Funciones de ponderación de coeficientes por área.

Calcula coeficientes C y CN ponderados para cuencas
con múltiples tipos de cobertura.
"""


def weighted_c(areas: list[float], coefficients: list[float]) -> float:
    """
    Calcula coeficiente C ponderado por area.

    Args:
        areas: Lista de areas en cualquier unidad (m2, ha, etc.)
        coefficients: Lista de coeficientes C correspondientes

    Returns:
        Coeficiente C ponderado
    """
    if len(areas) != len(coefficients):
        raise ValueError("Las listas de areas y coeficientes deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("El area total no puede ser cero")

    weighted_sum = sum(a * c for a, c in zip(areas, coefficients))
    return weighted_sum / total_area


def weighted_cn(areas: list[float], cn_values: list[int]) -> float:
    """
    Calcula Curva Numero CN ponderada por area.

    Args:
        areas: Lista de areas en cualquier unidad
        cn_values: Lista de valores CN correspondientes

    Returns:
        CN ponderado
    """
    if len(areas) != len(cn_values):
        raise ValueError("Las listas de areas y CN deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("El area total no puede ser cero")

    weighted_sum = sum(a * cn for a, cn in zip(areas, cn_values))
    return weighted_sum / total_area
