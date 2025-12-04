"""
Menus interactivos para el wizard.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner
from hidropluvial.core import kirpich, desbordes, temez
from hidropluvial.session import Session


class PostExecutionMenu:
    """Menu despues de ejecutar analisis."""

    def __init__(self, session: Session, c: float = None, cn: float = None, length: float = None):
        self.session = session
        self.manager = get_session_manager()
        self.c = c
        self.cn = cn
        self.length = length

    def show(self) -> None:
        """Muestra el menu post-ejecucion en un loop."""
        while True:
            typer.echo("")
            action = questionary.select(
                "Que deseas hacer ahora?",
                choices=[
                    "Ver tabla con sparklines",
                    "Ver hidrogramas (grafico)",
                    "Comparar hidrogramas",
                    "Filtrar resultados",
                    "Agregar mas analisis",
                    "Editar datos de la cuenca",
                    "Generar reporte LaTeX",
                    "Salir",
                ],
                style=WIZARD_STYLE,
            ).ask()

            if action is None or "Salir" in action:
                typer.echo(f"\n  Sesion guardada: {self.session.id}")
                typer.echo(f"  Usa 'hp session summary {self.session.id}' para ver resultados.\n")
                break

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
            elif "Editar" in action:
                result = self._edit_cuenca()
                if result == "new_session":
                    # Se creo nueva sesion, salir del loop
                    break
                elif result == "modified":
                    # Sesion modificada, recargar
                    self.session = self.manager.get_session(self.session.id)
            elif "Agregar" in action:
                self._add_analysis()
                # Recargar sesion actualizada
                self.session = self.manager.get_session(self.session.id)

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
            typer.echo("  No hay analisis disponibles.")
            return

        choices = []
        for i, a in enumerate(self.session.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            choices.append(f"{i}: {hydro.tc_method} + {storm.type} Tr{storm.return_period}{x_str}")

        selected = questionary.select(
            "Selecciona analisis:",
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if selected:
            idx = int(selected.split(":")[0])
            from hidropluvial.cli.session.preview import session_preview
            session_preview(self.session.id, analysis_idx=idx, compare=False)

    def _generate_report(self) -> None:
        """Genera reporte LaTeX."""
        default_name = self.session.name.lower().replace(" ", "_")
        output = questionary.text(
            "Nombre del archivo (sin extension):",
            default=default_name,
            style=WIZARD_STYLE,
        ).ask()

        if output:
            from hidropluvial.cli.session.report import session_report
            session_report(self.session.id, output, author=None, template_dir=None)
            typer.echo(f"\n  Reporte generado: {output}.tex")

    def _add_analysis(self) -> None:
        """Agrega mas analisis a la sesion."""
        menu = AddAnalysisMenu(self.session, self.c, self.cn, self.length)
        menu.show()

    def _filter_results(self) -> None:
        """Muestra menu de filtrado de resultados."""
        typer.echo("\n-- Filtrar Resultados --\n")

        # Obtener valores unicos de la sesion
        tr_values = sorted(set(a.storm.return_period for a in self.session.analyses))
        x_values = sorted(set(a.hydrograph.x_factor for a in self.session.analyses if a.hydrograph.x_factor))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.session.analyses))
        storm_types = sorted(set(a.storm.type for a in self.session.analyses))

        filter_type = questionary.select(
            "Filtrar por:",
            choices=[
                f"Periodo de retorno (Tr): {tr_values}",
                f"Factor X: {x_values}" if x_values else "Factor X: (no disponible)",
                f"Metodo Tc: {tc_methods}",
                f"Tipo de tormenta: {storm_types}",
                "Combinacion personalizada",
                "Cancelar",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if filter_type is None or "Cancelar" in filter_type:
            return

        tr_filter = None
        x_filter = None
        tc_filter = None
        storm_filter = None

        if "Periodo de retorno" in filter_type:
            tr_choices = [questionary.Choice(str(v), checked=False) for v in tr_values]
            selected = questionary.checkbox(
                "Selecciona Tr:",
                choices=tr_choices,
                style=WIZARD_STYLE,
            ).ask()
            if selected:
                tr_filter = ",".join(selected)

        elif "Factor X" in filter_type and x_values:
            x_choices = [questionary.Choice(f"{v:.2f}", checked=False) for v in x_values]
            selected = questionary.checkbox(
                "Selecciona X:",
                choices=x_choices,
                style=WIZARD_STYLE,
            ).ask()
            if selected:
                x_filter = ",".join(selected)

        elif "Metodo Tc" in filter_type:
            tc_choices = [questionary.Choice(v, checked=False) for v in tc_methods]
            selected = questionary.checkbox(
                "Selecciona metodo Tc:",
                choices=tc_choices,
                style=WIZARD_STYLE,
            ).ask()
            if selected:
                tc_filter = ",".join(selected)

        elif "tormenta" in filter_type:
            storm_choices = [questionary.Choice(v, checked=False) for v in storm_types]
            selected = questionary.checkbox(
                "Selecciona tipo de tormenta:",
                choices=storm_choices,
                style=WIZARD_STYLE,
            ).ask()
            if selected:
                storm_filter = ",".join(selected)

        elif "Combinacion" in filter_type:
            # Permitir multiples filtros
            tr_choices = [questionary.Choice(str(v), checked=False) for v in tr_values]
            tr_selected = questionary.checkbox(
                "Periodos de retorno (Enter para todos):",
                choices=tr_choices,
                style=WIZARD_STYLE,
            ).ask()
            if tr_selected:
                tr_filter = ",".join(tr_selected)

            if x_values:
                x_choices = [questionary.Choice(f"{v:.2f}", checked=False) for v in x_values]
                x_selected = questionary.checkbox(
                    "Factores X (Enter para todos):",
                    choices=x_choices,
                    style=WIZARD_STYLE,
                ).ask()
                if x_selected:
                    x_filter = ",".join(x_selected)

            tc_choices = [questionary.Choice(v, checked=False) for v in tc_methods]
            tc_selected = questionary.checkbox(
                "Metodos Tc (Enter para todos):",
                choices=tc_choices,
                style=WIZARD_STYLE,
            ).ask()
            if tc_selected:
                tc_filter = ",".join(tc_selected)

        # Mostrar resultados filtrados
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
        if questionary.confirm("Comparar hidrogramas filtrados?", default=False, style=WIZARD_STYLE).ask():
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
        typer.echo("\n" + "="*65)
        typer.echo("  EDITAR DATOS DE LA CUENCA")
        typer.echo("="*65)

        cuenca = self.session.cuenca
        n_analyses = len(self.session.analyses)
        n_tc = len(self.session.tc_results)

        # Mostrar datos actuales
        typer.echo(f"\n  Datos actuales:")
        typer.echo(f"  {'-'*40}")
        typer.echo(f"  Area:         {cuenca.area_ha:>12.2f} ha")
        typer.echo(f"  Pendiente:    {cuenca.slope_pct:>12.2f} %")
        typer.echo(f"  P3,10:        {cuenca.p3_10:>12.1f} mm")
        if cuenca.c:
            typer.echo(f"  Coef. C:      {cuenca.c:>12.2f}")
        if cuenca.cn:
            typer.echo(f"  CN:           {cuenca.cn:>12}")
        if cuenca.length_m:
            typer.echo(f"  Longitud:     {cuenca.length_m:>12.0f} m")

        if n_analyses > 0 or n_tc > 0:
            typer.echo(f"\n  ⚠️  ADVERTENCIA:")
            typer.echo(f"      Esta sesion tiene {n_tc} calculos de Tc y {n_analyses} analisis.")
            typer.echo(f"      Los cambios INVALIDARAN estos resultados.")

        # Opciones
        action = questionary.select(
            "\nQue deseas hacer?",
            choices=[
                "Modificar sesion actual (elimina analisis existentes)",
                "Crear nueva sesion con datos modificados (preserva original)",
                "Cancelar",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if action is None or "Cancelar" in action:
            return "cancelled"

        clone_mode = "nueva" in action.lower()

        # Solicitar nuevos valores
        typer.echo("\n  Ingresa nuevos valores (Enter para mantener actual):\n")

        def ask_float(prompt: str, current: float, required: bool = True) -> Optional[float]:
            default_str = f"{current:.2f}" if current else ""
            val = questionary.text(
                prompt,
                default=default_str,
                style=WIZARD_STYLE,
            ).ask()
            if val is None:
                return None
            val = val.strip()
            if val == "" or val == default_str:
                return None  # Mantener actual
            try:
                return float(val)
            except ValueError:
                typer.echo(f"  Valor invalido, se mantiene {current}")
                return None

        new_area = ask_float(f"Area (ha) [{cuenca.area_ha:.2f}]:", cuenca.area_ha)
        new_slope = ask_float(f"Pendiente (%) [{cuenca.slope_pct:.2f}]:", cuenca.slope_pct)
        new_p3_10 = ask_float(f"P3,10 (mm) [{cuenca.p3_10:.1f}]:", cuenca.p3_10)
        new_c = ask_float(f"Coef. C [{cuenca.c if cuenca.c else 'N/A'}]:", cuenca.c or 0)
        new_cn_str = questionary.text(
            f"CN [{cuenca.cn if cuenca.cn else 'N/A'}]:",
            default=str(cuenca.cn) if cuenca.cn else "",
            style=WIZARD_STYLE,
        ).ask()
        new_cn = None
        if new_cn_str and new_cn_str.strip() and new_cn_str != str(cuenca.cn):
            try:
                new_cn = int(new_cn_str)
            except ValueError:
                pass
        new_length = ask_float(f"Longitud (m) [{cuenca.length_m if cuenca.length_m else 'N/A'}]:", cuenca.length_m or 0)

        # Verificar si hay cambios
        if all(v is None or v == 0 for v in [new_area, new_slope, new_p3_10, new_c, new_cn, new_length]):
            typer.echo("\n  No se especificaron cambios.")
            return "cancelled"

        # Confirmar
        typer.echo(f"\n  Cambios a aplicar:")
        if new_area:
            typer.echo(f"    Area: {cuenca.area_ha} → {new_area} ha")
        if new_slope:
            typer.echo(f"    Pendiente: {cuenca.slope_pct} → {new_slope}%")
        if new_p3_10:
            typer.echo(f"    P3,10: {cuenca.p3_10} → {new_p3_10} mm")
        if new_c:
            typer.echo(f"    C: {cuenca.c} → {new_c}")
        if new_cn:
            typer.echo(f"    CN: {cuenca.cn} → {new_cn}")
        if new_length:
            typer.echo(f"    Longitud: {cuenca.length_m} → {new_length} m")

        if not questionary.confirm("\nAplicar cambios?", default=True, style=WIZARD_STYLE).ask():
            return "cancelled"

        if clone_mode:
            # Crear nueva sesion
            new_name = questionary.text(
                "Nombre para la nueva sesion:",
                default=f"{self.session.name} (modificado)",
                style=WIZARD_STYLE,
            ).ask()

            new_session, changes = self.manager.clone_with_modified_cuenca(
                self.session,
                new_name=new_name,
                area_ha=new_area,
                slope_pct=new_slope,
                p3_10=new_p3_10,
                c=new_c,
                cn=new_cn,
                length_m=new_length,
            )

            typer.echo(f"\n  ✓ Nueva sesion creada: {new_session.id}")
            typer.echo(f"    Nombre: {new_session.name}")
            typer.echo(f"\n  Sesion original '{self.session.id}' sin modificar.")
            typer.echo(f"\n  Usa 'hp session tc {new_session.id}' para calcular Tc")
            typer.echo(f"  Usa 'hp wizard' para continuar con la nueva sesion\n")
            return "new_session"

        else:
            # Modificar en lugar
            changes = self.manager.update_cuenca_in_place(
                self.session,
                area_ha=new_area,
                slope_pct=new_slope,
                p3_10=new_p3_10,
                c=new_c,
                cn=new_cn,
                length_m=new_length,
                clear_analyses=True,
            )

            if changes:
                typer.echo(f"\n  ✓ Sesion actualizada.")
                typer.echo(f"\n  Cambios aplicados:")
                for change in changes:
                    typer.echo(f"    - {change}")

                typer.echo(f"\n  Debes recalcular Tc y ejecutar nuevos analisis.")

                # Ofrecer recalcular Tc inmediatamente
                if questionary.confirm("Recalcular Tc ahora?", default=True, style=WIZARD_STYLE).ask():
                    from hidropluvial.cli.session.base import session_tc
                    methods = "desbordes"
                    if self.session.cuenca.length_m:
                        methods = "kirpich,desbordes"
                    session_tc(self.session.id, methods=methods)

                return "modified"

            return "cancelled"


class AddAnalysisMenu:
    """Menu para agregar analisis adicionales."""

    def __init__(self, session: Session, c: float = None, cn: float = None, length: float = None):
        self.session = session
        self.manager = get_session_manager()
        self.c = c
        self.cn = cn
        self.length = length

    def show(self) -> None:
        """Muestra menu de opciones para agregar analisis."""
        typer.echo("\n-- Agregar Analisis --\n")

        que_agregar = questionary.select(
            "Que tipo de analisis quieres agregar?",
            choices=[
                "Otra tormenta (Bloques, Bimodal, etc.)",
                "Otros periodos de retorno",
                "Otros valores de X",
                "Otro metodo de Tc",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if que_agregar is None:
            return

        tc_existentes = [tc.method for tc in self.session.tc_results]

        if "tormenta" in que_agregar.lower():
            self._add_storm(tc_existentes)
        elif "retorno" in que_agregar.lower():
            self._add_return_periods(tc_existentes)
        elif "X" in que_agregar:
            self._add_x_factors(tc_existentes)
        elif "Tc" in que_agregar:
            self._add_tc_method(tc_existentes)

    def _add_storm(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nueva tormenta."""
        storm_choices = [
            "GZ (6 horas)",
            "Bloques alternantes",
            "Bloques 24 horas",
            "Bimodal Uruguay",
        ]
        storm_type = questionary.select(
            "Tipo de tormenta:",
            choices=storm_choices,
            style=WIZARD_STYLE,
        ).ask()

        if storm_type is None:
            return

        storm_code = "gz"
        if "Bloques alternantes" in storm_type:
            storm_code = "blocks"
        elif "24 horas" in storm_type:
            storm_code = "blocks24"
        elif "Bimodal" in storm_type:
            storm_code = "bimodal"

        # Periodos de retorno
        tr_choices = [
            questionary.Choice("2", checked=True),
            questionary.Choice("10", checked=True),
            questionary.Choice("25", checked=False),
        ]
        return_periods = questionary.checkbox(
            "Periodos de retorno:",
            choices=tr_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not return_periods:
            return

        # Factor X solo para GZ
        x_factors = [1.0]
        if storm_code == "gz":
            x_choices = [
                questionary.Choice("1.00", checked=True),
                questionary.Choice("1.25", checked=True),
            ]
            x_selected = questionary.checkbox(
                "Valores de X:",
                choices=x_choices,
                style=WIZARD_STYLE,
            ).ask()
            if x_selected:
                x_factors = [float(x) for x in x_selected]

        runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
        runner.run(tc_existentes, storm_code, [int(tr) for tr in return_periods], x_factors)

    def _add_return_periods(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nuevos periodos de retorno."""
        tr_choices = [
            questionary.Choice("2", checked=False),
            questionary.Choice("5", checked=False),
            questionary.Choice("10", checked=False),
            questionary.Choice("25", checked=False),
            questionary.Choice("50", checked=True),
            questionary.Choice("100", checked=False),
        ]
        return_periods = questionary.checkbox(
            "Periodos de retorno adicionales:",
            choices=tr_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not return_periods:
            return

        runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
        runner.run(tc_existentes, "gz", [int(tr) for tr in return_periods], [1.0, 1.25])

    def _add_x_factors(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nuevos valores de X."""
        x_choices = [
            questionary.Choice("1.00", checked=False),
            questionary.Choice("1.25", checked=False),
            questionary.Choice("1.67", checked=True),
            questionary.Choice("2.25", checked=False),
            questionary.Choice("3.33", checked=False),
        ]
        x_selected = questionary.checkbox(
            "Valores de X adicionales:",
            choices=x_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not x_selected:
            return

        x_factors = [float(x) for x in x_selected]
        runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
        runner.run(tc_existentes, "gz", [2, 10, 25], x_factors)

    def _add_tc_method(self, tc_existentes: list[str]) -> None:
        """Agrega nuevo metodo de Tc y ejecuta analisis."""
        tc_choices = []
        if self.c and "desbordes" not in tc_existentes:
            tc_choices.append("Desbordes")
        if self.length and "kirpich" not in tc_existentes:
            tc_choices.append("Kirpich")
        if self.length and "temez" not in [tc.lower() for tc in tc_existentes]:
            tc_choices.append("Temez")

        if not tc_choices:
            typer.echo("  No hay metodos de Tc adicionales disponibles.")
            return

        new_tc = questionary.select(
            "Metodo de Tc:",
            choices=tc_choices,
            style=WIZARD_STYLE,
        ).ask()

        if new_tc is None:
            return

        # Calcular nuevo Tc
        tc_hr = None
        method = new_tc.lower()
        if method == "kirpich" and self.length:
            tc_hr = kirpich(self.length, self.session.cuenca.slope_pct / 100)
        elif method == "temez" and self.length:
            tc_hr = temez(self.length / 1000, self.session.cuenca.slope_pct / 100)
        elif method == "desbordes" and self.c:
            tc_hr = desbordes(self.session.cuenca.area_ha, self.session.cuenca.slope_pct, self.c)

        if tc_hr:
            result = self.manager.add_tc_result(self.session, method, tc_hr)
            typer.echo(f"  + Tc ({method}): {result.tc_min:.1f} min")

            # Ejecutar analisis con nuevo Tc
            runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
            runner.run([method], "gz", [2, 10, 25], [1.0, 1.25])


def continue_session_menu() -> None:
    """Menu para continuar con una sesion existente."""
    manager = get_session_manager()
    sessions = manager.list_sessions()

    if not sessions:
        typer.echo("\n  No hay sesiones guardadas.")
        typer.echo("  Usa 'hp wizard' y selecciona 'Nuevo analisis' para comenzar.\n")
        return

    choices = []
    for s in sessions:
        n_analyses = s["n_analyses"]
        choices.append(f"{s['id']} - {s['name']} ({n_analyses} analisis)")

    choice = questionary.select(
        "Selecciona una sesion:",
        choices=choices,
        style=WIZARD_STYLE,
    ).ask()

    if choice is None:
        return

    session_id = choice.split(" - ")[0]

    action = questionary.select(
        "Que deseas hacer?",
        choices=[
            "Ver resumen",
            "Agregar analisis",
            "Generar reporte",
            "Eliminar sesion",
        ],
        style=WIZARD_STYLE,
    ).ask()

    if action is None:
        return

    if "resumen" in action.lower():
        from hidropluvial.cli.session.base import session_summary
        session_summary(session_id)
    elif "Agregar" in action:
        # Cargar sesión y abrir menú post-ejecución para agregar análisis
        session = manager.get_session(session_id)
        if session:
            menu = PostExecutionMenu(session)
            menu.show()
    elif "reporte" in action.lower():
        output = questionary.text(
            "Nombre del archivo (sin extension):",
            style=WIZARD_STYLE,
        ).ask()
        if output:
            from hidropluvial.cli.session.report import session_report
            session_report(session_id, output, author=None, template_dir=None)
    elif "Eliminar" in action:
        confirmar = questionary.confirm(
            f"Seguro que deseas eliminar la sesion {session_id}?",
            default=False,
            style=WIZARD_STYLE,
        ).ask()
        if confirmar:
            from hidropluvial.cli.session.base import session_delete
            session_delete(session_id, force=True)


def idf_lookup_menu() -> None:
    """Menu para consultar tabla IDF."""
    typer.echo("\n  Estaciones IDF disponibles (Uruguay - DINAGUA):\n")
    typer.echo("  70 - Artigas          74 - Paysandu")
    typer.echo("  71 - Rivera           75 - Mercedes")
    typer.echo("  72 - Salto            76 - Colonia")
    typer.echo("  73 - Bella Union      77 - Rocha")
    typer.echo("  78 - Paso de los Toros")
    typer.echo("  79 - Treinta y Tres")
    typer.echo("  80 - Carrasco")
    typer.echo("  81 - Prado\n")

    estacion = questionary.text(
        "Numero de estacion:",
        validate=lambda x: x.isdigit() and 70 <= int(x) <= 81 or "Estacion no valida (70-81)",
        style=WIZARD_STYLE,
    ).ask()

    if estacion:
        from hidropluvial.cli.idf import idf_tabla_uy
        idf_tabla_uy(int(estacion))
