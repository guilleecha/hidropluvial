"""
Módulo de gestión de sesiones de análisis hidrológico.

Permite crear, guardar y cargar sesiones con múltiples análisis
para una cuenca, facilitando comparaciones entre métodos.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Modelos de Datos
# ============================================================================

class CuencaConfig(BaseModel):
    """Configuración de una cuenca hidrológica."""
    nombre: str = ""
    area_ha: float
    length_m: Optional[float] = None
    slope_pct: float
    c: Optional[float] = None  # Coeficiente de escorrentía
    cn: Optional[int] = None   # Curve Number (SCS)
    p3_10: float               # Precipitación P3,10 en mm


class TcResult(BaseModel):
    """Resultado de cálculo de tiempo de concentración."""
    method: str
    tc_hr: float
    tc_min: float
    parameters: dict = Field(default_factory=dict)


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


class HydrographResult(BaseModel):
    """Resultado de cálculo de hidrograma."""
    tc_method: str
    tc_min: float
    storm_type: str
    return_period: int
    x_factor: Optional[float] = None
    peak_flow_m3s: float
    time_to_peak_hr: float
    time_to_peak_min: float
    volume_m3: float
    total_depth_mm: float
    runoff_mm: float
    # Series temporales para gráficos
    time_hr: list[float] = Field(default_factory=list)
    flow_m3s: list[float] = Field(default_factory=list)


class AnalysisRun(BaseModel):
    """Un análisis completo (Tc + Tormenta + Hidrograma)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tc: TcResult
    storm: StormResult
    hydrograph: HydrographResult


class Session(BaseModel):
    """Sesión de análisis hidrológico."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    cuenca: CuencaConfig
    tc_results: list[TcResult] = Field(default_factory=list)
    analyses: list[AnalysisRun] = Field(default_factory=list)


# ============================================================================
# Gestor de Sesiones
# ============================================================================

class SessionManager:
    """Gestiona sesiones de análisis hidrológico."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Inicializa el gestor de sesiones.

        Args:
            sessions_dir: Directorio para guardar sesiones.
                         Default: ~/.hidropluvial/sessions/
        """
        if sessions_dir is None:
            sessions_dir = Path.home() / ".hidropluvial" / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """Retorna la ruta del archivo de sesión."""
        return self.sessions_dir / f"{session_id}.json"

    def create(
        self,
        name: str,
        area_ha: float,
        slope_pct: float,
        p3_10: float,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length_m: Optional[float] = None,
        cuenca_nombre: str = "",
    ) -> Session:
        """
        Crea una nueva sesión.

        Args:
            name: Nombre de la sesión
            area_ha: Área de la cuenca en hectáreas
            slope_pct: Pendiente media en %
            p3_10: Precipitación P3,10 en mm
            c: Coeficiente de escorrentía (opcional)
            cn: Curve Number SCS (opcional)
            length_m: Longitud del cauce en metros (opcional)
            cuenca_nombre: Nombre descriptivo de la cuenca

        Returns:
            Session creada
        """
        cuenca = CuencaConfig(
            nombre=cuenca_nombre or name,
            area_ha=area_ha,
            length_m=length_m,
            slope_pct=slope_pct,
            c=c,
            cn=cn,
            p3_10=p3_10,
        )

        session = Session(name=name, cuenca=cuenca)
        self.save(session)
        return session

    def save(self, session: Session) -> Path:
        """Guarda una sesión a disco."""
        session.updated_at = datetime.now().isoformat()
        path = self._session_path(session.id)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, indent=2, ensure_ascii=False)

        return path

    def load(self, session_id: str) -> Session:
        """Carga una sesión desde disco."""
        path = self._session_path(session_id)

        if not path.exists():
            raise FileNotFoundError(f"Sesión no encontrada: {session_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Session(**data)

    def load_by_name(self, name: str) -> Session:
        """Carga una sesión por nombre."""
        for path in self.sessions_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("name") == name:
                return Session(**data)

        raise FileNotFoundError(f"Sesión no encontrada: {name}")

    def find(self, name_or_id: str) -> Session:
        """Busca una sesión por nombre o ID."""
        # Primero intentar por ID
        path = self._session_path(name_or_id)
        if path.exists():
            return self.load(name_or_id)

        # Luego por nombre
        return self.load_by_name(name_or_id)

    def list_sessions(self) -> list[dict]:
        """Lista todas las sesiones disponibles."""
        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "id": data["id"],
                "name": data["name"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "cuenca": data["cuenca"]["nombre"],
                "n_analyses": len(data.get("analyses", [])),
            })
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    def delete(self, session_id: str) -> bool:
        """Elimina una sesión."""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def add_tc_result(
        self,
        session: Session,
        method: str,
        tc_hr: float,
        **parameters,
    ) -> TcResult:
        """Agrega un resultado de Tc a la sesión."""
        result = TcResult(
            method=method,
            tc_hr=tc_hr,
            tc_min=tc_hr * 60,
            parameters=parameters,
        )

        # Evitar duplicados
        existing = [r for r in session.tc_results if r.method != method]
        existing.append(result)
        session.tc_results = existing

        self.save(session)
        return result

    def add_analysis(
        self,
        session: Session,
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
        storm_time_min: Optional[list[float]] = None,
        storm_intensity_mmhr: Optional[list[float]] = None,
        hydrograph_time_hr: Optional[list[float]] = None,
        hydrograph_flow_m3s: Optional[list[float]] = None,
        **tc_params,
    ) -> AnalysisRun:
        """Agrega un análisis completo a la sesión."""
        tc = TcResult(
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

        hydrograph = HydrographResult(
            tc_method=tc_method,
            tc_min=tc_hr * 60,
            storm_type=storm_type,
            return_period=return_period,
            x_factor=x_factor,
            peak_flow_m3s=peak_flow_m3s,
            time_to_peak_hr=time_to_peak_hr,
            time_to_peak_min=time_to_peak_hr * 60,
            volume_m3=volume_m3,
            total_depth_mm=total_depth_mm,
            runoff_mm=runoff_mm,
            time_hr=hydrograph_time_hr or [],
            flow_m3s=hydrograph_flow_m3s or [],
        )

        analysis = AnalysisRun(tc=tc, storm=storm, hydrograph=hydrograph)
        session.analyses.append(analysis)

        self.save(session)
        return analysis

    def get_summary_table(self, session: Session) -> list[dict]:
        """Genera tabla resumen de todos los análisis."""
        rows = []
        for a in session.analyses:
            rows.append({
                "id": a.id,
                "tc_method": a.tc.method,
                "tc_min": a.tc.tc_min,
                "storm": a.storm.type,
                "tr": a.storm.return_period,
                "x": a.hydrograph.x_factor,
                "depth_mm": a.storm.total_depth_mm,
                "runoff_mm": a.hydrograph.runoff_mm,
                "qpeak_m3s": a.hydrograph.peak_flow_m3s,
                "tp_min": a.hydrograph.time_to_peak_min,
                "vol_m3": a.hydrograph.volume_m3,
            })
        return rows
