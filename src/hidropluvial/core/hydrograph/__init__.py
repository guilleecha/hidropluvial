"""
Módulo de hidrogramas unitarios sintéticos.

Implementa métodos para generar hidrogramas:
- SCS Triangular Unit Hydrograph
- SCS/NRCS Curvilinear (Dimensionless) Unit Hydrograph
- Snyder Synthetic Unit Hydrograph (1938)
- Clark Unit Hydrograph
- Hidrograma Triangular con Factor X (GZ/Porto)
- Convolución de exceso de lluvia
"""

# Tipos y parámetros base
from .base import (
    HydrographOutput,
    load_uh_data,
    scs_lag_time,
    scs_time_to_peak,
    scs_time_base,
    recommended_dt,
    get_dt_limits,
)

# SCS methods
from .scs import (
    scs_triangular_peak,
    scs_triangular_uh,
    scs_curvilinear_uh,
    gamma_uh,
)

# Triangular con factor X
from .triangular_x import triangular_uh_x

# Snyder
from .snyder import (
    snyder_lag_time,
    snyder_peak,
    snyder_widths,
    snyder_uh,
)

# Clark
from .clark import (
    clark_time_area,
    clark_uh,
)

# Convolution y dispatchers
from .convolution import (
    convolve_uh,
    generate_unit_hydrograph,
    generate_hydrograph,
)

__all__ = [
    # Base
    "HydrographOutput",
    "load_uh_data",
    "scs_lag_time",
    "scs_time_to_peak",
    "scs_time_base",
    "recommended_dt",
    "get_dt_limits",
    # SCS
    "scs_triangular_peak",
    "scs_triangular_uh",
    "scs_curvilinear_uh",
    "gamma_uh",
    # Triangular X
    "triangular_uh_x",
    # Snyder
    "snyder_lag_time",
    "snyder_peak",
    "snyder_widths",
    "snyder_uh",
    # Clark
    "clark_time_area",
    "clark_uh",
    # Convolution
    "convolve_uh",
    "generate_unit_hydrograph",
    "generate_hydrograph",
]
