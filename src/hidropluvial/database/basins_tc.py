"""
Operaciones de tiempo de concentración (Tc) para cuencas.
"""

import json
from datetime import datetime
from typing import Optional

from hidropluvial.database.connection import _json_dict


class TcOperationsMixin:
    """Mixin con operaciones de Tc para BasinRepository."""

    def add_tc_result(
        self,
        basin_id: str,
        method: str,
        tc_hr: float,
        parameters: Optional[dict] = None,
    ) -> dict:
        """Agrega o actualiza un resultado de Tc."""
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tc_results (basin_id, method, tc_hr, tc_min, parameters)
                VALUES (?, ?, ?, ?, ?)
                """,
                (basin_id, method, tc_hr, tc_hr * 60, json.dumps(parameters or {}))
            )

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
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tc_results WHERE basin_id = ?",
                (basin_id,)
            )
            return [self._row_to_tc_result(r) for r in cursor]

    def clear_tc_results(self, basin_id: str) -> int:
        """Elimina todos los resultados de Tc de una cuenca."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tc_results WHERE basin_id = ?",
                (basin_id,)
            )
            return cursor.rowcount

    def _row_to_tc_result(self, row) -> dict:
        """Convierte una fila de Tc a diccionario."""
        return {
            "method": row["method"],
            "tc_hr": row["tc_hr"],
            "tc_min": row["tc_min"],
            "parameters": _json_dict(row["parameters"]),
        }
