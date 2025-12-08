"""
Operaciones de base de datos para cuencas (basins).
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from hidropluvial.database.connection import DatabaseConnection, _json_dict
from hidropluvial.models import WeightedCoefficient
from hidropluvial.config import (
    SheetFlowSegment,
    ShallowFlowSegment,
    ChannelFlowSegment,
    TCSegmentType,
)


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
        p2_mm: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Crea una nueva cuenca en un proyecto."""
        basin_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO basins (id, project_id, name, area_ha, slope_pct,
                                   length_m, p3_10, c, cn, p2_mm, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (basin_id, project_id, name, area_ha, slope_pct,
                 length_m, p3_10, c, cn, p2_mm, notes, now, now)
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
            "p2_mm": p2_mm,
            "c_weighted": None,
            "cn_weighted": None,
            "nrcs_segments": [],
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

            # Obtener segmentos NRCS
            cursor = conn.execute(
                "SELECT * FROM nrcs_segments WHERE basin_id = ? ORDER BY segment_order",
                (basin["id"],)
            )
            basin["nrcs_segments"] = [
                self._row_to_nrcs_segment(r) for r in cursor
            ]

            # Obtener coeficientes ponderados desde tablas normalizadas
            basin["c_weighted"] = self._get_weighted_from_tables(conn, basin["id"], "c")
            basin["cn_weighted"] = self._get_weighted_from_tables(conn, basin["id"], "cn")

            # Obtener análisis si se solicita
            if include_analyses:
                from hidropluvial.database.analyses import AnalysisRepository
                analysis_repo = AnalysisRepository(self._db)
                basin["analyses"] = analysis_repo.get_by_basin(basin["id"])
            else:
                basin["analyses"] = []

            return basin

    def _get_weighted_from_tables(self, conn, basin_id: str, coef_type: str) -> Optional[dict]:
        """Obtiene un coeficiente ponderado desde las tablas normalizadas."""
        cursor = conn.execute(
            "SELECT * FROM weighted_coefficients WHERE basin_id = ? AND coef_type = ?",
            (basin_id, coef_type)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        # Obtener items
        cursor = conn.execute(
            "SELECT * FROM coverage_items WHERE weighted_coef_id = ? ORDER BY item_order",
            (row["id"],)
        )

        items = []
        for item_row in cursor:
            items.append({
                "description": item_row["description"],
                "area_ha": item_row["area_ha"],
                "value": item_row["value"],
                "percentage": item_row["percentage"],
                "table_index": item_row["table_index"],
            })

        return {
            "type": row["coef_type"],
            "table_used": row["table_used"] or "",
            "weighted_value": row["weighted_value"],
            "base_tr": row["base_tr"],
            "items": items,
        }

    def _row_to_dict(self, row) -> dict:
        """Convierte una fila de la BD a diccionario de cuenca."""
        # Verificar si la columna p2_mm existe (compatibilidad con BD antiguas)
        p2_mm = None
        try:
            p2_mm = row["p2_mm"]
        except (IndexError, KeyError):
            pass

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
            "p2_mm": p2_mm,
            # c_weighted y cn_weighted se cargan desde tablas normalizadas
            "c_weighted": None,
            "cn_weighted": None,
            "nrcs_segments": [],  # Se carga por separado
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

    def _row_to_nrcs_segment(self, row):
        """Convierte una fila de segmento NRCS al objeto correspondiente."""
        segment_type = row["segment_type"]

        if segment_type == "sheet":
            return SheetFlowSegment(
                length_m=row["length_m"],
                n=row["n_manning"],
                slope=row["slope"],
                p2_mm=50.0,  # Se obtiene de la cuenca
            )
        elif segment_type == "shallow":
            return ShallowFlowSegment(
                length_m=row["length_m"],
                slope=row["slope"],
                surface=row["surface"] or "unpaved",
            )
        elif segment_type == "channel":
            return ChannelFlowSegment(
                length_m=row["length_m"],
                n=row["n_manning"],
                slope=row["slope"],
                hydraulic_radius_m=row["hydraulic_radius_m"],
            )
        else:
            raise ValueError(f"Tipo de segmento desconocido: {segment_type}")

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
        p2_mm: Optional[float] = None,
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
        if p2_mm is not None:
            updates.append("p2_mm = ?")
            params.append(p2_mm)
        # c_weighted y cn_weighted se manejan en tablas normalizadas
        # Usar set_weighted_coefficient() en lugar de update()
        if c_weighted is not None:
            raise ValueError(
                "c_weighted debe guardarse con set_weighted_coefficient(), no con update()"
            )
        if cn_weighted is not None:
            raise ValueError(
                "cn_weighted debe guardarse con set_weighted_coefficient(), no con update()"
            )
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

    # ========================================================================
    # Operaciones de Segmentos NRCS
    # ========================================================================

    def set_nrcs_segments(
        self,
        basin_id: str,
        segments: list,
        p2_mm: Optional[float] = None,
    ) -> None:
        """
        Guarda los segmentos NRCS de una cuenca.

        Reemplaza todos los segmentos existentes.

        Args:
            basin_id: ID de la cuenca
            segments: Lista de segmentos (SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment)
            p2_mm: Precipitación P2 para flujo laminar (opcional, se guarda en la cuenca)
        """
        with self._db.connection() as conn:
            # Eliminar segmentos existentes
            conn.execute(
                "DELETE FROM nrcs_segments WHERE basin_id = ?",
                (basin_id,)
            )

            # Insertar nuevos segmentos
            for order, segment in enumerate(segments):
                segment_type = segment.type.value  # 'sheet', 'shallow', 'channel'

                # Extraer campos según tipo
                n_manning = None
                surface = None
                hydraulic_radius_m = None

                if segment_type == "sheet":
                    n_manning = segment.n
                elif segment_type == "shallow":
                    surface = segment.surface
                elif segment_type == "channel":
                    n_manning = segment.n
                    hydraulic_radius_m = segment.hydraulic_radius_m

                conn.execute(
                    """
                    INSERT INTO nrcs_segments
                    (basin_id, segment_order, segment_type, length_m, slope,
                     n_manning, surface, hydraulic_radius_m)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (basin_id, order, segment_type, segment.length_m, segment.slope,
                     n_manning, surface, hydraulic_radius_m)
                )

            # Actualizar p2_mm si se proporciona
            if p2_mm is not None:
                conn.execute(
                    "UPDATE basins SET p2_mm = ?, updated_at = ? WHERE id = ?",
                    (p2_mm, datetime.now().isoformat(), basin_id)
                )
            else:
                conn.execute(
                    "UPDATE basins SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), basin_id)
                )

    def get_nrcs_segments(self, basin_id: str) -> list:
        """
        Obtiene los segmentos NRCS de una cuenca.

        Returns:
            Lista de objetos segmento (SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment)
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM nrcs_segments WHERE basin_id = ? ORDER BY segment_order",
                (basin_id,)
            )
            return [self._row_to_nrcs_segment(r) for r in cursor]

    def clear_nrcs_segments(self, basin_id: str) -> int:
        """
        Elimina todos los segmentos NRCS de una cuenca.

        Returns:
            Número de segmentos eliminados
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM nrcs_segments WHERE basin_id = ?",
                (basin_id,)
            )

            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), basin_id)
            )

            return cursor.rowcount

    # ========================================================================
    # Operaciones de Coeficientes Ponderados
    # ========================================================================

    def set_weighted_coefficient(
        self,
        basin_id: str,
        coef_type: str,
        weighted_value: float,
        items: list,
        table_used: str = "",
        base_tr: Optional[int] = None,
    ) -> int:
        """
        Guarda un coeficiente ponderado (C o CN) con sus items de cobertura.

        Args:
            basin_id: ID de la cuenca
            coef_type: 'c' o 'cn'
            weighted_value: Valor ponderado resultante
            items: Lista de CoverageItem o dicts con los items
            table_used: Tabla usada ('chow', 'fhwa', 'uruguay', 'nrcs')
            base_tr: Período de retorno base

        Returns:
            ID del coeficiente ponderado creado
        """
        with self._db.connection() as conn:
            # Eliminar coeficiente existente (CASCADE elimina items)
            conn.execute(
                "DELETE FROM weighted_coefficients WHERE basin_id = ? AND coef_type = ?",
                (basin_id, coef_type)
            )

            # Insertar nuevo coeficiente
            cursor = conn.execute(
                """
                INSERT INTO weighted_coefficients (basin_id, coef_type, table_used, weighted_value, base_tr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (basin_id, coef_type, table_used, weighted_value, base_tr)
            )
            weighted_id = cursor.lastrowid

            # Insertar items de cobertura
            for order, item in enumerate(items):
                # Soportar tanto objetos como dicts
                if hasattr(item, 'description'):
                    desc = item.description
                    area = item.area_ha
                    val = item.value
                    pct = item.percentage
                    idx = getattr(item, 'table_index', None)
                else:
                    desc = item.get('description', '')
                    area = item.get('area_ha', 0)
                    val = item.get('value', 0)
                    pct = item.get('percentage', 0)
                    idx = item.get('table_index')

                conn.execute(
                    """
                    INSERT INTO coverage_items
                    (weighted_coef_id, item_order, description, area_ha, value, percentage, table_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (weighted_id, order, desc, area, val, pct, idx)
                )

            # Actualizar timestamp de la cuenca
            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), basin_id)
            )

            return weighted_id

    def get_weighted_coefficient(self, basin_id: str, coef_type: str) -> Optional[dict]:
        """
        Obtiene un coeficiente ponderado con sus items.

        Args:
            basin_id: ID de la cuenca
            coef_type: 'c' o 'cn'

        Returns:
            Dict con estructura WeightedCoefficient o None
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM weighted_coefficients WHERE basin_id = ? AND coef_type = ?",
                (basin_id, coef_type)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Obtener items
            cursor = conn.execute(
                "SELECT * FROM coverage_items WHERE weighted_coef_id = ? ORDER BY item_order",
                (row["id"],)
            )

            items = []
            for item_row in cursor:
                items.append({
                    "description": item_row["description"],
                    "area_ha": item_row["area_ha"],
                    "value": item_row["value"],
                    "percentage": item_row["percentage"],
                    "table_index": item_row["table_index"],
                })

            return {
                "type": row["coef_type"],
                "table_used": row["table_used"] or "",
                "weighted_value": row["weighted_value"],
                "base_tr": row["base_tr"],
                "items": items,
            }

    def delete_weighted_coefficient(self, basin_id: str, coef_type: str) -> bool:
        """
        Elimina un coeficiente ponderado y sus items.

        Returns:
            True si se eliminó, False si no existía
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM weighted_coefficients WHERE basin_id = ? AND coef_type = ?",
                (basin_id, coef_type)
            )

            if cursor.rowcount > 0:
                conn.execute(
                    "UPDATE basins SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), basin_id)
                )

            return cursor.rowcount > 0
