"""
Menu para continuar con una sesion existente.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.session import Session


class ContinueSessionMenu(BaseMenu):
    """Menu para continuar trabajando con una sesion existente."""

    def __init__(self):
        super().__init__()
        self.session: Optional[Session] = None

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

        self.session = self.manager.get_session(session_id)
        if not self.session:
            self.error(f"No se pudo cargar la sesión {session_id}")
            return

        # Mostrar menu de acciones en loop
        self._show_session_menu()

    def _select_session(self, sessions: list[dict]) -> Optional[str]:
        """Permite seleccionar una sesion."""
        choices = []
        for s in sessions:
            n_analyses = s["n_analyses"]
            choices.append(f"{s['id']} - {s['name']} ({n_analyses} analisis)")
        choices.append("← Volver al menu principal")

        choice = self.select("Selecciona una sesion:", choices)

        if choice is None or "Volver" in choice:
            return None

        return choice.split(" - ")[0]

    def _show_session_menu(self) -> None:
        """Muestra el menu de acciones para la sesion seleccionada."""
        while True:
            # Recargar sesion para tener datos actualizados
            self.session = self.manager.get_session(self.session.id)

            self._show_session_header()

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver tabla resumen",
                    "Ver fichas de analisis (navegacion interactiva)",
                    "Comparar hidrogramas",
                    "Ver hietograma",
                    "Agregar mas analisis",
                    "Filtrar resultados",
                    "Exportar (Excel/LaTeX)",
                    "Editar datos de la cuenca",
                    "Agregar/editar notas",
                    "Eliminar sesion",
                    "← Volver (elegir otra sesion)",
                    "← Salir al menu principal",
                ],
            )

            if action is None or "Salir" in action:
                return
            elif "otra sesion" in action.lower():
                # Volver a seleccionar sesion
                sessions = self.manager.list_sessions()
                session_id = self._select_session(sessions)
                if session_id:
                    self.session = self.manager.get_session(session_id)
                    if not self.session:
                        return
                else:
                    return
            else:
                self._handle_action(action)

    def _show_session_header(self) -> None:
        """Muestra encabezado con info de la sesion."""
        self.session_info(self.session)

    def _handle_action(self, action: str) -> None:
        """Maneja la accion seleccionada."""
        if "tabla" in action.lower():
            self._show_table()
        elif "fichas" in action.lower():
            self._show_interactive_viewer()
        elif "Comparar" in action:
            self._compare_hydrographs()
        elif "hietograma" in action.lower():
            self._show_hyetograph()
        elif "Agregar" in action and "analisis" in action.lower():
            self._add_analysis()
        elif "Filtrar" in action:
            self._filter_results()
        elif "Exportar" in action:
            self._export()
        elif "Editar" in action:
            self._edit_cuenca()
        elif "notas" in action.lower():
            self._manage_notes()
        elif "Eliminar" in action:
            if self._delete_session():
                return  # Salir del menu si se elimino

    def _safe_call(self, func, *args, **kwargs) -> None:
        """Ejecuta una funcion capturando typer.Exit."""
        try:
            func(*args, **kwargs)
        except SystemExit:
            pass

    def _show_table(self) -> None:
        """Muestra tabla con sparklines."""
        from hidropluvial.cli.session.preview import session_preview
        self._safe_call(session_preview, self.session.id, analysis_idx=None, compare=False)

    def _show_interactive_viewer(self) -> None:
        """Muestra visor interactivo de fichas de analisis."""
        self.show_analysis_cards()

    def _compare_hydrographs(self) -> None:
        """Compara hidrogramas con opcion de seleccionar cuales."""
        if not self.session.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        n = len(self.session.analyses)
        if n > 2:
            mode = self.select(
                "Que hidrogramas comparar?",
                choices=[
                    "Todos",
                    "Seleccionar cuales",
                    "← Cancelar",
                ],
            )

            if mode is None or "Cancelar" in mode:
                return

            if "Seleccionar" in mode:
                selected = self._select_analyses_to_compare()
                if selected:
                    from hidropluvial.cli.session.preview import session_preview
                    self._safe_call(
                        session_preview,
                        self.session.id,
                        compare=True,
                        select=selected,
                    )
                return

        from hidropluvial.cli.session.preview import session_preview
        self._safe_call(session_preview, self.session.id, compare=True)

    def _select_analyses_to_compare(self) -> Optional[str]:
        """Permite seleccionar analisis para comparar."""
        import questionary

        choices = []
        for i, a in enumerate(self.session.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            label = f"[{i}] {hydro.tc_method} {storm.type} Tr{storm.return_period}{x_str} Qp={hydro.peak_flow_m3s:.2f}"
            choices.append(questionary.Choice(label, checked=True))

        selected = self.checkbox("Selecciona analisis a comparar:", choices)

        if not selected:
            return None

        # Extraer indices
        indices = []
        for sel in selected:
            idx = int(sel.split("]")[0].replace("[", ""))
            indices.append(str(idx))

        return ",".join(indices)

    def _show_hyetograph(self) -> None:
        """Muestra hietograma de un analisis."""
        if not self.session.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        # Seleccionar cual
        choices = []
        for i, a in enumerate(self.session.analyses):
            storm = a.storm
            choices.append(f"{i}: {storm.type} Tr{storm.return_period} P={storm.total_depth_mm:.1f}mm")

        selected = self.select("Selecciona analisis:", choices)
        if selected:
            idx = int(selected.split(":")[0])
            from hidropluvial.cli.session.preview import session_preview
            self._safe_call(session_preview, self.session.id, analysis_idx=idx, hyetograph=True)

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la sesion."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu

        c = self.session.cuenca.c
        cn = self.session.cuenca.cn
        length = self.session.cuenca.length_m

        menu = AddAnalysisMenu(self.session, c, cn, length)
        menu.show()

    def _filter_results(self) -> None:
        """Filtra y muestra resultados."""
        if not self.session.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        # Obtener valores disponibles
        tr_values = sorted(set(a.storm.return_period for a in self.session.analyses))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.session.analyses))

        filter_type = self.select(
            "Filtrar por:",
            choices=[
                f"Periodo de retorno: {tr_values}",
                f"Metodo Tc: {tc_methods}",
                "← Cancelar",
            ],
        )

        if filter_type is None or "Cancelar" in filter_type:
            return

        if "retorno" in filter_type.lower():
            tr_choice = self.select("Selecciona Tr:", [str(t) for t in tr_values])
            if tr_choice:
                from hidropluvial.cli.session.preview import session_preview
                self._safe_call(session_preview, self.session.id, compare=True, tr=tr_choice)
        elif "Metodo" in filter_type:
            tc_choice = self.select("Selecciona metodo:", tc_methods)
            if tc_choice:
                from hidropluvial.cli.session.preview import session_preview
                self._safe_call(session_preview, self.session.id, compare=True, tc=tc_choice)

    def _export(self) -> None:
        """Exporta resultados."""
        from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
        export_menu = ExportMenu(self.session)
        export_menu.show()

    def _edit_cuenca(self) -> None:
        """Edita datos de la cuenca."""
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(self.session, self.manager)
        result = editor.edit()

        if result == "modified":
            # Recargar sesion
            self.session = self.manager.get_session(self.session.id)

    def _manage_notes(self) -> None:
        """Gestiona notas de la sesion."""
        current = self.session.notes or ""

        self.echo(f"\n  Notas actuales: {current if current else '(sin notas)'}\n")

        new_notes = self.text("Nuevas notas (vacio para eliminar):", default=current)

        if new_notes is not None:
            self.manager.set_session_notes(self.session, new_notes)
            self.echo("  Notas guardadas." if new_notes else "  Notas eliminadas.")

    def _delete_session(self) -> bool:
        """Elimina la sesion. Retorna True si se elimino."""
        if self.confirm(f"Seguro que deseas eliminar la sesion {self.session.id}?", default=False):
            if self.manager.delete(self.session.id):
                self.echo(f"\n  Sesion {self.session.id} eliminada.\n")
                return True
            else:
                self.error("No se pudo eliminar la sesión")
        return False
