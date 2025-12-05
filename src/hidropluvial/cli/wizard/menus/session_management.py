"""
Menu para gestionar sesiones.
"""

from typing import Optional

import questionary

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor


class SessionManagementMenu(BaseMenu):
    """Menu para gestionar sesiones (ver, eliminar, renombrar, duplicar)."""

    def show(self) -> None:
        """Muestra el menu de gestion de sesiones."""
        sessions = self.manager.list_sessions()

        if not sessions:
            self.echo("\n  No hay sesiones guardadas.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nuevo analisis' para comenzar.\n")
            return

        while True:
            self._show_sessions_table(sessions)

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver detalles de una sesion",
                    "Exportar sesion (Excel/LaTeX)",
                    "Editar cuenca",
                    "Duplicar sesion",
                    "Renombrar sesion",
                    "Eliminar sesion",
                    "Eliminar sesiones vacias",
                    "Volver al menu principal",
                ],
            )

            if action is None or "Volver" in action:
                return

            # Ejecutar accion y recargar lista
            self._handle_action(action, sessions)
            sessions = self.manager.list_sessions()

            if not sessions:
                self.echo("\n  No quedan sesiones.\n")
                return

    def _show_sessions_table(self, sessions: list[dict]) -> None:
        """Muestra tabla de sesiones."""
        self.echo(f"\n{'='*65}")
        self.echo(f"  SESIONES GUARDADAS ({len(sessions)})")
        self.echo(f"{'='*65}")
        self.echo(f"  {'ID':<10} {'Nombre':<28} {'Cuenca':<15} {'N':>5}")
        self.echo(f"  {'-'*60}")

        for s in sessions[:15]:
            name = s['name'][:27] if len(s['name']) > 27 else s['name']
            cuenca = s['cuenca'][:14] if len(s['cuenca']) > 14 else s['cuenca']
            self.echo(f"  {s['id']:<10} {name:<28} {cuenca:<15} {s['n_analyses']:>5}")

        if len(sessions) > 15:
            self.echo(f"  ... y {len(sessions) - 15} mas")
        self.echo(f"{'='*65}\n")

    def _handle_action(self, action: str, sessions: list[dict]) -> None:
        """Maneja la accion seleccionada."""
        if "Ver detalles" in action:
            self._view_details(sessions)
        elif "Exportar" in action:
            self._export_session(sessions)
        elif "Editar cuenca" in action:
            self._edit_cuenca(sessions)
        elif "Duplicar" in action:
            self._duplicate(sessions)
        elif "Renombrar" in action:
            self._rename(sessions)
        elif "Eliminar sesion" in action:
            self._delete(sessions)
        elif "vacias" in action:
            self._delete_empty(sessions)

    def _select_session(self, sessions: list[dict], prompt: str) -> Optional[str]:
        """Permite seleccionar una sesion de la lista."""
        choices = [f"{s['id']} - {s['name']}" for s in sessions]
        choices.append("Cancelar")

        choice = self.select(prompt, choices)

        if choice is None or choice == "Cancelar":
            return None

        return choice.split(" - ")[0]

    def _view_details(self, sessions: list[dict]) -> None:
        """Ver detalles de una sesion."""
        session_id = self._select_session(sessions, "Selecciona sesion:")
        if session_id:
            from hidropluvial.cli.session.base import session_show
            try:
                session_show(session_id)
            except SystemExit:
                pass  # Capturar typer.Exit

    def _export_session(self, sessions: list[dict]) -> None:
        """Exportar una sesion a Excel o LaTeX."""
        # Filtrar sesiones con analisis
        sessions_with_analyses = [s for s in sessions if s['n_analyses'] > 0]

        if not sessions_with_analyses:
            self.echo("\n  No hay sesiones con analisis para exportar.\n")
            return

        choices = [
            f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)"
            for s in sessions_with_analyses
        ]
        choices.append("Cancelar")

        choice = self.select("Selecciona sesion a exportar:", choices)

        if choice is None or choice == "Cancelar":
            return

        session_id = choice.split(" - ")[0]
        session = self.manager.get_session(session_id)

        if session:
            from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
            export_menu = ExportMenu(session)
            export_menu.show()

    def _rename(self, sessions: list[dict]) -> None:
        """Renombrar una sesion."""
        session_id = self._select_session(sessions, "Selecciona sesion a renombrar:")
        if not session_id:
            return

        session = self.manager.get_session(session_id)
        new_name = self.text(
            f"Nuevo nombre (actual: {session.name}):",
            default=session.name,
        )

        if new_name and new_name != session.name:
            session.name = new_name
            self.manager.save(session)
            self.echo(f"\n  Sesion renombrada a '{new_name}'\n")

    def _delete(self, sessions: list[dict]) -> None:
        """Eliminar una sesion."""
        choices = [f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)" for s in sessions]
        choices.append("Cancelar")

        choice = self.select("Selecciona sesion a eliminar:", choices)

        if choice is None or choice == "Cancelar":
            return

        session_id = choice.split(" - ")[0]

        if self.confirm(f"Seguro que deseas eliminar la sesion {session_id}?", default=False):
            if self.manager.delete(session_id):
                self.echo(f"\n  Sesion {session_id} eliminada.\n")
            else:
                self.echo(f"\n  Error al eliminar sesion.\n")

    def _delete_empty(self, sessions: list[dict]) -> None:
        """Eliminar sesiones sin analisis."""
        empty = [s for s in sessions if s['n_analyses'] == 0]

        if not empty:
            self.echo("\n  No hay sesiones vacias.\n")
            return

        self.echo(f"\n  Sesiones vacias encontradas: {len(empty)}")
        for s in empty:
            self.echo(f"    - {s['id']}: {s['name']}")

        if self.confirm(f"\nEliminar {len(empty)} sesiones vacias?", default=False):
            deleted = sum(1 for s in empty if self.manager.delete(s['id']))
            self.echo(f"\n  {deleted} sesiones eliminadas.\n")

    def _edit_cuenca(self, sessions: list[dict]) -> None:
        """Editar parametros de cuenca de una sesion."""
        choices = [f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)" for s in sessions]
        choices.append("Cancelar")

        choice = self.select("Selecciona sesion a editar:", choices)

        if choice is None or choice == "Cancelar":
            return

        session_id = choice.split(" - ")[0]
        session = self.manager.get_session(session_id)
        cuenca = session.cuenca

        self._show_cuenca_values(session, cuenca)

        if session.analyses:
            self.echo(f"  ADVERTENCIA: Esta sesion tiene {len(session.analyses)} analisis.")
            self.echo(f"  Al modificar la cuenca se eliminaran todos los analisis.\n")

        # Preguntar que editar
        params_to_edit = self.checkbox(
            "Selecciona parametros a modificar:",
            [
                "Area (ha)",
                "Pendiente (%)",
                "P3,10 (mm)",
                "Coeficiente C",
                "Curve Number (CN)",
                "Longitud cauce (m)",
            ],
        )

        if not params_to_edit:
            self.echo("\n  No se seleccionaron parametros.\n")
            return

        new_values = self._collect_cuenca_values(cuenca, params_to_edit)

        if not new_values:
            self.echo("\n  No se ingresaron valores nuevos.\n")
            return

        # Confirmar cambios
        self.echo(f"\n  Cambios a aplicar:")
        for k, v in new_values.items():
            self.echo(f"    {k}: {v}")

        if self.confirm("\nAplicar cambios? (se eliminaran los analisis existentes)", default=False):
            changes = self.manager.update_cuenca_in_place(session, **new_values, clear_analyses=True)
            self.echo(f"\n  Sesion actualizada.")
            for c in changes:
                self.echo(f"    - {c}")
            self.echo(f"\n  Usa 'Continuar sesion' para recalcular Tc y analisis.\n")

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

    def _collect_cuenca_values(self, cuenca, params_to_edit: list) -> dict:
        """Recolecta nuevos valores de cuenca."""
        new_values = {}
        params_str = str(params_to_edit)

        if "Area" in params_str:
            val = self.text(f"Nueva area [actual: {cuenca.area_ha}]:", default=str(cuenca.area_ha))
            if val:
                new_values['area_ha'] = float(val)

        if "Pendiente" in params_str:
            val = self.text(f"Nueva pendiente [actual: {cuenca.slope_pct}]:", default=str(cuenca.slope_pct))
            if val:
                new_values['slope_pct'] = float(val)

        if "P3,10" in params_str:
            val = self.text(f"Nuevo P3,10 [actual: {cuenca.p3_10}]:", default=str(cuenca.p3_10))
            if val:
                new_values['p3_10'] = float(val)

        if "Coeficiente C" in params_str:
            current = cuenca.c if cuenca.c else 0.5
            val = self.text(f"Nuevo coef. C [actual: {cuenca.c}]:", default=str(current))
            if val:
                new_values['c'] = float(val)

        if "Curve Number" in params_str:
            current = cuenca.cn if cuenca.cn else 75
            val = self.text(f"Nuevo CN [actual: {cuenca.cn}]:", default=str(current))
            if val:
                new_values['cn'] = int(val)

        if "Longitud" in params_str:
            current = cuenca.length_m if cuenca.length_m else 1000
            val = self.text(f"Nueva longitud [actual: {cuenca.length_m}]:", default=str(current))
            if val:
                new_values['length_m'] = float(val)

        return new_values

    def _duplicate(self, sessions: list[dict]) -> None:
        """Duplicar una sesion existente."""
        session_id = self._select_session(sessions, "Selecciona sesion a duplicar:")
        if not session_id:
            return

        session = self.manager.get_session(session_id)
        new_name = self.text(
            "Nombre para la nueva sesion:",
            default=f"{session.name} (copia)",
        )

        if not new_name:
            return

        # Clonar sesion
        new_session, changes = self.manager.clone_with_modified_cuenca(
            session,
            new_name=new_name,
        )

        self.echo(f"\n  Sesion duplicada:")
        self.echo(f"    ID original: {session.id}")
        self.echo(f"    ID nueva:    {new_session.id}")
        self.echo(f"    Nombre:      {new_session.name}")
        self.echo(f"\n  La nueva sesion no tiene analisis.")
        self.echo(f"  Usa 'Continuar sesion' para agregar analisis.\n")
