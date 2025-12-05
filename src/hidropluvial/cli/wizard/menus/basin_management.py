"""
Menu para gestionar cuencas dentro de un proyecto.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
from hidropluvial.project import Project, Basin, get_project_manager


class BasinManagementMenu(BaseMenu):
    """Menu para gestionar cuencas de un proyecto especifico."""

    def __init__(self, project: Project):
        super().__init__()
        self.project_manager = get_project_manager()
        self.project = project

    def show(self) -> None:
        """Muestra el menu de gestion de cuencas."""
        while True:
            # Recargar proyecto para tener datos actualizados
            self.project = self.project_manager.get_project(self.project.id)
            if not self.project:
                self.echo("\n  Error: Proyecto no encontrado.\n")
                return

            self._show_overview()

            if not self.project.basins:
                action = self.select(
                    "Que deseas hacer?",
                    choices=[
                        "Agregar nueva cuenca",
                        "Importar cuenca desde otro proyecto",
                        "← Volver a gestion de proyectos",
                    ],
                )
            else:
                action = self.select(
                    "Que deseas hacer?",
                    choices=[
                        "Ver detalles de una cuenca",
                        "Editar cuenca",
                        "Duplicar cuenca",
                        "Renombrar cuenca",
                        "Exportar cuenca (Excel/LaTeX)",
                        "Eliminar cuenca",
                        "Agregar nueva cuenca",
                        "Importar cuenca desde otro proyecto",
                        "← Volver a gestion de proyectos",
                    ],
                )

            if action is None or "Volver" in action:
                return

            self._handle_action(action)

    def _show_overview(self) -> None:
        """Muestra resumen de cuencas del proyecto."""
        self.echo(f"\n{'='*60}")
        self.echo(f"  CUENCAS DEL PROYECTO: {self.project.name}")
        self.echo(f"{'='*60}")

        if self.project.basins:
            self.echo(f"  {'ID':<10} {'Nombre':<30} {'Area (ha)':>10} {'Analisis':>8}")
            self.echo(f"  {'-'*58}")

            for b in self.project.basins:
                name = b.name[:29] if len(b.name) > 29 else b.name
                self.echo(
                    f"  {b.id:<10} {name:<30} {b.area_ha:>10.1f} {len(b.analyses):>8}"
                )
        else:
            self.echo("  No hay cuencas en este proyecto.")

        self.echo(f"{'='*60}")
        self.echo(f"  Total: {self.project.n_basins} cuencas, {self.project.total_analyses} analisis\n")

    def _handle_action(self, action: str) -> None:
        """Maneja la accion seleccionada."""
        if "Ver detalles" in action:
            self._view_basin_details()
        elif "Editar cuenca" in action:
            self._edit_basin()
        elif "Duplicar" in action:
            self._duplicate_basin()
        elif "Renombrar" in action:
            self._rename_basin()
        elif "Exportar" in action:
            self._export_basin()
        elif "Eliminar" in action:
            self._delete_basin()
        elif "Agregar nueva" in action:
            self._add_new_basin()
        elif "Importar" in action:
            self._import_basin()

    def _select_basin(self, prompt: str = "Selecciona una cuenca:") -> Optional[Basin]:
        """Permite seleccionar una cuenca del proyecto."""
        if not self.project.basins:
            self.echo("  No hay cuencas en este proyecto.")
            return None

        choices = []
        for b in self.project.basins:
            choices.append(f"{b.id} - {b.name} ({len(b.analyses)} analisis)")
        choices.append("← Cancelar")

        choice = self.select(prompt, choices)

        if choice is None or "Cancelar" in choice:
            return None

        basin_id = choice.split(" - ")[0]
        return self.project.get_basin(basin_id)

    def _view_basin_details(self) -> None:
        """Ver detalles de una cuenca."""
        basin = self._select_basin("Selecciona cuenca a ver:")
        if not basin:
            return

        self.echo(f"\n{'='*55}")
        self.echo(f"  CUENCA: {basin.name}")
        self.echo(f"{'='*55}")
        self.echo(f"  ID: {basin.id}")
        self.echo(f"  Area: {basin.area_ha} ha")
        self.echo(f"  Pendiente: {basin.slope_pct} %")
        self.echo(f"  P3,10: {basin.p3_10} mm")

        if basin.c is not None:
            self.echo(f"  Coef. C: {basin.c}")
        if basin.cn is not None:
            self.echo(f"  CN: {basin.cn}")
        if basin.length_m:
            self.echo(f"  Longitud: {basin.length_m} m")
        if basin.notes:
            self.echo(f"  Notas: {basin.notes}")

        self.echo(f"\n  Analisis: {len(basin.analyses)}")
        if basin.analyses:
            self.echo(f"  {'-'*50}")
            for i, a in enumerate(basin.analyses):
                h = a.hydrograph
                s = a.storm
                self.echo(
                    f"    [{i}] {h.tc_method} {s.type} Tr{s.return_period} "
                    f"Qp={h.peak_flow_m3s:.2f} m3/s"
                )

        self.echo(f"{'='*55}\n")

    def _edit_basin(self) -> None:
        """Editar parametros de una cuenca."""
        basin = self._select_basin("Selecciona cuenca a editar:")
        if not basin:
            return

        # Convertir a session para usar el editor existente
        session = basin.to_session()

        self.echo(f"\n  Valores actuales de '{basin.name}':")
        self.echo(f"    Area:      {basin.area_ha} ha")
        self.echo(f"    Pendiente: {basin.slope_pct} %")
        self.echo(f"    P3,10:     {basin.p3_10} mm")
        if basin.c is not None:
            self.echo(f"    Coef. C:   {basin.c}")
        if basin.cn is not None:
            self.echo(f"    CN:        {basin.cn}")
        if basin.length_m:
            self.echo(f"    Longitud:  {basin.length_m} m")

        if basin.analyses:
            self.echo(f"\n  ADVERTENCIA: Esta cuenca tiene {len(basin.analyses)} analisis.")
            self.echo(f"  Al modificar la cuenca se eliminaran todos los analisis.\n")

        # Usar editor de cuenca
        editor = CuencaEditor(session, self.manager)
        result = editor.edit()

        if result == "modified":
            # Actualizar basin desde session modificada
            updated_session = self.manager.get_session(session.id)
            if updated_session:
                updated_basin = Basin.from_session(updated_session)
                # Reemplazar en proyecto
                self.project.remove_basin(basin.id)
                self.project.add_basin(updated_basin)
                self.project_manager.save_project(self.project)
                self.echo(f"\n  Cuenca '{updated_basin.name}' actualizada.\n")

    def _duplicate_basin(self) -> None:
        """Duplicar una cuenca existente."""
        basin = self._select_basin("Selecciona cuenca a duplicar:")
        if not basin:
            return

        new_name = self.text(
            "Nombre para la nueva cuenca:",
            default=f"{basin.name} (copia)",
        )

        if not new_name:
            return

        # Clonar la cuenca
        basin_data = basin.model_dump()
        basin_data['id'] = None  # Forzar nuevo ID
        basin_data['name'] = new_name
        basin_data['analyses'] = []  # Nueva cuenca sin analisis

        new_basin = Basin.model_validate(basin_data)
        self.project.add_basin(new_basin)
        self.project_manager.save_project(self.project)

        self.echo(f"\n  Cuenca duplicada:")
        self.echo(f"    ID original: {basin.id}")
        self.echo(f"    ID nueva:    {new_basin.id}")
        self.echo(f"    Nombre:      {new_basin.name}")
        self.echo(f"\n  La nueva cuenca no tiene analisis.")
        self.echo(f"  Usa 'Continuar proyecto' para agregar analisis.\n")

    def _rename_basin(self) -> None:
        """Renombrar una cuenca."""
        basin = self._select_basin("Selecciona cuenca a renombrar:")
        if not basin:
            return

        new_name = self.text(
            f"Nuevo nombre (actual: {basin.name}):",
            default=basin.name,
        )

        if new_name and new_name != basin.name:
            basin.name = new_name
            self.project_manager.save_project(self.project)
            self.echo(f"\n  Cuenca renombrada a '{new_name}'\n")

    def _export_basin(self) -> None:
        """Exportar una cuenca a Excel o LaTeX."""
        # Filtrar cuencas con analisis
        basins_with_analyses = [b for b in self.project.basins if b.analyses]

        if not basins_with_analyses:
            self.echo("\n  No hay cuencas con analisis para exportar.\n")
            return

        choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} analisis)"
            for b in basins_with_analyses
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca a exportar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        basin_id = choice.split(" - ")[0]
        basin = self.project.get_basin(basin_id)

        if basin:
            session = basin.to_session()
            from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
            export_menu = ExportMenu(session)
            export_menu.show()

    def _delete_basin(self) -> None:
        """Eliminar una cuenca."""
        basin = self._select_basin("Selecciona cuenca a eliminar:")
        if not basin:
            return

        msg = f"Eliminar cuenca '{basin.name}'"
        if basin.analyses:
            msg += f" y sus {len(basin.analyses)} analisis"
        msg += "?"

        if self.confirm(msg, default=False):
            if self.project.remove_basin(basin.id):
                self.project_manager.save_project(self.project)
                self.echo(f"\n  Cuenca '{basin.name}' eliminada.\n")
            else:
                self.echo(f"\n  Error al eliminar cuenca.\n")

    def _add_new_basin(self) -> None:
        """Agrega una nueva cuenca al proyecto."""
        from hidropluvial.cli.wizard.config import WizardConfig
        from hidropluvial.cli.wizard.runner import AnalysisRunner
        from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu

        self.echo(f"\n  Agregando cuenca al proyecto: {self.project.name}\n")

        # Usar WizardConfig
        config = WizardConfig.from_wizard(project_id=self.project.id)
        if config is None:
            return

        config.print_summary()

        if not self.confirm("\nEjecutar analisis?", default=True):
            return

        self.echo("\n" + "=" * 60)
        self.echo("  EJECUTANDO ANALISIS")
        self.echo("=" * 60 + "\n")

        runner = AnalysisRunner(config, project_id=self.project.id)
        updated_project, basin = runner.run()

        self.echo(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

        # Menu post-ejecucion
        menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
        menu.show()

    def _import_basin(self) -> None:
        """Importa una cuenca desde otro proyecto o sesion legacy."""
        other_projects = [
            p for p in self.project_manager.list_projects()
            if p['id'] != self.project.id and p['n_basins'] > 0
        ]
        sessions = self.manager.list_sessions()

        if not other_projects and not sessions:
            self.echo("\n  No hay otros proyectos ni cuencas disponibles para importar.\n")
            return

        # Construir opciones
        choices = []

        for p in other_projects:
            choices.append(f"[Proyecto] {p['id']} - {p['name']} ({p['n_basins']} cuencas)")

        for s in sessions:
            choices.append(f"[Cuenca legacy] {s['id']} - {s['name']}")

        choices.append("← Cancelar")

        choice = self.select("Selecciona origen de la cuenca:", choices)

        if choice is None or "Cancelar" in choice:
            return

        if "[Proyecto]" in choice:
            self._import_from_project(choice)
        elif "[Cuenca legacy]" in choice:
            self._import_from_legacy(choice)

    def _import_from_project(self, choice: str) -> None:
        """Importa cuenca desde otro proyecto."""
        source_id = choice.split(" - ")[0].replace("[Proyecto] ", "")
        source_project = self.project_manager.get_project(source_id)

        if not source_project or not source_project.basins:
            self.echo("\n  El proyecto no tiene cuencas.\n")
            return

        basin_choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} analisis)"
            for b in source_project.basins
        ]
        basin_choices.append("← Cancelar")

        basin_choice = self.select("Selecciona cuenca a importar:", basin_choices)

        if basin_choice is None or "Cancelar" in basin_choice:
            return

        basin_id = basin_choice.split(" - ")[0]
        source_basin = source_project.get_basin(basin_id)

        if source_basin:
            # Clonar la cuenca con nuevo ID
            basin_data = source_basin.model_dump()
            basin_data['id'] = None  # Forzar nuevo ID
            new_basin = Basin.model_validate(basin_data)

            self.project.add_basin(new_basin)
            self.project_manager.save_project(self.project)

            self.echo(f"\n  Cuenca '{new_basin.name}' importada al proyecto.")
            self.echo(f"  (Nueva ID: {new_basin.id})\n")

    def _import_from_legacy(self, choice: str) -> None:
        """Importa cuenca desde sesion legacy."""
        session_id = choice.split(" - ")[0].replace("[Cuenca legacy] ", "")
        session = self.manager.get_session(session_id)

        if session:
            basin = Basin.from_session(session)
            self.project.add_basin(basin)
            self.project_manager.save_project(self.project)

            self.echo(f"\n  Cuenca '{basin.name}' importada al proyecto.\n")
