"""
Módulo de datos y tablas de coeficientes.

Provee acceso unificado a tablas de coeficientes del sistema
y (en el futuro) tablas personalizadas de usuario.
"""

from hidropluvial.data.coefficient_loader import (
    CoefficientLoader,
    CoefficientTable,
    CNValue,
    CoverType,
    CValue,
    TableSource,
    TableType,
)

__all__ = [
    "CoefficientLoader",
    "CoefficientTable",
    "CNValue",
    "CoverType",
    "CValue",
    "TableSource",
    "TableType",
]
