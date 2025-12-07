"""
Menu para gestionar proyectos.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.basin_management import BasinManagementMenu
from hidropluvial.cli.theme import (
    get_console, print_projects_table, print_info,
)
from hidropluvial.project import Project, get_project_manager


class ProjectManagementMenu(BaseMenu):
    """Menu para gestionar proyectos (crear, ver, editar, eliminar)."""

    def __init__(self):
        super().__init__()
        self.project_manager = get_project_manager()

    def show(self) -> None:
        """Muestra el menu de gestion de proyectos."""
        projects = self.project_manager.list_projects()

        if not projects:
            self.echo("\n  No hay proyectos guardados.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nueva cuenca' para comenzar.\n")
            return

        while True:
            # Recargar lista
            projects = self.project_manager.list_projects()

            if not projects:
                self.echo("\n  No quedan proyectos.\n")
                return

            self._show_overview(projects)

            choices = [
                "Ver detalles de un proyecto",
                "Gestionar cuencas de un proyecto",
                "Editar metadatos de proyecto",
                "Renombrar proyecto",
                "Eliminar proyecto",
                "Crear nuevo proyecto",
                "← Volver al menu principal",
            ]

            action = self.select("Que deseas hacer?", choices)

            if action is None or "Volver" in action:
                return

            self._handle_action(action, projects)

    def _show_overview(self, projects: list[dict]) -> None:
        """Muestra resumen de proyectos."""
        console = get_console()
        console.print()

        if projects:
            print_projects_table(projects[:10], title="Gestion de Proyectos")
            if len(projects) > 10:
                print_info(f"... y {len(projects) - 10} proyectos mas")

        total_basins = sum(p.get("n_basins", 0) for p in projects)
        console.print()
        print_info(f"Total: {len(projects)} proyectos, {total_basins} cuencas")
        console.print()

    def _handle_action(self, action: str, projects: list[dict]) -> None:
        """Maneja la accion seleccionada."""
        if "Ver detalles" in action:
            self._view_project_details(projects)
        elif "Gestionar cuencas" in action:
            self._manage_basins(projects)
        elif "Editar metadatos" in action:
            self._edit_project_metadata(projects)
        elif "Renombrar proyecto" in action:
            self._rename_project(projects)
        elif "Eliminar proyecto" in action:
            self._delete_project(projects)
        elif "Crear nuevo" in action:
            self._create_project()

    def _select_project(self, projects: list[dict], prompt: str) -> Optional[Project]:
        """Permite seleccionar un proyecto."""
        if not projects:
            self.echo("  No hay proyectos disponibles.")
            return None

        choices = [
            f"{p['id']} - {p['name']} ({p['n_basins']} cuencas)"
            for p in projects
        ]
        choices.append("← Cancelar")

        choice = self.select(prompt, choices)

        if choice is None or "Cancelar" in choice:
            return None

        project_id = choice.split(" - ")[0]
        return self.project_manager.get_project(project_id)

    def _view_project_details(self, projects: list[dict]) -> None:
        """Ver detalles de un proyecto."""
        project = self._select_project(projects, "Selecciona proyecto:")
        if not project:
            return

        self.project_info(project)

        if project.basins:
            self.section("Cuencas del proyecto")
            for b in project.basins:
                self.basin_info(b, project.name)

    def _manage_basins(self, projects: list[dict]) -> None:
        """Abre el menu de gestion de cuencas de un proyecto."""
        project = self._select_project(projects, "Selecciona proyecto para gestionar cuencas:")
        if not project:
            return

        menu = BasinManagementMenu(project)
        menu.show()

    def _edit_project_metadata(self, projects: list[dict]) -> None:
        """Edita metadatos de un proyecto."""
        project = self._select_project(projects, "Selecciona proyecto a editar:")
        if not project:
            return

        self.echo(f"\n  Editando metadatos de '{project.name}'...\n")

        new_name = self.text("Nombre:", default=project.name)
        if new_name:
            project.name = new_name

        new_desc = self.text("Descripcion:", default=project.description or "")
        if new_desc is not None:
            project.description = new_desc

        new_author = self.text("Autor:", default=project.author or "")
        if new_author is not None:
            project.author = new_author

        new_location = self.text("Ubicacion:", default=project.location or "")
        if new_location is not None:
            project.location = new_location

        self.project_manager.save_project(project)
        self.echo("\n  Metadatos actualizados.\n")

    def _rename_project(self, projects: list[dict]) -> None:
        """Renombrar un proyecto."""
        project = self._select_project(projects, "Selecciona proyecto a renombrar:")
        if not project:
            return

        new_name = self.text(
            f"Nuevo nombre (actual: {project.name}):",
            default=project.name,
        )

        if new_name and new_name != project.name:
            project.name = new_name
            self.project_manager.save_project(project)
            self.echo(f"\n  Proyecto renombrado a '{new_name}'\n")

    def _delete_project(self, projects: list[dict]) -> None:
        """Eliminar un proyecto."""
        project = self._select_project(projects, "Selecciona proyecto a eliminar:")
        if not project:
            return

        msg = f"Eliminar proyecto '{project.name}'"
        if project.basins:
            msg += f" y sus {project.n_basins} cuencas"
        msg += "?"

        if self.confirm(msg, default=False):
            if self.project_manager.delete_project(project.id):
                self.echo(f"\n  Proyecto '{project.name}' eliminado.\n")
            else:
                self.error("No se pudo eliminar el proyecto")

    def _create_project(self) -> None:
        """Crea un nuevo proyecto."""
        self.echo("\n  Crear nuevo proyecto\n")

        name = self.text("Nombre del proyecto:")
        if not name:
            return

        description = self.text("Descripcion (opcional):", default="")
        author = self.text("Autor (opcional):", default="")
        location = self.text("Ubicacion (opcional):", default="")

        project = self.project_manager.create_project(
            name=name,
            description=description or "",
            author=author or "",
            location=location or "",
        )

        self.echo(f"\n  Proyecto creado:")
        self.echo(f"    ID: {project.id}")
        self.echo(f"    Nombre: {project.name}")
        self.echo(f"\n  Usa 'Nueva cuenca' o 'Gestionar cuencas' para agregar cuencas.\n")
