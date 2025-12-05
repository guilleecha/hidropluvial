"""
Menu post-ejecucion de analisis.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.session import Session


class PostExecutionMenu(SessionMenu):
    """Menu despues de ejecutar analisis."""

    def __init__(
        self,
        session: Session,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(session)
        # Usar valores de la sesion si no se pasan explicitamente
        self.c = c if c is not None else session.cuenca.c
        self.cn = cn if cn is not None else session.cuenca.cn
        self.length = length if length is not None else session.cuenca.length_m

    def show(self) -> None:
        """Muestra el menu post-ejecucion en un loop."""
        while True:
            self.echo("")
            action = self.select(
                "Que deseas hacer ahora?",
                choices=[
                    "Ver tabla con sparklines",
                    "Ver hidrogramas (grafico)",
                    "Comparar hidrogramas",
                    "Filtrar resultados",
                    "Agregar mas analisis",
                    "Definir CN por ponderacion (tablas NRCS)",
                    "Editar datos de la cuenca",
                    "Generar reporte LaTeX",
                    "Salir",
                ],
            )

            if action is None or "Salir" in action:
                self.echo(f"\n  Sesion guardada: {self.session.id}")
                self.echo(f"  Usa 'hp session summary {self.session.id}' para ver resultados.\n")
                break

            self._handle_action(action)

    def _handle_action(self, action: str) -> None:
        """Maneja la accion seleccionada."""
        if "tabla" in action.lower():
            self._show_table()
        elif "Comparar" in action:
            self._compare_hydrographs()
        elif "grafico" in action.lower():
            self._show_single_hydrograph()
        elif "Filtrar" in action:
            self._filter_results()
        elif "reporte" in action.lower():
            self._generate_report()
        elif "ponderacion" in action.lower():
            self._define_weighted_cn()
            self.reload_session()
        elif "Editar" in action:
            result = self._edit_cuenca()
            if result == "new_session":
                return  # Salir del menu
            elif result == "modified":
                self.reload_session()
        elif "Agregar" in action:
            self._add_analysis()
            self.reload_session()

    def _show_table(self) -> None:
        """Muestra tabla con sparklines."""
        from hidropluvial.cli.session.preview import session_preview
        session_preview(self.session.id, analysis_idx=None, compare=False)

    def _compare_hydrographs(self) -> None:
        """Compara todos los hidrogramas."""
        from hidropluvial.cli.session.preview import session_preview
        session_preview(self.session.id, analysis_idx=None, compare=True)

    def _show_single_hydrograph(self) -> None:
        """Muestra un hidrograma individual."""
        n_analyses = len(self.session.analyses)
        if n_analyses == 0:
            self.echo("  No hay analisis disponibles.")
            return

        choices = []
        for i, a in enumerate(self.session.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            choices.append(f"{i}: {hydro.tc_method} + {storm.type} Tr{storm.return_period}{x_str}")

        selected = self.select("Selecciona analisis:", choices)
        if selected:
            idx = int(selected.split(":")[0])
            from hidropluvial.cli.session.preview import session_preview
            session_preview(self.session.id, analysis_idx=idx, compare=False)

    def _generate_report(self) -> None:
        """Genera reporte LaTeX."""
        default_name = self.session.name.lower().replace(" ", "_")
        output = self.text("Nombre del archivo (sin extension):", default=default_name)

        if output:
            from hidropluvial.cli.session.report import session_report
            session_report(self.session.id, output, author=None, template_dir=None)
            self.echo(f"\n  Reporte generado: {output}.tex")

    def _define_weighted_cn(self) -> None:
        """Define el CN mediante ponderacion por areas."""
        from hidropluvial.cli.runoff import collect_weighted_cn_interactive

        self.header("DEFINIR CN POR PONDERACION")

        # Mostrar CN actual si existe
        if self.session.cuenca.cn:
            self.echo(f"\n  CN actual: {self.session.cuenca.cn}")
            if self.session.cuenca.cn_weighted:
                n_items = len(self.session.cuenca.cn_weighted.items)
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
            area_total=self.session.cuenca.area_ha,
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

        # Guardar en la sesion
        self.manager.set_weighted_coefficient(self.session, weighted_result)
        self.cn = cn_value

        self.echo(f"\n  CN actualizado a {self.cn}")
        self.echo("    Los datos de ponderacion se incluiran en el reporte.")

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la sesion."""
        from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
        menu = AddAnalysisMenu(self.session, self.c, self.cn, self.length)
        menu.show()

    def _filter_results(self) -> None:
        """Muestra menu de filtrado de resultados."""
        self.echo("\n-- Filtrar Resultados --\n")

        # Obtener valores unicos de la sesion
        tr_values = sorted(set(a.storm.return_period for a in self.session.analyses))
        x_values = sorted(set(a.hydrograph.x_factor for a in self.session.analyses if a.hydrograph.x_factor))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.session.analyses))
        storm_types = sorted(set(a.storm.type for a in self.session.analyses))

        x_choice = f"Factor X: {x_values}" if x_values else "Factor X: (no disponible)"
        filter_type = self.select(
            "Filtrar por:",
            choices=[
                f"Periodo de retorno (Tr): {tr_values}",
                x_choice,
                f"Metodo Tc: {tc_methods}",
                f"Tipo de tormenta: {storm_types}",
                "Combinacion personalizada",
                "Cancelar",
            ],
        )

        if filter_type is None or "Cancelar" in filter_type:
            return

        filters = self._collect_filters(filter_type, tr_values, x_values, tc_methods, storm_types)
        self._show_filtered_results(**filters)

    def _collect_filters(
        self,
        filter_type: str,
        tr_values: list,
        x_values: list,
        tc_methods: list,
        storm_types: list,
    ) -> dict:
        """Recolecta los filtros segun el tipo seleccionado."""
        tr_filter = None
        x_filter = None
        tc_filter = None
        storm_filter = None

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

        elif "tormenta" in filter_type:
            storm_choices = [questionary.Choice(v, checked=False) for v in storm_types]
            selected = self.checkbox("Selecciona tipo de tormenta:", storm_choices)
            if selected:
                storm_filter = ",".join(selected)

        elif "Combinacion" in filter_type:
            tr_filter, x_filter, tc_filter = self._collect_combined_filters(
                tr_values, x_values, tc_methods
            )

        return {
            "tr_filter": tr_filter,
            "x_filter": x_filter,
            "tc_filter": tc_filter,
            "storm_filter": storm_filter,
        }

    def _collect_combined_filters(
        self,
        tr_values: list,
        x_values: list,
        tc_methods: list,
    ) -> tuple:
        """Recolecta filtros combinados."""
        tr_filter = None
        x_filter = None
        tc_filter = None

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

        return tr_filter, x_filter, tc_filter

    def _show_filtered_results(
        self,
        tr_filter: Optional[str],
        x_filter: Optional[str],
        tc_filter: Optional[str],
        storm_filter: Optional[str],
    ) -> None:
        """Muestra resultados filtrados."""
        from hidropluvial.cli.session.preview import session_preview

        session_preview(
            self.session.id,
            analysis_idx=None,
            compare=False,
            tr=tr_filter,
            x=x_filter,
            tc=tc_filter,
            storm=storm_filter,
        )

        # Ofrecer comparar filtrados
        if self.confirm("Comparar hidrogramas filtrados?", default=False):
            session_preview(
                self.session.id,
                analysis_idx=None,
                compare=True,
                tr=tr_filter,
                x=x_filter,
                tc=tc_filter,
                storm=storm_filter,
            )

    def _edit_cuenca(self) -> str:
        """
        Permite editar los datos de la cuenca.

        Returns:
            "new_session" si se creo nueva sesion
            "modified" si se modifico la sesion actual
            "cancelled" si se cancelo
        """
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
        editor = CuencaEditor(self.session, self.manager)
        return editor.edit()
