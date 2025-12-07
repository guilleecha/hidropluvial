"""
Modelo para resultados de hidrograma.
"""

from typing import Optional

from pydantic import BaseModel, Field


class HydrographResult(BaseModel):
    """Resultado de cálculo de hidrograma."""

    tc_method: str
    tc_min: float
    storm_type: str
    return_period: int
    x_factor: Optional[float] = None
    peak_flow_m3s: float
    time_to_peak_hr: float  # Tp - tiempo pico del hidrograma resultante
    time_to_peak_min: float
    tp_unit_hr: Optional[float] = None  # tp - tiempo pico del HU (ΔD/2 + 0.6×Tc)
    tp_unit_min: Optional[float] = None
    tb_hr: Optional[float] = None  # tb - tiempo base del HU (2.67×tp)
    tb_min: Optional[float] = None
    volume_m3: float
    total_depth_mm: float
    runoff_mm: float
    # Series temporales para gráficos
    time_hr: list[float] = Field(default_factory=list)
    flow_m3s: list[float] = Field(default_factory=list)
