"""
Menú para gestionar cuencas dentro de un proyecto.
"""

from typing import Optional

from hidropluvial.cli.wizard.menus.base import BaseMenu
from hidropluvial.cli.theme import (
    get_console, print_basins_table, print_header, print_info,
)
from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
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
                action = self._show_empty_project_menu()
            else:
                action = self._show_project_menu()

            if action is None:
                return

            self._handle_action(action)

    def _show_empty_project_menu(self) -> Optional[str]:
        """Menú cuando el proyecto no tiene cuencas."""
        items = [
            MenuItem(key="n", label="Crear nueva cuenca", value="new", hint="Wizard completo"),
            MenuItem(key="i", label="Importar desde otro proyecto", value="import", hint="Copiar cuenca existente"),
        ]

        return menu_panel(
            title=f"Proyecto: {self.project.name}",
            subtitle="No hay cuencas en este proyecto",
            items=items,
            allow_back=True,
        )

    def _show_project_menu(self) -> Optional[str]:
        """Menú principal cuando hay cuencas."""
        items = [
            MenuItem(key="v", label="Ver detalles de una cuenca", value="view"),
            MenuItem(key="g", label="Gestionar análisis", value="analyses", hint="Agregar/eliminar"),
            MenuItem(key="e", label="Editar cuenca", value="edit"),
            MenuItem(key="d", label="Duplicar cuenca", value="duplicate"),
            MenuItem(key="r", label="Renombrar cuenca", value="rename"),
            MenuItem(key="x", label="Exportar cuenca", value="export", hint="Excel/LaTeX"),
            MenuItem(key="separator1", label="", separator=True),
            MenuItem(key="n", label="Crear nueva cuenca", value="new"),
            MenuItem(key="i", label="Importar desde otro proyecto", value="import"),
            MenuItem(key="separator2", label="", separator=True),
            MenuItem(key="z", label="Eliminar cuenca", value="delete"),
        ]

        return menu_panel(
            title=f"Proyecto: {self.project.name}",
            subtitle=f"{self.project.n_basins} cuencas, {self.project.total_analyses} análisis",
            items=items,
            allow_back=True,
        )

    def _show_overview(self) -> None:
        """Muestra resumen de cuencas del proyecto."""
        console = get_console()
        console.print()

        title = f"Cuencas del Proyecto: {self.project.name}"
        print_basins_table(self.project.basins, title=title)

        print_info(f"Total: {self.project.n_basins} cuencas, {self.project.total_analyses} análisis")
        console.print()

    def _handle_action(self, action: str) -> None:
        """Maneja la acción seleccionada."""
        actions = {
            "view": self._view_basin_details,
            "analyses": self._manage_analyses,
            "edit": self._edit_basin,
            "duplicate": self._duplicate_basin,
            "rename": self._rename_basin,
            "export": self._export_basin,
            "delete": self._delete_basin,
            "new": self._add_new_basin,
            "import": self._import_basin,
        }
        handler = actions.get(action)
        if handler:
            handler()

    def _select_basin(self, prompt: str = "Selecciona una cuenca:") -> Optional[Basin]:
        """Permite seleccionar una cuenca del proyecto."""
        return self.select_basin_from_project(self.project, prompt)

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

        result = self.edit_basin_with_editor(basin, self.project_manager)

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

        # Crear nueva cuenca en la BD con los datos de la cuenca origen
        new_basin = self.project_manager.create_basin(
            project=self.project,
            name=new_name,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            p3_10=basin.p3_10,
            c=basin.c,
            cn=basin.cn,
            length_m=basin.length_m,
        )

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

        choice = self.select("Selecciona cuenca a exportar:", choices)

        if choice is None:
            return

        basin_id = choice.split(" - ")[0]
        basin = self.project.get_basin(basin_id)

        if basin:
            from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
            export_menu = ExportMenu(basin, self.project)
            export_menu.show()

    def _delete_basin(self) -> None:
        """Eliminar una cuenca."""
        basin = self._select_basin("Selecciona cuenca a eliminar:")
        if not basin:
            return

        self.delete_basin_from_project(basin, self.project, self.project_manager)

    def _add_new_basin(self) -> None:
        """Agrega una nueva cuenca al proyecto."""
        result = self.add_basin_with_wizard(self.project, show_post_menu=True)
        if result:
            self.project, _ = result

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

        choice = self.select("Selecciona proyecto origen:", choices)

        if choice is None:
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

        basin_choice = self.select("Selecciona cuenca a importar:", basin_choices)

        if basin_choice is None:
            return

        basin_id = basin_choice.split(" - ")[0]
        source_basin = source_project.get_basin(basin_id)

        if source_basin:
            # Crear nueva cuenca en la BD con los datos de la cuenca origen
            new_basin = self.project_manager.create_basin(
                project=self.project,
                name=source_basin.name,
                area_ha=source_basin.area_ha,
                slope_pct=source_basin.slope_pct,
                p3_10=source_basin.p3_10,
                c=source_basin.c,
                cn=source_basin.cn,
                length_m=source_basin.length_m,
            )

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

        choice = self.select("Selecciona cuenca:", choices)

        if choice is None:
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
                ],
            )

            if action is None:
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

        choice = self.select("Selecciona análisis a eliminar:", choices)

        if choice is None:
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

        choice = self.select("Selecciona análisis:", choices)

        if choice is None:
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
            ],
        )

        if note_action is None:
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
