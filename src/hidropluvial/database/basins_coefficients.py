"""
Operaciones de coeficientes ponderados (C y CN) para cuencas.
"""

from datetime import datetime
from typing import Optional


class WeightedCoefficientsMixin:
    """Mixin con operaciones de coeficientes ponderados para BasinRepository."""

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
