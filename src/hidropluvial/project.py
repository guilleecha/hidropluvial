"""
Módulo de gestión de proyectos y cuencas hidrológicas.

Este módulo proporciona una interfaz de alto nivel sobre la base de datos SQLite.
Mantiene compatibilidad con la API anterior para no romper código existente.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from hidropluvial.models import (
    Basin,
    Project,
    TcResult,
    StormResult,
    HydrographResult,
    AnalysisRun,
)


# ============================================================================
# Gestor de Proyectos (usa Database internamente)
# ============================================================================

class ProjectManager:
    """
    Gestiona proyectos y cuencas hidrológicas.

    Esta clase es un adaptador sobre la base de datos SQLite.
    Mantiene la misma API que la versión anterior para compatibilidad.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Inicializa el gestor de proyectos.

        Args:
            data_dir: Si se especifica, usa una base de datos en ese directorio.
                     Si es None, usa la base de datos global.
        """
        from hidropluvial.database import Database, get_database
        if data_dir is not None:
            # Usar una base de datos específica en ese directorio
            db_path = Path(data_dir) / "hidropluvial.db"
            self._db = Database(db_path)
        else:
            self._db = get_database()

    # ========================================================================
    # Operaciones de Proyecto
    # ========================================================================

    def create_project(
        self,
        name: str,
        description: str = "",
        author: str = "",
        location: str = "",
    ) -> Project:
        """Crea un nuevo proyecto vacío."""
        return self._db.create_project_model(
            name=name,
            description=description,
            author=author,
            location=location,
        )

    def save_project(self, project: Project) -> Path:
        """Guarda cambios de un proyecto."""
        self._db.save_project_model(project)
        # Retornar path ficticio para compatibilidad
        return Path.home() / ".hidropluvial" / "hidropluvial.db"

    def load_project(self, project_id: str) -> Project:
        """Carga un proyecto desde la base de datos."""
        project = self._db.get_project_model(project_id)
        if project is None:
            raise FileNotFoundError(f"Proyecto no encontrado: {project_id}")
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Obtiene un proyecto por ID (parcial o completo)."""
        return self._db.get_project_model(project_id)

    def list_projects(self) -> list[dict]:
        """Lista todos los proyectos disponibles."""
        return self._db.list_projects()

    def delete_project(self, project_id: str) -> bool:
        """Elimina un proyecto."""
        return self._db.delete_project(project_id)

    # ========================================================================
    # Operaciones de Cuenca (Basin)
    # ========================================================================

    def create_basin(
        self,
        project: Project,
        name: str,
        area_ha: float,
        slope_pct: float,
        p3_10: float,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length_m: Optional[float] = None,
    ) -> Basin:
        """Crea una nueva cuenca y la agrega al proyecto."""
        basin = self._db.create_basin_model(
            project_id=project.id,
            name=name,
            area_ha=area_ha,
            slope_pct=slope_pct,
            p3_10=p3_10,
            c=c,
            cn=cn,
            length_m=length_m,
        )
        # Agregar al modelo en memoria
        project.add_basin(basin)
        return basin

    def update_basin(self, project: Project, basin: Basin) -> None:
        """Actualiza una cuenca en el proyecto."""
        self._db.update_basin(
            basin_id=basin.id,
            name=basin.name,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            length_m=basin.length_m,
            p3_10=basin.p3_10,
            c=basin.c,
            cn=basin.cn,
            c_weighted=basin.c_weighted,
            cn_weighted=basin.cn_weighted,
            notes=basin.notes,
        )

    def add_tc_result(
        self,
        project: Project,
        basin: Basin,
        method: str,
        tc_hr: float,
        **parameters,
    ) -> TcResult:
        """Agrega un resultado de Tc a una cuenca."""
        result = TcResult(
            method=method,
            tc_hr=tc_hr,
            tc_min=tc_hr * 60,
            parameters=parameters,
        )
        # Guardar en DB
        self._db.add_tc_result(basin.id, method, tc_hr, parameters)
        # Agregar al modelo en memoria
        basin.add_tc_result(result)
        return result

    def add_analysis(
        self,
        project: Project,
        basin: Basin,
        tc_method: str,
        tc_hr: float,
        storm_type: str,
        return_period: int,
        duration_hr: float,
        total_depth_mm: float,
        peak_intensity_mmhr: float,
        n_intervals: int,
        peak_flow_m3s: float,
        time_to_peak_hr: float,
        volume_m3: float,
        runoff_mm: float,
        x_factor: Optional[float] = None,
        tp_unit_hr: Optional[float] = None,
        storm_time_min: list[float] = None,
        storm_intensity_mmhr: list[float] = None,
        hydrograph_time_hr: list[float] = None,
        hydrograph_flow_m3s: list[float] = None,
        **tc_params,
    ) -> AnalysisRun:
        """Agrega un análisis completo a una cuenca."""
        tc_result = TcResult(
            method=tc_method,
            tc_hr=tc_hr,
            tc_min=tc_hr * 60,
            parameters=tc_params,
        )

        storm = StormResult(
            type=storm_type,
            return_period=return_period,
            duration_hr=duration_hr,
            total_depth_mm=total_depth_mm,
            peak_intensity_mmhr=peak_intensity_mmhr,
            n_intervals=n_intervals,
            time_min=storm_time_min or [],
            intensity_mmhr=storm_intensity_mmhr or [],
        )

        # Calcular tb (tiempo base) = 2.67 × tp
        tb_hr = 2.67 * tp_unit_hr if tp_unit_hr else None

        hydrograph = HydrographResult(
            tc_method=tc_method,
            tc_min=tc_hr * 60,
            storm_type=storm_type,
            return_period=return_period,
            x_factor=x_factor,
            peak_flow_m3s=peak_flow_m3s,
            time_to_peak_hr=time_to_peak_hr,
            time_to_peak_min=time_to_peak_hr * 60,
            tp_unit_hr=tp_unit_hr,
            tp_unit_min=tp_unit_hr * 60 if tp_unit_hr else None,
            tb_hr=tb_hr,
            tb_min=tb_hr * 60 if tb_hr else None,
            volume_m3=volume_m3,
            total_depth_mm=total_depth_mm,
            runoff_mm=runoff_mm,
            time_hr=hydrograph_time_hr or [],
            flow_m3s=hydrograph_flow_m3s or [],
        )

        # Guardar en DB
        analysis = self._db.add_analysis_model(
            basin_id=basin.id,
            tc=tc_result,
            storm=storm,
            hydrograph=hydrograph,
        )

        # Agregar al modelo en memoria
        basin.add_analysis(analysis)
        return analysis


# ============================================================================
# Función de conveniencia para obtener el manager global
# ============================================================================

_project_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """Retorna el gestor de proyectos global."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager
