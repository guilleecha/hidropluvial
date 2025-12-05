"""
Editor de parametros de cuenca.
"""

from typing import Optional

import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.session import Session, SessionManager


class CuencaEditor:
    """Editor para modificar parametros de una cuenca."""

    def __init__(self, session: Session, manager: SessionManager):
        self.session = session
        self.manager = manager
        self.cuenca = session.cuenca

    def echo(self, message: str) -> None:
        """Wrapper para print."""
        import typer
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
        """Recolecta los nuevos valores del usuario."""
        self.echo("\n  Ingresa nuevos valores (Enter para mantener actual):\n")

        new_values = {}

        # Area
        val = self._ask_float(f"Area (ha) [{self.cuenca.area_ha:.2f}]:", self.cuenca.area_ha)
        if val is not None:
            new_values["area_ha"] = val

        # Pendiente
        val = self._ask_float(f"Pendiente (%) [{self.cuenca.slope_pct:.2f}]:", self.cuenca.slope_pct)
        if val is not None:
            new_values["slope_pct"] = val

        # P3,10
        val = self._ask_float(f"P3,10 (mm) [{self.cuenca.p3_10:.1f}]:", self.cuenca.p3_10)
        if val is not None:
            new_values["p3_10"] = val

        # Coef C
        c_default = self.cuenca.c if self.cuenca.c else "N/A"
        val = self._ask_float(f"Coef. C [{c_default}]:", self.cuenca.c or 0)
        if val is not None and val != 0:
            new_values["c"] = val

        # CN
        cn_default = str(self.cuenca.cn) if self.cuenca.cn else ""
        cn_str = questionary.text(
            f"CN [{self.cuenca.cn if self.cuenca.cn else 'N/A'}]:",
            default=cn_default,
            style=WIZARD_STYLE,
        ).ask()
        if cn_str and cn_str.strip() and cn_str != str(self.cuenca.cn):
            try:
                new_values["cn"] = int(cn_str)
            except ValueError:
                pass

        # Longitud
        length_default = self.cuenca.length_m if self.cuenca.length_m else "N/A"
        val = self._ask_float(f"Longitud (m) [{length_default}]:", self.cuenca.length_m or 0)
        if val is not None and val != 0:
            new_values["length_m"] = val

        return new_values

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
