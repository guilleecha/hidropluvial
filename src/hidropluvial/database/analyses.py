"""
Operaciones de base de datos para análisis.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from hidropluvial.database.connection import DatabaseConnection, _json_list, _json_dict
from hidropluvial.models import TcResult, StormResult, HydrographResult


class AnalysisRepository:
    """Repositorio para operaciones CRUD de análisis."""

    def __init__(self, db: DatabaseConnection):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de DatabaseConnection
        """
        self._db = db

    def add(
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

        with self._db.connection() as conn:
            # Insertar análisis principal
            conn.execute(
                """
                INSERT INTO analyses (
                    id, basin_id, timestamp, note,
                    tc_method, tc_hr, tc_min, tc_parameters,
                    storm_type, return_period, duration_hr, total_depth_mm,
                    peak_intensity_mmhr, n_intervals,
                    bimodal_peak1, bimodal_peak2, bimodal_vol_split, bimodal_peak_width,
                    x_factor, peak_flow_m3s, time_to_peak_hr, time_to_peak_min,
                    tp_unit_hr, tp_unit_min, tb_hr, tb_min, volume_m3, runoff_mm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id, basin_id, timestamp, note,
                    tc.method, tc.tc_hr, tc.tc_min, json.dumps(tc.parameters),
                    storm.type, storm.return_period, storm.duration_hr, storm.total_depth_mm,
                    storm.peak_intensity_mmhr, storm.n_intervals,
                    storm.bimodal_peak1, storm.bimodal_peak2,
                    storm.bimodal_vol_split, storm.bimodal_peak_width,
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

    def get(self, analysis_id: str) -> Optional[dict]:
        """Obtiene un análisis por ID con sus series temporales."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE id = ? OR id LIKE ?",
                (analysis_id, f"{analysis_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_dict(row, conn)

    def _row_to_tc_dict(self, row: sqlite3.Row) -> dict:
        """Extrae datos de Tc de una fila de análisis."""
        return {
            "method": row["tc_method"],
            "tc_hr": row["tc_hr"],
            "tc_min": row["tc_min"],
            "parameters": _json_dict(row["tc_parameters"]),
        }

    def _row_to_storm_dict(self, row: sqlite3.Row, storm_ts: Optional[sqlite3.Row]) -> dict:
        """Extrae datos de tormenta de una fila de análisis."""
        result = {
            "type": row["storm_type"],
            "return_period": row["return_period"],
            "duration_hr": row["duration_hr"],
            "total_depth_mm": row["total_depth_mm"],
            "peak_intensity_mmhr": row["peak_intensity_mmhr"],
            "n_intervals": row["n_intervals"],
            "time_min": _json_list(storm_ts["time_min"]) if storm_ts else [],
            "intensity_mmhr": _json_list(storm_ts["intensity_mmhr"]) if storm_ts else [],
        }
        # Agregar parámetros bimodales si existen
        if row["bimodal_peak1"] is not None:
            result["bimodal_peak1"] = row["bimodal_peak1"]
            result["bimodal_peak2"] = row["bimodal_peak2"]
            result["bimodal_vol_split"] = row["bimodal_vol_split"]
            result["bimodal_peak_width"] = row["bimodal_peak_width"]
        return result

    def _row_to_hydrograph_dict(self, row: sqlite3.Row, hydro_ts: Optional[sqlite3.Row]) -> dict:
        """Extrae datos de hidrograma de una fila de análisis."""
        return {
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
            "time_hr": _json_list(hydro_ts["time_hr"]) if hydro_ts else [],
            "flow_m3s": _json_list(hydro_ts["flow_m3s"]) if hydro_ts else [],
        }

    def _row_to_dict(self, row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
        """Convierte una fila de análisis a diccionario completo."""
        analysis_id = row["id"]

        # Obtener series temporales
        storm_ts = conn.execute(
            "SELECT * FROM storm_timeseries WHERE analysis_id = ?",
            (analysis_id,)
        ).fetchone()

        hydro_ts = conn.execute(
            "SELECT * FROM hydrograph_timeseries WHERE analysis_id = ?",
            (analysis_id,)
        ).fetchone()

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "note": row["note"],
            "tc": self._row_to_tc_dict(row),
            "storm": self._row_to_storm_dict(row, storm_ts),
            "hydrograph": self._row_to_hydrograph_dict(row, hydro_ts),
        }

    def get_by_basin(self, basin_id: str) -> list[dict]:
        """Obtiene todos los análisis de una cuenca."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analyses WHERE basin_id = ? ORDER BY timestamp",
                (basin_id,)
            )
            return [self._row_to_dict(row, conn) for row in cursor]

    def get_summary(self, basin_id: str) -> list[dict]:
        """Obtiene resumen de análisis sin series temporales (más rápido)."""
        with self._db.connection() as conn:
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

    def update_note(self, analysis_id: str, note: Optional[str]) -> bool:
        """Actualiza la nota de un análisis."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "UPDATE analyses SET note = ? WHERE id = ?",
                (note, analysis_id)
            )
            return cursor.rowcount > 0

    def delete(self, analysis_id: str) -> bool:
        """Elimina un análisis."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE id = ?",
                (analysis_id,)
            )
            return cursor.rowcount > 0

    def clear_by_basin(self, basin_id: str) -> int:
        """Elimina todos los análisis de una cuenca."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE basin_id = ?",
                (basin_id,)
            )
            return cursor.rowcount

    def search(
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

        with self._db.connection() as conn:
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
