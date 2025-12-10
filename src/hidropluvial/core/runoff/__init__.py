"""
Módulo de cálculo de escorrentía.

Implementa métodos para calcular escorrentía superficial:
- Método Racional
- Método SCS Curve Number (CN)
"""

# Infiltración
from .infiltration import (
    MINIMUM_INFILTRATION_RATE,
    get_minimum_infiltration_rate,
)

# SCS-CN
from .scs import (
    scs_potential_retention,
    scs_initial_abstraction,
    scs_runoff,
    adjust_cn_for_amc,
    composite_cn,
    get_cn_from_table,
    calculate_scs_runoff,
    rainfall_excess_series,
)

# Método Racional
from .rational import (
    RATIONAL_C,
    rational_peak_flow,
    composite_c,
    get_rational_c,
)

__all__ = [
    # Infiltración
    "MINIMUM_INFILTRATION_RATE",
    "get_minimum_infiltration_rate",
    # SCS-CN
    "scs_potential_retention",
    "scs_initial_abstraction",
    "scs_runoff",
    "adjust_cn_for_amc",
    "composite_cn",
    "get_cn_from_table",
    "calculate_scs_runoff",
    "rainfall_excess_series",
    # Racional
    "RATIONAL_C",
    "rational_peak_flow",
    "composite_c",
    "get_rational_c",
]
