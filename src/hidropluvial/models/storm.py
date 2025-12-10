"""
Modelo para resultados de tormenta de diseño.
"""

from typing import Optional
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
    # Parámetros bimodales (solo para type="bimodal")
    bimodal_peak1: Optional[float] = None  # Posición primer pico (0-1)
    bimodal_peak2: Optional[float] = None  # Posición segundo pico (0-1)
    bimodal_vol_split: Optional[float] = None  # División de volumen (0-1)
    bimodal_peak_width: Optional[float] = None  # Ancho de picos (0-1)
