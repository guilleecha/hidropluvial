"""
Módulo de gestión de proyectos y cuencas hidrológicas.

Estructura jerárquica:
- Project: Contenedor de múltiples cuencas (ej: "Estudio Arroyo XYZ")
- Basin: Una cuenca con sus análisis (antes "Session")

Mantiene compatibilidad con sesiones existentes mediante migración automática.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from hidropluvial.session import (
    CuencaConfig,
    TcResult,
    AnalysisRun,
    CoverageItem,
    WeightedCoefficient,
    Session,  # Para migración
)


# ============================================================================
# Modelos de Datos
# ============================================================================

class Basin(BaseModel):
    """
    Cuenca hidrológica con sus análisis.

    Equivalente mejorado de Session, representa una cuenca física
    con todos sus cálculos de Tc y análisis de crecidas.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str  # Nombre de la cuenca (ej: "Cuenca Alta", "Subcuenca A")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Datos físicos de la cuenca
    area_ha: float
    slope_pct: float
    length_m: Optional[float] = None
    p3_10: float  # Precipitación P(3h, Tr=10) en mm

    # Coeficientes de escorrentía
    c: Optional[float] = None  # Coeficiente C (método racional)
    cn: Optional[int] = None   # Curve Number (método SCS)

    # Detalle de ponderación (opcional)
    c_weighted: Optional[WeightedCoefficient] = None
    cn_weighted: Optional[WeightedCoefficient] = None

    # Resultados
    tc_results: list[TcResult] = Field(default_factory=list)
    analyses: list[AnalysisRun] = Field(default_factory=list)

    # Metadatos
    notes: Optional[str] = None

    @classmethod
    def from_session(cls, session: Session) -> "Basin":
        """Convierte una Session legacy a Basin."""
        return cls(
            id=session.id,
            name=session.cuenca.nombre or session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            area_ha=session.cuenca.area_ha,
            slope_pct=session.cuenca.slope_pct,
            length_m=session.cuenca.length_m,
            p3_10=session.cuenca.p3_10,
            c=session.cuenca.c,
            cn=session.cuenca.cn,
            c_weighted=session.cuenca.c_weighted,
            cn_weighted=session.cuenca.cn_weighted,
            tc_results=session.tc_results,
            analyses=session.analyses,
            notes=session.notes,
        )

    def to_session(self) -> Session:
        """Convierte Basin a Session (compatibilidad hacia atrás)."""
        cuenca = CuencaConfig(
            nombre=self.name,
            area_ha=self.area_ha,
            slope_pct=self.slope_pct,
            length_m=self.length_m,
            p3_10=self.p3_10,
            c=self.c,
            cn=self.cn,
            c_weighted=self.c_weighted,
            cn_weighted=self.cn_weighted,
        )
        return Session(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            updated_at=self.updated_at,
            cuenca=cuenca,
            tc_results=self.tc_results,
            analyses=self.analyses,
            notes=self.notes,
        )

    @property
    def cuenca(self) -> CuencaConfig:
        """Compatibilidad: retorna CuencaConfig para código legacy."""
        return CuencaConfig(
            nombre=self.name,
            area_ha=self.area_ha,
            slope_pct=self.slope_pct,
            length_m=self.length_m,
            p3_10=self.p3_10,
            c=self.c,
            cn=self.cn,
            c_weighted=self.c_weighted,
            cn_weighted=self.cn_weighted,
        )


class Project(BaseModel):
    """
    Proyecto hidrológico que agrupa múltiples cuencas.

    Representa un estudio completo (ej: "Estudio de Drenaje Pluvial Barrio X")
    que puede contener varias cuencas a analizar.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str  # Nombre del proyecto
    description: str = ""  # Descripción del proyecto
    author: str = ""  # Autor/responsable
    location: str = ""  # Ubicación geográfica
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

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
        self.updated_at = datetime.now().isoformat()
        return basin

    def remove_basin(self, basin_id: str) -> bool:
        """Elimina una cuenca del proyecto."""
        for i, basin in enumerate(self.basins):
            if basin.id == basin_id or basin.id.startswith(basin_id):
                self.basins.pop(i)
                self.updated_at = datetime.now().isoformat()
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
        self.sessions_dir = self.data_dir / "sessions"  # Legacy

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
        for path in sorted(self.projects_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
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
        # Evitar duplicados
        for existing in basin.tc_results:
            if existing.method == method:
                basin.tc_results.remove(existing)
                break

        result = TcResult(
            method=method,
            tc_hr=tc_hr,
            tc_min=tc_hr * 60,
            parameters=parameters,
        )
        basin.tc_results.append(result)
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
        from hidropluvial.session import StormResult, HydrographResult

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

        basin.analyses.append(analysis)
        self.save_project(project)
        return analysis

    # ========================================================================
    # Migración de Sesiones Legacy
    # ========================================================================

    def migrate_sessions_to_project(
        self,
        project_name: str = "Proyecto Migrado",
        delete_sessions: bool = False,
    ) -> Optional[Project]:
        """
        Migra todas las sesiones existentes a un nuevo proyecto.

        Args:
            project_name: Nombre para el nuevo proyecto
            delete_sessions: Si True, elimina las sesiones originales

        Returns:
            Proyecto creado con las cuencas migradas, o None si no hay sesiones
        """
        if not self.sessions_dir.exists():
            return None

        session_files = list(self.sessions_dir.glob("*.json"))
        if not session_files:
            return None

        # Crear proyecto
        project = self.create_project(
            name=project_name,
            description="Proyecto creado por migración de sesiones existentes",
        )

        # Migrar cada sesión
        for path in session_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                session = Session.model_validate(data)
                basin = Basin.from_session(session)
                project.add_basin(basin)

                if delete_sessions:
                    path.unlink()

            except Exception as e:
                print(f"Error migrando {path.name}: {e}")
                continue

        self.save_project(project)
        return project

    def import_session_as_basin(
        self,
        project: Project,
        session_id: str,
    ) -> Optional[Basin]:
        """
        Importa una sesión legacy como cuenca en un proyecto existente.

        Args:
            project: Proyecto destino
            session_id: ID de la sesión a importar

        Returns:
            Basin creado, o None si la sesión no existe
        """
        session_path = self.sessions_dir / f"{session_id}.json"

        if not session_path.exists():
            # Buscar por ID parcial
            for path in self.sessions_dir.glob("*.json"):
                if path.stem.startswith(session_id):
                    session_path = path
                    break
            else:
                return None

        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        session = Session.model_validate(data)
        basin = Basin.from_session(session)
        project.add_basin(basin)
        self.save_project(project)

        return basin


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
