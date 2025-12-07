"""
Modelos de datos para HidroPluvial.

Este módulo contiene todos los modelos Pydantic utilizados en la aplicación.
"""

from hidropluvial.models.base import (
    TimestampedModel,
    IdentifiedModel,
    generate_id,
    generate_timestamp,
)
from hidropluvial.models.coverage import CoverageItem, WeightedCoefficient
from hidropluvial.models.tc import TcResult
from hidropluvial.models.storm import StormResult
from hidropluvial.models.hydrograph import HydrographResult
from hidropluvial.models.analysis import AnalysisRun
from hidropluvial.models.basin import Basin
from hidropluvial.models.project import Project

__all__ = [
    # Clases base
    "TimestampedModel",
    "IdentifiedModel",
    "generate_id",
    "generate_timestamp",
    # Cobertura y ponderación
    "CoverageItem",
    "WeightedCoefficient",
    # Resultados individuales
    "TcResult",
    "StormResult",
    "HydrographResult",
    # Análisis completo
    "AnalysisRun",
    # Cuenca y proyecto
    "Basin",
    "Project",
]
