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

SCHEMA_VERSION = 3

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
    p2_mm REAL,  -- Precipitación 2 años, 24h (mm) para NRCS
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

-- Tabla de segmentos NRCS (método de velocidades TR-55)
CREATE TABLE IF NOT EXISTS nrcs_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basin_id TEXT NOT NULL,
    segment_order INTEGER NOT NULL,  -- Orden del segmento en el recorrido
    segment_type TEXT NOT NULL,  -- 'sheet', 'shallow', 'channel'
    length_m REAL NOT NULL,
    slope REAL NOT NULL,
    -- Campos para sheet flow
    n_manning REAL,  -- Coeficiente de Manning (sheet/channel)
    -- Campos para shallow flow
    surface TEXT,  -- Tipo de superficie ('paved', 'unpaved', 'grassed', 'short_grass')
    -- Campos para channel flow
    hydraulic_radius_m REAL,
    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE
);

-- Tabla de coeficientes ponderados (C y CN)
CREATE TABLE IF NOT EXISTS weighted_coefficients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basin_id TEXT NOT NULL,
    coef_type TEXT NOT NULL,  -- 'c' o 'cn'
    table_used TEXT,          -- 'chow', 'fhwa', 'uruguay', 'nrcs', etc.
    weighted_value REAL NOT NULL,
    base_tr INTEGER,          -- Período de retorno base (ej: 2 para Ven Te Chow)
    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE,
    UNIQUE (basin_id, coef_type)
);

-- Tabla de items de cobertura para ponderación
CREATE TABLE IF NOT EXISTS coverage_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weighted_coef_id INTEGER NOT NULL,
    item_order INTEGER NOT NULL,
    description TEXT NOT NULL,
    area_ha REAL NOT NULL,
    value REAL NOT NULL,       -- Valor de C o CN para esta cobertura
    percentage REAL NOT NULL,  -- Porcentaje del área total
    table_index INTEGER,       -- Índice en tabla original (para recálculo)
    FOREIGN KEY (weighted_coef_id) REFERENCES weighted_coefficients(id) ON DELETE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_nrcs_segments_basin ON nrcs_segments(basin_id);
CREATE INDEX IF NOT EXISTS idx_weighted_coef_basin ON weighted_coefficients(basin_id);
CREATE INDEX IF NOT EXISTS idx_coverage_items_coef ON coverage_items(weighted_coef_id);
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
            else:
                current_version = int(row["value"])
                if current_version < SCHEMA_VERSION:
                    self._migrate(conn, current_version)

    def _migrate(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Ejecuta migraciones incrementales del esquema."""
        if from_version < 2:
            # Migración v1 -> v2: Agregar soporte NRCS
            # Agregar columna p2_mm a basins si no existe
            cursor = conn.execute("PRAGMA table_info(basins)")
            columns = [col["name"] for col in cursor]
            if "p2_mm" not in columns:
                conn.execute("ALTER TABLE basins ADD COLUMN p2_mm REAL")

            # Crear tabla nrcs_segments si no existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nrcs_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    basin_id TEXT NOT NULL,
                    segment_order INTEGER NOT NULL,
                    segment_type TEXT NOT NULL,
                    length_m REAL NOT NULL,
                    slope REAL NOT NULL,
                    n_manning REAL,
                    surface TEXT,
                    hydraulic_radius_m REAL,
                    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nrcs_segments_basin ON nrcs_segments(basin_id)"
            )

        if from_version < 3:
            # Migración v2 -> v3: Normalizar coeficientes ponderados
            # Crear tabla weighted_coefficients
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weighted_coefficients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    basin_id TEXT NOT NULL,
                    coef_type TEXT NOT NULL,
                    table_used TEXT,
                    weighted_value REAL NOT NULL,
                    base_tr INTEGER,
                    FOREIGN KEY (basin_id) REFERENCES basins(id) ON DELETE CASCADE,
                    UNIQUE (basin_id, coef_type)
                )
            """)

            # Crear tabla coverage_items
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weighted_coef_id INTEGER NOT NULL,
                    item_order INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    area_ha REAL NOT NULL,
                    value REAL NOT NULL,
                    percentage REAL NOT NULL,
                    table_index INTEGER,
                    FOREIGN KEY (weighted_coef_id) REFERENCES weighted_coefficients(id) ON DELETE CASCADE
                )
            """)

            # Crear índices
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_weighted_coef_basin ON weighted_coefficients(basin_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_coverage_items_coef ON coverage_items(weighted_coef_id)"
            )

            # Migrar datos JSON existentes a las nuevas tablas
            self._migrate_weighted_coefficients(conn)

        # Actualizar versión del esquema
        conn.execute(
            "UPDATE metadata SET value = ? WHERE key = 'schema_version'",
            (str(SCHEMA_VERSION),)
        )

    def _migrate_weighted_coefficients(self, conn: sqlite3.Connection) -> None:
        """Migra c_weighted y cn_weighted de JSON a tablas normalizadas."""
        cursor = conn.execute(
            "SELECT id, c_weighted, cn_weighted FROM basins WHERE c_weighted IS NOT NULL OR cn_weighted IS NOT NULL"
        )

        for row in cursor.fetchall():
            basin_id = row["id"]

            # Migrar c_weighted
            if row["c_weighted"]:
                self._migrate_single_weighted(conn, basin_id, row["c_weighted"], "c")

            # Migrar cn_weighted
            if row["cn_weighted"]:
                self._migrate_single_weighted(conn, basin_id, row["cn_weighted"], "cn")

    def _migrate_single_weighted(
        self, conn: sqlite3.Connection, basin_id: str, json_data: str, coef_type: str
    ) -> None:
        """Migra un coeficiente ponderado individual."""
        try:
            data = json.loads(json_data)

            # Insertar coeficiente ponderado
            cursor = conn.execute(
                """
                INSERT INTO weighted_coefficients (basin_id, coef_type, table_used, weighted_value, base_tr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    basin_id,
                    coef_type,
                    data.get("table_used", ""),
                    data.get("weighted_value", 0),
                    data.get("base_tr"),
                )
            )
            weighted_id = cursor.lastrowid

            # Insertar items de cobertura
            items = data.get("items", [])
            for order, item in enumerate(items):
                conn.execute(
                    """
                    INSERT INTO coverage_items
                    (weighted_coef_id, item_order, description, area_ha, value, percentage, table_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        weighted_id,
                        order,
                        item.get("description", ""),
                        item.get("area_ha", 0),
                        item.get("value", 0),
                        item.get("percentage", 0),
                        item.get("table_index"),
                    )
                )
        except (json.JSONDecodeError, KeyError):
            # Si hay error en el JSON, ignorar este registro
            pass

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
