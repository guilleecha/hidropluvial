"""
Menu para agregar analisis adicionales.
"""

from typing import Optional

import questionary

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner
from hidropluvial.core import kirpich, desbordes, temez
from hidropluvial.session import Session


class AddAnalysisMenu(SessionMenu):
    """Menu para agregar analisis adicionales a una sesion."""

    def __init__(
        self,
        session: Session,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(session)
        self.c = c
        self.cn = cn
        self.length = length

    def show(self) -> None:
        """Muestra menu de opciones para agregar analisis."""
        self.echo("\n-- Agregar Analisis --\n")

        que_agregar = self.select(
            "Que tipo de analisis quieres agregar?",
            choices=[
                "Otra tormenta (Bloques, Bimodal, etc.)",
                "Otros periodos de retorno",
                "Otros valores de X",
                "Otro metodo de Tc",
            ],
        )

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
        storm_type = self.select(
            "Tipo de tormenta:",
            choices=[
                "GZ (6 horas)",
                "Bloques alternantes",
                "Bloques 24 horas",
                "Bimodal Uruguay",
            ],
        )

        if storm_type is None:
            return

        storm_code = self._get_storm_code(storm_type)

        # Periodos de retorno
        tr_choices = [
            questionary.Choice("2", checked=True),
            questionary.Choice("10", checked=True),
            questionary.Choice("25", checked=False),
        ]
        return_periods = self.checkbox("Periodos de retorno:", tr_choices)

        if not return_periods:
            return

        # Factor X solo para GZ
        x_factors = [1.0]
        if storm_code == "gz":
            x_factors = self._ask_x_factors()

        runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
        runner.run(tc_existentes, storm_code, [int(tr) for tr in return_periods], x_factors)

    def _get_storm_code(self, storm_type: str) -> str:
        """Convierte tipo de tormenta a codigo."""
        if "Bloques alternantes" in storm_type:
            return "blocks"
        elif "24 horas" in storm_type:
            return "blocks24"
        elif "Bimodal" in storm_type:
            return "bimodal"
        return "gz"

    def _ask_x_factors(self) -> list[float]:
        """Solicita valores de X para GZ."""
        x_choices = [
            questionary.Choice("1.00", checked=True),
            questionary.Choice("1.25", checked=True),
        ]
        x_selected = self.checkbox("Valores de X:", x_choices)
        if x_selected:
            return [float(x) for x in x_selected]
        return [1.0]

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
        return_periods = self.checkbox("Periodos de retorno adicionales:", tr_choices)

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
        x_selected = self.checkbox("Valores de X adicionales:", x_choices)

        if not x_selected:
            return

        x_factors = [float(x) for x in x_selected]
        runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
        runner.run(tc_existentes, "gz", [2, 10, 25], x_factors)

    def _add_tc_method(self, tc_existentes: list[str]) -> None:
        """Agrega nuevo metodo de Tc y ejecuta analisis."""
        tc_choices = self._get_available_tc_methods(tc_existentes)

        if not tc_choices:
            self.echo("  No hay metodos de Tc adicionales disponibles.")
            return

        new_tc = self.select("Metodo de Tc:", tc_choices)
        if new_tc is None:
            return

        method = new_tc.lower()
        tc_hr, tc_params = self._calculate_tc_with_params(method)
        if tc_hr:
            result = self.manager.add_tc_result(self.session, method, tc_hr, **tc_params)
            self.echo(f"  + Tc ({method}): {result.tc_min:.1f} min")

            # Ejecutar analisis con nuevo Tc
            runner = AdditionalAnalysisRunner(self.session, self.c, self.cn)
            runner.run([method], "gz", [2, 10, 25], [1.0, 1.25])

    def _get_available_tc_methods(self, tc_existentes: list[str]) -> list[str]:
        """Retorna metodos de Tc disponibles."""
        tc_choices = []
        if self.c and "desbordes" not in tc_existentes:
            tc_choices.append("Desbordes")
        if self.length and "kirpich" not in tc_existentes:
            tc_choices.append("Kirpich")
        if self.length and "temez" not in [tc.lower() for tc in tc_existentes]:
            tc_choices.append("Temez")
        return tc_choices

    def _calculate_tc_with_params(self, method: str) -> tuple[Optional[float], dict]:
        """Calcula Tc segun el metodo y retorna parametros usados."""
        if method == "kirpich" and self.length:
            tc_hr = kirpich(self.length, self.session.cuenca.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "temez" and self.length:
            tc_hr = temez(self.length / 1000, self.session.cuenca.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "desbordes" and self.c:
            tc_hr = desbordes(
                self.session.cuenca.area_ha,
                self.session.cuenca.slope_pct,
                self.c,
            )
            return tc_hr, {"c": self.c, "area_ha": self.session.cuenca.area_ha}
        return None, {}
