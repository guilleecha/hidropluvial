"""
Editor de proyecto usando formulario interactivo.
"""

from typing import Optional

from hidropluvial.cli.theme import print_info, print_success, get_console, get_palette
from hidropluvial.cli.viewer.form_viewer import (
    interactive_form,
    FormField,
    FieldType,
    FormResult,
)
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


class ProjectEditor:
    """Editor para modificar metadatos de un proyecto usando formulario interactivo."""

    def __init__(self, project, project_manager=None):
        """
        Inicializa el editor.

        Args:
            project: Proyecto a editar
            project_manager: ProjectManager para guardar cambios
        """
        self.project = project
        self.project_manager = project_manager

    def edit(self) -> str:
        """
        Permite editar los datos del proyecto usando formulario interactivo.

        Returns:
            "modified" si se modificó el proyecto
            "cancelled" si se canceló
        """
        # Mostrar formulario con datos precargados
        new_values = self._show_edit_form()
        if new_values is None:
            return "cancelled"

        # Verificar si hay cambios
        changes = self._get_changes(new_values)
        if not changes:
            print_info("No se realizaron cambios.")
            return "cancelled"

        # Aplicar cambios
        return self._apply_changes(new_values, changes)

    def _show_edit_form(self) -> Optional[dict]:
        """Muestra el formulario de edición con datos precargados."""
        fields = [
            FormField(
                key="name",
                label="Nombre del proyecto",
                field_type=FieldType.TEXT,
                required=True,
                default=self.project.name,
                hint="Identificador del proyecto",
            ),
            FormField(
                key="description",
                label="Descripción",
                field_type=FieldType.TEXT,
                required=False,
                default=self.project.description or "",
                hint="Descripción del estudio",
            ),
            FormField(
                key="author",
                label="Autor",
                field_type=FieldType.TEXT,
                required=False,
                default=self.project.author or "",
                hint="Responsable del estudio",
            ),
            FormField(
                key="location",
                label="Ubicación",
                field_type=FieldType.TEXT,
                required=False,
                default=self.project.location or "",
                hint="Ubicación geográfica",
            ),
            FormField(
                key="notes",
                label="Notas",
                field_type=FieldType.TEXT,
                required=False,
                default=self.project.notes or "",
                hint="Observaciones adicionales",
            ),
        ]

        result = interactive_form(
            title=f"Editar Proyecto: {self.project.name}",
            fields=fields,
            allow_back=True,
        )

        if result is None:
            return None

        if result.get("_result") == FormResult.BACK:
            return None

        return result

    def _get_changes(self, new_values: dict) -> dict:
        """Compara valores nuevos con actuales y retorna solo los cambios."""
        changes = {}

        if new_values.get("name") != self.project.name:
            changes["name"] = (self.project.name, new_values.get("name"))

        new_desc = new_values.get("description") or ""
        old_desc = self.project.description or ""
        if new_desc != old_desc:
            changes["description"] = (old_desc, new_desc)

        new_author = new_values.get("author") or ""
        old_author = self.project.author or ""
        if new_author != old_author:
            changes["author"] = (old_author, new_author)

        new_location = new_values.get("location") or ""
        old_location = self.project.location or ""
        if new_location != old_location:
            changes["location"] = (old_location, new_location)

        new_notes = new_values.get("notes") or ""
        old_notes = self.project.notes or ""
        if new_notes != old_notes:
            changes["notes"] = (old_notes, new_notes)

        return changes

    def _apply_changes(self, new_values: dict, changes: dict) -> str:
        """Aplica los cambios al proyecto."""
        # Aplicar todos los valores nuevos
        if "name" in new_values and new_values["name"]:
            self.project.name = new_values["name"]

        self.project.description = new_values.get("description") or ""
        self.project.author = new_values.get("author") or ""
        self.project.location = new_values.get("location") or ""
        self.project.notes = new_values.get("notes") or None

        # Guardar si tenemos project_manager
        if self.project_manager:
            self.project_manager.save_project(self.project)

        print_success("Proyecto actualizado correctamente.")
        return "modified"
