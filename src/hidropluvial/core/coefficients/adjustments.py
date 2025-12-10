"""
Funciones de ajuste de coeficientes por período de retorno.

Permite recalcular coeficientes C para diferentes Tr usando
las tablas originales o factores de ajuste promedio.
"""

from .types import ChowCEntry, FHWACEntry
from .tables_c import C_TABLES
from .weighting import weighted_c


def get_c_for_tr_from_table(table_index: int, tr: int, table_key: str = "chow") -> float:
    """
    Obtiene el coeficiente C para un Tr específico desde la tabla original.

    Args:
        table_index: Índice de la entrada en la tabla
        tr: Período de retorno (años)
        table_key: Clave de la tabla ("chow", "fhwa", "uruguay")

    Returns:
        Coeficiente C para el Tr especificado
    """
    if table_key not in C_TABLES:
        raise ValueError(f"Tabla '{table_key}' no disponible")

    _, table_data = C_TABLES[table_key]

    if table_index < 0 or table_index >= len(table_data):
        raise ValueError(f"Índice {table_index} fuera de rango para tabla {table_key}")

    entry = table_data[table_index]

    if isinstance(entry, ChowCEntry):
        return entry.get_c(tr)
    elif isinstance(entry, FHWACEntry):
        return entry.get_c(tr)
    else:
        # CoefficientEntry - no varía con Tr
        return entry.c_recommended


def recalculate_weighted_c_for_tr(
    items: list,  # list[CoverageItem] - evitamos import circular
    tr: int,
    table_key: str = "chow",
) -> float:
    """
    Recalcula el coeficiente C ponderado para un período de retorno específico.

    Usa los índices guardados en cada CoverageItem para obtener el C
    correspondiente al Tr desde la tabla original.

    Args:
        items: Lista de CoverageItem con table_index definido
        tr: Período de retorno objetivo (años)
        table_key: Clave de la tabla usada

    Returns:
        C ponderado para el Tr especificado

    Example:
        >>> # items contiene coberturas con sus índices de tabla
        >>> recalculate_weighted_c_for_tr(items, tr=25, table_key="chow")
        0.45  # C ponderado para Tr=25
    """
    if not items:
        raise ValueError("La lista de coberturas no puede estar vacía")

    areas = []
    coefficients = []

    for item in items:
        if item.table_index is not None:
            # Obtener C desde la tabla para el Tr específico
            c_val = get_c_for_tr_from_table(item.table_index, tr, table_key)
        else:
            # Sin índice de tabla, usar el valor guardado (sin ajuste)
            c_val = item.value

        areas.append(item.area_ha)
        coefficients.append(c_val)

    return weighted_c(areas, coefficients)


def adjust_c_for_tr(c_base: float, tr: int, base_tr: int = 2) -> float:
    """
    Ajusta un coeficiente C base para un período de retorno diferente.

    NOTA: Esta función usa factores promedio y es menos precisa que
    recalculate_weighted_c_for_tr(). Se mantiene para compatibilidad
    con C ingresados manualmente (sin datos de ponderación).

    Args:
        c_base: Coeficiente C para el período de retorno base
        tr: Período de retorno objetivo (años)
        base_tr: Período de retorno del C base (default: 2 años)

    Returns:
        C ajustado para el Tr objetivo (máximo 1.0)
    """
    if tr == base_tr:
        return c_base

    # Factores promedio derivados de la tabla Ven Te Chow
    # (menos preciso que usar la tabla directamente)
    tr_factors = {
        2: 1.00,
        5: 1.17,
        10: 1.33,
        25: 1.50,
        50: 1.66,
        100: 1.84,
    }

    tr_values = sorted(tr_factors.keys())

    def get_factor(t: int) -> float:
        if t <= tr_values[0]:
            return tr_factors[tr_values[0]]
        if t >= tr_values[-1]:
            return tr_factors[tr_values[-1]]

        # Interpolar
        for i in range(len(tr_values) - 1):
            if tr_values[i] <= t <= tr_values[i + 1]:
                t1, t2 = tr_values[i], tr_values[i + 1]
                f1 = tr_factors[t1]
                f2 = tr_factors[t2]
                return f1 + (f2 - f1) * (t - t1) / (t2 - t1)

        return 1.0

    factor_base = get_factor(base_tr)
    factor_target = get_factor(tr)

    # Ajustar C manteniendo la proporción
    c_adjusted = c_base * (factor_target / factor_base)

    # C no puede exceder 1.0
    return min(c_adjusted, 1.0)
