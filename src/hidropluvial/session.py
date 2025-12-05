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

class CoverageItem(BaseModel):
    """Un ítem de cobertura para ponderación de C o CN."""
    description: str           # Descripción de la cobertura
    area_ha: float             # Área en hectáreas
    value: float               # Valor de C o CN para esta cobertura (Tr base)
    percentage: float = 0.0    # Porcentaje del área total
    # Para recálculo por Tr (tabla Ven Te Chow)
    table_index: Optional[int] = None  # Índice en la tabla original


class WeightedCoefficient(BaseModel):
    """Coeficiente ponderado (C o CN) con detalle de cálculo."""
    type: str                  # "c" o "cn"
    table_used: str = ""       # Tabla usada: "chow", "fhwa", "uruguay", "nrcs"
    weighted_value: float      # Valor ponderado resultante (para Tr base)
    items: list[CoverageItem] = Field(default_factory=list)
    # Para tabla Ven Te Chow: permite recalcular C para cualquier Tr
    base_tr: Optional[int] = None  # Tr base (2 para Ven Te Chow)


class CuencaConfig(BaseModel):
    """Configuración de una cuenca hidrológica."""
    nombre: str = ""
    area_ha: float
    length_m: Optional[float] = None
    slope_pct: float
    c: Optional[float] = None  # Coeficiente de escorrentía
    cn: Optional[int] = None   # Curve Number (SCS)
    p3_10: float               # Precipitación P3,10 en mm
    # Detalle de ponderación (opcional)
    c_weighted: Optional[WeightedCoefficient] = None
    cn_weighted: Optional[WeightedCoefficient] = None


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
    # Comentario opcional para este análisis
    note: Optional[str] = None


class Session(BaseModel):
    """Sesión de análisis hidrológico."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    cuenca: CuencaConfig
    tc_results: list[TcResult] = Field(default_factory=list)
    analyses: list[AnalysisRun] = Field(default_factory=list)
    # Notas generales de la sesión
    notes: Optional[str] = None


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

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Obtiene una sesión por ID (parcial o completo).

        Args:
            session_id: ID de sesión (mínimo 8 caracteres)

        Returns:
            Session o None si no existe
        """
        # Buscar por ID exacto primero
        path = self._session_path(session_id)
        if path.exists():
            return self.load(session_id)

        # Buscar por ID parcial
        for p in self.sessions_dir.glob("*.json"):
            if p.stem.startswith(session_id):
                return self.load(p.stem)

        return None

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

    def clone_with_modified_cuenca(
        self,
        session: Session,
        new_name: Optional[str] = None,
        area_ha: Optional[float] = None,
        slope_pct: Optional[float] = None,
        p3_10: Optional[float] = None,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length_m: Optional[float] = None,
    ) -> Session:
        """
        Crea una nueva sesión clonando los datos base pero con parámetros modificados.

        Los análisis NO se copian porque fueron calculados con los datos originales.
        Los métodos de Tc tampoco se copian porque dependen de los parámetros.

        Args:
            session: Sesión original a clonar
            new_name: Nuevo nombre (default: "{nombre} (modificado)")
            area_ha: Nueva área (None = mantener original)
            slope_pct: Nueva pendiente (None = mantener original)
            p3_10: Nuevo P3,10 (None = mantener original)
            c: Nuevo C (None = mantener original)
            cn: Nuevo CN (None = mantener original)
            length_m: Nueva longitud (None = mantener original)

        Returns:
            Nueva sesión con datos modificados (sin análisis)
        """
        # Determinar qué cambió
        original = session.cuenca
        changes = []

        final_area = area_ha if area_ha is not None else original.area_ha
        if area_ha is not None and area_ha != original.area_ha:
            changes.append(f"area: {original.area_ha} → {area_ha} ha")

        final_slope = slope_pct if slope_pct is not None else original.slope_pct
        if slope_pct is not None and slope_pct != original.slope_pct:
            changes.append(f"pendiente: {original.slope_pct} → {slope_pct}%")

        final_p3_10 = p3_10 if p3_10 is not None else original.p3_10
        if p3_10 is not None and p3_10 != original.p3_10:
            changes.append(f"P3,10: {original.p3_10} → {p3_10} mm")

        final_c = c if c is not None else original.c
        if c is not None and c != original.c:
            changes.append(f"C: {original.c} → {c}")

        final_cn = cn if cn is not None else original.cn
        if cn is not None and cn != original.cn:
            changes.append(f"CN: {original.cn} → {cn}")

        final_length = length_m if length_m is not None else original.length_m
        if length_m is not None and length_m != original.length_m:
            changes.append(f"longitud: {original.length_m} → {length_m} m")

        # Crear nueva sesión
        if new_name is None:
            new_name = f"{session.name} (modificado)"

        new_session = self.create(
            name=new_name,
            area_ha=final_area,
            slope_pct=final_slope,
            p3_10=final_p3_10,
            c=final_c,
            cn=final_cn,
            length_m=final_length,
            cuenca_nombre=original.nombre,
        )

        return new_session, changes

    def update_cuenca_in_place(
        self,
        session: Session,
        area_ha: Optional[float] = None,
        slope_pct: Optional[float] = None,
        p3_10: Optional[float] = None,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length_m: Optional[float] = None,
        clear_analyses: bool = True,
    ) -> list[str]:
        """
        Actualiza los datos de la cuenca en la sesión existente.

        ADVERTENCIA: Si hay análisis, estos quedan invalidados porque
        fueron calculados con los datos anteriores.

        Args:
            session: Sesión a modificar
            area_ha: Nueva área (None = mantener original)
            slope_pct: Nueva pendiente (None = mantener original)
            p3_10: Nuevo P3,10 (None = mantener original)
            c: Nuevo C (None = mantener original)
            cn: Nuevo CN (None = mantener original)
            length_m: Nueva longitud (None = mantener original)
            clear_analyses: Si True, elimina análisis existentes

        Returns:
            Lista de cambios realizados
        """
        original = session.cuenca
        changes = []

        if area_ha is not None and area_ha != original.area_ha:
            changes.append(f"area: {original.area_ha} → {area_ha} ha")
            session.cuenca.area_ha = area_ha

        if slope_pct is not None and slope_pct != original.slope_pct:
            changes.append(f"pendiente: {original.slope_pct} → {slope_pct}%")
            session.cuenca.slope_pct = slope_pct

        if p3_10 is not None and p3_10 != original.p3_10:
            changes.append(f"P3,10: {original.p3_10} → {p3_10} mm")
            session.cuenca.p3_10 = p3_10

        if c is not None and c != original.c:
            changes.append(f"C: {original.c} → {c}")
            session.cuenca.c = c

        if cn is not None and cn != original.cn:
            changes.append(f"CN: {original.cn} → {cn}")
            session.cuenca.cn = cn

        if length_m is not None and length_m != original.length_m:
            changes.append(f"longitud: {original.length_m} → {length_m} m")
            session.cuenca.length_m = length_m

        if changes:
            # Limpiar resultados de Tc (dependen de los parámetros)
            session.tc_results = []

            if clear_analyses:
                n_analyses = len(session.analyses)
                if n_analyses > 0:
                    changes.append(f"eliminados {n_analyses} análisis (datos obsoletos)")
                session.analyses = []

            self.save(session)

        return changes

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

    def set_weighted_coefficient(
        self,
        session: Session,
        weighted_coef: "WeightedCoefficient",
    ) -> None:
        """
        Actualiza el coeficiente ponderado (C o CN) de la cuenca.

        Args:
            session: Sesión a modificar
            weighted_coef: Datos de ponderación
        """
        if weighted_coef.type == "cn":
            session.cuenca.cn = int(round(weighted_coef.weighted_value))
            session.cuenca.cn_weighted = weighted_coef
        elif weighted_coef.type == "c":
            session.cuenca.c = weighted_coef.weighted_value
            session.cuenca.c_weighted = weighted_coef

        self.save(session)

    def set_session_notes(self, session: Session, notes: Optional[str]) -> None:
        """
        Establece las notas generales de la sesión.

        Args:
            session: Sesión a modificar
            notes: Notas (None o string vacío para eliminar)
        """
        session.notes = notes if notes and notes.strip() else None
        self.save(session)

    def set_analysis_note(
        self,
        session: Session,
        analysis_id: str,
        note: Optional[str],
    ) -> bool:
        """
        Establece la nota de un análisis específico.

        Args:
            session: Sesión que contiene el análisis
            analysis_id: ID del análisis
            note: Nota (None o string vacío para eliminar)

        Returns:
            True si se encontró y actualizó el análisis
        """
        for analysis in session.analyses:
            if analysis.id == analysis_id:
                analysis.note = note if note and note.strip() else None
                self.save(session)
                return True
        return False

    def get_analyses_with_notes(self, session: Session) -> list[AnalysisRun]:
        """
        Retorna los análisis que tienen notas.

        Args:
            session: Sesión

        Returns:
            Lista de análisis con notas
        """
        return [a for a in session.analyses if a.note]
