"""
Módulo de base de datos SQLite para HidroPluvial.

Proporciona persistencia eficiente para proyectos, cuencas y análisis
con soporte para búsquedas y consultas rápidas.

Este módulo expone la clase Database que mantiene compatibilidad con
la API anterior, delegando internamente a los repositorios especializados.
"""

from pathlib import Path
from typing import Optional

from hidropluvial.database.connection import DatabaseConnection
from hidropluvial.database.projects import ProjectRepository
from hidropluvial.database.basins import BasinRepository
from hidropluvial.database.analyses import AnalysisRepository

from hidropluvial.models import (
    TcResult,
    StormResult,
    HydrographResult,
    WeightedCoefficient,
)


class Database:
    """
    Gestor de base de datos SQLite para HidroPluvial.

    Esta clase proporciona una fachada sobre los repositorios especializados
    manteniendo compatibilidad con la API anterior.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa la conexión a la base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Default: ~/.hidropluvial/hidropluvial.db
        """
        self._conn = DatabaseConnection(db_path)
        self._projects = ProjectRepository(self._conn)
        self._basins = BasinRepository(self._conn)
        self._analyses = AnalysisRepository(self._conn)

    @property
    def db_path(self) -> Path:
        """Ruta al archivo de base de datos."""
        return self._conn.db_path

    def connection(self):
        """Context manager para conexiones a la base de datos."""
        return self._conn.connection()

    # ========================================================================
    # Operaciones de Proyecto
    # ========================================================================

    def create_project(
        self,
        name: str,
        description: str = "",
        author: str = "",
        location: str = "",
        notes: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """Crea un nuevo proyecto."""
        return self._projects.create(name, description, author, location, notes, tags)

    def get_project(self, project_id: str) -> Optional[dict]:
        """Obtiene un proyecto por ID (parcial o completo)."""
        return self._projects.get(project_id)

    def list_projects(self) -> list[dict]:
        """Lista todos los proyectos con resumen."""
        return self._projects.list_all()

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """Actualiza un proyecto existente."""
        return self._projects.update(project_id, name, description, author, location, notes, tags)

    def delete_project(self, project_id: str) -> bool:
        """Elimina un proyecto y todas sus cuencas."""
        return self._projects.delete(project_id)

    # ========================================================================
    # Operaciones de Cuenca (Basin)
    # ========================================================================

    def create_basin(
        self,
        project_id: str,
        name: str,
        area_ha: float,
        slope_pct: float,
        p3_10: float,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length_m: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Crea una nueva cuenca en un proyecto."""
        return self._basins.create(project_id, name, area_ha, slope_pct, p3_10, c, cn, length_m, notes)

    def get_basin(self, basin_id: str) -> Optional[dict]:
        """Obtiene una cuenca por ID con todos sus datos."""
        return self._basins.get(basin_id)

    def get_project_basins(self, project_id: str) -> list[dict]:
        """Obtiene todas las cuencas de un proyecto."""
        return self._basins.get_by_project(project_id)

    def update_basin(
        self,
        basin_id: str,
        name: Optional[str] = None,
        area_ha: Optional[float] = None,
        slope_pct: Optional[float] = None,
        length_m: Optional[float] = None,
        p3_10: Optional[float] = None,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        c_weighted: Optional[WeightedCoefficient] = None,
        cn_weighted: Optional[WeightedCoefficient] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Actualiza una cuenca existente."""
        return self._basins.update(basin_id, name, area_ha, slope_pct, length_m, p3_10, c, cn, c_weighted, cn_weighted, notes)

    def delete_basin(self, basin_id: str) -> bool:
        """Elimina una cuenca y todos sus análisis."""
        return self._basins.delete(basin_id)

    # ========================================================================
    # Operaciones de Tc
    # ========================================================================

    def add_tc_result(
        self,
        basin_id: str,
        method: str,
        tc_hr: float,
        parameters: Optional[dict] = None,
    ) -> dict:
        """Agrega o actualiza un resultado de Tc."""
        return self._basins.add_tc_result(basin_id, method, tc_hr, parameters)

    def get_tc_results(self, basin_id: str) -> list[dict]:
        """Obtiene todos los resultados de Tc de una cuenca."""
        return self._basins.get_tc_results(basin_id)

    def clear_tc_results(self, basin_id: str) -> int:
        """Elimina todos los resultados de Tc de una cuenca."""
        return self._basins.clear_tc_results(basin_id)

    # ========================================================================
    # Operaciones de Análisis
    # ========================================================================

    def add_analysis(
        self,
        basin_id: str,
        tc: TcResult,
        storm: StormResult,
        hydrograph: HydrographResult,
        note: Optional[str] = None,
    ) -> dict:
        """Agrega un análisis completo a una cuenca."""
        return self._analyses.add(basin_id, tc, storm, hydrograph, note)

    def get_analysis(self, analysis_id: str) -> Optional[dict]:
        """Obtiene un análisis por ID con sus series temporales."""
        return self._analyses.get(analysis_id)

    def get_basin_analyses(self, basin_id: str) -> list[dict]:
        """Obtiene todos los análisis de una cuenca."""
        return self._analyses.get_by_basin(basin_id)

    def get_analysis_summary(self, basin_id: str) -> list[dict]:
        """Obtiene resumen de análisis sin series temporales (más rápido)."""
        return self._analyses.get_summary(basin_id)

    def update_analysis_note(self, analysis_id: str, note: Optional[str]) -> bool:
        """Actualiza la nota de un análisis."""
        return self._analyses.update_note(analysis_id, note)

    def delete_analysis(self, analysis_id: str) -> bool:
        """Elimina un análisis."""
        return self._analyses.delete(analysis_id)

    def clear_basin_analyses(self, basin_id: str) -> int:
        """Elimina todos los análisis de una cuenca."""
        return self._analyses.clear_by_basin(basin_id)

    # ========================================================================
    # Consultas y Estadísticas
    # ========================================================================

    def get_stats(self) -> dict:
        """Obtiene estadísticas generales de la base de datos."""
        with self._conn.connection() as conn:
            stats = {}

            cursor = conn.execute("SELECT COUNT(*) FROM projects")
            stats["n_projects"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM basins")
            stats["n_basins"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM analyses")
            stats["n_analyses"] = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT SUM(LENGTH(time_min) + LENGTH(intensity_mmhr)) FROM storm_timeseries"
            )
            storm_size = cursor.fetchone()[0] or 0

            cursor = conn.execute(
                "SELECT SUM(LENGTH(time_hr) + LENGTH(flow_m3s)) FROM hydrograph_timeseries"
            )
            hydro_size = cursor.fetchone()[0] or 0

            stats["timeseries_bytes"] = storm_size + hydro_size
            stats["db_size_bytes"] = self.db_path.stat().st_size if self.db_path.exists() else 0

            return stats

    def search_basins(
        self,
        name: Optional[str] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        has_cn: Optional[bool] = None,
        has_c: Optional[bool] = None,
    ) -> list[dict]:
        """Busca cuencas con filtros."""
        return self._basins.search(name, min_area, max_area, has_cn, has_c)

    def search_analyses(
        self,
        storm_type: Optional[str] = None,
        return_period: Optional[int] = None,
        min_peak_flow: Optional[float] = None,
        max_peak_flow: Optional[float] = None,
    ) -> list[dict]:
        """Busca análisis con filtros."""
        return self._analyses.search(storm_type, return_period, min_peak_flow, max_peak_flow)


# ============================================================================
# Función de conveniencia para obtener la instancia global
# ============================================================================

_database: Optional[Database] = None


def get_database() -> Database:
    """Retorna la instancia global de la base de datos."""
    global _database
    if _database is None:
        _database = Database()
    return _database


def reset_database() -> None:
    """Reinicia la instancia global (útil para tests)."""
    global _database
    _database = None


# Exportar las clases principales
__all__ = [
    "Database",
    "DatabaseConnection",
    "ProjectRepository",
    "BasinRepository",
    "AnalysisRepository",
    "get_database",
    "reset_database",
]
