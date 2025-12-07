"""
Menú para gestionar cuencas dentro de un proyecto.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
from hidropluvial.cli.theme import (
    get_console, print_basins_table, print_header, print_info,
)
from hidropluvial.project import Project, Basin, get_project_manager


class BasinManagementMenu(BaseMenu):
    """Menú para gestionar cuencas de un proyecto específico."""

    def __init__(self, project: Project):
        super().__init__()
        self.project_manager = get_project_manager()
        self.project = project

    def show(self) -> None:
        """Muestra el menú de gestión de cuencas."""
        while True:
            # Recargar proyecto para tener datos actualizados
            self.project = self.project_manager.get_project(self.project.id)
            if not self.project:
                self.error("Proyecto no encontrado")
                return

            self._show_overview()

            if not self.project.basins:
                action = self.select(
                    "¿Qué deseas hacer?",
                    choices=[
                        "Agregar nueva cuenca",
                        "Importar cuenca desde otro proyecto",
                        "← Volver a gestión de proyectos",
                    ],
                )
            else:
                action = self.select(
                    "¿Qué deseas hacer?",
                    choices=[
                        "Ver detalles de una cuenca",
                        "Gestionar análisis de una cuenca",
                        "Editar cuenca",
                        "Duplicar cuenca",
                        "Renombrar cuenca",
                        "Exportar cuenca (Excel/LaTeX)",
                        "Eliminar cuenca",
                        "Agregar nueva cuenca",
                        "Importar cuenca desde otro proyecto",
                        "← Volver a gestión de proyectos",
                    ],
                )

            if action is None or "Volver" in action:
                return

            self._handle_action(action)

    def _show_overview(self) -> None:
        """Muestra resumen de cuencas del proyecto."""
        console = get_console()
        console.print()

        title = f"Cuencas del Proyecto: {self.project.name}"
        print_basins_table(self.project.basins, title=title)

        print_info(f"Total: {self.project.n_basins} cuencas, {self.project.total_analyses} análisis")
        console.print()

    def _handle_action(self, action: str) -> None:
        """Maneja la accion seleccionada."""
        if "Ver detalles" in action:
            self._view_basin_details()
        elif "Gestionar análisis" in action:
            self._manage_analyses()
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
            choices.append(f"{b.id} - {b.name} ({len(b.analyses)} análisis)")
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

        self.basin_info(basin, self.project.name)

        # Mostrar detalles adicionales no incluidos en basin_info
        if basin.p3_10:
            self.info(f"P3,10: {basin.p3_10} mm")
        if basin.length_m:
            self.info(f"Longitud cauce: {basin.length_m} m")
        if basin.notes:
            self.note(f"Notas: {basin.notes}")

        # Lista detallada de análisis
        if basin.analyses:
            self.section("Análisis")
            for i, a in enumerate(basin.analyses):
                h = a.hydrograph
                s = a.storm
                self.echo(
                    f"  [{i}] {h.tc_method} {s.type} Tr{s.return_period} "
                    f"Qp={h.peak_flow_m3s:.2f} m³/s"
                )

    def _edit_basin(self) -> None:
        """Editar parametros de una cuenca."""
        basin = self._select_basin("Selecciona cuenca a editar:")
        if not basin:
            return

        self.section(f"Valores actuales de '{basin.name}'")
        self.basin_info(basin, self.project.name)

        if basin.analyses:
            self.warning(f"ADVERTENCIA: Esta cuenca tiene {len(basin.analyses)} análisis.")
            self.warning("Al modificar la cuenca se eliminaran todos los análisis.")

        # Usar editor de cuenca directamente con Basin
        editor = CuencaEditor(basin, self.project_manager)
        result = editor.edit()

        if result == "modified":
            # Recargar proyecto para obtener cambios
            self.project = self.project_manager.get_project(self.project.id)
            self.echo(f"\n  Cuenca '{basin.name}' actualizada.\n")

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
        basin_data['analyses'] = []  # Nueva cuenca sin análisis

        new_basin = Basin.model_validate(basin_data)
        self.project.add_basin(new_basin)
        self.project_manager.save_project(self.project)

        self.echo(f"\n  Cuenca duplicada:")
        self.echo(f"    ID original: {basin.id}")
        self.echo(f"    ID nueva:    {new_basin.id}")
        self.echo(f"    Nombre:      {new_basin.name}")
        self.echo(f"\n  La nueva cuenca no tiene análisis.")
        self.echo(f"  Usa 'Continuar proyecto' para agregar análisis.\n")

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
        # Filtrar cuencas con análisis
        basins_with_analyses = [b for b in self.project.basins if b.analyses]

        if not basins_with_analyses:
            self.echo("\n  No hay cuencas con análisis para exportar.\n")
            return

        choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} análisis)"
            for b in basins_with_analyses
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca a exportar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        basin_id = choice.split(" - ")[0]
        basin = self.project.get_basin(basin_id)

        if basin:
            from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
            # ExportMenu can work with Basin directly via SessionMenu
            export_menu = ExportMenu(basin)
            export_menu.show()

    def _delete_basin(self) -> None:
        """Eliminar una cuenca."""
        basin = self._select_basin("Selecciona cuenca a eliminar:")
        if not basin:
            return

        msg = f"Eliminar cuenca '{basin.name}'"
        if basin.analyses:
            msg += f" y sus {len(basin.analyses)} análisis"
        msg += "?"

        if self.confirm(msg, default=False):
            if self.project.remove_basin(basin.id):
                self.project_manager.save_project(self.project)
                self.echo(f"\n  Cuenca '{basin.name}' eliminada.\n")
            else:
                self.error("No se pudo eliminar la cuenca")

    def _add_new_basin(self) -> None:
        """Agrega una nueva cuenca al proyecto."""
        from hidropluvial.cli.wizard.config import WizardConfig
        from hidropluvial.cli.wizard.runner import AnalysisRunner
        from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu

        self.echo(f"\n  Agregando cuenca al proyecto: {self.project.name}\n")

        # Usar WizardConfig
        config = WizardConfig.from_wizard()
        if config is None:
            return

        config.print_summary()

        if not self.confirm("\n¿Ejecutar análisis?", default=True):
            return

        self.echo("\n" + "=" * 60)
        self.echo("  EJECUTANDO ANÁLISIS")
        self.echo("=" * 60 + "\n")

        runner = AnalysisRunner(config, project_id=self.project.id)
        updated_project, basin = runner.run()

        self.echo(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

        # Menu post-ejecucion
        menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
        menu.show()

    def _import_basin(self) -> None:
        """Importa una cuenca desde otro proyecto."""
        other_projects = [
            p for p in self.project_manager.list_projects()
            if p['id'] != self.project.id and p['n_basins'] > 0
        ]

        if not other_projects:
            self.echo("\n  No hay otros proyectos con cuencas disponibles para importar.\n")
            return

        # Construir opciones
        choices = [
            f"{p['id']} - {p['name']} ({p['n_basins']} cuencas)"
            for p in other_projects
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona proyecto origen:", choices)

        if choice is None or "Cancelar" in choice:
            return

        self._import_from_project(choice)

    def _import_from_project(self, choice: str) -> None:
        """Importa cuenca desde otro proyecto."""
        source_id = choice.split(" - ")[0]
        source_project = self.project_manager.get_project(source_id)

        if not source_project or not source_project.basins:
            self.echo("\n  El proyecto no tiene cuencas.\n")
            return

        basin_choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} análisis)"
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

    def _manage_analyses(self) -> None:
        """Gestionar análisis de una cuenca."""
        # Filtrar cuencas con análisis
        basins_with_analyses = [b for b in self.project.basins if b.analyses]

        if not basins_with_analyses:
            self.echo("\n  No hay cuencas con análisis para gestionar.\n")
            return

        choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} análisis)"
            for b in basins_with_analyses
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona cuenca:", choices)

        if choice is None or "Cancelar" in choice:
            return

        basin_id = choice.split(" - ")[0]
        basin = self.project.get_basin(basin_id)

        if basin:
            self._show_analysis_menu(basin)

    def _show_analysis_menu(self, basin: Basin) -> None:
        """Muestra submenú de gestión de análisis para una cuenca."""
        from hidropluvial.database import get_database

        while True:
            # Recargar cuenca para tener datos actualizados
            self.project = self.project_manager.get_project(self.project.id)
            basin = self.project.get_basin(basin.id) if self.project else None

            if not basin:
                self.error("Cuenca no encontrada")
                return

            self.section(f"Análisis de: {basin.name}")
            self.echo(f"  Cuenca tiene {len(basin.analyses)} análisis\n")

            # Listar análisis
            if basin.analyses:
                for i, a in enumerate(basin.analyses):
                    h = a.hydrograph
                    s = a.storm
                    note = f" [{a.note}]" if a.note else ""
                    self.echo(
                        f"  [{a.id}] {h.tc_method} {s.type.upper()} Tr{s.return_period} "
                        f"Qp={h.peak_flow_m3s:.2f} m³/s{note}"
                    )
                self.echo("")

            action = self.select(
                "¿Qué deseas hacer?",
                choices=[
                    "Eliminar un análisis",
                    "Agregar/editar nota de un análisis",
                    "Eliminar TODOS los análisis",
                    "← Volver",
                ],
            )

            if action is None or "Volver" in action:
                return

            db = get_database()

            if "Eliminar un análisis" in action:
                self._delete_one_analysis(basin, db)
            elif "Agregar/editar nota" in action:
                self._edit_analysis_note(basin, db)
            elif "Eliminar TODOS" in action:
                if self._clear_all_analyses(basin, db):
                    return  # Si se eliminaron todos, volver

    def _delete_one_analysis(self, basin: Basin, db) -> None:
        """Elimina un análisis seleccionado."""
        if not basin.analyses:
            self.echo("\n  No hay análisis para eliminar.\n")
            return

        choices = []
        for a in basin.analyses:
            h = a.hydrograph
            s = a.storm
            note = f" [{a.note}]" if a.note else ""
            choices.append(
                f"{a.id} - {h.tc_method} {s.type.upper()} Tr{s.return_period} "
                f"Qp={h.peak_flow_m3s:.2f}{note}"
            )
        choices.append("← Cancelar")

        choice = self.select("Selecciona análisis a eliminar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        analysis_id = choice.split(" - ")[0]

        if self.confirm(f"¿Eliminar análisis {analysis_id}?", default=False):
            if db.delete_analysis(analysis_id):
                self.echo(f"\n  Análisis '{analysis_id}' eliminado.\n")
            else:
                self.error("No se pudo eliminar el análisis")

    def _edit_analysis_note(self, basin: Basin, db) -> None:
        """Edita la nota de un análisis."""
        if not basin.analyses:
            self.echo("\n  No hay análisis.\n")
            return

        choices = []
        for a in basin.analyses:
            h = a.hydrograph
            s = a.storm
            note_preview = f" [{a.note[:20]}...]" if a.note and len(a.note) > 20 else (f" [{a.note}]" if a.note else " [sin nota]")
            choices.append(
                f"{a.id} - {h.tc_method} {s.type.upper()} Tr{s.return_period}{note_preview}"
            )
        choices.append("← Cancelar")

        choice = self.select("Selecciona análisis:", choices)

        if choice is None or "Cancelar" in choice:
            return

        analysis_id = choice.split(" - ")[0]

        # Buscar análisis actual para obtener nota existente
        current_analysis = next((a for a in basin.analyses if a.id == analysis_id), None)
        current_note = current_analysis.note if current_analysis else ""

        note_action = self.select(
            "¿Qué deseas hacer con la nota?",
            choices=[
                "Establecer/cambiar nota",
                "Eliminar nota",
                "← Cancelar",
            ],
        )

        if note_action is None or "Cancelar" in note_action:
            return

        if "Eliminar nota" in note_action:
            db.update_analysis_note(analysis_id, None)
            self.echo(f"\n  Nota eliminada del análisis '{analysis_id}'.\n")
        else:
            new_note = self.text(
                "Nueva nota:",
                default=current_note or "",
            )
            if new_note is not None:
                db.update_analysis_note(analysis_id, new_note if new_note else None)
                self.echo(f"\n  Nota actualizada para análisis '{analysis_id}'.\n")

    def _clear_all_analyses(self, basin: Basin, db) -> bool:
        """Elimina todos los análisis de una cuenca. Retorna True si se eliminaron."""
        n_analyses = len(basin.analyses)

        if n_analyses == 0:
            self.echo("\n  No hay análisis para eliminar.\n")
            return False

        self.warning(f"ATENCIÓN: Se eliminarán {n_analyses} análisis de '{basin.name}'")
        self.warning("Esta operación no se puede deshacer.")

        if self.confirm(f"¿Eliminar los {n_analyses} análisis?", default=False):
            deleted = db.clear_basin_analyses(basin.id)
            self.echo(f"\n  Eliminados {deleted} análisis.\n")
            return True

        return False
