"""
Menú para agregar analisis adicionales.

Permite seleccionar exactamente qué análisis agregar, similar al wizard inicial,
detectando y descartando duplicados de análisis ya existentes.
"""

from typing import Optional, Set, Tuple

import questionary

from hidropluvial.cli.wizard.menus.base import SessionMenu
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner
from hidropluvial.core import kirpich, desbordes, temez


def _get_analysis_key(analysis) -> Tuple[str, str, int, float]:
    """
    Genera una clave única para identificar un análisis.

    Returns:
        Tupla (tc_method, storm_type, return_period, x_factor)
    """
    tc_method = analysis.hydrograph.tc_method.lower()
    storm_type = analysis.storm.type.lower()
    return_period = analysis.storm.return_period
    x_factor = analysis.hydrograph.x_factor or 1.0
    return (tc_method, storm_type, return_period, x_factor)


class AddAnalysisMenu(SessionMenu):
    """Menú para agregar analisis adicionales a una cuenca."""

    def __init__(
        self,
        basin,
        c: Optional[float] = None,
        cn: Optional[int] = None,
        length: Optional[float] = None,
    ):
        super().__init__(basin)
        self.c = c
        self.cn = cn
        self.length = length
        # Obtener claves de análisis existentes para detectar duplicados
        self._existing_keys: Set[Tuple[str, str, int, float]] = set()
        for a in basin.analyses:
            self._existing_keys.add(_get_analysis_key(a))

    def show(self) -> None:
        """Muestra menú de opciones para agregar análisis."""
        while True:
            self.echo("\n-- Agregar Analisis --\n")
            self.echo(f"  Cuenca: {self.basin.name} ({len(self.basin.analyses)} análisis)\n")

            que_agregar = self.select(
                "¿Cómo quieres agregar análisis?",
                choices=[
                    "Selección individual (elegir Tc, tormenta, Tr, X)",
                    "Agregar rápido por categoría",
                    "← Volver",
                ],
            )

            if que_agregar is None or "Volver" in que_agregar:
                return

            if "individual" in que_agregar.lower():
                self._add_individual()
            elif "rápido" in que_agregar.lower():
                self._add_quick_menu()

            # Recargar sesion para mostrar contador actualizado
            self.reload_session()

    def _add_individual(self) -> None:
        """Wizard de selección individual para agregar análisis específicos."""
        self.echo("\n  === Selección Individual ===\n")

        # 1. Seleccionar métodos Tc (múltiple)
        tc_existentes = [tc.method for tc in self.basin.tc_results]
        if not tc_existentes:
            self.warning("No hay métodos de Tc calculados en esta cuenca")
            return

        tc_choices = [
            questionary.Choice(tc, checked=(i == 0))
            for i, tc in enumerate(tc_existentes)
        ]
        tc_methods = self.checkbox("Métodos de Tc:", tc_choices)
        if not tc_methods:
            return

        # 2. Seleccionar tipos de tormenta (múltiple)
        storm_choices = [
            questionary.Choice("GZ (6 horas) - DINAGUA Uruguay", checked=True),
            questionary.Choice("Bloques alternantes (duración = 2×Tc)", checked=False),
            questionary.Choice("Bloques 24 horas", checked=False),
            questionary.Choice("Bimodal Uruguay", checked=False),
        ]
        storm_types = self.checkbox("Tipos de tormenta:", storm_choices)
        if not storm_types:
            return
        storm_codes = [self._get_storm_code(st) for st in storm_types]

        # 3. Seleccionar período de retorno
        tr_choices = [
            questionary.Choice("2 años", checked=False),
            questionary.Choice("5 años", checked=False),
            questionary.Choice("10 años", checked=True),
            questionary.Choice("25 años", checked=False),
            questionary.Choice("50 años", checked=False),
            questionary.Choice("100 años", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno:", tr_choices)
        if not return_periods:
            return
        tr_list = [int(tr.split()[0]) for tr in return_periods]

        # 4. Seleccionar factor X (solo si hay GZ entre las tormentas)
        x_factors = [1.0]
        if "gz" in storm_codes:
            x_choices = [
                questionary.Choice("X=1.00 - Racional/urbano interno", checked=True),
                questionary.Choice("X=1.25 - Urbano (gran pendiente)", checked=False),
                questionary.Choice("X=1.67 - NRCS estándar", checked=False),
                questionary.Choice("X=2.25 - Mixto rural/urbano", checked=False),
                questionary.Choice("X=3.33 - Rural sinuoso", checked=False),
            ]
            x_selected = self.checkbox("Factor X (forma del hidrograma):", x_choices)
            if x_selected:
                x_factors = [float(x.split("=")[1].split()[0]) for x in x_selected]

        # Calcular cuántos análisis nuevos se agregarán (descartando duplicados)
        new_analyses = []
        duplicates = []
        for tc_method in tc_methods:
            for storm_code in storm_codes:
                for tr in tr_list:
                    # Factor X solo aplica a GZ, para otras tormentas usar 1.0
                    x_list = x_factors if storm_code == "gz" else [1.0]
                    for x in x_list:
                        key = (tc_method.lower(), storm_code, tr, x)
                        if key in self._existing_keys:
                            duplicates.append(f"Tc={tc_method}, {storm_code}, Tr={tr}, X={x:.2f}")
                        else:
                            new_analyses.append((tc_method, storm_code, tr, x))

        if duplicates:
            self.echo(f"\n  Se descartarán {len(duplicates)} análisis duplicados:")
            for dup in duplicates[:5]:  # Mostrar máximo 5
                self.echo(f"    - {dup}")
            if len(duplicates) > 5:
                self.echo(f"    ... y {len(duplicates) - 5} más")

        if not new_analyses:
            self.warning("Todos los análisis seleccionados ya existen")
            return

        # Confirmar
        self.echo(f"\n  Se agregarán {len(new_analyses)} análisis nuevos:")
        for tc, storm, tr, x in new_analyses[:5]:
            x_str = f", X={x:.2f}" if x != 1.0 else ""
            self.echo(f"    + Tc={tc}, {storm}, Tr={tr}{x_str}")
        if len(new_analyses) > 5:
            self.echo(f"    ... y {len(new_analyses) - 5} más")

        if not self.confirm(f"\n¿Ejecutar {len(new_analyses)} análisis?", default=True):
            return

        # Ejecutar análisis por cada tipo de tormenta
        runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
        total_count = 0

        for storm_code in storm_codes:
            # Filtrar análisis para esta tormenta
            storm_analyses = [(tc, tr, x) for tc, st, tr, x in new_analyses if st == storm_code]
            if not storm_analyses:
                continue

            # Obtener Tc, Tr y X únicos para esta tormenta
            unique_tcs = sorted(set(tc for tc, _, _ in storm_analyses))
            unique_trs = sorted(set(tr for _, tr, _ in storm_analyses))
            unique_xs = sorted(set(x for _, _, x in storm_analyses))

            count = runner.run(unique_tcs, storm_code, unique_trs, unique_xs)
            total_count += count

        self.success(f"Se agregaron {total_count} análisis")

    def _add_quick_menu(self) -> None:
        """Menú rápido por categoría (comportamiento original simplificado)."""
        while True:
            self.echo("\n  === Agregar Rápido ===\n")

            que_agregar = self.select(
                "¿Qué tipo de análisis quieres agregar?",
                choices=[
                    "Otra tormenta (Bloques, Bimodal, etc.)",
                    "Otros períodos de retorno",
                    "Otros valores de X",
                    "Otro método de Tc",
                    "← Volver",
                ],
            )

            if que_agregar is None or "Volver" in que_agregar:
                return

            tc_existentes = [tc.method for tc in self.basin.tc_results]

            if "tormenta" in que_agregar.lower():
                self._add_storm(tc_existentes)
            elif "retorno" in que_agregar.lower():
                self._add_return_periods(tc_existentes)
            elif "X" in que_agregar:
                self._add_x_factors(tc_existentes)
            elif "Tc" in que_agregar:
                self._add_tc_method(tc_existentes)

            # Actualizar claves existentes
            self._existing_keys.clear()
            for a in self.basin.analyses:
                self._existing_keys.add(_get_analysis_key(a))

    def _add_storm(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nueva tormenta."""
        storm_type = self.select(
            "Tipo de tormenta:",
            choices=[
                "GZ (6 horas)",
                "Bloques alternantes",
                "Bloques 24 horas",
                "Bimodal Uruguay",
                "← Cancelar",
            ],
        )

        if storm_type is None or "Cancelar" in storm_type:
            return

        storm_code = self._get_storm_code(storm_type)

        # Períodos de retorno
        tr_choices = [
            questionary.Choice("2", checked=True),
            questionary.Choice("10", checked=True),
            questionary.Choice("25", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno:", tr_choices)

        if not return_periods:
            return

        # Factor X solo para GZ
        x_factors = [1.0]
        if storm_code == "gz":
            x_factors = self._ask_x_factors()

        # Mostrar preview y confirmar
        n_new = self._preview_and_confirm(
            tc_existentes, storm_code,
            [int(tr) for tr in return_periods],
            x_factors
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, storm_code, [int(tr) for tr in return_periods], x_factors)
            self.success(f"Se agregaron {count} análisis")

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

    def _preview_and_confirm(
        self,
        tc_methods: list[str],
        storm_code: str,
        return_periods: list[int],
        x_factors: list[float]
    ) -> int:
        """
        Muestra preview de análisis a agregar y confirma.

        Returns:
            Número de análisis nuevos (0 si cancela o todos son duplicados)
        """
        new_analyses = []
        duplicates = []

        for tc in tc_methods:
            for tr in return_periods:
                for x in x_factors:
                    key = (tc.lower(), storm_code, tr, x)
                    if key in self._existing_keys:
                        duplicates.append(key)
                    else:
                        new_analyses.append(key)

        if duplicates:
            self.echo(f"\n  Se descartarán {len(duplicates)} análisis duplicados")

        if not new_analyses:
            self.warning("Todos los análisis seleccionados ya existen")
            return 0

        self.echo(f"\n  Se agregarán {len(new_analyses)} análisis nuevos")

        if not self.confirm(f"¿Continuar?", default=True):
            return 0

        return len(new_analyses)

    def _add_return_periods(self, tc_existentes: list[str]) -> None:
        """Agrega analisis con nuevos períodos de retorno."""
        tr_choices = [
            questionary.Choice("2", checked=False),
            questionary.Choice("5", checked=False),
            questionary.Choice("10", checked=False),
            questionary.Choice("25", checked=False),
            questionary.Choice("50", checked=True),
            questionary.Choice("100", checked=False),
        ]
        return_periods = self.checkbox("Períodos de retorno adicionales:", tr_choices)

        if not return_periods:
            return

        # Usar GZ por defecto y X=[1.0, 1.25]
        n_new = self._preview_and_confirm(
            tc_existentes, "gz",
            [int(tr) for tr in return_periods],
            [1.0, 1.25]
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, "gz", [int(tr) for tr in return_periods], [1.0, 1.25])
            self.success(f"Se agregaron {count} análisis")

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

        # Usar Tr existentes o defaults
        existing_trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
        if not existing_trs:
            existing_trs = [2, 10, 25]

        n_new = self._preview_and_confirm(
            tc_existentes, "gz",
            existing_trs,
            x_factors
        )

        if n_new > 0:
            runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
            count = runner.run(tc_existentes, "gz", existing_trs, x_factors)
            self.success(f"Se agregaron {count} análisis")

    def _add_tc_method(self, tc_existentes: list[str]) -> None:
        """Agrega nuevo método de Tc y ejecuta análisis."""
        tc_choices = self._get_available_tc_methods(tc_existentes)

        if not tc_choices:
            self.echo("  No hay métodos de Tc adicionales disponibles.")
            return

        new_tc = self.select("Método de Tc:", tc_choices + ["← Cancelar"])
        if new_tc is None or "Cancelar" in new_tc:
            return

        method = new_tc.lower()
        tc_hr, tc_params = self._calculate_tc_with_params(method)
        if tc_hr:
            result = self.manager.add_tc_result(self.basin, method, tc_hr, **tc_params)
            self.success(f"Tc ({method}): {result.tc_min:.1f} min")

            # Usar Tr y X existentes o defaults
            existing_trs = sorted(set(a.storm.return_period for a in self.basin.analyses))
            if not existing_trs:
                existing_trs = [2, 10, 25]

            n_new = self._preview_and_confirm(
                [method], "gz",
                existing_trs,
                [1.0, 1.25]
            )

            if n_new > 0:
                runner = AdditionalAnalysisRunner(self.basin, self.c, self.cn)
                count = runner.run([method], "gz", existing_trs, [1.0, 1.25])
                self.success(f"Se agregaron {count} análisis")

    def _get_available_tc_methods(self, tc_existentes: list[str]) -> list[str]:
        """Retorna métodos de Tc disponibles."""
        tc_choices = []
        tc_lower = [tc.lower() for tc in tc_existentes]
        if self.c and "desbordes" not in tc_lower:
            tc_choices.append("Desbordes")
        if self.length and "kirpich" not in tc_lower:
            tc_choices.append("Kirpich")
        if self.length and "temez" not in tc_lower:
            tc_choices.append("Temez")
        return tc_choices

    def _calculate_tc_with_params(self, method: str) -> tuple[Optional[float], dict]:
        """Calcula Tc segun el método y retorna parametros usados."""
        if method == "kirpich" and self.length:
            tc_hr = kirpich(self.length, self.basin.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "temez" and self.length:
            tc_hr = temez(self.length / 1000, self.basin.slope_pct / 100)
            return tc_hr, {"length_m": self.length}
        elif method == "desbordes" and self.c:
            tc_hr = desbordes(
                self.basin.area_ha,
                self.basin.slope_pct,
                self.c,
            )
            return tc_hr, {"c": self.c, "area_ha": self.basin.area_ha}
        return None, {}
