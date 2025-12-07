"""
Menu post-ejecucion de analisis.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.project import Project
from hidropluvial.models import Basin


class PostExecutionMenu(SessionMenu):
    """Menu despues de ejecutar analisis."""

    def __init__(
        self,
        project: Project,
        basin: Basin,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(basin)

        self.project = project

        # Usar valores de la cuenca si no se pasan explicitamente
        self.c = c if c is not None else basin.c
        self.cn = cn if cn is not None else basin.cn
        self.length = length if length is not None else basin.length_m

    def show(self) -> None:
        """Muestra el menu post-ejecucion en un loop."""
        while True:
            # Recargar sesion para tener datos actualizados
            self.reload_session()

            self._show_session_header()

            action = self.select(
                "Que deseas hacer ahora?",
                choices=[
                    "Ver tabla resumen",
                    "Ver fichas de analisis (navegacion interactiva)",
                    "Comparar hidrogramas",
                    "Ver hietograma",
                    "Filtrar resultados",
                    "Agregar mas analisis",
                    "Definir CN por ponderacion (tablas NRCS)",
                    "Editar datos de la cuenca",
                    "Agregar/editar notas",
                    "Exportar (Excel/LaTeX)",
                    "← Salir al menu principal",
                ],
            )

            if action is None or "Salir" in action:
                self.success(f"Cuenca guardada: {self.basin.id}")
                self.info(f"Proyecto: {self.project.name} [{self.project.id}]")
                break

            self._handle_action(action)

    def _show_session_header(self) -> None:
        """Muestra encabezado con info de la sesion/cuenca."""
        self.basin_info(self.basin, self.project.name)

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
        elif "Filtrar" in action:
            self._filter_results()
        elif "ponderacion" in action.lower():
            self._define_weighted_cn()
        elif "Editar" in action:
            result = self._edit_cuenca()
            if result == "new_session":
                return  # Salir del menu
        elif "notas" in action.lower():
            self._manage_notes()
        elif "Exportar" in action:
            self._export()
        elif "Agregar" in action:
            self._add_analysis()

    def _safe_call(self, func, *args, **kwargs) -> None:
        """Ejecuta una funcion capturando typer.Exit para no salir del wizard."""
        try:
            func(*args, **kwargs)
        except SystemExit:
            # typer.Exit() lanza SystemExit, lo capturamos para continuar
            pass

    def _show_table(self) -> None:
        """Muestra tabla con sparklines."""
        from hidropluvial.cli.basin.preview import basin_preview_table
        self._safe_call(basin_preview_table, self.basin)

    def _compare_hydrographs(self) -> None:
        """Compara hidrogramas con opcion de seleccionar cuales."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        n = len(self.basin.analyses)
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
                    from hidropluvial.cli.basin.preview import basin_preview_compare
                    indices = [int(i) for i in selected.split(",")]
                    selected_analyses = [self.basin.analyses[i] for i in indices]
                    self._safe_call(basin_preview_compare, selected_analyses, self.basin.name)
                return

        from hidropluvial.cli.basin.preview import basin_preview_compare
        self._safe_call(basin_preview_compare, self.basin.analyses, self.basin.name)

    def _select_analyses_to_compare(self) -> Optional[str]:
        """Permite seleccionar analisis para comparar."""
        choices = []
        for i, a in enumerate(self.basin.analyses):
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

    def _show_interactive_viewer(self) -> None:
        """Muestra visor interactivo de fichas de analisis."""
        self.show_analysis_cards()

    def _show_hyetograph(self) -> None:
        """Muestra hietograma de un analisis."""
        if not self.basin.analyses:
            self.echo("  No hay analisis disponibles.")
            return

        # Seleccionar cual
        choices = []
        for i, a in enumerate(self.basin.analyses):
            storm = a.storm
            choices.append(f"{i}: {storm.type} Tr{storm.return_period} P={storm.total_depth_mm:.1f}mm")

        selected = self.select("Selecciona analisis:", choices)
        if selected:
            idx = int(selected.split(":")[0])
            analysis = self.basin.analyses[idx]
            from hidropluvial.cli.basin.preview import basin_preview_hyetograph
            self._safe_call(basin_preview_hyetograph, analysis, self.basin.name)

    def _export(self) -> None:
        """Exporta los resultados a Excel o LaTeX con opciones de filtrado."""
        from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
        export_menu = ExportMenu(self.basin)
        export_menu.show()

    def _define_weighted_cn(self) -> None:
        """Define el CN mediante ponderacion por areas."""
        from hidropluvial.cli.runoff import collect_weighted_cn_interactive

        self.header("DEFINIR CN POR PONDERACION")

        # Mostrar CN actual si existe
        if self.basin.cn:
            self.echo(f"\n  CN actual: {self.basin.cn}")
            if hasattr(self.basin, 'cn_weighted') and self.basin.cn_weighted:
                n_items = len(self.basin.cn_weighted.items)
                self.echo(f"  (calculado por ponderacion con {n_items} coberturas)")

        # Preguntar grupo hidrologico
        soil_group = self.select(
            "\nGrupo hidrologico del suelo:",
            choices=[
                "A - Arena, grava (alta infiltracion)",
                "B - Limos, suelos moderados",
                "C - Arcilla limosa (baja infiltracion)",
                "D - Arcilla, suelos impermeables",
            ],
        )

        if soil_group is None:
            return

        soil = soil_group[0]  # Extraer letra A, B, C o D

        # Recopilar datos de ponderacion
        weighted_result = collect_weighted_cn_interactive(
            area_total=self.basin.area_ha,
            soil_group=soil,
            echo_fn=typer.echo,
        )

        if weighted_result is None:
            self.echo("\n  Operacion cancelada.")
            return

        # Confirmar
        cn_value = int(round(weighted_result.weighted_value))
        self.echo(f"\n  Se actualizara el CN de la cuenca a: {cn_value}")
        if not self.confirm("Aplicar cambios?"):
            return

        # Guardar en la cuenca
        self.basin.cn = cn_value
        if hasattr(self.basin, 'cn_weighted'):
            self.basin.cn_weighted = weighted_result
        self.cn = cn_value

        # Save project
        from hidropluvial.project import get_project_manager
        project_manager = get_project_manager()
        project_manager.save_project(self.project)

        self.echo(f"\n  CN actualizado a {self.cn}")
        self.echo("    Los datos de ponderacion se incluiran en el reporte.")

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la cuenca."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
        menu = AddAnalysisMenu(self.basin, self.c, self.cn, self.length)
        menu.show()

    def _filter_results(self) -> None:
        """Muestra menu de filtrado de resultados."""
        self.echo("\n-- Filtrar Resultados --\n")

        # Obtener valores unicos de la cuenca
        tr_values = sorted(set(a.storm.return_period for a in self.basin.analyses))
        x_values = sorted(set(a.hydrograph.x_factor for a in self.basin.analyses if a.hydrograph.x_factor))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.basin.analyses))
        storm_types = sorted(set(a.storm.type for a in self.basin.analyses))

        # Obtener métodos de escorrentía disponibles
        runoff_methods = set()
        for a in self.basin.analyses:
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                runoff_methods.add(a.tc.parameters["runoff_method"])
            elif a.tc.parameters:
                # Inferir de parámetros existentes para análisis antiguos
                if "cn_adjusted" in a.tc.parameters:
                    runoff_methods.add("scs-cn")
                elif "c" in a.tc.parameters:
                    runoff_methods.add("racional")
        runoff_methods = sorted(runoff_methods)

        x_choice = f"Factor X: {x_values}" if x_values else "Factor X: (no disponible)"
        runoff_choice = f"Metodo escorrentia: {runoff_methods}" if runoff_methods else "Metodo escorrentia: (no disponible)"

        filter_type = self.select(
            "Filtrar por:",
            choices=[
                f"Periodo de retorno (Tr): {tr_values}",
                x_choice,
                f"Metodo Tc: {tc_methods}",
                f"Tipo de tormenta: {storm_types}",
                runoff_choice,
                "Combinacion personalizada",
                "← Cancelar",
            ],
        )

        if filter_type is None or "Cancelar" in filter_type:
            return

        filters = self._collect_filters(filter_type, tr_values, x_values, tc_methods, storm_types, runoff_methods)
        self._show_filtered_results(**filters)

    def _collect_filters(
        self,
        filter_type: str,
        tr_values: list,
        x_values: list,
        tc_methods: list,
        storm_types: list,
        runoff_methods: list,
    ) -> dict:
        """Recolecta los filtros segun el tipo seleccionado."""
        tr_filter = None
        x_filter = None
        tc_filter = None
        storm_filter = None
        runoff_filter = None

        if "Periodo de retorno" in filter_type:
            tr_choices = [questionary.Choice(str(v), checked=False) for v in tr_values]
            selected = self.checkbox("Selecciona Tr:", tr_choices)
            if selected:
                tr_filter = ",".join(selected)

        elif "Factor X" in filter_type and x_values:
            x_choices = [questionary.Choice(f"{v:.2f}", checked=False) for v in x_values]
            selected = self.checkbox("Selecciona X:", x_choices)
            if selected:
                x_filter = ",".join(selected)

        elif "Metodo Tc" in filter_type:
            tc_choices = [questionary.Choice(v, checked=False) for v in tc_methods]
            selected = self.checkbox("Selecciona metodo Tc:", tc_choices)
            if selected:
                tc_filter = ",".join(selected)

        elif "tormenta" in filter_type.lower():
            storm_choices = [questionary.Choice(v, checked=False) for v in storm_types]
            selected = self.checkbox("Selecciona tipo de tormenta:", storm_choices)
            if selected:
                storm_filter = ",".join(selected)

        elif "escorrentia" in filter_type.lower() and runoff_methods:
            # Mostrar etiquetas amigables
            runoff_labels = {
                "racional": "Racional (C)",
                "scs-cn": "SCS-CN (CN)",
            }
            runoff_choices = [
                questionary.Choice(runoff_labels.get(v, v), value=v, checked=False)
                for v in runoff_methods
            ]
            selected = self.checkbox("Selecciona metodo de escorrentia:", runoff_choices)
            if selected:
                runoff_filter = ",".join(selected)

        elif "Combinacion" in filter_type:
            tr_filter, x_filter, tc_filter, runoff_filter = self._collect_combined_filters(
                tr_values, x_values, tc_methods, runoff_methods
            )

        return {
            "tr_filter": tr_filter,
            "x_filter": x_filter,
            "tc_filter": tc_filter,
            "storm_filter": storm_filter,
            "runoff_filter": runoff_filter,
        }

    def _collect_combined_filters(
        self,
        tr_values: list,
        x_values: list,
        tc_methods: list,
        runoff_methods: list,
    ) -> tuple:
        """Recolecta filtros combinados."""
        tr_filter = None
        x_filter = None
        tc_filter = None
        runoff_filter = None

        tr_choices = [questionary.Choice(str(v), checked=False) for v in tr_values]
        tr_selected = self.checkbox("Periodos de retorno (Enter para todos):", tr_choices)
        if tr_selected:
            tr_filter = ",".join(tr_selected)

        if x_values:
            x_choices = [questionary.Choice(f"{v:.2f}", checked=False) for v in x_values]
            x_selected = self.checkbox("Factores X (Enter para todos):", x_choices)
            if x_selected:
                x_filter = ",".join(x_selected)

        tc_choices = [questionary.Choice(v, checked=False) for v in tc_methods]
        tc_selected = self.checkbox("Metodos Tc (Enter para todos):", tc_choices)
        if tc_selected:
            tc_filter = ",".join(tc_selected)

        if runoff_methods:
            runoff_labels = {
                "racional": "Racional (C)",
                "scs-cn": "SCS-CN (CN)",
            }
            runoff_choices = [
                questionary.Choice(runoff_labels.get(v, v), value=v, checked=False)
                for v in runoff_methods
            ]
            runoff_selected = self.checkbox("Metodos escorrentia (Enter para todos):", runoff_choices)
            if runoff_selected:
                runoff_filter = ",".join(runoff_selected)

        return tr_filter, x_filter, tc_filter, runoff_filter

    def _show_filtered_results(
        self,
        tr_filter: Optional[str],
        x_filter: Optional[str],
        tc_filter: Optional[str],
        storm_filter: Optional[str],
        runoff_filter: Optional[str] = None,
    ) -> None:
        """Muestra resultados filtrados."""
        from hidropluvial.cli.basin.preview import basin_preview_table, basin_preview_compare

        self._safe_call(
            basin_preview_table,
            self.basin,
            tr=tr_filter,
            x=x_filter,
            tc=tc_filter,
            storm=storm_filter,
            runoff=runoff_filter,
        )

        # Ofrecer comparar filtrados
        if self.confirm("Comparar hidrogramas filtrados?", default=False):
            # Filter analyses
            filtered_analyses = self.basin.analyses
            # Apply filters...
            # For now, pass all analyses - filtering logic would need to be implemented
            self._safe_call(basin_preview_compare, filtered_analyses, self.basin.name)

    def _edit_cuenca(self) -> str:
        """
        Permite editar los datos de la cuenca.

        Returns:
            "modified" si se modifico la cuenca
            "cancelled" si se cancelo
        """
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(self.basin)
        result = editor.edit()

        # Reload project after edit
        if result == "modified":
            from hidropluvial.project import get_project_manager
            project_manager = get_project_manager()
            self.project = project_manager.get_project(self.project.id)

        return result

    def _manage_notes(self) -> None:
        """Gestiona notas de la cuenca y analisis."""
        self.header("NOTAS Y COMENTARIOS")

        # Mostrar notas actuales
        if self.basin.notes:
            self.echo(f"\n  Notas de la cuenca:")
            self.echo(f"  {'-'*50}")
            for line in self.basin.notes.split('\n'):
                self.echo(f"    {line}")
            self.echo("")

        # Contar analisis con notas
        analyses_with_notes = [a for a in self.basin.analyses if a.note]
        if analyses_with_notes:
            self.echo(f"  Analisis con notas: {len(analyses_with_notes)}")

        # Menu de opciones
        choices = [
            "Editar notas de la cuenca",
            "Agregar nota a un analisis",
        ]
        if analyses_with_notes:
            choices.append("Ver notas de analisis")
        choices.append("← Volver")

        action = self.select("\nQue deseas hacer?", choices)

        if action is None or "Volver" in action:
            return

        if "cuenca" in action.lower():
            self._edit_basin_notes()
        elif "Agregar" in action:
            self._add_analysis_note()
        elif "Ver" in action:
            self._view_analysis_notes()

    def _edit_basin_notes(self) -> None:
        """Edita las notas generales de la cuenca."""
        self.echo("\n  Notas de la cuenca:")
        self.echo("  (Dejar vacio para eliminar notas existentes)\n")

        current = self.basin.notes or ""

        new_notes = self.text("Notas:", default=current)

        if new_notes is not None:
            self.basin.notes = new_notes
            # Save project
            from hidropluvial.project import get_project_manager
            project_manager = get_project_manager()
            project_manager.save_project(self.project)

            if new_notes:
                self.echo("\n  Notas guardadas.")
            else:
                self.echo("\n  Notas eliminadas.")

    def _add_analysis_note(self) -> None:
        """Agrega una nota a un analisis especifico."""
        if not self.basin.analyses:
            self.echo("\n  No hay analisis disponibles.")
            return

        # Mostrar lista de analisis
        choices = []
        for i, a in enumerate(self.basin.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            note_indicator = " [nota]" if a.note else ""
            choices.append(
                f"{a.id}: {hydro.tc_method} Tr{storm.return_period}{x_str} "
                f"Qp={hydro.peak_flow_m3s:.2f}m3/s{note_indicator}"
            )

        selected = self.select("Selecciona analisis:", choices)

        if selected is None:
            return

        analysis_id = selected.split(":")[0]

        # Buscar analisis y mostrar nota actual si existe
        for a in self.basin.analyses:
            if a.id == analysis_id:
                if a.note:
                    self.echo(f"\n  Nota actual: {a.note}")

                new_note = self.text(
                    "Nueva nota (vacio para eliminar):",
                    default=a.note or "",
                )

                if new_note is not None:
                    a.note = new_note
                    # Save project
                    from hidropluvial.project import get_project_manager
                    project_manager = get_project_manager()
                    project_manager.save_project(self.project)

                    if new_note:
                        self.echo(f"\n  Nota guardada para analisis {analysis_id}.")
                    else:
                        self.echo(f"\n  Nota eliminada de analisis {analysis_id}.")
                break

    def _view_analysis_notes(self) -> None:
        """Muestra las notas de todos los analisis."""
        self.echo("\n  Notas de analisis:")
        self.echo(f"  {'-'*50}")

        for a in self.basin.analyses:
            if a.note:
                hydro = a.hydrograph
                storm = a.storm
                x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
                self.echo(f"\n  [{a.id}] {hydro.tc_method} Tr{storm.return_period}{x_str}")
                self.echo(f"    Qp={hydro.peak_flow_m3s:.2f} m3/s")
                self.echo(f"    Nota: {a.note}")
