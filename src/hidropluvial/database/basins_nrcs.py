"""
Operaciones de segmentos y templates NRCS para cuencas.
"""

from datetime import datetime
from typing import Optional

from hidropluvial.config import (
    SheetFlowSegment,
    ShallowFlowSegment,
    ChannelFlowSegment,
)


class NRCSOperationsMixin:
    """Mixin con operaciones NRCS para BasinRepository."""

    # ========================================================================
    # Segmentos NRCS (legacy - directamente en cuenca)
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
                self._insert_segment(conn, basin_id, None, order, segment)

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
    # Templates NRCS
    # ========================================================================

    def create_nrcs_template(
        self,
        basin_id: str,
        name: str,
        segments: list,
        p2_mm: float = 50.0,
    ) -> dict:
        """
        Crea un nuevo template NRCS para una cuenca.

        Args:
            basin_id: ID de la cuenca
            name: Nombre del template
            segments: Lista de segmentos (SheetFlowSegment, etc.)
            p2_mm: Precipitación P2 (2 años, 24h)

        Returns:
            Dict con el template creado (id, name, p2_mm, segments, created_at)
        """
        now = datetime.now().isoformat()

        with self._db.connection() as conn:
            # Crear template
            cursor = conn.execute(
                """
                INSERT INTO nrcs_templates (basin_id, name, p2_mm, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (basin_id, name, p2_mm, now)
            )
            template_id = cursor.lastrowid

            # Insertar segmentos
            for order, segment in enumerate(segments):
                self._insert_segment(conn, None, template_id, order, segment)

            # Actualizar timestamp de cuenca
            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (now, basin_id)
            )

        return {
            "id": template_id,
            "basin_id": basin_id,
            "name": name,
            "p2_mm": p2_mm,
            "segments": segments,
            "created_at": now,
        }

    def get_nrcs_templates(self, basin_id: str) -> list[dict]:
        """
        Obtiene todos los templates NRCS de una cuenca.

        Returns:
            Lista de dicts con templates (id, name, p2_mm, segments, created_at)
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM nrcs_templates WHERE basin_id = ? ORDER BY created_at",
                (basin_id,)
            )

            templates = []
            for row in cursor:
                template = {
                    "id": row["id"],
                    "basin_id": row["basin_id"],
                    "name": row["name"],
                    "p2_mm": row["p2_mm"],
                    "created_at": row["created_at"],
                    "segments": [],
                }

                # Obtener segmentos del template
                seg_cursor = conn.execute(
                    "SELECT * FROM nrcs_segments WHERE template_id = ? ORDER BY segment_order",
                    (row["id"],)
                )
                template["segments"] = [
                    self._row_to_nrcs_segment(s) for s in seg_cursor
                ]

                templates.append(template)

            return templates

    def get_nrcs_template(self, template_id: int) -> Optional[dict]:
        """
        Obtiene un template NRCS por ID.

        Returns:
            Dict con el template o None si no existe
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM nrcs_templates WHERE id = ?",
                (template_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            template = {
                "id": row["id"],
                "basin_id": row["basin_id"],
                "name": row["name"],
                "p2_mm": row["p2_mm"],
                "created_at": row["created_at"],
                "segments": [],
            }

            # Obtener segmentos
            seg_cursor = conn.execute(
                "SELECT * FROM nrcs_segments WHERE template_id = ? ORDER BY segment_order",
                (template_id,)
            )
            template["segments"] = [
                self._row_to_nrcs_segment(s) for s in seg_cursor
            ]

            return template

    def update_nrcs_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        segments: Optional[list] = None,
        p2_mm: Optional[float] = None,
    ) -> bool:
        """
        Actualiza un template NRCS existente.

        Returns:
            True si se actualizó, False si no existía
        """
        with self._db.connection() as conn:
            # Verificar que existe
            cursor = conn.execute(
                "SELECT basin_id FROM nrcs_templates WHERE id = ?",
                (template_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return False

            basin_id = row["basin_id"]

            # Actualizar campos
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if p2_mm is not None:
                updates.append("p2_mm = ?")
                params.append(p2_mm)

            if updates:
                params.append(template_id)
                conn.execute(
                    f"UPDATE nrcs_templates SET {', '.join(updates)} WHERE id = ?",
                    params
                )

            # Actualizar segmentos si se proporcionan
            if segments is not None:
                # Eliminar segmentos existentes
                conn.execute(
                    "DELETE FROM nrcs_segments WHERE template_id = ?",
                    (template_id,)
                )

                # Insertar nuevos segmentos
                for order, segment in enumerate(segments):
                    self._insert_segment(conn, None, template_id, order, segment)

            # Actualizar timestamp de cuenca
            conn.execute(
                "UPDATE basins SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), basin_id)
            )

            return True

    def delete_nrcs_template(self, template_id: int) -> bool:
        """
        Elimina un template NRCS y sus segmentos.

        Returns:
            True si se eliminó, False si no existía
        """
        with self._db.connection() as conn:
            # Obtener basin_id para actualizar timestamp
            cursor = conn.execute(
                "SELECT basin_id FROM nrcs_templates WHERE id = ?",
                (template_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return False

            basin_id = row["basin_id"]

            # Eliminar template (CASCADE elimina segmentos)
            cursor = conn.execute(
                "DELETE FROM nrcs_templates WHERE id = ?",
                (template_id,)
            )

            if cursor.rowcount > 0:
                conn.execute(
                    "UPDATE basins SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), basin_id)
                )

            return cursor.rowcount > 0

    # ========================================================================
    # Helpers internos
    # ========================================================================

    def _insert_segment(
        self,
        conn,
        basin_id: Optional[str],
        template_id: Optional[int],
        order: int,
        segment
    ) -> None:
        """Inserta un segmento NRCS (para basin o template)."""
        segment_type = segment.type.value

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
            (basin_id, template_id, segment_order, segment_type, length_m, slope,
             n_manning, surface, hydraulic_radius_m)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (basin_id, template_id, order, segment_type, segment.length_m, segment.slope,
             n_manning, surface, hydraulic_radius_m)
        )

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

    def _get_templates_for_basin(self, conn, basin_id: str) -> list[dict]:
        """Obtiene templates NRCS de una cuenca (helper para get)."""
        cursor = conn.execute(
            "SELECT * FROM nrcs_templates WHERE basin_id = ? ORDER BY created_at",
            (basin_id,)
        )

        templates = []
        for row in cursor:
            template = {
                "id": row["id"],
                "basin_id": row["basin_id"],
                "name": row["name"],
                "p2_mm": row["p2_mm"],
                "created_at": row["created_at"],
                "segments": [],
            }

            seg_cursor = conn.execute(
                "SELECT * FROM nrcs_segments WHERE template_id = ? ORDER BY segment_order",
                (row["id"],)
            )
            template["segments"] = [
                self._row_to_nrcs_segment(s) for s in seg_cursor
            ]

            templates.append(template)

        return templates
