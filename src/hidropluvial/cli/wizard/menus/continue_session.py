"""
Menu para continuar con una sesion existente.
"""

from hidropluvial.cli.wizard.menus.base import BaseMenu


class ContinueSessionMenu(BaseMenu):
    """Menu para continuar trabajando con una sesion existente."""

    def show(self) -> None:
        """Muestra el menu para continuar una sesion."""
        sessions = self.manager.list_sessions()

        if not sessions:
            self.echo("\n  No hay sesiones guardadas.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nuevo analisis' para comenzar.\n")
            return

        # Seleccionar sesion
        session_id = self._select_session(sessions)
        if not session_id:
            return

        # Seleccionar accion
        action = self._select_action()
        if not action:
            return

        # Ejecutar accion
        self._execute_action(action, session_id)

    def _select_session(self, sessions: list[dict]) -> str:
        """Permite seleccionar una sesion."""
        choices = []
        for s in sessions:
            n_analyses = s["n_analyses"]
            choices.append(f"{s['id']} - {s['name']} ({n_analyses} analisis)")

        choice = self.select("Selecciona una sesion:", choices)

        if choice is None:
            return None

        return choice.split(" - ")[0]

    def _select_action(self) -> str:
        """Permite seleccionar la accion a realizar."""
        return self.select(
            "Que deseas hacer?",
            choices=[
                "Ver resumen",
                "Agregar analisis",
                "Generar reporte",
                "Eliminar sesion",
            ],
        )

    def _execute_action(self, action: str, session_id: str) -> None:
        """Ejecuta la accion seleccionada."""
        if "resumen" in action.lower():
            self._show_summary(session_id)
        elif "Agregar" in action:
            self._add_analysis(session_id)
        elif "reporte" in action.lower():
            self._generate_report(session_id)
        elif "Eliminar" in action:
            self._delete_session(session_id)

    def _show_summary(self, session_id: str) -> None:
        """Muestra resumen de la sesion."""
        from hidropluvial.cli.session.base import session_summary
        session_summary(session_id)

    def _add_analysis(self, session_id: str) -> None:
        """Abre el menu para agregar analisis."""
        session = self.manager.get_session(session_id)
        if session:
            from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
            menu = PostExecutionMenu(session)
            menu.show()

    def _generate_report(self, session_id: str) -> None:
        """Genera reporte LaTeX."""
        output = self.text("Nombre del archivo (sin extension):")
        if output:
            from hidropluvial.cli.session.report import session_report
            session_report(session_id, output, author=None, template_dir=None)

    def _delete_session(self, session_id: str) -> None:
        """Elimina la sesion."""
        if self.confirm(f"Seguro que deseas eliminar la sesion {session_id}?", default=False):
            from hidropluvial.cli.session.base import session_delete
            session_delete(session_id, force=True)
