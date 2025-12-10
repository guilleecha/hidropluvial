"""
Modelo de cuenca hidrológica (Basin).

Representa una cuenca física con todos sus cálculos de Tc y análisis de crecidas.
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import Field, BaseModel

from hidropluvial.models.base import TimestampedModel
from hidropluvial.models.coverage import WeightedCoefficient
from hidropluvial.models.tc import TcResult
from hidropluvial.models.analysis import AnalysisRun
from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment

# Tipo unión para segmentos NRCS
NRCSSegment = Union[SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment]


class NRCSTemplate(BaseModel):
    """
    Template de configuración NRCS (segmentos de flujo).

    Permite guardar y reutilizar configuraciones de segmentos NRCS
    con un nombre descriptivo.
    """

    id: Optional[int] = None
    basin_id: str
    name: str
    p2_mm: float = 50.0
    segments: list[NRCSSegment] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def to_tc_parameters(self) -> dict:
        """
        Convierte el template a parámetros para guardar en tc.parameters.

        Returns:
            Dict con p2_mm, segments serializados, template_name y template_id
        """
        return {
            "p2_mm": self.p2_mm,
            "segments": [seg.model_dump() for seg in self.segments],
            "template_name": self.name,
            "template_id": self.id,
        }

    @classmethod
    def from_tc_parameters(cls, params: dict, basin_id: str) -> "NRCSTemplate":
        """
        Crea un template desde parámetros de tc.

        Args:
            params: Dict de tc.parameters
            basin_id: ID de la cuenca

        Returns:
            NRCSTemplate con los segmentos deserializados
        """
        from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment

        segments = []
        for seg_dict in params.get("segments", []):
            seg_type = seg_dict.get("type", "")
            if seg_type == "sheet":
                segments.append(SheetFlowSegment(**seg_dict))
            elif seg_type == "shallow":
                segments.append(ShallowFlowSegment(**seg_dict))
            elif seg_type == "channel":
                segments.append(ChannelFlowSegment(**seg_dict))

        return cls(
            id=params.get("template_id"),
            basin_id=basin_id,
            name=params.get("template_name", "Custom"),
            p2_mm=params.get("p2_mm", 50.0),
            segments=segments,
        )


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
    nrcs_segments: list[NRCSSegment] = Field(default_factory=list)  # Legacy, usar templates
    nrcs_templates: list["NRCSTemplate"] = Field(default_factory=list)  # Templates nombrados

    # Resultados
    tc_results: list[TcResult] = Field(default_factory=list)
    analyses: list[AnalysisRun] = Field(default_factory=list)

    # Metadatos
    notes: Optional[str] = None

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
