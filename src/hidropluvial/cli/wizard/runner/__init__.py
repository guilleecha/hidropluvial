"""
Módulo runner - Ejecutores de análisis hidrológicos.

Este paquete contiene:
- AnalysisRunner: Ejecuta análisis completos desde WizardConfig
- AdditionalAnalysisRunner: Agrega análisis a cuencas existentes
- Funciones compartidas para generación de análisis
"""

from .analysis import AnalysisRunner
from .additional import AdditionalAnalysisRunner
from .helpers import get_amc_enum, get_c_for_tr, get_c_for_tr_from_basin
from .generators import (
    get_storm_duration_and_dt,
    generate_hyetograph,
    calculate_runoff,
    create_analysis_results,
)

__all__ = [
    # Clases principales
    "AnalysisRunner",
    "AdditionalAnalysisRunner",
    # Helpers
    "get_amc_enum",
    "get_c_for_tr",
    "get_c_for_tr_from_basin",
    # Generadores
    "get_storm_duration_and_dt",
    "generate_hyetograph",
    "calculate_runoff",
    "create_analysis_results",
]
