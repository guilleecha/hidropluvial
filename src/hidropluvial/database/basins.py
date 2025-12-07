"""
Operaciones de base de datos para cuencas (basins).
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from hidropluvial.database.connection import DatabaseConnection, _json_loads, _json_dict
from hidropluvial.models import WeightedCoefficient


class BasinRepository:
    """Repositorio para operaciones CRUD de cuencas."""

    def __init__(self, db: DatabaseConnection):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de DatabaseConnection
        """
        self._db = db

    def create(
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

        with self._db.connection() as conn:
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

    def get(self, basin_id: str, include_analyses: bool = True) -> Optional[dict]:
        """Obtiene una cuenca por ID con todos sus datos."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM basins WHERE id = ? OR id LIKE ?",
                (basin_id, f"{basin_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            basin = self._row_to_dict(row)

            # Obtener resultados de Tc
            cursor = conn.execute(
                "SELECT * FROM tc_results WHERE basin_id = ?",
                (basin["id"],)
            )
            basin["tc_results"] = [
                self._row_to_tc_result(r) for r in cursor
            ]

            # Obtener análisis si se solicita
            if include_analyses:
                from hidropluvial.database.analyses import AnalysisRepository
                analysis_repo = AnalysisRepository(self._db)
                basin["analyses"] = analysis_repo.get_by_basin(basin["id"])
            else:
                basin["analyses"] = []

            return basin

    def _row_to_dict(self, row) -> dict:
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
            "c_weighted": _json_loads(row["c_weighted"]),
            "cn_weighted": _json_loads(row["cn_weighted"]),
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_tc_result(self, row) -> dict:
        """Convierte una fila de Tc a diccionario."""
        return {
            "method": row["method"],
            "tc_hr": row["tc_hr"],
            "tc_min": row["tc_min"],
            "parameters": _json_dict(row["parameters"]),
        }

    def get_by_project(self, project_id: str) -> list[dict]:
        """Obtiene todas las cuencas de un proyecto."""
        with self._db.connection() as conn:
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
                basin = self._row_to_dict(row)
                basin["n_analyses"] = row["n_analyses"]
                basins.append(basin)

            return basins

    def update(
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

        with self._db.connection() as conn:
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

    def delete(self, basin_id: str) -> bool:
        """Elimina una cuenca y todos sus análisis."""
        with self._db.connection() as conn:
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

    # ========================================================================
    # Búsquedas
    # ========================================================================

    def search(
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

        with self._db.connection() as conn:
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
                basin = self._row_to_dict(row)
                basin["project_name"] = row["project_name"]
                basin["n_analyses"] = row["n_analyses"]
                results.append(basin)

            return results
