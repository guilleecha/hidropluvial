"""
Modelo para resultados de tormenta de diseño.
"""

from pydantic import BaseModel, Field


class StormResult(BaseModel):
    """Resultado de generación de tormenta."""

    type: str
    return_period: int
    duration_hr: float
    total_depth_mm: float
    peak_intensity_mmhr: float
    n_intervals: int
    # Series temporales para gráficos
    time_min: list[float] = Field(default_factory=list)
    intensity_mmhr: list[float] = Field(default_factory=list)
