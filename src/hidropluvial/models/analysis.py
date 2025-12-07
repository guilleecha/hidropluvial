"""
Modelo para un análisis completo (Tc + Tormenta + Hidrograma).
"""

from typing import Optional

from hidropluvial.models.base import IdentifiedModel
from hidropluvial.models.tc import TcResult
from hidropluvial.models.storm import StormResult
from hidropluvial.models.hydrograph import HydrographResult


class AnalysisRun(IdentifiedModel):
    """Un análisis completo (Tc + Tormenta + Hidrograma)."""

    tc: TcResult
    storm: StormResult
    hydrograph: HydrographResult
    # Comentario opcional para este análisis
    note: Optional[str] = None
