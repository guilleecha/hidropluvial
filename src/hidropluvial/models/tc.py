"""
Modelo para resultados de tiempo de concentración.
"""

from pydantic import BaseModel, Field


class TcResult(BaseModel):
    """Resultado de cálculo de tiempo de concentración."""

    method: str
    tc_hr: float
    tc_min: float
    parameters: dict = Field(default_factory=dict)
