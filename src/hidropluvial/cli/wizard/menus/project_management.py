"""
Menu para gestionar proyectos y cuencas.
"""

from typing import Optional

import questionary

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
from hidropluvial.project import Project, Basin, get_project_manager


class ProjectManagementMenu(BaseMenu):
    """Menu para gestionar proyectos y cuencas (ver, eliminar, renombrar, duplicar)."""

    def __init__(self):
        super().__init__()
        self.project_manager = get_project_manager()

    def show(self) -> None:
        """Muestra el menu de gestion de proyectos y cuencas."""
        projects = self.project_manager.list_projects()
        sessions = self.manager.list_sessions()  # Legacy sessions

        if not projects and not sessions:
            self.echo("\n  No hay proyectos ni cuencas guardadas.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nueva cuenca' para comenzar.\n")
            return

        while True:
            self._show_overview(projects, sessions)

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver detalles de un proyecto/cuenca",
                    "Exportar cuenca (Excel/LaTeX)",
                    "Editar cuenca",
                    "Duplicar cuenca",
                    "Renombrar proyecto/cuenca",
                    "Eliminar proyecto/cuenca",
                    "Eliminar cuencas vacias",
                    "Crear nuevo proyecto",
                    "Migrar sesiones legacy a proyecto",
                    "Volver al menu principal",
                ],
            )

            if action is None or "Volver" in action:
                return

            # Ejecutar accion y recargar listas
            self._handle_action(action, projects, sessions)
            projects = self.project_manager.list_projects()
            sessions = self.manager.list_sessions()

            if not projects and not sessions:
                self.echo("\n  No quedan proyectos ni cuencas.\n")
                return

    def _show_overview(self, projects: list[dict], sessions: list[dict]) -> None:
        """Muestra resumen de proyectos y cuencas."""
        total_projects = len(projects)
        total_sessions = len(sessions)
        total_basins = sum(p.get("n_basins", 0) for p in projects)

        self.echo(f"\n{'='*65}")
        self.echo(f"  GESTION DE PROYECTOS Y CUENCAS")
        self.echo(f"{'='*65}")

        if projects:
            self.echo(f"  {'ID':<10} {'Nombre':<28} {'Cuencas':>8} {'Analisis':>10}")
            self.echo(f"  {'-'*60}")

            for p in projects[:10]:
                name = p['name'][:27] if len(p['name']) > 27 else p['name']
                self.echo(
                    f"  {p['id']:<10} {name:<28} {p['n_basins']:>8} {p['total_analyses']:>10}"
                )

            if len(projects) > 10:
                self.echo(f"  ... y {len(projects) - 10} proyectos mas")

        if sessions:
            if projects:
                self.echo(f"\n  --- Sesiones Legacy (no migradas): {len(sessions)} ---")
            else:
                self.echo(f"  {'ID':<10} {'Nombre':<28} {'Cuenca':<15} {'N':>5}")
                self.echo(f"  {'-'*60}")

            for s in sessions[:5]:
                name = s['name'][:27] if len(s['name']) > 27 else s['name']
                cuenca = s['cuenca'][:14] if len(s['cuenca']) > 14 else s['cuenca']
                self.echo(f"  {s['id']:<10} {name:<28} {cuenca:<15} {s['n_analyses']:>5}")

            if len(sessions) > 5:
                self.echo(f"  ... y {len(sessions) - 5} sesiones mas")

        self.echo(f"{'='*65}\n")
        self.echo(f"  Total: {total_projects} proyectos, {total_basins + total_sessions} cuencas\n")

    def _handle_action(self, action: str, projects: list[dict], sessions: list[dict]) -> None:
        """Maneja la accion seleccionada."""
        if "Ver detalles" in action:
            self._view_details(projects, sessions)
        elif "Exportar" in action:
            self._export_basin(projects, sessions)
        elif "Editar cuenca" in action:
            self._edit_cuenca(projects, sessions)
        elif "Duplicar" in action:
            self._duplicate(projects, sessions)
        elif "Renombrar" in action:
            self._rename(projects, sessions)
        elif "Eliminar proyecto" in action:
            self._delete(projects, sessions)
        elif "vacias" in action:
            self._delete_empty(projects, sessions)
        elif "Crear nuevo" in action:
            self._create_project()
        elif "Migrar" in action:
            self._migrate_sessions(sessions)

    def _select_project_or_basin(
        self, projects: list[dict], sessions: list[dict], prompt: str
    ) -> Optional[tuple[str, str, Optional[str]]]:
        """
        Permite seleccionar un proyecto o cuenca.

        Returns:
            Tupla (tipo, id, parent_id) donde:
            - tipo: 'project', 'basin', o 'session'
            - id: ID del elemento
            - parent_id: ID del proyecto padre (solo para basins)
        """
        choices = []

        for p in projects:
            choices.append(f"[Proyecto] {p['id']} - {p['name']} ({p['n_basins']} cuencas)")

        for s in sessions:
            choices.append(f"[Cuenca legacy] {s['id']} - {s['name']} ({s['n_analyses']} analisis)")

        choices.append("← Cancelar")

        choice = self.select(prompt, choices)

        if choice is None or "Cancelar" in choice:
            return None

        if "[Proyecto]" in choice:
            project_id = choice.split(" - ")[0].replace("[Proyecto] ", "")
            return ("project", project_id, None)
        elif "[Cuenca legacy]" in choice:
            session_id = choice.split(" - ")[0].replace("[Cuenca legacy] ", "")
            return ("session", session_id, None)

        return None

    def _select_basin_from_project(self, project: Project) -> Optional[Basin]:
        """Permite seleccionar una cuenca de un proyecto."""
        if not project.basins:
            self.echo("  No hay cuencas en este proyecto.")
            return None

        choices = []
        for b in project.basins:
            choices.append(f"{b.id} - {b.name} ({len(b.analyses)} analisis)")
        choices.append("← Cancelar")

        choice = self.select("Selecciona una cuenca:", choices)

        if choice is None or "Cancelar" in choice:
            return None

        basin_id = choice.split(" - ")[0]
        return project.get_basin(basin_id)

    def _view_details(self, projects: list[dict], sessions: list[dict]) -> None:
        """Ver detalles de un proyecto o cuenca."""
        selection = self._select_project_or_basin(projects, sessions, "Selecciona:")

        if not selection:
            return

        sel_type, sel_id, _ = selection

        if sel_type == "project":
            project = self.project_manager.get_project(sel_id)
            if project:
                self._show_project_details(project)
        elif sel_type == "session":
            from hidropluvial.cli.session.base import session_show
            try:
                session_show(sel_id)
            except SystemExit:
                pass

    def _show_project_details(self, project: Project) -> None:
        """Muestra detalles de un proyecto."""
        self.echo(f"\n{'='*55}")
        self.echo(f"  PROYECTO: {project.name}")
        self.echo(f"{'='*55}")
        self.echo(f"  ID: {project.id}")
        if project.description:
            self.echo(f"  Descripcion: {project.description}")
        if project.author:
            self.echo(f"  Autor: {project.author}")
        if project.location:
            self.echo(f"  Ubicacion: {project.location}")
        self.echo(f"  Cuencas: {project.n_basins}")
        self.echo(f"  Total analisis: {project.total_analyses}")

        if project.basins:
            self.echo(f"\n  Cuencas del proyecto:")
            self.echo(f"  {'-'*50}")
            for b in project.basins:
                self.echo(f"    [{b.id}] {b.name}")
                self.echo(f"           Area: {b.area_ha} ha, S: {b.slope_pct}%")
                self.echo(f"           Analisis: {len(b.analyses)}")

        self.echo(f"{'='*55}\n")

    def _export_basin(self, projects: list[dict], sessions: list[dict]) -> None:
        """Exportar una cuenca a Excel o LaTeX."""
        # Construir lista de cuencas con analisis
        choices = []

        for p in projects:
            project = self.project_manager.get_project(p['id'])
            if project:
                for b in project.basins:
                    if b.analyses:
                        choices.append(
                            f"{b.id} - {b.name} [Proyecto: {project.name}] ({len(b.analyses)} analisis)"
                        )

        sessions_with_analyses = [s for s in sessions if s['n_analyses'] > 0]
        for s in sessions_with_analyses:
            choices.append(f"{s['id']} - {s['name']} [Legacy] ({s['n_analyses']} analisis)")

        if not choices:
            self.echo("\n  No hay cuencas con analisis para exportar.\n")
            return

        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca a exportar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        basin_id = choice.split(" - ")[0]

        # Buscar la cuenca
        session = None

        # Buscar en proyectos
        for p in projects:
            project = self.project_manager.get_project(p['id'])
            if project:
                basin = project.get_basin(basin_id)
                if basin:
                    session = basin.to_session()
                    break

        # Buscar en sesiones legacy
        if not session:
            session = self.manager.get_session(basin_id)

        if session:
            from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
            export_menu = ExportMenu(session)
            export_menu.show()

    def _rename(self, projects: list[dict], sessions: list[dict]) -> None:
        """Renombrar un proyecto o cuenca."""
        selection = self._select_project_or_basin(projects, sessions, "Selecciona a renombrar:")

        if not selection:
            return

        sel_type, sel_id, _ = selection

        if sel_type == "project":
            project = self.project_manager.get_project(sel_id)
            if project:
                new_name = self.text(
                    f"Nuevo nombre (actual: {project.name}):",
                    default=project.name,
                )
                if new_name and new_name != project.name:
                    project.name = new_name
                    self.project_manager.save_project(project)
                    self.echo(f"\n  Proyecto renombrado a '{new_name}'\n")

        elif sel_type == "session":
            session = self.manager.get_session(sel_id)
            if session:
                new_name = self.text(
                    f"Nuevo nombre (actual: {session.name}):",
                    default=session.name,
                )
                if new_name and new_name != session.name:
                    session.name = new_name
                    self.manager.save(session)
                    self.echo(f"\n  Cuenca renombrada a '{new_name}'\n")

    def _delete(self, projects: list[dict], sessions: list[dict]) -> None:
        """Eliminar un proyecto o cuenca."""
        selection = self._select_project_or_basin(projects, sessions, "Selecciona a eliminar:")

        if not selection:
            return

        sel_type, sel_id, _ = selection

        if sel_type == "project":
            project = self.project_manager.get_project(sel_id)
            if project:
                if self.confirm(
                    f"Eliminar proyecto '{project.name}' y todas sus cuencas?",
                    default=False,
                ):
                    if self.project_manager.delete_project(project.id):
                        self.echo(f"\n  Proyecto {project.id} eliminado.\n")
                    else:
                        self.echo(f"\n  Error al eliminar proyecto.\n")

        elif sel_type == "session":
            if self.confirm(f"Eliminar cuenca {sel_id}?", default=False):
                if self.manager.delete(sel_id):
                    self.echo(f"\n  Cuenca {sel_id} eliminada.\n")
                else:
                    self.echo(f"\n  Error al eliminar cuenca.\n")

    def _delete_empty(self, projects: list[dict], sessions: list[dict]) -> None:
        """Eliminar cuencas sin analisis."""
        empty_basins = []

        # Buscar en proyectos
        for p in projects:
            project = self.project_manager.get_project(p['id'])
            if project:
                for b in project.basins:
                    if not b.analyses:
                        empty_basins.append({
                            "type": "basin",
                            "id": b.id,
                            "name": b.name,
                            "project": project,
                        })

        # Buscar en sesiones legacy
        empty_sessions = [s for s in sessions if s['n_analyses'] == 0]
        for s in empty_sessions:
            empty_basins.append({
                "type": "session",
                "id": s['id'],
                "name": s['name'],
                "project": None,
            })

        if not empty_basins:
            self.echo("\n  No hay cuencas vacias.\n")
            return

        self.echo(f"\n  Cuencas vacias encontradas: {len(empty_basins)}")
        for item in empty_basins:
            project_name = f" [{item['project'].name}]" if item['project'] else " [Legacy]"
            self.echo(f"    - {item['id']}: {item['name']}{project_name}")

        if self.confirm(f"\nEliminar {len(empty_basins)} cuencas vacias?", default=False):
            deleted = 0
            for item in empty_basins:
                if item['type'] == 'basin':
                    project = item['project']
                    if project.remove_basin(item['id']):
                        self.project_manager.save_project(project)
                        deleted += 1
                else:
                    if self.manager.delete(item['id']):
                        deleted += 1

            self.echo(f"\n  {deleted} cuencas eliminadas.\n")

    def _edit_cuenca(self, projects: list[dict], sessions: list[dict]) -> None:
        """Editar parametros de una cuenca."""
        # Solo mostrar sesiones legacy por ahora
        # (para cuencas en proyectos usar el otro menu)
        if not sessions:
            self.echo("\n  No hay cuencas legacy para editar.\n")
            self.echo("  Para editar cuencas de proyectos, usa 'Continuar proyecto'.\n")
            return

        choices = [
            f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)"
            for s in sessions
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca a editar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        session_id = choice.split(" - ")[0]
        session = self.manager.get_session(session_id)
        cuenca = session.cuenca

        self._show_cuenca_values(session, cuenca)

        if session.analyses:
            self.echo(f"  ADVERTENCIA: Esta cuenca tiene {len(session.analyses)} analisis.")
            self.echo(f"  Al modificar la cuenca se eliminaran todos los analisis.\n")

        # Usar editor de cuenca
        editor = CuencaEditor(session, self.manager)
        editor.edit()

    def _show_cuenca_values(self, session, cuenca) -> None:
        """Muestra valores actuales de la cuenca."""
        self.echo(f"\n{'='*55}")
        self.echo(f"  EDITAR CUENCA: {session.name}")
        self.echo(f"{'='*55}")
        self.echo(f"  Valores actuales:")
        self.echo(f"    Area:      {cuenca.area_ha} ha")
        self.echo(f"    Pendiente: {cuenca.slope_pct} %")
        self.echo(f"    P3,10:     {cuenca.p3_10} mm")
        if cuenca.c is not None:
            self.echo(f"    Coef. C:   {cuenca.c}")
        if cuenca.cn is not None:
            self.echo(f"    CN:        {cuenca.cn}")
        if cuenca.length_m:
            self.echo(f"    Longitud:  {cuenca.length_m} m")
        self.echo(f"{'='*55}\n")

    def _duplicate(self, projects: list[dict], sessions: list[dict]) -> None:
        """Duplicar una cuenca existente."""
        if not sessions:
            self.echo("\n  No hay cuencas legacy para duplicar.\n")
            self.echo("  Para duplicar cuencas de proyectos, usa 'Continuar proyecto'.\n")
            return

        choices = [f"{s['id']} - {s['name']}" for s in sessions]
        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca a duplicar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        session_id = choice.split(" - ")[0]
        session = self.manager.get_session(session_id)

        new_name = self.text(
            "Nombre para la nueva cuenca:",
            default=f"{session.name} (copia)",
        )

        if not new_name:
            return

        new_session, changes = self.manager.clone_with_modified_cuenca(
            session,
            new_name=new_name,
        )

        self.echo(f"\n  Cuenca duplicada:")
        self.echo(f"    ID original: {session.id}")
        self.echo(f"    ID nueva:    {new_session.id}")
        self.echo(f"    Nombre:      {new_session.name}")
        self.echo(f"\n  La nueva cuenca no tiene analisis.")
        self.echo(f"  Usa 'Continuar proyecto/cuenca' para agregar analisis.\n")

    def _create_project(self) -> None:
        """Crea un nuevo proyecto vacio."""
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
        self.echo(f"\n  Usa 'Nueva cuenca' para agregar cuencas al proyecto.\n")

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


# Alias para compatibilidad
SessionManagementMenu = ProjectManagementMenu
