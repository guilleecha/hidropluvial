"""
Editor de parametros de cuenca.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.cli.theme import (
    print_header, print_section, print_info, print_warning,
    print_success, print_error, get_console, get_palette,
)
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box


class CuencaEditor:
    """Editor para modificar parametros de una cuenca."""

    def __init__(self, session, manager):
        self.session = session
        self.manager = manager
        self.cuenca = session.cuenca
        self._area_changed = False
        self._original_area = self.cuenca.area_ha

    def echo(self, message: str) -> None:
        """Wrapper para print."""
        typer.echo(message)

    def edit(self) -> str:
        """
        Permite editar los datos de la cuenca.

        Returns:
            "new_session" si se creo nueva sesion
            "modified" si se modifico la sesion actual
            "cancelled" si se cancelo
        """
        self._show_current_values()
        self._show_warnings()

        action = self._ask_action()
        if action == "cancelled":
            return "cancelled"

        new_values = self._collect_new_values()
        if not self._has_changes(new_values):
            self.echo("\n  No se especificaron cambios.")
            return "cancelled"

        # Si cambio el area, manejar C/CN
        if self._area_changed:
            c_cn_result = self._handle_area_change(new_values)
            if c_cn_result == "cancelled":
                return "cancelled"

        self._show_changes(new_values)
        if not self._confirm_changes():
            return "cancelled"

        if action == "clone":
            return self._create_clone(new_values)
        else:
            return self._modify_in_place(new_values)

    def _show_current_values(self) -> None:
        """Muestra los valores actuales de la cuenca."""
        console = get_console()
        p = get_palette()

        # Crear tabla con los valores actuales
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Label", style=p.label, width=12)
        table.add_column("Value")

        # Área
        area_text = Text()
        area_text.append(f"{self.cuenca.area_ha:.2f}", style=f"bold {p.number}")
        area_text.append(" ha", style=p.unit)
        table.add_row("Área", area_text)

        # Pendiente
        slope_text = Text()
        slope_text.append(f"{self.cuenca.slope_pct:.2f}", style=f"bold {p.number}")
        slope_text.append(" %", style=p.unit)
        table.add_row("Pendiente", slope_text)

        # P3,10
        p310_text = Text()
        p310_text.append(f"{self.cuenca.p3_10:.1f}", style=f"bold {p.number}")
        p310_text.append(" mm", style=p.unit)
        table.add_row("P3,10", p310_text)

        if self.cuenca.c:
            table.add_row("Coef. C", Text(f"{self.cuenca.c:.2f}", style=f"bold {p.number}"))

        if self.cuenca.cn:
            table.add_row("CN", Text(str(self.cuenca.cn), style=f"bold {p.number}"))

        if self.cuenca.length_m:
            len_text = Text()
            len_text.append(f"{self.cuenca.length_m:.0f}", style=f"bold {p.number}")
            len_text.append(" m", style=p.unit)
            table.add_row("Longitud", len_text)

        title = Text("Editar datos de la cuenca", style=f"bold {p.primary}")

        console.print()
        panel = Panel(
            table,
            title=title,
            title_align="left",
            border_style=p.primary,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print(panel)

    def _show_warnings(self) -> None:
        """Muestra advertencias si hay analisis existentes."""
        n_analyses = len(self.session.analyses)
        n_tc = len(self.session.tc_results)

        if n_analyses > 0 or n_tc > 0:
            print_warning(f"Esta sesión tiene {n_tc} cálculos de Tc y {n_analyses} análisis.")
            print_warning("Los cambios INVALIDARÁN estos resultados.")

    def _ask_action(self) -> str:
        """Pregunta que accion tomar."""
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
        return "clone" if "nueva" in action.lower() else "modify"

    def _collect_new_values(self) -> dict:
        """Recolecta los nuevos valores del usuario (sin C/CN si area cambia)."""
        self.echo("\n  Ingresa nuevos valores (Enter para mantener actual):\n")

        new_values = {}

        # Area
        val = self._ask_float(f"Area (ha) [{self.cuenca.area_ha:.2f}]:", self.cuenca.area_ha)
        if val is not None:
            new_values["area_ha"] = val
            self._area_changed = True
            self.echo(f"\n  [!] El area cambio de {self._original_area:.2f} a {val:.2f} ha")
            self.echo(f"      Los valores de C y CN dependen del area de coberturas.")
            self.echo(f"      Se solicitara recalcular o ingresar nuevos valores.\n")

        # Pendiente
        val = self._ask_float(f"Pendiente (%) [{self.cuenca.slope_pct:.2f}]:", self.cuenca.slope_pct)
        if val is not None:
            new_values["slope_pct"] = val

        # P3,10
        val = self._ask_float(f"P3,10 (mm) [{self.cuenca.p3_10:.1f}]:", self.cuenca.p3_10)
        if val is not None:
            new_values["p3_10"] = val

        # Longitud
        length_default = self.cuenca.length_m if self.cuenca.length_m else "N/A"
        val = self._ask_float(f"Longitud (m) [{length_default}]:", self.cuenca.length_m or 0)
        if val is not None and val != 0:
            new_values["length_m"] = val

        # Si NO cambio el area, permitir editar C/CN directamente
        if not self._area_changed:
            self._collect_c_cn_values(new_values)

        return new_values

    def _collect_c_cn_values(self, new_values: dict) -> None:
        """Recolecta valores de C y CN (area no cambio)."""
        area = self.cuenca.area_ha

        # Preguntar si quiere modificar C
        if self.cuenca.c:
            c_result = self._ask_coefficient_edit("C", self.cuenca.c, area)
            if c_result is not None:
                new_values["c"] = c_result
        else:
            # No tiene C, preguntar si quiere agregar
            add_c = questionary.confirm(
                "Agregar coeficiente C (Racional)?",
                default=False,
                style=WIZARD_STYLE,
            ).ask()
            if add_c:
                c_result = self._ask_new_coefficient("C", area)
                if c_result is not None:
                    new_values["c"] = c_result

        # Preguntar si quiere modificar CN
        if self.cuenca.cn:
            cn_result = self._ask_cn_edit(self.cuenca.cn, area)
            if cn_result is not None:
                new_values["cn"] = cn_result
        else:
            # No tiene CN, preguntar si quiere agregar
            add_cn = questionary.confirm(
                "Agregar CN (SCS)?",
                default=False,
                style=WIZARD_STYLE,
            ).ask()
            if add_cn:
                cn_result = self._ask_new_cn(area)
                if cn_result is not None:
                    new_values["cn"] = cn_result

    def _ask_coefficient_edit(self, coef_name: str, current: float, area: float) -> Optional[float]:
        """Pregunta como editar un coeficiente C existente."""
        choice = questionary.select(
            f"Coeficiente {coef_name} actual = {current:.2f}. Que deseas hacer?",
            choices=[
                f"Mantener {coef_name} = {current:.2f}",
                f"Recalcular {coef_name} usando tablas de coberturas",
                f"Ingresar nuevo valor de {coef_name} directamente",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Mantener" in choice:
            return None

        if "Recalcular" in choice:
            return self._recalculate_c(area)

        if "Ingresar" in choice:
            val = self._ask_float(f"Nuevo valor de {coef_name} (0.1-1.0):", current)
            return val

        return None

    def _ask_new_coefficient(self, coef_name: str, area: float) -> Optional[float]:
        """Pregunta como ingresar un nuevo coeficiente C."""
        choice = questionary.select(
            f"Como deseas configurar {coef_name}?",
            choices=[
                f"Calcular {coef_name} usando tablas de coberturas",
                f"Ingresar valor de {coef_name} directamente",
                "Cancelar",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Cancelar" in choice:
            return None

        if "Calcular" in choice:
            return self._recalculate_c(area)

        if "Ingresar" in choice:
            val = self._ask_float(f"Valor de {coef_name} (0.1-1.0):", 0.5)
            return val

        return None

    def _ask_cn_edit(self, current_cn: int, area: float) -> Optional[int]:
        """Pregunta como editar un CN existente."""
        choice = questionary.select(
            f"CN actual = {current_cn}. Que deseas hacer?",
            choices=[
                f"Mantener CN = {current_cn}",
                "Recalcular CN usando tablas de coberturas",
                "Ingresar nuevo valor de CN directamente",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Mantener" in choice:
            return None

        if "Recalcular" in choice:
            return self._recalculate_cn(area)

        if "Ingresar" in choice:
            cn_str = questionary.text(
                "Nuevo valor de CN (30-98):",
                default=str(current_cn),
                style=WIZARD_STYLE,
            ).ask()
            if cn_str:
                try:
                    return int(cn_str)
                except ValueError:
                    pass

        return None

    def _ask_new_cn(self, area: float) -> Optional[int]:
        """Pregunta como ingresar un nuevo CN."""
        choice = questionary.select(
            "Como deseas configurar CN?",
            choices=[
                "Calcular CN usando tablas de coberturas",
                "Ingresar valor de CN directamente",
                "Cancelar",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Cancelar" in choice:
            return None

        if "Calcular" in choice:
            return self._recalculate_cn(area)

        if "Ingresar" in choice:
            cn_str = questionary.text(
                "Valor de CN (30-98):",
                default="75",
                style=WIZARD_STYLE,
            ).ask()
            if cn_str:
                try:
                    return int(cn_str)
                except ValueError:
                    pass

        return None

    def _handle_area_change(self, new_values: dict) -> str:
        """
        Maneja el cambio de area - solicita recalcular o ingresar C/CN.

        Returns:
            "ok" si se configuro C/CN
            "cancelled" si se cancelo
        """
        new_area = new_values.get("area_ha", self.cuenca.area_ha)

        console = get_console()
        p = get_palette()

        # Crear tabla con los valores
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Label", style=p.label, width=14)
        table.add_column("Value")

        area_ant = Text()
        area_ant.append(f"{self._original_area:.2f}", style=p.muted)
        area_ant.append(" ha", style=p.unit)
        table.add_row("Área anterior", area_ant)

        area_new = Text()
        area_new.append(f"{new_area:.2f}", style=f"bold {p.number}")
        area_new.append(" ha", style=p.unit)
        table.add_row("Área nueva", area_new)

        title = Text("Configurar C y CN para nueva área", style=f"bold {p.secondary}")

        console.print()
        panel = Panel(
            table,
            title=title,
            title_align="left",
            border_style=p.secondary,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print(panel)

        # Preguntar que hacer con C (si existia)
        if self.cuenca.c:
            c_result = self._handle_coefficient_change("C", self.cuenca.c, new_area)
            if c_result == "cancelled":
                return "cancelled"
            if c_result is not None:
                new_values["c"] = c_result

        # Preguntar que hacer con CN (si existia)
        if self.cuenca.cn:
            cn_result = self._handle_cn_change(self.cuenca.cn, new_area)
            if cn_result == "cancelled":
                return "cancelled"
            if cn_result is not None:
                new_values["cn"] = cn_result

        return "ok"

    def _handle_coefficient_change(self, coef_name: str, current_value: float, new_area: float) -> Optional[float]:
        """
        Maneja el cambio de un coeficiente (C) cuando cambia el area.

        Returns:
            Nuevo valor, None para mantener, o "cancelled"
        """
        self.echo(f"\n  Coeficiente {coef_name} actual: {current_value:.2f}")
        self.echo(f"  Este valor fue calculado para un area de {self._original_area:.2f} ha")

        choice = questionary.select(
            f"Como deseas configurar {coef_name} para la nueva area?",
            choices=[
                f"Mantener {coef_name} = {current_value:.2f} (asume coberturas similares)",
                f"Recalcular {coef_name} usando tablas de coberturas",
                f"Ingresar nuevo valor de {coef_name} directamente",
                "Cancelar edicion",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Cancelar" in choice:
            return "cancelled"

        if "Mantener" in choice:
            return None  # No cambiar

        if "Recalcular" in choice:
            return self._recalculate_c(new_area)

        if "Ingresar" in choice:
            val = self._ask_float(f"Nuevo valor de {coef_name} (0.1-1.0):", current_value)
            return val if val else current_value

        return None

    def _handle_cn_change(self, current_cn: int, new_area: float) -> Optional[int]:
        """
        Maneja el cambio de CN cuando cambia el area.

        Returns:
            Nuevo valor, None para mantener, o "cancelled"
        """
        self.echo(f"\n  CN actual: {current_cn}")
        self.echo(f"  Este valor fue calculado para un area de {self._original_area:.2f} ha")

        choice = questionary.select(
            "Como deseas configurar CN para la nueva area?",
            choices=[
                f"Mantener CN = {current_cn} (asume coberturas similares)",
                "Recalcular CN usando tablas de coberturas",
                "Ingresar nuevo valor de CN directamente",
                "Cancelar edicion",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if choice is None or "Cancelar" in choice:
            return "cancelled"

        if "Mantener" in choice:
            return None  # No cambiar

        if "Recalcular" in choice:
            return self._recalculate_cn(new_area)

        if "Ingresar" in choice:
            cn_str = questionary.text(
                "Nuevo valor de CN (30-98):",
                default=str(current_cn),
                style=WIZARD_STYLE,
            ).ask()
            if cn_str:
                try:
                    return int(cn_str)
                except ValueError:
                    return current_cn
            return current_cn

        return None

    def _recalculate_c(self, new_area: float) -> Optional[float]:
        """Recalcula C usando tablas de coberturas."""
        from hidropluvial.core.coefficients import (
            C_TABLES, ChowCEntry, FHWACEntry, weighted_c
        )
        from hidropluvial.cli.theme import (
            print_c_table_chow, print_c_table_fhwa, print_c_table_simple
        )

        print_info(f"Calculando C ponderado para área de {new_area:.2f} ha")

        # Seleccionar tabla
        table_choice = questionary.select(
            "Selecciona tabla de coeficientes:",
            choices=[
                "Ven Te Chow (C según cobertura y Tr)",
                "FHWA (C único por uso)",
                "Tabla Uruguay",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if table_choice is None:
            return None

        if "Chow" in table_choice:
            table_key = "chow"
        elif "FHWA" in table_choice:
            table_key = "fhwa"
        else:
            table_key = "uruguay"

        table_name, table_data = C_TABLES[table_key]
        first_entry = table_data[0]

        # Mostrar tabla estilizada según tipo
        if isinstance(first_entry, ChowCEntry):
            print_c_table_chow(table_data, table_name, selection_mode=True)
        elif isinstance(first_entry, FHWACEntry):
            print_c_table_fhwa(table_data, table_name, tr=10)
        else:
            print_c_table_simple(table_data, table_name)

        # Para tabla Chow siempre se usa Tr=2 como base
        is_chow = table_key == "chow"

        areas = []
        coefficients = []
        area_remaining = new_area

        while area_remaining > 0.001:
            self.echo(f"\n  Area restante: {area_remaining:.3f} ha ({area_remaining/new_area*100:.1f}%)")

            choices = []
            for i, entry in enumerate(table_data):
                if isinstance(entry, ChowCEntry):
                    c_val = entry.c_tr2  # Siempre Tr=2 para Chow
                elif isinstance(entry, FHWACEntry):
                    c_val = entry.c
                else:
                    c_val = entry.c
                choices.append(f"{i+1}. {entry.description} (C={c_val:.2f})")

            choices.append("Terminar (asignar resto a ultima cobertura)")
            choices.append("Cancelar")

            selection = questionary.select("Selecciona cobertura:", choices, style=WIZARD_STYLE).ask()

            if selection is None or "Cancelar" in selection:
                return None

            if "Terminar" in selection:
                if areas:
                    # Asignar resto a ultima cobertura
                    areas[-1] += area_remaining
                break

            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]

            if isinstance(entry, ChowCEntry):
                c_val = entry.c_tr2  # Siempre Tr=2 para Chow
            elif isinstance(entry, FHWACEntry):
                c_val = entry.c
            else:
                c_val = entry.c

            area_str = questionary.text(
                f"Area para '{entry.description}' (ha, max {area_remaining:.2f}):",
                default=f"{area_remaining:.2f}",
                style=WIZARD_STYLE,
            ).ask()

            if area_str:
                try:
                    area_val = float(area_str)
                    area_val = min(area_val, area_remaining)
                    areas.append(area_val)
                    coefficients.append(c_val)
                    area_remaining -= area_val
                except ValueError:
                    pass

        if not areas:
            return None

        c_weighted = weighted_c(areas, coefficients)
        self.echo(f"\n  C ponderado calculado: {c_weighted:.2f}")
        return round(c_weighted, 2)

    def _recalculate_cn(self, new_area: float) -> Optional[int]:
        """Recalcula CN usando tablas de coberturas."""
        from hidropluvial.core.coefficients import CN_TABLES, weighted_cn

        self.echo(f"\n  Calculando CN ponderado para area de {new_area:.2f} ha")

        # Seleccionar grupo de suelo
        soil_choice = questionary.select(
            "Grupo hidrologico de suelo:",
            choices=[
                "A - Alta infiltracion (arena, grava)",
                "B - Moderada infiltracion (limo arenoso)",
                "C - Baja infiltracion (limo arcilloso)",
                "D - Muy baja infiltracion (arcilla)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if soil_choice is None:
            return None

        soil_group = soil_choice[0]

        areas = []
        cn_values = []
        area_remaining = new_area

        while area_remaining > 0.001:
            self.echo(f"\n  Area restante: {area_remaining:.3f} ha ({area_remaining/new_area*100:.1f}%)")

            # Seleccionar tabla
            table_choice = questionary.select(
                "Agregar cobertura de:",
                choices=[
                    "Tabla Urbana (residencial, comercial, industrial)",
                    "Tabla Agricola (cultivos, pasturas, bosque)",
                    "Terminar (asignar resto a ultima cobertura)",
                    "Cancelar",
                ],
                style=WIZARD_STYLE,
            ).ask()

            if table_choice is None or "Cancelar" in table_choice:
                return None

            if "Terminar" in table_choice:
                if areas:
                    areas[-1] += area_remaining
                break

            table_key = "urban" if "Urbana" in table_choice else "agricultural"
            table_name, table_data = CN_TABLES[table_key]

            choices = []
            for i, entry in enumerate(table_data):
                cn = entry.get_cn(soil_group)
                cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
                choices.append(f"{i+1}. {entry.category} - {entry.description}{cond} (CN={cn})")

            choices.append("Volver")

            selection = questionary.select("Selecciona cobertura:", choices, style=WIZARD_STYLE).ask()

            if selection is None or "Volver" in selection:
                continue

            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]
            cn = entry.get_cn(soil_group)

            area_str = questionary.text(
                f"Area para esta cobertura (ha, max {area_remaining:.2f}):",
                default=f"{area_remaining:.2f}",
                style=WIZARD_STYLE,
            ).ask()

            if area_str:
                try:
                    area_val = float(area_str)
                    area_val = min(area_val, area_remaining)
                    areas.append(area_val)
                    cn_values.append(cn)
                    area_remaining -= area_val
                except ValueError:
                    pass

        if not areas:
            return None

        cn_weighted = weighted_cn(areas, cn_values)
        self.echo(f"\n  CN ponderado calculado: {cn_weighted}")
        return cn_weighted

    def _ask_float(self, prompt: str, current: Optional[float]) -> Optional[float]:
        """Solicita un valor float."""
        default_str = f"{current:.2f}" if current else ""
        val = questionary.text(prompt, default=default_str, style=WIZARD_STYLE).ask()
        if val is None:
            return None
        val = val.strip()
        if val == "" or val == default_str:
            return None
        try:
            return float(val)
        except ValueError:
            self.echo(f"  Valor invalido, se mantiene {current}")
            return None

    def _has_changes(self, new_values: dict) -> bool:
        """Verifica si hay cambios."""
        return len(new_values) > 0

    def _show_changes(self, new_values: dict) -> None:
        """Muestra los cambios a aplicar."""
        self.echo(f"\n  Cambios a aplicar:")
        if "area_ha" in new_values:
            self.echo(f"    Area: {self.cuenca.area_ha} -> {new_values['area_ha']} ha")
        if "slope_pct" in new_values:
            self.echo(f"    Pendiente: {self.cuenca.slope_pct} -> {new_values['slope_pct']}%")
        if "p3_10" in new_values:
            self.echo(f"    P3,10: {self.cuenca.p3_10} -> {new_values['p3_10']} mm")
        if "c" in new_values:
            self.echo(f"    C: {self.cuenca.c} -> {new_values['c']}")
        if "cn" in new_values:
            self.echo(f"    CN: {self.cuenca.cn} -> {new_values['cn']}")
        if "length_m" in new_values:
            self.echo(f"    Longitud: {self.cuenca.length_m} -> {new_values['length_m']} m")

    def _confirm_changes(self) -> bool:
        """Confirma los cambios."""
        return questionary.confirm(
            "\nAplicar cambios?",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

    def _create_clone(self, new_values: dict) -> str:
        """Crea una nueva sesion con los valores modificados."""
        new_name = questionary.text(
            "Nombre para la nueva sesion:",
            default=f"{self.session.name} (modificado)",
            style=WIZARD_STYLE,
        ).ask()

        new_session, changes = self.manager.clone_with_modified_cuenca(
            self.session,
            new_name=new_name,
            **new_values,
        )

        self.echo(f"\n  Nueva sesion creada: {new_session.id}")
        self.echo(f"    Nombre: {new_session.name}")
        self.echo(f"\n  Sesion original '{self.session.id}' sin modificar.")
        self.echo(f"\n  Usa 'hp session tc {new_session.id}' para calcular Tc")
        self.echo(f"  Usa 'hp wizard' para continuar con la nueva sesion\n")
        return "new_session"

    def _modify_in_place(self, new_values: dict) -> str:
        """Modifica la sesion actual."""
        changes = self.manager.update_cuenca_in_place(
            self.session,
            **new_values,
            clear_analyses=True,
        )

        if changes:
            self.echo(f"\n  Sesion actualizada.")
            self.echo(f"\n  Cambios aplicados:")
            for change in changes:
                self.echo(f"    - {change}")

            self.echo(f"\n  Debes recalcular Tc y ejecutar nuevos analisis.")

            # Ofrecer recalcular Tc inmediatamente
            if questionary.confirm(
                "Recalcular Tc ahora?",
                default=True,
                style=WIZARD_STYLE,
            ).ask():
                from hidropluvial.cli.session.base import session_tc
                methods = "desbordes"
                if self.session.cuenca.length_m:
                    methods = "kirpich,desbordes"
                session_tc(self.session.id, methods=methods)

            return "modified"

        return "cancelled"
