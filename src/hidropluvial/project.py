"""
Módulo de gestión de proyectos y cuencas hidrológicas.

Estructura jerárquica:
- Project: Contenedor de múltiples cuencas (ej: "Estudio Arroyo XYZ")
- Basin: Una cuenca con sus análisis
"""

import json
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
# Gestor de Proyectos
# ============================================================================

class ProjectManager:
    """Gestiona proyectos y cuencas hidrológicas."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Inicializa el gestor de proyectos.

        Args:
            data_dir: Directorio base para datos.
                     Default: ~/.hidropluvial/
        """
        if data_dir is None:
            data_dir = Path.home() / ".hidropluvial"

        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"

        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _project_path(self, project_id: str) -> Path:
        """Retorna la ruta del archivo de proyecto."""
        return self.projects_dir / f"{project_id}.json"

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
        project = Project(
            name=name,
            description=description,
            author=author,
            location=location,
        )
        self.save_project(project)
        return project

    def save_project(self, project: Project) -> Path:
        """Guarda un proyecto a disco."""
        project.updated_at = datetime.now().isoformat()
        path = self._project_path(project.id)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(), f, indent=2, ensure_ascii=False)

        return path

    def load_project(self, project_id: str) -> Project:
        """Carga un proyecto desde disco."""
        path = self._project_path(project_id)

        if not path.exists():
            raise FileNotFoundError(f"Proyecto no encontrado: {project_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Project.model_validate(data)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Obtiene un proyecto por ID (parcial o completo)."""
        # Buscar por ID exacto o parcial
        for path in self.projects_dir.glob("*.json"):
            if path.stem == project_id or path.stem.startswith(project_id):
                return self.load_project(path.stem)
        return None

    def list_projects(self) -> list[dict]:
        """Lista todos los proyectos disponibles."""
        projects = []
        for path in sorted(
            self.projects_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                project = self.load_project(path.stem)
                projects.append({
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "author": project.author,
                    "n_basins": project.n_basins,
                    "total_analyses": project.total_analyses,
                    "updated_at": project.updated_at,
                })
            except Exception:
                continue
        return projects

    def delete_project(self, project_id: str) -> bool:
        """Elimina un proyecto."""
        project = self.get_project(project_id)
        if project:
            path = self._project_path(project.id)
            path.unlink()
            return True
        return False

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
        basin = Basin(
            name=name,
            area_ha=area_ha,
            slope_pct=slope_pct,
            p3_10=p3_10,
            c=c,
            cn=cn,
            length_m=length_m,
        )
        project.add_basin(basin)
        self.save_project(project)
        return basin

    def update_basin(self, project: Project, basin: Basin) -> None:
        """Actualiza una cuenca en el proyecto."""
        basin.updated_at = datetime.now().isoformat()
        self.save_project(project)

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
        basin.add_tc_result(result)
        self.save_project(project)
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

        analysis = AnalysisRun(
            tc=tc_result,
            storm=storm,
            hydrograph=hydrograph,
        )

        basin.add_analysis(analysis)
        self.save_project(project)
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
