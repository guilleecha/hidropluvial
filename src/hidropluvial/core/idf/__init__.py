"""
Módulo de curvas Intensidad-Duración-Frecuencia (IDF).

Implementa métodos para calcular precipitación e intensidad de lluvia:
- Uruguay/DINAGUA (Rodríguez Fontal 1980) - MÉTODO PRINCIPAL
- Sherman (1931)
- Bernard (Power Law)
- Koutsoyiannis (1998)

La metodología DINAGUA calcula precipitación acumulada P(d,Tr,A) mediante:

    P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)

Donde:
- P₃,₁₀: Precipitación máxima 3h, Tr=10 años (del mapa de isoyetas)
- Cd(d): Factor de corrección por duración
- Ct(Tr): Factor de corrección por período de retorno
- CA(A,d): Factor de corrección por área de cuenca

La intensidad se deriva como I = P / d
"""

# Conversiones base
from .base import (
    depth_from_intensity,
    intensity_from_depth,
)

# Método Uruguay/DINAGUA
from .dinagua import (
    P3_10_URUGUAY,
    UruguayIDFResult,
    dinagua_cd,
    dinagua_ct,
    dinagua_ca,
    dinagua_precipitation,
    dinagua_intensity,
    dinagua_intensity_simple,
    dinagua_depth,
    generate_dinagua_idf_table,
    get_p3_10,
)

# Métodos internacionales
from .international import (
    sherman_intensity,
    bernard_intensity,
    koutsoyiannis_intensity,
)

# Tablas y utilidades
from .tables import (
    generate_idf_table,
    fit_sherman_coefficients,
    get_intensity,
    get_depth,
)

__all__ = [
    # Base
    "depth_from_intensity",
    "intensity_from_depth",
    # DINAGUA
    "P3_10_URUGUAY",
    "UruguayIDFResult",
    "dinagua_cd",
    "dinagua_ct",
    "dinagua_ca",
    "dinagua_precipitation",
    "dinagua_intensity",
    "dinagua_intensity_simple",
    "dinagua_depth",
    "generate_dinagua_idf_table",
    "get_p3_10",
    # International
    "sherman_intensity",
    "bernard_intensity",
    "koutsoyiannis_intensity",
    # Tables
    "generate_idf_table",
    "fit_sherman_coefficients",
    "get_intensity",
    "get_depth",
]
