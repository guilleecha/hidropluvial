"""
Módulo de conexión a base de datos SQLite.

Proporciona la clase base con manejo de conexión y esquema.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Iterator, TypeVar, Any


# ============================================================================
# Helpers para JSON
# ============================================================================

T = TypeVar("T")


def _json_loads(value: Optional[str], default: T = None) -> T | Any:
    """
    Deserializa JSON de forma segura.

    Args:
        value: String JSON o None
        default: Valor por defecto si value es None o vacío

    Returns:
        Objeto deserializado o default
    """
    if not value:
        return default
    return json.loads(value)


def _json_list(value: Optional[str]) -> list:
    """Deserializa JSON a lista, retorna lista vacía si es None."""
    return _json_loads(value, [])


def _json_dict(value: Optional[str]) -> dict:
    """Deserializa JSON a dict, retorna dict vacío si es None."""
    return _json_loads(value, {})


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
# Clase DatabaseConnection
# ============================================================================

class DatabaseConnection:
    """Gestor de conexión a base de datos SQLite."""

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
