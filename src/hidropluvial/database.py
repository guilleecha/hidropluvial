"""
Módulo de base de datos SQLite para HidroPluvial.

Proporciona persistencia eficiente para proyectos, cuencas y análisis
con soporte para búsquedas y consultas rápidas.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterator, Any

from pydantic import BaseModel

from hidropluvial.session import (
    TcResult,
    StormResult,
    HydrographResult,
    AnalysisRun,
    WeightedCoefficient,
    CoverageItem,
)


# ============================================================================
# Esquema de la Base de Datos
# ============================================================================

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Tabla de proyectos
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    author TEXT DEFAULT '',
    location TEXT DEFAULT '',
    notes TEXT,
    tags TEXT,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tabla de cuencas (basins)
CREATE TABLE IF NOT EXISTS basins (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    area_ha REAL NOT NULL,
    slope_pct REAL NOT NULL,
    length_m REAL,
    p3_10 REAL NOT NULL,
    c REAL,
    cn INTEGER,
    c_weighted TEXT,  -- JSON WeightedCoefficient
    cn_weighted TEXT,  -- JSON WeightedCoefficient
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Tabla de resultados de tiempo de concentración
CREATE TABLE IF NOT EXISTS tc_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basin_id TEXT NOT NULL,
    method TEXT NOT NULL,
    tc_hr REAL NOT NULL,
    tc_min REAL NOT NULL,
    parameters TEXT,  -- JSON dict
    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE,
    UNIQUE (basin_id, method)
);

-- Tabla de análisis
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    basin_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT,
    -- Tc info
    tc_method TEXT NOT NULL,
    tc_hr REAL NOT NULL,
    tc_min REAL NOT NULL,
    tc_parameters TEXT,  -- JSON dict
    -- Storm info
    storm_type TEXT NOT NULL,
    return_period INTEGER NOT NULL,
    duration_hr REAL NOT NULL,
    total_depth_mm REAL NOT NULL,
    peak_intensity_mmhr REAL NOT NULL,
    n_intervals INTEGER NOT NULL,
    -- Hydrograph info
    x_factor REAL,
    peak_flow_m3s REAL NOT NULL,
    time_to_peak_hr REAL NOT NULL,
    time_to_peak_min REAL NOT NULL,
    tp_unit_hr REAL,
    tp_unit_min REAL,
    tb_hr REAL,
    tb_min REAL,
    volume_m3 REAL NOT NULL,
    runoff_mm REAL NOT NULL,
    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE
);

-- Tabla de series temporales de tormentas
CREATE TABLE IF NOT EXISTS storm_timeseries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL,
    time_min TEXT NOT NULL,  -- JSON array
    intensity_mmhr TEXT NOT NULL,  -- JSON array
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    UNIQUE (analysis_id)
);

-- Tabla de series temporales de hidrogramas
CREATE TABLE IF NOT EXISTS hydrograph_timeseries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL,
    time_hr TEXT NOT NULL,  -- JSON array
    flow_m3s TEXT NOT NULL,  -- JSON array
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    UNIQUE (analysis_id)
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_basins_project ON basins(project_id);
CREATE INDEX IF NOT EXISTS idx_tc_results_basin ON tc_results(basin_id);
CREATE INDEX IF NOT EXISTS idx_analyses_basin ON analyses(basin_id);
CREATE INDEX IF NOT EXISTS idx_analyses_storm ON analyses(storm_type, return_period);
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Tabla de metadatos
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# ============================================================================
# Clase Database
# ============================================================================

class Database:
    """Gestor de base de datos SQLite para HidroPluvial."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa la conexión a la base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Default: ~/.hidropluvial/hidropluvial.db
        """
        if db_path is None:
            db_path = Path.home() / ".hidropluvial" / "hidropluvial.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self) -> None:
        """Inicializa el esquema de la base de datos."""
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)

            # Verificar/establecer versión del esquema
            cursor = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            )
            row = cursor.fetchone()

            if row is None:
                conn.execute(
                    "INSERT INTO metadata (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION))
                )
            # Aquí se agregarían migraciones si cambia el esquema

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager para conexiones a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, author, location,
                                      notes, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, name, description, author, location,
                 notes, json.dumps(tags or []), now, now)
            )

        return {
            "id": project_id,
            "name": name,
            "description": description,
            "author": author,
            "location": location,
            "notes": notes,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }

    def get_project(self, project_id: str) -> Optional[dict]:
        """Obtiene un proyecto por ID (parcial o completo)."""
        with self.connection() as conn:
            # Buscar por ID exacto o parcial
            cursor = conn.execute(
                "SELECT * FROM projects WHERE id = ? OR id LIKE ?",
                (project_id, f"{project_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_project(row)

    def _row_to_project(self, row: sqlite3.Row) -> dict:
        """Convierte una fila de la BD a diccionario de proyecto."""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "author": row["author"],
            "location": row["location"],
            "notes": row["notes"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_projects(self) -> list[dict]:
        """Lista todos los proyectos con resumen."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                SELECT p.*,
                       COUNT(DISTINCT b.id) as n_basins,
                       COUNT(a.id) as total_analyses
                FROM projects p
                LEFT JOIN basins b ON b.project_id = p.id
                LEFT JOIN analyses a ON a.basin_id = b.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            )

            projects = []
            for row in cursor:
                project = self._row_to_project(row)
                project["n_basins"] = row["n_basins"]
                project["total_analyses"] = row["total_analyses"]
                projects.append(project)

            return projects

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
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if author is not None:
            updates.append("author = ?")
            params.append(author)
        if location is not None:
            updates.append("location = ?")
            params.append(location)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(project_id)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                params
            )
            return cursor.rowcount > 0

    def delete_project(self, project_id: str) -> bool:
        """Elimina un proyecto y todas sus cuencas."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM projects WHERE id = ? OR id LIKE ?",
                (project_id, f"{project_id}%")
            )
            return cursor.rowcount > 0

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
        basin_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO basins (id, project_id, name, area_ha, slope_pct,
                                   length_m, p3_10, c, cn, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (basin_id, project_id, name, area_ha, slope_pct,
                 length_m, p3_10, c, cn, notes, now, now)
            )

            # Actualizar timestamp del proyecto
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, project_id)
            )

        return {
            "id": basin_id,
            "project_id": project_id,
            "name": name,
            "area_ha": area_ha,
            "slope_pct": slope_pct,
            "length_m": length_m,
            "p3_10": p3_10,
            "c": c,
            "cn": cn,
            "c_weighted": None,
            "cn_weighted": None,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
            "tc_results": [],
            "analyses": [],
        }

    def get_basin(self, basin_id: str) -> Optional[dict]:
        """Obtiene una cuenca por ID con todos sus datos."""
        with self.connection() as conn:
            # Obtener cuenca
            cursor = conn.execute(
                "SELECT * FROM basins WHERE id = ? OR id LIKE ?",
                (basin_id, f"{basin_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            basin = self._row_to_basin(row)

            # Obtener resultados de Tc
            cursor = conn.execute(
                "SELECT * FROM tc_results WHERE basin_id = ?",
                (basin["id"],)
            )
            basin["tc_results"] = [
                self._row_to_tc_result(r) for r in cursor
            ]

            # Obtener análisis
            basin["analyses"] = self.get_basin_analyses(basin["id"])

            return basin

    def _row_to_basin(self, row: sqlite3.Row) -> dict:
        """Convierte una fila de la BD a diccionario de cuenca."""
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "name": row["name"],
            "area_ha": row["area_ha"],
            "slope_pct": row["slope_pct"],
            "length_m": row["length_m"],
            "p3_10": row["p3_10"],
            "c": row["c"],
            "cn": row["cn"],
            "c_weighted": json.loads(row["c_weighted"]) if row["c_weighted"] else None,
            "cn_weighted": json.loads(row["cn_weighted"]) if row["cn_weighted"] else None,
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_tc_result(self, row: sqlite3.Row) -> dict:
        """Convierte una fila de Tc a diccionario."""
        return {
            "method": row["method"],
            "tc_hr": row["tc_hr"],
            "tc_min": row["tc_min"],
            "parameters": json.loads(row["parameters"]) if row["parameters"] else {},
        }

    def get_project_basins(self, project_id: str) -> list[dict]:
        """Obtiene todas las cuencas de un proyecto."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                SELECT b.*, COUNT(a.id) as n_analyses
                FROM basins b
                LEFT JOIN analyses a ON a.basin_id = b.id
                WHERE b.project_id = ?
                GROUP BY b.id
                ORDER BY b.created_at
                """,
                (project_id,)
            )

            basins = []
            for row in cursor:
                basin = self._row_to_basin(row)
                basin["n_analyses"] = row["n_analyses"]
                basins.append(basin)

            return basins

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
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if area_ha is not None:
            updates.append("area_ha = ?")
            params.append(area_ha)
        if slope_pct is not None:
            updates.append("slope_pct = ?")
            params.append(slope_pct)
        if length_m is not None:
            updates.append("length_m = ?")
            params.append(length_m)
        if p3_10 is not None:
            updates.append("p3_10 = ?")
            params.append(p3_10)
        if c is not None:
            updates.append("c = ?")
            params.append(c)
        if cn is not None:
            updates.append("cn = ?")
            params.append(cn)
        if c_weighted is not None:
            updates.append("c_weighted = ?")
            params.append(c_weighted.model_dump_json() if isinstance(c_weighted, BaseModel) else json.dumps(c_weighted))
        if cn_weighted is not None:
            updates.append("cn_weighted = ?")
            params.append(cn_weighted.model_dump_json() if isinstance(cn_weighted, BaseModel) else json.dumps(cn_weighted))
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(basin_id)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE basins SET {', '.join(updates)} WHERE id = ?",
                params
            )

            if cursor.rowcount > 0:
                # Actualizar proyecto padre
                conn.execute(
                    """
                    UPDATE projects SET updated_at = ?
                    WHERE id = (SELECT project_id FROM basins WHERE id = ?)
                    """,
                    (datetime.now().isoformat(), basin_id)
                )

            return cursor.rowcount > 0

    def delete_basin(self, basin_id: str) -> bool:
        """Elimina una cuenca y todos sus análisis."""
        with self.connection() as conn:
            # Obtener proyecto para actualizar timestamp
            cursor = conn.execute(
                "SELECT project_id FROM basins WHERE id = ?",
                (basin_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return False

            project_id = row["project_id"]

            cursor = conn.execute(
                "DELETE FROM basins WHERE id = ?",
                (basin_id,)
            )

            if cursor.rowcount > 0:
                conn.execute(
                    "UPDATE projects SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), project_id)
                )

            return cursor.rowcount > 0

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
        with self.connection() as conn:
            # Usar REPLACE para actualizar si ya existe el método
            conn.execute(
                """
                INSERT OR REPLACE INTO tc_results (basin_id, method, tc_hr, tc_min, parameters)
                VALUES (?, ?, ?, ?, ?)
                """,
                (basin_id, method, tc_hr, tc_hr * 60, json.dumps(parameters or {}))
            )

            # Actualizar timestamp de la cuenca
            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), basin_id)
            )

        return {
            "method": method,
            "tc_hr": tc_hr,
            "tc_min": tc_hr * 60,
            "parameters": parameters or {},
        }

    def get_tc_results(self, basin_id: str) -> list[dict]:
        """Obtiene todos los resultados de Tc de una cuenca."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tc_results WHERE basin_id = ?",
                (basin_id,)
            )
            return [self._row_to_tc_result(r) for r in cursor]

    def clear_tc_results(self, basin_id: str) -> int:
        """Elimina todos los resultados de Tc de una cuenca."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tc_results WHERE basin_id = ?",
                (basin_id,)
            )
            return cursor.rowcount

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
        analysis_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        with self.connection() as conn:
            # Insertar análisis principal
            conn.execute(
                """
                INSERT INTO analyses (
                    id, basin_id, timestamp, note,
                    tc_method, tc_hr, tc_min, tc_parameters,
                    storm_type, return_period, duration_hr, total_depth_mm,
                    peak_intensity_mmhr, n_intervals,
                    x_factor, peak_flow_m3s, time_to_peak_hr, time_to_peak_min,
                    tp_unit_hr, tp_unit_min, tb_hr, tb_min, volume_m3, runoff_mm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id, basin_id, timestamp, note,
                    tc.method, tc.tc_hr, tc.tc_min, json.dumps(tc.parameters),
                    storm.type, storm.return_period, storm.duration_hr, storm.total_depth_mm,
                    storm.peak_intensity_mmhr, storm.n_intervals,
                    hydrograph.x_factor, hydrograph.peak_flow_m3s,
                    hydrograph.time_to_peak_hr, hydrograph.time_to_peak_min,
                    hydrograph.tp_unit_hr, hydrograph.tp_unit_min,
                    hydrograph.tb_hr, hydrograph.tb_min,
                    hydrograph.volume_m3, hydrograph.runoff_mm,
                )
            )

            # Insertar series temporales de tormenta
            if storm.time_min and storm.intensity_mmhr:
                conn.execute(
                    """
                    INSERT INTO storm_timeseries (analysis_id, time_min, intensity_mmhr)
                    VALUES (?, ?, ?)
                    """,
                    (analysis_id, json.dumps(storm.time_min), json.dumps(storm.intensity_mmhr))
                )

            # Insertar series temporales de hidrograma
            if hydrograph.time_hr and hydrograph.flow_m3s:
                conn.execute(
                    """
                    INSERT INTO hydrograph_timeseries (analysis_id, time_hr, flow_m3s)
                    VALUES (?, ?, ?)
                    """,
                    (analysis_id, json.dumps(hydrograph.time_hr), json.dumps(hydrograph.flow_m3s))
                )

            # Actualizar timestamp de la cuenca
            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (timestamp, basin_id)
            )

        return {
            "id": analysis_id,
            "timestamp": timestamp,
            "tc": tc.model_dump(),
            "storm": storm.model_dump(),
            "hydrograph": hydrograph.model_dump(),
            "note": note,
        }

    def get_analysis(self, analysis_id: str) -> Optional[dict]:
        """Obtiene un análisis por ID con sus series temporales."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE id = ? OR id LIKE ?",
                (analysis_id, f"{analysis_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            analysis = self._row_to_analysis(row, conn)
            return analysis

    def _row_to_analysis(self, row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
        """Convierte una fila de análisis a diccionario completo."""
        analysis_id = row["id"]

        # Obtener series temporales de tormenta
        storm_cursor = conn.execute(
            "SELECT * FROM storm_timeseries WHERE analysis_id = ?",
            (analysis_id,)
        )
        storm_ts = storm_cursor.fetchone()

        # Obtener series temporales de hidrograma
        hydro_cursor = conn.execute(
            "SELECT * FROM hydrograph_timeseries WHERE analysis_id = ?",
            (analysis_id,)
        )
        hydro_ts = hydro_cursor.fetchone()

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "note": row["note"],
            "tc": {
                "method": row["tc_method"],
                "tc_hr": row["tc_hr"],
                "tc_min": row["tc_min"],
                "parameters": json.loads(row["tc_parameters"]) if row["tc_parameters"] else {},
            },
            "storm": {
                "type": row["storm_type"],
                "return_period": row["return_period"],
                "duration_hr": row["duration_hr"],
                "total_depth_mm": row["total_depth_mm"],
                "peak_intensity_mmhr": row["peak_intensity_mmhr"],
                "n_intervals": row["n_intervals"],
                "time_min": json.loads(storm_ts["time_min"]) if storm_ts else [],
                "intensity_mmhr": json.loads(storm_ts["intensity_mmhr"]) if storm_ts else [],
            },
            "hydrograph": {
                "tc_method": row["tc_method"],
                "tc_min": row["tc_min"],
                "storm_type": row["storm_type"],
                "return_period": row["return_period"],
                "x_factor": row["x_factor"],
                "peak_flow_m3s": row["peak_flow_m3s"],
                "time_to_peak_hr": row["time_to_peak_hr"],
                "time_to_peak_min": row["time_to_peak_min"],
                "tp_unit_hr": row["tp_unit_hr"],
                "tp_unit_min": row["tp_unit_min"],
                "tb_hr": row["tb_hr"],
                "tb_min": row["tb_min"],
                "volume_m3": row["volume_m3"],
                "total_depth_mm": row["total_depth_mm"],
                "runoff_mm": row["runoff_mm"],
                "time_hr": json.loads(hydro_ts["time_hr"]) if hydro_ts else [],
                "flow_m3s": json.loads(hydro_ts["flow_m3s"]) if hydro_ts else [],
            },
        }

    def get_basin_analyses(self, basin_id: str) -> list[dict]:
        """Obtiene todos los análisis de una cuenca."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE basin_id = ? ORDER BY timestamp",
                (basin_id,)
            )
            return [self._row_to_analysis(row, conn) for row in cursor]

    def get_analysis_summary(self, basin_id: str) -> list[dict]:
        """Obtiene resumen de análisis sin series temporales (más rápido)."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, note, tc_method, tc_min,
                       storm_type, return_period, x_factor,
                       total_depth_mm, runoff_mm, peak_flow_m3s,
                       time_to_peak_min, tp_unit_min, tb_min, volume_m3
                FROM analyses
                WHERE basin_id = ?
                ORDER BY timestamp
                """,
                (basin_id,)
            )

            rows = []
            for row in cursor:
                rows.append({
                    "id": row["id"],
                    "tc_method": row["tc_method"],
                    "tc_min": row["tc_min"],
                    "tp_min": row["tp_unit_min"],
                    "tb_min": row["tb_min"],
                    "storm": row["storm_type"],
                    "tr": row["return_period"],
                    "x": row["x_factor"],
                    "depth_mm": row["total_depth_mm"],
                    "runoff_mm": row["runoff_mm"],
                    "qpeak_m3s": row["peak_flow_m3s"],
                    "Tp_min": row["time_to_peak_min"],
                    "vol_m3": row["volume_m3"],
                    "vol_hm3": row["volume_m3"] / 1_000_000,
                })

            return rows

    def update_analysis_note(self, analysis_id: str, note: Optional[str]) -> bool:
        """Actualiza la nota de un análisis."""
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE analyses SET note = ? WHERE id = ?",
                (note, analysis_id)
            )
            return cursor.rowcount > 0

    def delete_analysis(self, analysis_id: str) -> bool:
        """Elimina un análisis."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE id = ?",
                (analysis_id,)
            )
            return cursor.rowcount > 0

    def clear_basin_analyses(self, basin_id: str) -> int:
        """Elimina todos los análisis de una cuenca."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE basin_id = ?",
                (basin_id,)
            )
            return cursor.rowcount

    # ========================================================================
    # Consultas y Estadísticas
    # ========================================================================

    def get_stats(self) -> dict:
        """Obtiene estadísticas generales de la base de datos."""
        with self.connection() as conn:
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
        conditions = []
        params = []

        if name:
            conditions.append("b.name LIKE ?")
            params.append(f"%{name}%")
        if min_area is not None:
            conditions.append("b.area_ha >= ?")
            params.append(min_area)
        if max_area is not None:
            conditions.append("b.area_ha <= ?")
            params.append(max_area)
        if has_cn is True:
            conditions.append("b.cn IS NOT NULL")
        elif has_cn is False:
            conditions.append("b.cn IS NULL")
        if has_c is True:
            conditions.append("b.c IS NOT NULL")
        elif has_c is False:
            conditions.append("b.c IS NULL")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with self.connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT b.*, p.name as project_name, COUNT(a.id) as n_analyses
                FROM basins b
                JOIN projects p ON p.id = b.project_id
                LEFT JOIN analyses a ON a.basin_id = b.id
                {where_clause}
                GROUP BY b.id
                ORDER BY b.updated_at DESC
                """,
                params
            )

            results = []
            for row in cursor:
                basin = self._row_to_basin(row)
                basin["project_name"] = row["project_name"]
                basin["n_analyses"] = row["n_analyses"]
                results.append(basin)

            return results

    def search_analyses(
        self,
        storm_type: Optional[str] = None,
        return_period: Optional[int] = None,
        min_peak_flow: Optional[float] = None,
        max_peak_flow: Optional[float] = None,
    ) -> list[dict]:
        """Busca análisis con filtros."""
        conditions = []
        params = []

        if storm_type:
            conditions.append("a.storm_type = ?")
            params.append(storm_type)
        if return_period:
            conditions.append("a.return_period = ?")
            params.append(return_period)
        if min_peak_flow is not None:
            conditions.append("a.peak_flow_m3s >= ?")
            params.append(min_peak_flow)
        if max_peak_flow is not None:
            conditions.append("a.peak_flow_m3s <= ?")
            params.append(max_peak_flow)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with self.connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT a.*, b.name as basin_name, p.name as project_name
                FROM analyses a
                JOIN basins b ON b.id = a.basin_id
                JOIN projects p ON p.id = b.project_id
                {where_clause}
                ORDER BY a.peak_flow_m3s DESC
                LIMIT 100
                """,
                params
            )

            results = []
            for row in cursor:
                results.append({
                    "id": row["id"],
                    "basin_name": row["basin_name"],
                    "project_name": row["project_name"],
                    "storm_type": row["storm_type"],
                    "return_period": row["return_period"],
                    "peak_flow_m3s": row["peak_flow_m3s"],
                    "volume_m3": row["volume_m3"],
                    "timestamp": row["timestamp"],
                })

            return results


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
