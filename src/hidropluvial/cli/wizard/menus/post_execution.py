"""
Menú post-ejecución de análisis.

Organizado en submenús temáticos:
- Ver resultados: tabla, fichas, comparar, hietograma, filtrar
- Agregar/Editar: agregar análisis, editar cuenca, definir CN, notas
- Exportar: Excel, LaTeX
"""

from typing import Optional

import typer

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
from hidropluvial.project import Project
from hidropluvial.models import Basin


class PostExecutionMenu(SessionMenu):
    """Menú después de ejecutar análisis."""

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

        # Usar valores de la cuenca si no se pasan explícitamente
        self.c = c if c is not None else basin.c
        self.cn = cn if cn is not None else basin.cn
        self.length = length if length is not None else basin.length_m

    def show(self) -> None:
        """Muestra el menú post-ejecución con submenús agrupados."""
        while True:
            self.reload_session()

            n_analyses = len(self.basin.analyses) if self.basin.analyses else 0

            items = [
                # Grupo: Ver resultados
                MenuItem(
                    key="v",
                    label="Ver resultados",
                    value="view",
                    hint=f"{n_analyses} análisis",
                ),
                MenuItem(key="", label="", separator=True),
                # Grupo: Agregar/Editar
                MenuItem(
                    key="a",
                    label="Agregar análisis",
                    value="add_analysis",
                    hint="Nuevas combinaciones",
                ),
                MenuItem(
                    key="e",
                    label="Editar cuenca",
                    value="edit",
                    hint="Datos y parámetros",
                ),
                MenuItem(key="", label="", separator=True),
                # Exportar
                MenuItem(
                    key="x",
                    label="Exportar",
                    value="export",
                    hint="Excel / LaTeX",
                ),
                MenuItem(key="", label="", separator=True),
                # Volver
                MenuItem(
                    key="q",
                    label="Volver al menú principal",
                    value="back",
                ),
            ]

            # Construir info panel con datos de la cuenca
            info_panel = self._build_basin_info_panel()

            action = menu_panel(
                title="Menú de Cuenca",
                items=items,
                subtitle=f"{self.basin.name} - {self.project.name}",
                info_panel=info_panel,
                allow_back=True,
            )

            if action is None or action == "back":
                self.success(f"Cuenca guardada: {self.basin.id}")
                self.info(f"Proyecto: {self.project.name} [{self.project.id}]")
                break

            self._handle_action(action)

    def _build_basin_info_panel(self):
        """Construye panel de información de la cuenca."""
        from rich.panel import Panel
        from rich.text import Text
        from hidropluvial.cli.theme import get_palette

        p = get_palette()
        info = Text()

        # Datos básicos
        info.append("  Área: ", style=p.muted)
        info.append(f"{self.basin.area_ha:.1f} ha", style=f"bold {p.number}")
        info.append("  │  Pendiente: ", style=p.muted)
        info.append(f"{self.basin.slope_pct:.1f}%", style=f"bold {p.number}")

        # Coeficientes
        if self.c:
            info.append("  │  C: ", style=p.muted)
            info.append(f"{self.c:.2f}", style=f"bold {p.number}")
        if self.cn:
            info.append("  │  CN: ", style=p.muted)
            info.append(f"{self.cn}", style=f"bold {p.number}")

        # Tc si existe
        if self.basin.tc_results:
            tc = self.basin.tc_results[0].tc_min
            info.append("  │  Tc: ", style=p.muted)
            info.append(f"{tc:.0f} min", style=f"bold {p.number}")

        # Análisis
        n = len(self.basin.analyses) if self.basin.analyses else 0
        info.append("\n  Análisis: ", style=p.muted)
        info.append(f"{n}", style=f"bold {p.primary}")

        if n > 0:
            # Resumen de tipos
            trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
            info.append(f"  │  Tr: {trs}", style=p.muted)

        return Panel(info, border_style=p.border, padding=(0, 1))

    def _handle_action(self, action: str) -> None:
        """Maneja la acción seleccionada."""
        if action == "view":
            self._show_view_submenu()
        elif action == "add_analysis":
            self._add_analysis()
        elif action == "edit":
            self._show_edit_submenu()
        elif action == "export":
            self._export()

    def _show_view_submenu(self) -> None:
        """Submenú para ver resultados."""
        while True:
            n_analyses = len(self.basin.analyses) if self.basin.analyses else 0
            has_analyses = n_analyses > 0

            items = [
                MenuItem(
                    key="t",
                    label="Tabla resumen",
                    value="table",
                    disabled=not has_analyses,
                ),
                MenuItem(
                    key="f",
                    label="Fichas de análisis",
                    value="cards",
                    hint="Navegación interactiva",
                    disabled=not has_analyses,
                ),
                MenuItem(
                    key="c",
                    label="Comparar hidrogramas",
                    value="compare",
                    disabled=not has_analyses,
                ),
                MenuItem(
                    key="h",
                    label="Ver hietograma",
                    value="hyetograph",
                    disabled=not has_analyses,
                ),
                MenuItem(key="", label="", separator=True),
                MenuItem(
                    key="r",
                    label="Filtrar resultados",
                    value="filter",
                    disabled=not has_analyses,
                ),
            ]

            action = menu_panel(
                title="Ver Resultados",
                items=items,
                subtitle=f"{n_analyses} análisis disponibles",
                allow_back=True,
            )

            if action is None:
                break

            if action == "table":
                self._show_table()
            elif action == "cards":
                self._show_interactive_viewer()
            elif action == "compare":
                self._compare_hydrographs()
            elif action == "hyetograph":
                self._show_hyetograph()
            elif action == "filter":
                self._filter_results()

    def _show_edit_submenu(self) -> None:
        """Submenú para editar cuenca y datos."""
        while True:
            items = [
                MenuItem(
                    key="d",
                    label="Datos de la cuenca",
                    value="edit_data",
                    hint="Área, pendiente, longitud",
                ),
                MenuItem(
                    key="c",
                    label="Definir CN ponderado",
                    value="define_cn",
                    hint="Tablas NRCS",
                ),
                MenuItem(
                    key="n",
                    label="Notas y comentarios",
                    value="notes",
                ),
            ]

            action = menu_panel(
                title="Editar Cuenca",
                items=items,
                subtitle=self.basin.name,
                allow_back=True,
            )

            if action is None:
                break

            if action == "edit_data":
                result = self._edit_cuenca()
                if result == "new_session":
                    break
            elif action == "define_cn":
                self._define_weighted_cn()
            elif action == "notes":
                self._manage_notes()

    def _safe_call(self, func, *args, **kwargs) -> None:
        """Ejecuta una función capturando typer.Exit para no salir del wizard."""
        try:
            func(*args, **kwargs)
        except SystemExit:
            pass

    def _show_table(self) -> None:
        """Muestra tabla resumen interactiva."""
        self.show_summary_table()

    def _compare_hydrographs(self) -> None:
        """Compara hidrogramas con opción de seleccionar cuáles."""
        if not self.basin.analyses:
            self.warning("No hay análisis disponibles.")
            return

        n = len(self.basin.analyses)
        if n > 2:
            items = [
                MenuItem(key="t", label="Todos", value="all"),
                MenuItem(key="s", label="Seleccionar cuáles", value="select"),
            ]

            mode = menu_panel(
                title="Comparar Hidrogramas",
                items=items,
                subtitle=f"{n} análisis disponibles",
                allow_back=True,
            )

            if mode is None:
                return

            if mode == "select":
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
        """Permite seleccionar análisis para comparar."""
        choices = []
        for i, a in enumerate(self.basin.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            label = f"[{i}] {hydro.tc_method} {storm.type} Tr{storm.return_period}{x_str} Qp={hydro.peak_flow_m3s:.2f} m³/s"
            choices.append({"name": label, "value": i, "checked": True})

        selected = self.checkbox("Selecciona análisis a comparar:", choices)

        if not selected:
            return None

        # selected contiene los índices directamente
        return ",".join(str(idx) for idx in selected)

    def _show_interactive_viewer(self) -> None:
        """Muestra visor interactivo de fichas de análisis."""
        self.show_analysis_cards()

    def _show_hyetograph(self) -> None:
        """Muestra hietograma de un análisis."""
        if not self.basin.analyses:
            self.warning("No hay análisis disponibles.")
            return

        from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

        items = []
        for i, a in enumerate(self.basin.analyses):
            storm = a.storm
            key = chr(ord('a') + i) if i < 26 else str(i)
            items.append(MenuItem(
                key=key,
                label=f"{storm.type} Tr{storm.return_period}",
                value=str(i),
                hint=f"P={storm.total_depth_mm:.1f} mm",
            ))

        selected = menu_panel(
            title="Ver Hietograma",
            items=items,
            subtitle="Selecciona análisis",
            allow_back=True,
        )

        if selected is not None:
            idx = int(selected)
            analysis = self.basin.analyses[idx]
            from hidropluvial.cli.basin.preview import basin_preview_hyetograph
            self._safe_call(basin_preview_hyetograph, analysis, self.basin.name)

    def _export(self) -> None:
        """Exporta los resultados a Excel o LaTeX."""
        from hidropluvial.cli.wizard.menus.export_menu import ExportMenu
        export_menu = ExportMenu(self.basin, self.project)
        export_menu.show()

    def _define_weighted_cn(self) -> None:
        """Define el CN mediante ponderación por áreas."""
        from hidropluvial.cli.runoff import collect_weighted_cn_interactive
        from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

        self.header("DEFINIR CN POR PONDERACIÓN")

        if self.basin.cn:
            self.info(f"CN actual: {self.basin.cn}")
            if hasattr(self.basin, 'cn_weighted') and self.basin.cn_weighted:
                n_items = len(self.basin.cn_weighted.items)
                self.note(f"Calculado por ponderación con {n_items} coberturas")

        items = [
            MenuItem(key="a", label="A - Arena, grava", value="A", hint="Alta infiltración"),
            MenuItem(key="b", label="B - Limos, suelos moderados", value="B"),
            MenuItem(key="c", label="C - Arcilla limosa", value="C", hint="Baja infiltración"),
            MenuItem(key="d", label="D - Arcilla, impermeables", value="D"),
        ]

        soil = menu_panel(
            title="Grupo Hidrológico del Suelo",
            items=items,
            allow_back=True,
        )

        if soil is None:
            return

        weighted_result = collect_weighted_cn_interactive(
            area_total=self.basin.area_ha,
            soil_group=soil,
            echo_fn=typer.echo,
        )

        if weighted_result is None:
            self.info("Operación cancelada.")
            return

        cn_value = int(round(weighted_result.weighted_value))
        self.info(f"Se actualizará el CN de la cuenca a: {cn_value}")
        if not self.confirm("¿Aplicar cambios?"):
            return

        self.basin.cn = cn_value
        if hasattr(self.basin, 'cn_weighted'):
            self.basin.cn_weighted = weighted_result
        self.cn = cn_value

        from hidropluvial.project import get_project_manager
        project_manager = get_project_manager()
        project_manager.save_project(self.project)

        self.success(f"CN actualizado a {self.cn}")
        self.info("Los datos de ponderación se incluirán en el reporte.")

    def _add_analysis(self) -> None:
        """Agrega más análisis a la cuenca."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
        menu = AddAnalysisMenu(self.basin, self.c, self.cn, self.length)
        menu.show()

    def _filter_results(self) -> None:
        """Muestra menú de filtrado de resultados."""
        from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

        # Obtener valores únicos
        tr_values = sorted(set(a.storm.return_period for a in self.basin.analyses))
        x_values = sorted(set(a.hydrograph.x_factor for a in self.basin.analyses if a.hydrograph.x_factor))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.basin.analyses))
        storm_types = sorted(set(a.storm.type for a in self.basin.analyses))

        runoff_methods = set()
        for a in self.basin.analyses:
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                runoff_methods.add(a.tc.parameters["runoff_method"])
            elif a.tc.parameters:
                if "cn_adjusted" in a.tc.parameters:
                    runoff_methods.add("scs-cn")
                elif "c" in a.tc.parameters:
                    runoff_methods.add("racional")
        runoff_methods = sorted(runoff_methods)

        items = [
            MenuItem(
                key="t",
                label="Por período de retorno",
                value="tr",
                hint=f"Tr: {tr_values}",
            ),
            MenuItem(
                key="x",
                label="Por factor X",
                value="x",
                hint=f"X: {[f'{v:.2f}' for v in x_values]}" if x_values else "No disponible",
                disabled=not x_values,
            ),
            MenuItem(
                key="m",
                label="Por método Tc",
                value="tc",
                hint=f"{len(tc_methods)} métodos",
            ),
            MenuItem(
                key="s",
                label="Por tipo de tormenta",
                value="storm",
                hint=f"{len(storm_types)} tipos",
            ),
            MenuItem(
                key="e",
                label="Por método escorrentía",
                value="runoff",
                disabled=not runoff_methods,
            ),
            MenuItem(key="", label="", separator=True),
            MenuItem(
                key="c",
                label="Combinación personalizada",
                value="combined",
            ),
        ]

        filter_type = menu_panel(
            title="Filtrar Resultados",
            items=items,
            allow_back=True,
        )

        if filter_type is None:
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
        """Recolecta los filtros según el tipo seleccionado."""
        tr_filter = None
        x_filter = None
        tc_filter = None
        storm_filter = None
        runoff_filter = None

        if filter_type == "tr":
            tr_choices = [{"name": str(v), "value": str(v), "checked": False} for v in tr_values]
            selected = self.checkbox("Selecciona período(s) de retorno:", tr_choices)
            if selected:
                tr_filter = ",".join(selected)

        elif filter_type == "x" and x_values:
            x_choices = [{"name": f"{v:.2f}", "value": f"{v:.2f}", "checked": False} for v in x_values]
            selected = self.checkbox("Selecciona factor(es) X:", x_choices)
            if selected:
                x_filter = ",".join(selected)

        elif filter_type == "tc":
            tc_choices = [{"name": v, "value": v, "checked": False} for v in tc_methods]
            selected = self.checkbox("Selecciona método(s) Tc:", tc_choices)
            if selected:
                tc_filter = ",".join(selected)

        elif filter_type == "storm":
            storm_choices = [{"name": v, "value": v, "checked": False} for v in storm_types]
            selected = self.checkbox("Selecciona tipo(s) de tormenta:", storm_choices)
            if selected:
                storm_filter = ",".join(selected)

        elif filter_type == "runoff" and runoff_methods:
            runoff_labels = {
                "racional": "Racional (C)",
                "scs-cn": "SCS-CN (CN)",
            }
            runoff_choices = [
                {"name": runoff_labels.get(v, v), "value": v, "checked": False}
                for v in runoff_methods
            ]
            selected = self.checkbox("Selecciona método(s) de escorrentía:", runoff_choices)
            if selected:
                runoff_filter = ",".join(selected)

        elif filter_type == "combined":
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

        tr_choices = [{"name": str(v), "value": str(v), "checked": False} for v in tr_values]
        tr_selected = self.checkbox("Períodos de retorno (Enter para todos):", tr_choices)
        if tr_selected:
            tr_filter = ",".join(tr_selected)

        if x_values:
            x_choices = [{"name": f"{v:.2f}", "value": f"{v:.2f}", "checked": False} for v in x_values]
            x_selected = self.checkbox("Factores X (Enter para todos):", x_choices)
            if x_selected:
                x_filter = ",".join(x_selected)

        tc_choices = [{"name": v, "value": v, "checked": False} for v in tc_methods]
        tc_selected = self.checkbox("Métodos Tc (Enter para todos):", tc_choices)
        if tc_selected:
            tc_filter = ",".join(tc_selected)

        if runoff_methods:
            runoff_labels = {
                "racional": "Racional (C)",
                "scs-cn": "SCS-CN (CN)",
            }
            runoff_choices = [
                {"name": runoff_labels.get(v, v), "value": v, "checked": False}
                for v in runoff_methods
            ]
            runoff_selected = self.checkbox("Métodos escorrentía (Enter para todos):", runoff_choices)
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

        if self.confirm("¿Comparar hidrogramas filtrados?", default=False):
            filtered_analyses = self.basin.analyses
            self._safe_call(basin_preview_compare, filtered_analyses, self.basin.name)

    def _edit_cuenca(self) -> str:
        """Permite editar los datos de la cuenca."""
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(self.basin)
        result = editor.edit()

        if result == "modified":
            from hidropluvial.project import get_project_manager
            project_manager = get_project_manager()
            self.project = project_manager.get_project(self.project.id)

        return result

    def _manage_notes(self) -> None:
        """Gestiona notas de la cuenca y análisis."""
        from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

        while True:
            # Mostrar notas actuales
            has_basin_notes = bool(self.basin.notes)
            analyses_with_notes = [a for a in self.basin.analyses if a.note]

            items = [
                MenuItem(
                    key="c",
                    label="Notas de la cuenca",
                    value="basin",
                    hint="Editar" if has_basin_notes else "Agregar",
                ),
                MenuItem(
                    key="a",
                    label="Nota a un análisis",
                    value="analysis",
                    hint="Agregar/editar",
                    disabled=not self.basin.analyses,
                ),
            ]

            if analyses_with_notes:
                items.append(MenuItem(
                    key="v",
                    label="Ver notas de análisis",
                    value="view",
                    hint=f"{len(analyses_with_notes)} con notas",
                ))

            action = menu_panel(
                title="Notas y Comentarios",
                items=items,
                allow_back=True,
            )

            if action is None:
                break

            if action == "basin":
                self._edit_basin_notes()
            elif action == "analysis":
                self._add_analysis_note()
            elif action == "view":
                self._view_analysis_notes()

    def _edit_basin_notes(self) -> None:
        """Edita las notas generales de la cuenca."""
        from hidropluvial.cli.viewer.panel_input import panel_text

        current = self.basin.notes or ""

        new_notes = panel_text(
            title="Notas de la Cuenca",
            default=current,
            hint="Dejar vacío para eliminar",
        )

        if new_notes is not None:
            self.basin.notes = new_notes
            from hidropluvial.project import get_project_manager
            project_manager = get_project_manager()
            project_manager.save_project(self.project)

            if new_notes:
                self.success("Notas guardadas.")
            else:
                self.info("Notas eliminadas.")

    def _add_analysis_note(self) -> None:
        """Agrega una nota a un análisis específico."""
        if not self.basin.analyses:
            self.warning("No hay análisis disponibles.")
            return

        from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

        items = []
        for i, a in enumerate(self.basin.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            note_indicator = " [nota]" if a.note else ""
            key = chr(ord('a') + i) if i < 26 else str(i)
            items.append(MenuItem(
                key=key,
                label=f"{hydro.tc_method} Tr{storm.return_period}{x_str}",
                value=a.id,
                hint=f"Qp={hydro.peak_flow_m3s:.2f}{note_indicator}",
            ))

        selected_id = menu_panel(
            title="Seleccionar Análisis",
            items=items,
            allow_back=True,
        )

        if selected_id is None:
            return

        from hidropluvial.cli.viewer.panel_input import panel_text

        for a in self.basin.analyses:
            if a.id == selected_id:
                new_note = panel_text(
                    title="Nota del Análisis",
                    default=a.note or "",
                    hint="Vacío para eliminar",
                )

                if new_note is not None:
                    a.note = new_note
                    from hidropluvial.project import get_project_manager
                    project_manager = get_project_manager()
                    project_manager.save_project(self.project)

                    if new_note:
                        self.success(f"Nota guardada.")
                    else:
                        self.info(f"Nota eliminada.")
                break

    def _view_analysis_notes(self) -> None:
        """Muestra las notas de todos los análisis."""
        from rich.table import Table
        from hidropluvial.cli.theme import get_palette, get_console

        console = get_console()
        p = get_palette()

        table = Table(
            title="Notas de Análisis",
            title_style=f"bold {p.primary}",
            border_style=p.border,
        )
        table.add_column("Análisis", style="bold")
        table.add_column("Nota")

        for a in self.basin.analyses:
            if a.note:
                hydro = a.hydrograph
                storm = a.storm
                x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
                label = f"{hydro.tc_method} Tr{storm.return_period}{x_str}"
                table.add_row(label, a.note)

        console.print(table)
        input("\n  Presiona Enter para continuar...")
