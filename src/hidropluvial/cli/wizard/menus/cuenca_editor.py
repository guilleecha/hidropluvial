"""
Editor de parametros de cuenca.
"""

from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE


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
        self.echo(f"\n{'='*65}")
        self.echo("  EDITAR DATOS DE LA CUENCA")
        self.echo(f"{'='*65}")
        self.echo(f"\n  Datos actuales:")
        self.echo(f"  {'-'*40}")
        self.echo(f"  Area:         {self.cuenca.area_ha:>12.2f} ha")
        self.echo(f"  Pendiente:    {self.cuenca.slope_pct:>12.2f} %")
        self.echo(f"  P3,10:        {self.cuenca.p3_10:>12.1f} mm")
        if self.cuenca.c:
            self.echo(f"  Coef. C:      {self.cuenca.c:>12.2f}")
        if self.cuenca.cn:
            self.echo(f"  CN:           {self.cuenca.cn:>12}")
        if self.cuenca.length_m:
            self.echo(f"  Longitud:     {self.cuenca.length_m:>12.0f} m")

    def _show_warnings(self) -> None:
        """Muestra advertencias si hay analisis existentes."""
        n_analyses = len(self.session.analyses)
        n_tc = len(self.session.tc_results)

        if n_analyses > 0 or n_tc > 0:
            self.echo(f"\n  ADVERTENCIA:")
            self.echo(f"      Esta sesion tiene {n_tc} calculos de Tc y {n_analyses} analisis.")
            self.echo(f"      Los cambios INVALIDARAN estos resultados.")

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
        """Recolecta valores de C y CN (solo si area no cambio)."""
        # Coef C
        c_default = self.cuenca.c if self.cuenca.c else "N/A"
        val = self._ask_float(f"Coef. C [{c_default}]:", self.cuenca.c or 0)
        if val is not None and val != 0:
            new_values["c"] = val

        # CN
        cn_str = questionary.text(
            f"CN [{self.cuenca.cn if self.cuenca.cn else 'N/A'}]:",
            default=str(self.cuenca.cn) if self.cuenca.cn else "",
            style=WIZARD_STYLE,
        ).ask()
        if cn_str and cn_str.strip() and cn_str != str(self.cuenca.cn):
            try:
                new_values["cn"] = int(cn_str)
            except ValueError:
                pass

    def _handle_area_change(self, new_values: dict) -> str:
        """
        Maneja el cambio de area - solicita recalcular o ingresar C/CN.

        Returns:
            "ok" si se configuro C/CN
            "cancelled" si se cancelo
        """
        new_area = new_values.get("area_ha", self.cuenca.area_ha)

        self.echo(f"\n{'='*60}")
        self.echo("  CONFIGURAR C y CN PARA NUEVA AREA")
        self.echo(f"{'='*60}")
        self.echo(f"  Area anterior: {self._original_area:.2f} ha")
        self.echo(f"  Area nueva:    {new_area:.2f} ha\n")

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
            C_TABLES, ChowCEntry, FHWACEntry, format_c_table, weighted_c
        )

        self.echo(f"\n  Calculando C ponderado para area de {new_area:.2f} ha")

        # Seleccionar tabla
        table_choice = questionary.select(
            "Selecciona tabla de coeficientes:",
            choices=[
                "Ven Te Chow (C según pendiente)",
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
        self.echo(format_c_table(table_data, table_name))

        # Seleccionar categoria de pendiente si es Chow
        slope_cat = None
        if table_key == "chow":
            slope_cat = questionary.select(
                "Categoria de pendiente:",
                choices=["flat", "rolling", "hilly"],
                style=WIZARD_STYLE,
            ).ask()

        areas = []
        coefficients = []
        area_remaining = new_area

        while area_remaining > 0.001:
            self.echo(f"\n  Area restante: {area_remaining:.3f} ha ({area_remaining/new_area*100:.1f}%)")

            choices = []
            for i, entry in enumerate(table_data):
                if isinstance(entry, ChowCEntry):
                    c_val = entry.get_c(slope_cat)
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
                c_val = entry.get_c(slope_cat)
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
        from hidropluvial.core.coefficients import CN_TABLES, format_cn_table, weighted_cn

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
