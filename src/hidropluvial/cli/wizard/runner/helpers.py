"""
Funciones auxiliares para los runners de análisis.
"""

from typing import Optional

from hidropluvial.config import AntecedentMoistureCondition
from hidropluvial.core import adjust_c_for_tr, recalculate_weighted_c_for_tr
from hidropluvial.models import Basin, CoverageItem


def get_amc_enum(amc_str: str) -> AntecedentMoistureCondition:
    """Convierte string AMC a enum."""
    if amc_str == "I":
        return AntecedentMoistureCondition.DRY
    elif amc_str == "III":
        return AntecedentMoistureCondition.WET
    return AntecedentMoistureCondition.AVERAGE


def get_c_for_tr(config, tr: int) -> float:
    """
    Obtiene el coeficiente C ajustado para un período de retorno específico.

    Si hay datos de ponderación (tabla Ven Te Chow), recalcula usando
    los valores exactos de la tabla. Si no, usa el factor de ajuste promedio.

    Args:
        config: WizardConfig con los datos de la cuenca
        tr: Período de retorno en años

    Returns:
        Coeficiente C ajustado
    """
    if config.c_weighted_data and config.c_weighted_data.get("table_key") == "chow":
        table_key = config.c_weighted_data["table_key"]
        items_data = config.c_weighted_data["items"]

        items = [
            CoverageItem(
                description=d["description"],
                area_ha=d["area"],
                value=d["c_val"],
                table_index=d["table_index"],
            )
            for d in items_data
        ]

        return recalculate_weighted_c_for_tr(items, tr, table_key)
    else:
        return adjust_c_for_tr(config.c, tr, base_tr=2)


def get_c_for_tr_from_basin(basin: Basin, c_base: float, tr: int) -> float:
    """
    Obtiene el coeficiente C ajustado para un Tr desde datos de cuenca.

    Si la cuenca tiene datos de ponderación (c_weighted), recalcula exacto.
    Si no, usa el factor de ajuste promedio.

    Args:
        basin: Cuenca con datos de ponderación
        c_base: Coeficiente C base
        tr: Período de retorno en años

    Returns:
        Coeficiente C ajustado
    """
    c_weighted = basin.c_weighted

    if c_weighted and c_weighted.table_used == "chow" and c_weighted.items:
        has_indices = all(item.table_index is not None for item in c_weighted.items)
        if has_indices:
            return recalculate_weighted_c_for_tr(
                c_weighted.items, tr, c_weighted.table_used
            )

    return adjust_c_for_tr(c_base, tr, base_tr=2)
