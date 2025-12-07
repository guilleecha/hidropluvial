"""
Clases base para modelos Pydantic.

Proporciona funcionalidad común para modelos con ID y timestamps.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


def generate_id() -> str:
    """Genera un ID corto único (8 caracteres)."""
    return str(uuid.uuid4())[:8]


def generate_timestamp() -> str:
    """Genera timestamp ISO actual."""
    return datetime.now().isoformat()


class TimestampedModel(BaseModel):
    """
    Modelo base con ID y timestamps automáticos.

    Proporciona:
    - id: ID único de 8 caracteres
    - created_at: Timestamp de creación
    - updated_at: Timestamp de última actualización
    """

    id: str = Field(default_factory=generate_id)
    created_at: str = Field(default_factory=generate_timestamp)
    updated_at: str = Field(default_factory=generate_timestamp)

    def touch(self) -> None:
        """Actualiza el timestamp de modificación."""
        self.updated_at = generate_timestamp()


class IdentifiedModel(BaseModel):
    """
    Modelo base solo con ID y timestamp de creación.

    Útil para modelos inmutables como análisis.
    """

    id: str = Field(default_factory=generate_id)
    timestamp: str = Field(default_factory=generate_timestamp)
