"""
Menu para continuar con un proyecto/cuenca existente.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.theme import get_console, print_basins_detail_table
from hidropluvial.project import Project, Basin, ProjectManager


class ContinueProjectMenu(BaseMenu):
    """Menu para continuar trabajando con un proyecto/cuenca existente."""

    def __init__(self):
        super().__init__()
        self.project_manager = ProjectManager()
        self.project: Optional[Project] = None
        self.basin: Optional[Basin] = None

    def show(self) -> None:
        """Muestra el menu para continuar un proyecto."""
        projects = self.project_manager.list_projects()

        # Tambien mostrar sesiones legacy si existen
        sessions = self.manager.list_sessions()

        if not projects and not sessions:
            self.echo("\n  No hay proyectos ni cuencas guardadas.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nueva cuenca' para comenzar.\n")
            return

        # Seleccionar proyecto o sesion legacy
        selection = self._select_project_or_session(projects, sessions)
        if not selection:
            return

        sel_type, sel_id = selection

        if sel_type == "project":
            self.project = self.project_manager.get_project(sel_id)
            if not self.project:
                self.echo(f"\n  Error: No se pudo cargar el proyecto {sel_id}\n")
                return
            self._show_project_menu()

        elif sel_type == "session":
            # Cargar sesion legacy como Basin
            session = self.manager.get_session(sel_id)
            if not session:
                self.echo(f"\n  Error: No se pudo cargar la sesion {sel_id}\n")
                return
            # Convertir a Basin
            self.basin = Basin.from_session(session)
            self._show_basin_menu()

    def _select_project_or_session(
        self, projects: list[dict], sessions: list[dict]
    ) -> Optional[tuple[str, str]]:
        """Permite seleccionar un proyecto o sesion legacy."""
        choices = []

        # Proyectos primero
        if projects:
            for p in projects:
                n_basins = p.get("n_basins", 0)
                n_analyses = p.get("total_analyses", 0)
                choices.append(
                    f"[Proyecto] {p['id']} - {p['name']} ({n_basins} cuencas, {n_analyses} analisis)"
                )

        # Sesiones legacy
        if sessions:
            if projects:
                choices.append("--- Sesiones legacy (no migradas) ---")
            for s in sessions:
                n_analyses = s["n_analyses"]
                choices.append(
                    f"[Cuenca] {s['id']} - {s['name']} ({n_analyses} analisis)"
                )

        choices.append("← Volver al menu principal")

        choice = self.select("Selecciona un proyecto o cuenca:", choices)

        if choice is None or "Volver" in choice or choice.startswith("---"):
            return None

        # Parsear seleccion
        if "[Proyecto]" in choice:
            project_id = choice.split(" - ")[0].replace("[Proyecto] ", "")
            return ("project", project_id)
        elif "[Cuenca]" in choice:
            session_id = choice.split(" - ")[0].replace("[Cuenca] ", "")
            return ("session", session_id)

        return None

    def _show_project_menu(self) -> None:
        """Muestra el menu de acciones para el proyecto."""
        while True:
            # Recargar proyecto
            self.project = self.project_manager.get_project(self.project.id)

            self._show_project_header()

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver cuencas del proyecto",
                    "Seleccionar cuenca para trabajar",
                    "Agregar nueva cuenca al proyecto",
                    "Editar metadatos del proyecto",
                    "Eliminar proyecto",
                    "← Volver (elegir otro proyecto)",
                    "← Salir al menu principal",
                ],
            )

            if action is None or "Salir" in action:
                return
            elif "otro proyecto" in action.lower():
                projects = self.project_manager.list_projects()
                sessions = self.manager.list_sessions()
                selection = self._select_project_or_session(projects, sessions)
                if selection:
                    sel_type, sel_id = selection
                    if sel_type == "project":
                        self.project = self.project_manager.get_project(sel_id)
                    else:
                        session = self.manager.get_session(sel_id)
                        self.basin = Basin.from_session(session)
                        self._show_basin_menu()
                        return
                else:
                    return
            else:
                self._handle_project_action(action)

    def _show_project_header(self) -> None:
        """Muestra encabezado con info del proyecto."""
        self.echo(f"\n{'='*60}")
        self.echo(f"  PROYECTO: {self.project.name} [{self.project.id}]")
        self.echo(f"{'='*60}")
        if self.project.description:
            self.echo(f"  Descripcion: {self.project.description}")
        self.echo(f"  Cuencas: {self.project.n_basins}")
        self.echo(f"  Total analisis: {self.project.total_analyses}")
        self.echo(f"{'='*60}\n")

    def _handle_project_action(self, action: str) -> None:
        """Maneja la accion seleccionada para el proyecto."""
        if "Ver cuencas" in action:
            self._list_basins()
        elif "Seleccionar cuenca" in action:
            basin = self._select_basin()
            if basin:
                self.basin = basin
                self._show_basin_menu()
        elif "Agregar nueva" in action:
            self._add_basin_to_project()
        elif "Editar metadatos" in action:
            self._edit_project_metadata()
        elif "Eliminar proyecto" in action:
            if self._delete_project():
                return

    def _list_basins(self) -> None:
        """Lista las cuencas del proyecto."""
        console = get_console()
        console.print()
        print_basins_detail_table(
            self.project.basins,
            title=f"Cuencas en {self.project.name}"
        )
        console.print()

    def _select_basin(self) -> Optional[Basin]:
        """Permite seleccionar una cuenca del proyecto."""
        if not self.project.basins:
            self.echo("  No hay cuencas en este proyecto.")
            return None

        choices = []
        for b in self.project.basins:
            choices.append(f"{b.id} - {b.name} ({len(b.analyses)} analisis)")
        choices.append("← Cancelar")

        choice = self.select("Selecciona una cuenca:", choices)

        if choice is None or "Cancelar" in choice:
            return None

        basin_id = choice.split(" - ")[0]
        return self.project.get_basin(basin_id)

    def _add_basin_to_project(self) -> None:
        """Agrega una nueva cuenca al proyecto usando el wizard."""
        from hidropluvial.cli.wizard.config import WizardConfig
        from hidropluvial.cli.wizard.runner import AnalysisRunner

        self.echo("\n  Configurando nueva cuenca para el proyecto...\n")

        # Usar WizardConfig pero forzar el proyecto actual
        config = WizardConfig.from_wizard(project_id=self.project.id)
        if config is None:
            return

        config.print_summary()

        if not self.confirm("\nEjecutar analisis?", default=True):
            return

        runner = AnalysisRunner(config)
        _, basin = runner.run()

        self.echo(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

    def _edit_project_metadata(self) -> None:
        """Edita metadatos del proyecto."""
        self.echo("\n  Editando metadatos del proyecto...\n")

        new_name = self.text("Nombre:", default=self.project.name)
        if new_name:
            self.project.name = new_name

        new_desc = self.text("Descripcion:", default=self.project.description)
        if new_desc is not None:
            self.project.description = new_desc

        new_author = self.text("Autor:", default=self.project.author)
        if new_author is not None:
            self.project.author = new_author

        self.project_manager.save_project(self.project)
        self.echo("  Metadatos actualizados.\n")

    def _delete_project(self) -> bool:
        """Elimina el proyecto."""
        if self.confirm(
            f"Seguro que deseas eliminar el proyecto '{self.project.name}' y todas sus cuencas?",
            default=False,
        ):
            if self.project_manager.delete_project(self.project.id):
                self.echo(f"\n  Proyecto {self.project.id} eliminado.\n")
                return True
            else:
                self.echo("\n  Error al eliminar proyecto.\n")
        return False

    # ========================================================================
    # Menu de Cuenca (Basin)
    # ========================================================================

    def _show_basin_menu(self) -> None:
        """Muestra el menu de acciones para la cuenca seleccionada."""
        while True:
            self._show_basin_header()

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver tabla resumen",
                    "Ver hidrogramas (navegacion interactiva)",
                    "Comparar hidrogramas",
                    "Ver hietograma",
                    "Agregar mas analisis",
                    "Filtrar resultados",
                    "Exportar (Excel/LaTeX)",
                    "Editar datos de la cuenca",
                    "Agregar/editar notas",
                    "Eliminar cuenca",
                    "← Volver (elegir otra cuenca)",
                    "← Salir al menu principal",
                ],
            )

            if action is None or "Salir" in action:
                return
            elif "otra cuenca" in action.lower():
                if self.project:
                    basin = self._select_basin()
                    if basin:
                        self.basin = basin
                    else:
                        return
                else:
                    # Volver a seleccionar proyecto/sesion
                    return
            else:
                self._handle_basin_action(action)

    def _show_basin_header(self) -> None:
        """Muestra encabezado con info de la cuenca."""
        self.echo(f"\n{'='*60}")
        self.echo(f"  CUENCA: {self.basin.name} [{self.basin.id}]")
        if self.project:
            self.echo(f"  Proyecto: {self.project.name}")
        self.echo(f"{'='*60}")
        self.echo(f"  Area: {self.basin.area_ha} ha, S={self.basin.slope_pct}%")
        self.echo(f"  Analisis: {len(self.basin.analyses)}")
        if self.basin.analyses:
            trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
            self.echo(f"  Periodos de retorno: {trs}")
        self.echo(f"{'='*60}\n")

    def _handle_basin_action(self, action: str) -> None:
        """Maneja la accion seleccionada para la cuenca."""
        # Convertir Basin a Session para usar funciones existentes
        session = self.basin.to_session()

        if "tabla" in action.lower():
            self._show_table(session)
        elif "navegacion" in action.lower():
            self._show_interactive_viewer()
        elif "Comparar" in action:
            self._compare_hydrographs(session)
        elif "hietograma" in action.lower():
            self._show_hyetograph(session)
        elif "Agregar" in action and "analisis" in action.lower():
            self._add_analysis()
        elif "Filtrar" in action:
            self._filter_results(session)
        elif "Exportar" in action:
            self._export(session)
        elif "Editar" in action:
            self._edit_basin()
        elif "notas" in action.lower():
            self._manage_notes()
        elif "Eliminar" in action:
            if self._delete_basin():
                return

    def _safe_call(self, func, *args, **kwargs) -> None:
        """Ejecuta una funcion capturando typer.Exit."""
        try:
            func(*args, **kwargs)
        except SystemExit:
            pass

    def _show_table(self, session) -> None:
        """Muestra tabla con sparklines."""
        from hidropluvial.cli.session.preview import session_preview
        # Guardar session temporal para usar CLI existente
        self.manager.save(session)
        self._safe_call(session_preview, session.id, analysis_idx=None, compare=False)

    def _show_interactive_viewer(self) -> None:
        """Muestra visor interactivo de hidrogramas."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer
        interactive_hydrograph_viewer(self.basin.analyses, self.basin.name)

    def _compare_hydrographs(self, session) -> None:
        """Compara hidrogramas con opcion de seleccionar cuales."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        n = len(self.basin.analyses)
        if n > 2:
            mode = self.select(
                "Que hidrogramas comparar?",
                choices=["Todos", "Seleccionar cuales", "Cancelar"],
            )

            if mode is None or "Cancelar" in mode:
                return

            if "Seleccionar" in mode:
                selected = self._select_analyses_to_compare()
                if selected:
                    from hidropluvial.cli.session.preview import session_preview
                    self._safe_call(session_preview, session.id, compare=True, select=selected)
                return

        from hidropluvial.cli.session.preview import session_preview
        self._safe_call(session_preview, session.id, compare=True)

    def _select_analyses_to_compare(self) -> Optional[str]:
        """Permite seleccionar analisis para comparar."""
        import questionary
        from hidropluvial.cli.formatters import format_flow

        choices = []
        for i, a in enumerate(self.basin.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            label = f"[{i}] {hydro.tc_method} {storm.type} Tr{storm.return_period}{x_str} Qp={format_flow(hydro.peak_flow_m3s)}"
            choices.append(questionary.Choice(label, checked=True))

        selected = self.checkbox("Selecciona analisis a comparar:", choices)

        if not selected:
            return None

        indices = []
        for sel in selected:
            idx = int(sel.split("]")[0].replace("[", ""))
            indices.append(str(idx))

        return ",".join(indices)

    def _show_hyetograph(self, session) -> None:
        """Muestra hietograma de un analisis."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        choices = []
        for i, a in enumerate(self.basin.analyses):
            storm = a.storm
            choices.append(f"{i}: {storm.type} Tr{storm.return_period} P={storm.total_depth_mm:.1f}mm")

        selected = self.select("Selecciona analisis:", choices)
        if selected:
            idx = int(selected.split(":")[0])
            from hidropluvial.cli.session.preview import session_preview
            self._safe_call(session_preview, session.id, analysis_idx=idx, hyetograph=True)

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la cuenca."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu

        # Convertir a session para compatibilidad
        session = self.basin.to_session()

        c = self.basin.c
        cn = self.basin.cn
        length = self.basin.length_m

        menu = AddAnalysisMenu(session, c, cn, length)
        menu.show()

        # Recargar basin desde session actualizada
        updated_session = self.manager.get_session(session.id)
        if updated_session:
            self.basin = Basin.from_session(updated_session)

    def _filter_results(self, session) -> None:
        """Filtra y muestra resultados."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        tr_values = sorted(set(a.storm.return_period for a in self.basin.analyses))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.basin.analyses))

        filter_type = self.select(
            "Filtrar por:",
            choices=[
                f"Periodo de retorno: {tr_values}",
                f"Metodo Tc: {tc_methods}",
                "Cancelar",
            ],
        )

        if filter_type is None or "Cancelar" in filter_type:
            return

        if "retorno" in filter_type.lower():
            tr_choice = self.select("Selecciona Tr:", [str(t) for t in tr_values])
            if tr_choice:
                from hidropluvial.cli.session.preview import session_preview
                self._safe_call(session_preview, session.id, compare=True, tr=tr_choice)
        elif "Metodo" in filter_type:
            tc_choice = self.select("Selecciona metodo:", tc_methods)
            if tc_choice:
                from hidropluvial.cli.session.preview import session_preview
                self._safe_call(session_preview, session.id, compare=True, tc=tc_choice)

    def _export(self, session) -> None:
        """Exporta resultados."""
        from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
        export_menu = ExportMenu(session)
        export_menu.show()

    def _edit_basin(self) -> None:
        """Edita datos de la cuenca."""
        session = self.basin.to_session()
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(session, self.manager)
        result = editor.edit()

        if result == "modified":
            updated_session = self.manager.get_session(session.id)
            if updated_session:
                self.basin = Basin.from_session(updated_session)

    def _manage_notes(self) -> None:
        """Gestiona notas de la cuenca."""
        current = self.basin.notes or ""

        self.echo(f"\n  Notas actuales: {current if current else '(sin notas)'}\n")

        new_notes = self.text("Nuevas notas (vacio para eliminar):", default=current)

        if new_notes is not None:
            self.basin.notes = new_notes
            # Guardar via session
            session = self.basin.to_session()
            self.manager.set_session_notes(session, new_notes)
            self.echo("  Notas guardadas." if new_notes else "  Notas eliminadas.")

    def _delete_basin(self) -> bool:
        """Elimina la cuenca."""
        if self.confirm(f"Seguro que deseas eliminar la cuenca '{self.basin.name}'?", default=False):
            # Si esta en un proyecto, eliminar del proyecto
            if self.project:
                if self.project.remove_basin(self.basin.id):
                    self.project_manager.save_project(self.project)
                    self.echo(f"\n  Cuenca '{self.basin.name}' eliminada del proyecto.\n")
                    return True
            else:
                # Es una sesion legacy
                if self.manager.delete(self.basin.id):
                    self.echo(f"\n  Cuenca {self.basin.id} eliminada.\n")
                    return True
            self.echo("\n  Error al eliminar cuenca.\n")
        return False
