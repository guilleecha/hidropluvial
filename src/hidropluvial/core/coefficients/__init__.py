"""
Tablas de coeficientes de escorrentia C y Curva Numero CN.

Fuentes:
- FHWA HEC-22 (Federal Highway Administration)
- Ven Te Chow - Applied Hydrology (Table 5.5.2)
- SCS/NRCS TR-55
"""

# Tipos de datos
from .types import (
    CoefficientEntry,
    ChowCEntry,
    FHWACEntry,
    CNEntry,
)

# Tablas de coeficiente C
from .tables_c import (
    FHWA_C_TABLE,
    VEN_TE_CHOW_C_TABLE,
    C_TABLES,
)

# Tablas de Curva Número
from .tables_cn import (
    SCS_CN_TABLE,
    SCS_CN_URBAN,
    SCS_CN_AGRICULTURAL,
    CN_TABLES,
)

# Funciones de ajuste por período de retorno
from .adjustments import (
    get_c_for_tr_from_table,
    recalculate_weighted_c_for_tr,
    adjust_c_for_tr,
)

# Funciones de ponderación
from .weighting import (
    weighted_c,
    weighted_cn,
)

# Funciones de formato
from .formatting import (
    format_c_table,
    format_cn_table,
)

__all__ = [
    # Tipos
    "CoefficientEntry",
    "ChowCEntry",
    "FHWACEntry",
    "CNEntry",
    # Tablas C
    "FHWA_C_TABLE",
    "VEN_TE_CHOW_C_TABLE",
    "C_TABLES",
    # Tablas CN
    "SCS_CN_TABLE",
    "SCS_CN_URBAN",
    "SCS_CN_AGRICULTURAL",
    "CN_TABLES",
    # Ajuste
    "get_c_for_tr_from_table",
    "recalculate_weighted_c_for_tr",
    "adjust_c_for_tr",
    # Ponderación
    "weighted_c",
    "weighted_cn",
    # Formato
    "format_c_table",
    "format_cn_table",
]
