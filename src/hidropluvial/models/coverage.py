"""
Modelos para coeficientes de cobertura y ponderación.
"""

from typing import Optional

from pydantic import BaseModel, Field


class CoverageItem(BaseModel):
    """Un ítem de cobertura para ponderación de C o CN."""

    description: str  # Descripción de la cobertura
    area_ha: float  # Área en hectáreas
    value: float  # Valor de C o CN para esta cobertura (Tr base)
    percentage: float = 0.0  # Porcentaje del área total
    # Para recálculo por Tr (tabla Ven Te Chow)
    table_index: Optional[int] = None  # Índice en la tabla original


class WeightedCoefficient(BaseModel):
    """Coeficiente ponderado (C o CN) con detalle de cálculo."""

    type: str  # "c" o "cn"
    table_used: str = ""  # Tabla usada: "chow", "fhwa", "uruguay", "nrcs"
    weighted_value: float  # Valor ponderado resultante (para Tr base)
    items: list[CoverageItem] = Field(default_factory=list)
    # Para tabla Ven Te Chow: permite recalcular C para cualquier Tr
    base_tr: Optional[int] = None  # Tr base (2 para Ven Te Chow)
