"""
Menu para continuar con un proyecto/cuenca existente.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.theme import get_console, print_basins_detail_table
from hidropluvial.database import get_database
from hidropluvial.models import Project, Basin


class ContinueProjectMenu(BaseMenu):
    """Menu para continuar trabajando con un proyecto/cuenca existente."""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.project: Optional[Project] = None
        self.basin: Optional[Basin] = None

    def show(self) -> None:
        """Muestra el menu para continuar un proyecto."""
        projects = self.db.list_projects()

        if not projects:
            self.echo("\n  No hay proyectos guardados.")
            self.echo("  Usa 'hp wizard' y selecciona 'Nueva cuenca' para comenzar.\n")
            return

        # Seleccionar proyecto
        selection = self._select_project(projects)
        if not selection:
            return

        self.project = self.db.get_project_model(selection)
        if not self.project:
            self.error(f"No se pudo cargar el proyecto {selection}")
            return
        self._show_project_menu()

    def _select_project(self, projects: list[dict]) -> Optional[str]:
        """Permite seleccionar un proyecto."""
        choices = []

        for p in projects:
            n_basins = p.get("n_basins", 0)
            n_analyses = p.get("total_analyses", 0)
            choices.append(
                f"{p['id']} - {p['name']} ({n_basins} cuencas, {n_analyses} analisis)"
            )

        choices.append(self.back_option("Volver al menu principal"))

        choice = self.select("Selecciona un proyecto:", choices)

        if choice is None or "Volver" in choice:
            return None

        # Parsear seleccion
        project_id = choice.split(" - ")[0]
        return project_id

    def _show_project_menu(self) -> None:
        """Muestra el menu de acciones para el proyecto."""
        while True:
            # Recargar proyecto
            self.project = self.db.get_project_model(self.project.id)

            self._show_project_header()

            action = self.select(
                "Que deseas hacer?",
                choices=[
                    "Ver cuencas del proyecto",
                    "Seleccionar cuenca para trabajar",
                    "Agregar nueva cuenca al proyecto",
                    "Editar metadatos del proyecto",
                    "Eliminar proyecto",
                    self.back_option("Volver (elegir otro proyecto)"),
                    self.back_option("Salir al menu principal"),
                ],
            )

            if action is None or "Salir" in action:
                return
            elif "otro proyecto" in action.lower():
                projects = self.db.list_projects()
                selection = self._select_project(projects)
                if selection:
                    self.project = self.db.get_project_model(selection)
                else:
                    return
            else:
                self._handle_project_action(action)

    def _show_project_header(self) -> None:
        """Muestra encabezado con info del proyecto."""
        self.project_info(self.project)

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
        choices.append(self.cancel_option())

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
        config = WizardConfig.from_wizard()
        if config is None:
            return

        config.print_summary()

        if not self.confirm("\nEjecutar analisis?", default=True):
            return

        runner = AnalysisRunner(config, project_id=self.project.id)
        updated_project, basin = runner.run()

        # Actualizar referencia local al proyecto
        self.project = updated_project

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

        self.db.save_project_model(self.project)
        self.echo("  Metadatos actualizados.\n")

    def _delete_project(self) -> bool:
        """Elimina el proyecto."""
        if self.confirm(
            f"Seguro que deseas eliminar el proyecto '{self.project.name}' y todas sus cuencas?",
            default=False,
        ):
            if self.db.delete_project(self.project.id):
                self.echo(f"\n  Proyecto {self.project.id} eliminado.\n")
                return True
            else:
                self.error("No se pudo eliminar el proyecto")
        return False

    # ========================================================================
    # Menu de Cuenca (Basin)
    # ========================================================================

    def _show_basin_menu(self) -> None:
        """Muestra el menu de acciones para la cuenca seleccionada."""
        while True:
            self._show_basin_header()

            action = self.select(
                "¿Qué deseas hacer?",
                choices=[
                    "Ver tabla resumen",
                    "Ver fichas de análisis",
                    "Comparar hidrogramas",
                    "Agregar análisis",
                    "Filtrar resultados",
                    "Exportar (Excel/LaTeX)",
                    "Editar cuenca...",
                    self.back_option("Volver (elegir otra cuenca)"),
                    self.back_option("Salir al menú principal"),
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
        project_name = self.project.name if self.project else None
        self.basin_info(self.basin, project_name)

    def _handle_basin_action(self, action: str) -> None:
        """Maneja la acción seleccionada para la cuenca."""
        if "tabla" in action.lower():
            self._show_table()
        elif "fichas" in action.lower():
            self._show_interactive_viewer()
        elif "Comparar" in action:
            self._compare_hydrographs()
        elif "Agregar" in action and "anál" in action.lower():
            self._add_analysis()
        elif "Filtrar" in action:
            self._filter_results()
        elif "Exportar" in action:
            self._export()
        elif "Editar cuenca" in action:
            self._show_edit_submenu()

    def _safe_call(self, func, *args, **kwargs) -> None:
        """Ejecuta una funcion capturando typer.Exit."""
        try:
            func(*args, **kwargs)
        except SystemExit:
            pass

    def _show_table(self) -> None:
        """Muestra tabla resumen interactiva."""
        if not self.basin.analyses:
            self.echo("  No hay análisis disponibles.")
            return

        from hidropluvial.cli.viewer.table_viewer import interactive_table_viewer
        from hidropluvial.cli.viewer.terminal import clear_screen
        from hidropluvial.database import get_database
        from hidropluvial.cli.wizard.styles import get_text_kwargs, get_confirm_kwargs
        import questionary

        db = get_database()

        def on_edit_note(analysis_id: str, current_note: str) -> str:
            clear_screen()
            print(f"\n  Editando nota del análisis {analysis_id[:8]}...\n")
            new_note = questionary.text(
                "Nueva nota (vacío para eliminar):",
                default=current_note or "",
                **get_text_kwargs(),
            ).ask()
            if new_note is not None:
                db.update_analysis_note(analysis_id, new_note if new_note else None)
                return new_note
            return None

        def on_delete(analysis_id: str) -> bool:
            """Elimina un análisis de la base de datos."""
            if db.delete_analysis(analysis_id):
                self.basin.analyses = [a for a in self.basin.analyses if a.id != analysis_id]
                # Guardar proyecto para persistir cambios
                if self.project:
                    self.db.save_project_model(self.project)
                return True
            return False

        updated = interactive_table_viewer(
            self.basin.analyses,
            self.basin.name,
            on_edit_note=on_edit_note,
            on_delete=on_delete,
        )
        if updated is not None:
            self.basin.analyses = updated

    def _show_interactive_viewer(self) -> None:
        """Muestra visor interactivo de fichas de análisis."""
        if not self.basin.analyses:
            self.echo("  No hay análisis disponibles.")
            return

        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer
        from hidropluvial.cli.viewer.terminal import clear_screen
        from hidropluvial.database import get_database
        from hidropluvial.cli.wizard.styles import get_text_kwargs, get_confirm_kwargs
        import questionary

        db = get_database()

        def on_edit_note(analysis_id: str, current_note: str) -> str:
            clear_screen()
            print(f"\n  Editando nota del análisis {analysis_id[:8]}...\n")
            new_note = questionary.text(
                "Nueva nota (vacío para eliminar):",
                default=current_note or "",
                **get_text_kwargs(),
            ).ask()
            if new_note is not None:
                db.update_analysis_note(analysis_id, new_note if new_note else None)
                return new_note
            return None

        def on_delete(analysis_id: str) -> bool:
            """Elimina un análisis de la base de datos."""
            if db.delete_analysis(analysis_id):
                self.basin.analyses = [a for a in self.basin.analyses if a.id != analysis_id]
                # Guardar proyecto para persistir cambios
                if self.project:
                    self.db.save_project_model(self.project)
                return True
            return False

        updated = interactive_hydrograph_viewer(
            self.basin.analyses,
            self.basin.name,
            on_edit_note=on_edit_note,
            on_delete=on_delete,
        )
        if updated is not None:
            self.basin.analyses = updated

    def _compare_hydrographs(self) -> None:
        """Compara hidrogramas con opcion de seleccionar cuales."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        n = len(self.basin.analyses)
        if n > 2:
            mode = self.select(
                "Que hidrogramas comparar?",
                choices=["Todos", "Seleccionar cuales", self.cancel_option()],
            )

            if mode is None or "Cancelar" in mode:
                return

            if "Seleccionar" in mode:
                selected = self._select_analyses_to_compare()
                if selected:
                    from hidropluvial.cli.basin.preview import basin_preview_compare
                    indices = [int(i) for i in selected.split(",")]
                    selected_analyses = [self.basin.analyses[i] for i in indices]
                    self._safe_call(basin_preview_compare, selected_analyses, self.basin.name)
                return

        from hidropluvial.cli.basin.preview import basin_preview_compare
        self._safe_call(basin_preview_compare, self.basin.analyses, self.basin.name)

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

    def _show_edit_submenu(self) -> None:
        """Muestra submenu de edicion de cuenca."""
        while True:
            action = self.select(
                f"Editar cuenca '{self.basin.name}':",
                choices=[
                    "Editar datos (area, pendiente, C, CN)",
                    "Editar notas",
                    "Eliminar cuenca",
                    self.back_option(),
                ],
            )

            if action is None or "Volver" in action:
                return

            if "datos" in action.lower():
                self._edit_basin()
            elif "notas" in action.lower():
                self._manage_notes()
            elif "Eliminar" in action:
                if self._delete_basin():
                    return

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la cuenca."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu

        c = self.basin.c
        cn = self.basin.cn
        length = self.basin.length_m

        # AddAnalysisMenu can work with Basin directly
        menu = AddAnalysisMenu(self.basin, c, cn, length)
        menu.show()

        # Reload basin from database if it's in a project
        if self.project:
            self.project = self.db.get_project_model(self.project.id)
            self.basin = self.project.get_basin(self.basin.id)

    def _filter_results(self) -> None:
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
                self.cancel_option(),
            ],
        )

        if filter_type is None or "Cancelar" in filter_type:
            return

        from hidropluvial.cli.basin.preview import basin_preview_table

        if "retorno" in filter_type.lower():
            tr_choice = self.select("Selecciona Tr:", [str(t) for t in tr_values])
            if tr_choice:
                self._safe_call(basin_preview_table, self.basin, tr=tr_choice)
        elif "Metodo" in filter_type:
            tc_choice = self.select("Selecciona metodo:", tc_methods)
            if tc_choice:
                self._safe_call(basin_preview_table, self.basin, tc=tc_choice)

    def _export(self) -> None:
        """Exporta resultados."""
        from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
        export_menu = ExportMenu(self.basin)
        export_menu.show()

    def _edit_basin(self) -> None:
        """Edita datos de la cuenca."""
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(self.basin)
        result = editor.edit()

        if result == "modified" and self.project:
            # Reload basin from project
            self.project = self.db.get_project_model(self.project.id)
            self.basin = self.project.get_basin(self.basin.id)

    def _manage_notes(self) -> None:
        """Gestiona notas de la cuenca."""
        current = self.basin.notes or ""

        self.echo(f"\n  Notas actuales: {current if current else '(sin notas)'}\n")

        new_notes = self.text("Nuevas notas (vacio para eliminar):", default=current)

        if new_notes is not None:
            self.basin.notes = new_notes
            # Save basin in project
            if self.project:
                self.db.save_project_model(self.project)
            self.echo("  Notas guardadas." if new_notes else "  Notas eliminadas.")

    def _delete_basin(self) -> bool:
        """Elimina la cuenca."""
        if self.confirm(f"Seguro que deseas eliminar la cuenca '{self.basin.name}'?", default=False):
            # Si esta en un proyecto, eliminar del proyecto
            if self.project:
                if self.project.remove_basin(self.basin.id):
                    self.db.save_project_model(self.project)
                    self.echo(f"\n  Cuenca '{self.basin.name}' eliminada del proyecto.\n")
                    return True
                else:
                    self.error("No se pudo eliminar la cuenca")
            else:
                self.error("La cuenca no pertenece a ningun proyecto")
        return False
