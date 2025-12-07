"""
Operaciones de base de datos para proyectos.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from hidropluvial.database.connection import DatabaseConnection, _json_list


class ProjectRepository:
    """Repositorio para operaciones CRUD de proyectos."""

    def __init__(self, db: DatabaseConnection):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de DatabaseConnection
        """
        self._db = db

    def create(
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

        with self._db.connection() as conn:
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

    def get(self, project_id: str) -> Optional[dict]:
        """Obtiene un proyecto por ID (parcial o completo)."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE id = ? OR id LIKE ?",
                (project_id, f"{project_id}%")
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_dict(row)

    def _row_to_dict(self, row) -> dict:
        """Convierte una fila de la BD a diccionario de proyecto."""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "author": row["author"],
            "location": row["location"],
            "notes": row["notes"],
            "tags": _json_list(row["tags"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_all(self) -> list[dict]:
        """Lista todos los proyectos con resumen."""
        with self._db.connection() as conn:
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
                project = self._row_to_dict(row)
                project["n_basins"] = row["n_basins"]
                project["total_analyses"] = row["total_analyses"]
                projects.append(project)

            return projects

    def update(
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

        with self._db.connection() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                params
            )
            return cursor.rowcount > 0

    def delete(self, project_id: str) -> bool:
        """Elimina un proyecto y todas sus cuencas."""
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM projects WHERE id = ? OR id LIKE ?",
                (project_id, f"{project_id}%")
            )
            return cursor.rowcount > 0
