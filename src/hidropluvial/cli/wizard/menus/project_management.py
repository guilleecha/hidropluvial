"""
Menu para gestionar proyectos.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.basin_management import BasinManagementMenu
from hidropluvial.cli.theme import (
    get_console, print_projects_table, print_sessions_table, print_info,
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
        sessions = self.manager.list_sessions()  # Legacy sessions

        if not projects and not sessions:
            self.echo("\n  No hay proyectos ni cuencas guardadas.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nueva cuenca' para comenzar.\n")
            return

        while True:
            # Recargar listas
            projects = self.project_manager.list_projects()
            sessions = self.manager.list_sessions()

            if not projects and not sessions:
                self.echo("\n  No quedan proyectos ni cuencas.\n")
                return

            self._show_overview(projects, sessions)

            # Construir opciones segun lo que existe
            choices = []

            if projects:
                choices.extend([
                    "Ver detalles de un proyecto",
                    "Gestionar cuencas de un proyecto",
                    "Editar metadatos de proyecto",
                    "Renombrar proyecto",
                    "Eliminar proyecto",
                ])

            choices.append("Crear nuevo proyecto")

            if sessions:
                choices.append("Migrar sesiones legacy a proyecto")
                choices.append("Gestionar sesiones legacy")

            choices.append("← Volver al menu principal")

            action = self.select("Que deseas hacer?", choices)

            if action is None or "Volver" in action:
                return

            self._handle_action(action, projects, sessions)

    def _show_overview(self, projects: list[dict], sessions: list[dict]) -> None:
        """Muestra resumen de proyectos."""
        console = get_console()
        console.print()

        if projects:
            print_projects_table(projects[:10], title="Gestion de Proyectos")
            if len(projects) > 10:
                print_info(f"... y {len(projects) - 10} proyectos mas")

        if sessions:
            console.print()
            print_sessions_table(sessions[:5], title=f"Sesiones Legacy ({len(sessions)} no migradas)")
            if len(sessions) > 5:
                print_info(f"... y {len(sessions) - 5} sesiones mas")

        total_basins = sum(p.get("n_basins", 0) for p in projects)
        console.print()
        print_info(f"Total: {len(projects)} proyectos, {total_basins + len(sessions)} cuencas")
        console.print()

    def _handle_action(self, action: str, projects: list[dict], sessions: list[dict]) -> None:
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
        elif "Migrar sesiones" in action:
            self._migrate_sessions(sessions)
        elif "Gestionar sesiones legacy" in action:
            self._manage_legacy_sessions(sessions)

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
                self.echo(f"\n  Error al eliminar proyecto.\n")

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

    def _migrate_sessions(self, sessions: list[dict]) -> None:
        """Migra sesiones legacy a un proyecto."""
        if not sessions:
            self.echo("\n  No hay sesiones legacy para migrar.\n")
            return

        self.echo(f"\n  Sesiones disponibles para migrar: {len(sessions)}")

        migrate_all = self.confirm("Migrar todas las sesiones a un nuevo proyecto?")

        if migrate_all:
            project_name = self.text(
                "Nombre del proyecto:",
                default="Proyecto Migrado",
            )

            if not project_name:
                return

            delete_originals = self.confirm(
                "Eliminar sesiones originales despues de migrar?",
                default=False,
            )

            project = self.project_manager.migrate_sessions_to_project(
                project_name=project_name,
                delete_sessions=delete_originals,
            )

            if project:
                self.echo(f"\n  Migracion completada:")
                self.echo(f"    Proyecto: {project.name} [{project.id}]")
                self.echo(f"    Cuencas migradas: {project.n_basins}")
                if delete_originals:
                    self.echo(f"    Sesiones originales eliminadas.")
                self.echo("")
            else:
                self.echo("\n  Error en la migracion.\n")
        else:
            self.echo("\n  Migracion individual no implementada aun.\n")

    def _manage_legacy_sessions(self, sessions: list[dict]) -> None:
        """Menu para gestionar sesiones legacy."""
        if not sessions:
            self.echo("\n  No hay sesiones legacy.\n")
            return

        while True:
            sessions = self.manager.list_sessions()
            if not sessions:
                self.echo("\n  No quedan sesiones legacy.\n")
                return

            console = get_console()
            console.print()
            print_sessions_table(sessions, title="Sesiones Legacy")

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver detalles de sesion",
                    "Renombrar sesion",
                    "Eliminar sesion",
                    "Eliminar sesiones vacias",
                    "← Volver",
                ],
            )

            if action is None or "Volver" in action:
                return

            if "Ver detalles" in action:
                self._view_session_details(sessions)
            elif "Renombrar" in action:
                self._rename_session(sessions)
            elif "Eliminar sesion" in action and "vacias" not in action:
                self._delete_session(sessions)
            elif "vacias" in action:
                self._delete_empty_sessions(sessions)

    def _select_session(self, sessions: list[dict], prompt: str) -> Optional[str]:
        """Permite seleccionar una sesion legacy."""
        choices = [
            f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)"
            for s in sessions
        ]
        choices.append("← Cancelar")

        choice = self.select(prompt, choices)

        if choice is None or "Cancelar" in choice:
            return None

        return choice.split(" - ")[0]

    def _view_session_details(self, sessions: list[dict]) -> None:
        """Ver detalles de una sesion legacy."""
        session_id = self._select_session(sessions, "Selecciona sesion:")
        if not session_id:
            return

        from hidropluvial.cli.session.base import session_show
        try:
            session_show(session_id)
        except SystemExit:
            pass

    def _rename_session(self, sessions: list[dict]) -> None:
        """Renombrar una sesion legacy."""
        session_id = self._select_session(sessions, "Selecciona sesion a renombrar:")
        if not session_id:
            return

        session = self.manager.get_session(session_id)
        if not session:
            return

        new_name = self.text(
            f"Nuevo nombre (actual: {session.name}):",
            default=session.name,
        )

        if new_name and new_name != session.name:
            session.name = new_name
            self.manager.save(session)
            self.echo(f"\n  Sesion renombrada a '{new_name}'\n")

    def _delete_session(self, sessions: list[dict]) -> None:
        """Eliminar una sesion legacy."""
        session_id = self._select_session(sessions, "Selecciona sesion a eliminar:")
        if not session_id:
            return

        if self.confirm(f"Eliminar sesion {session_id}?", default=False):
            if self.manager.delete(session_id):
                self.echo(f"\n  Sesion {session_id} eliminada.\n")
            else:
                self.echo(f"\n  Error al eliminar sesion.\n")

    def _delete_empty_sessions(self, sessions: list[dict]) -> None:
        """Eliminar sesiones sin analisis."""
        empty_sessions = [s for s in sessions if s['n_analyses'] == 0]

        if not empty_sessions:
            self.echo("\n  No hay sesiones vacias.\n")
            return

        self.echo(f"\n  Sesiones vacias encontradas: {len(empty_sessions)}")
        for s in empty_sessions:
            self.echo(f"    - {s['id']}: {s['name']}")

        if self.confirm(f"\nEliminar {len(empty_sessions)} sesiones vacias?", default=False):
            deleted = 0
            for s in empty_sessions:
                if self.manager.delete(s['id']):
                    deleted += 1

            self.echo(f"\n  {deleted} sesiones eliminadas.\n")


# Alias para compatibilidad
SessionManagementMenu = ProjectManagementMenu
