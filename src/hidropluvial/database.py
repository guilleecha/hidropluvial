"""
Módulo de base de datos SQLite para HidroPluvial.

NOTA: Este módulo ha sido refactorizado. El código ahora reside en
el paquete `hidropluvial.database`. Este archivo mantiene compatibilidad
con imports existentes redirigiendo al nuevo módulo.

Ver:
- hidropluvial/database/connection.py - Manejo de conexión y esquema
- hidropluvial/database/projects.py - Operaciones de proyectos
- hidropluvial/database/basins.py - Operaciones de cuencas
- hidropluvial/database/analyses.py - Operaciones de análisis
"""

# Re-exportar todo desde el nuevo módulo para mantener compatibilidad
from hidropluvial.database import (
    Database,
    DatabaseConnection,
    ProjectRepository,
    BasinRepository,
    AnalysisRepository,
    get_database,
    reset_database,
)

__all__ = [
    "Database",
    "DatabaseConnection",
    "ProjectRepository",
    "BasinRepository",
    "AnalysisRepository",
    "get_database",
    "reset_database",
]
