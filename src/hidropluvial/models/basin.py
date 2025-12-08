"""
Modelo de cuenca hidrológica (Basin).

Representa una cuenca física con todos sus cálculos de Tc y análisis de crecidas.
"""

from typing import Optional, Union

from pydantic import Field

from hidropluvial.models.base import TimestampedModel
from hidropluvial.models.coverage import WeightedCoefficient
from hidropluvial.models.tc import TcResult
from hidropluvial.models.analysis import AnalysisRun
from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment

# Tipo unión para segmentos NRCS
NRCSSegment = Union[SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment]


class Basin(TimestampedModel):
    """
    Cuenca hidrológica con sus análisis.

    Representa una cuenca física con todos sus cálculos de Tc
    y análisis de crecidas.
    """

    name: str  # Nombre de la cuenca (ej: "Cuenca Alta", "Subcuenca A")

    # Datos físicos de la cuenca
    area_ha: float
    slope_pct: float
    length_m: Optional[float] = None
    p3_10: float  # Precipitación P(3h, Tr=10) en mm

    # Coeficientes de escorrentía
    c: Optional[float] = None  # Coeficiente C (método racional)
    cn: Optional[int] = None  # Curve Number (método SCS)

    # Detalle de ponderación (opcional)
    c_weighted: Optional[WeightedCoefficient] = None
    cn_weighted: Optional[WeightedCoefficient] = None

    # Parámetros NRCS (método de velocidades TR-55)
    p2_mm: Optional[float] = None  # Precipitación 2 años, 24h (mm) para flujo laminar
    nrcs_segments: list[NRCSSegment] = Field(default_factory=list)

    # Resultados
    tc_results: list[TcResult] = Field(default_factory=list)
    analyses: list[AnalysisRun] = Field(default_factory=list)

    # Metadatos
    notes: Optional[str] = None

    @property
    def cuenca(self) -> "Basin":
        """Compatibilidad con código que usa session.cuenca.X."""
        return self

    def get_tc(self, method: str) -> Optional[TcResult]:
        """Obtiene resultado de Tc por método."""
        for tc in self.tc_results:
            if tc.method == method:
                return tc
        return None

    def add_tc_result(self, result: TcResult) -> None:
        """Agrega o actualiza un resultado de Tc."""
        # Eliminar si ya existe
        self.tc_results = [tc for tc in self.tc_results if tc.method != result.method]
        self.tc_results.append(result)
        self.touch()

    def add_analysis(self, analysis: AnalysisRun) -> None:
        """Agrega un análisis a la cuenca."""
        self.analyses.append(analysis)
        self.touch()

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRun]:
        """Obtiene un análisis por ID."""
        for a in self.analyses:
            if a.id == analysis_id or a.id.startswith(analysis_id):
                return a
        return None

    def remove_analysis(self, analysis_id: str) -> bool:
        """Elimina un análisis por ID."""
        for i, a in enumerate(self.analyses):
            if a.id == analysis_id or a.id.startswith(analysis_id):
                self.analyses.pop(i)
                self.touch()
                return True
        return False
