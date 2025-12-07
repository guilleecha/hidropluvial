"""
Modelo de proyecto hidrológico.

Un proyecto agrupa múltiples cuencas (basins) bajo un mismo estudio.
"""

from typing import Optional

from pydantic import Field

from hidropluvial.models.base import TimestampedModel
from hidropluvial.models.basin import Basin


class Project(TimestampedModel):
    """
    Proyecto hidrológico que agrupa múltiples cuencas.

    Representa un estudio completo (ej: "Estudio de Drenaje Pluvial Barrio X")
    que puede contener varias cuencas a analizar.
    """

    name: str  # Nombre del proyecto
    description: str = ""  # Descripción del proyecto
    author: str = ""  # Autor/responsable
    location: str = ""  # Ubicación geográfica

    # Cuencas del proyecto
    basins: list[Basin] = Field(default_factory=list)

    # Metadatos
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    def get_basin(self, basin_id: str) -> Optional[Basin]:
        """Obtiene una cuenca por ID (parcial o completo)."""
        for basin in self.basins:
            if basin.id == basin_id or basin.id.startswith(basin_id):
                return basin
        return None

    def add_basin(self, basin: Basin) -> Basin:
        """Agrega una cuenca al proyecto."""
        self.basins.append(basin)
        self.touch()
        return basin

    def remove_basin(self, basin_id: str) -> bool:
        """Elimina una cuenca del proyecto."""
        for i, basin in enumerate(self.basins):
            if basin.id == basin_id or basin.id.startswith(basin_id):
                self.basins.pop(i)
                self.touch()
                return True
        return False

    @property
    def n_basins(self) -> int:
        """Número de cuencas en el proyecto."""
        return len(self.basins)

    @property
    def total_analyses(self) -> int:
        """Total de análisis en todas las cuencas."""
        return sum(len(b.analyses) for b in self.basins)
