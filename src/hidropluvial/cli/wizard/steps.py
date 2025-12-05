"""
Sistema de pasos del wizard con navegación hacia atrás.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import (
    WIZARD_STYLE,
    validate_positive_float,
    validate_range,
)


class StepResult(Enum):
    """Resultado de un paso del wizard."""
    NEXT = "next"       # Continuar al siguiente paso
    BACK = "back"       # Volver al paso anterior
    CANCEL = "cancel"   # Cancelar wizard


@dataclass
class WizardState:
    """Estado compartido del wizard."""
    # Datos de cuenca
    nombre: str = ""
    area_ha: float = 0.0
    slope_pct: float = 0.0
    p3_10: float = 0.0
    c: Optional[float] = None
    cn: Optional[int] = None
    length_m: Optional[float] = None

    # Datos de ponderación
    c_weighted_data: Optional[dict] = None

    # Parámetros avanzados
    amc: str = "II"  # Condición de humedad antecedente: I, II, III
    lambda_coef: float = 0.2  # Coeficiente lambda para abstracción inicial
    t0_min: float = 5.0  # Tiempo de entrada inicial para Desbordes

    # Parámetros de análisis
    tc_methods: list[str] = field(default_factory=list)
    storm_codes: list[str] = field(default_factory=lambda: ["gz"])
    return_periods: list[int] = field(default_factory=list)
    x_factors: list[float] = field(default_factory=lambda: [1.0])

    # Salida
    output_name: Optional[str] = None


class WizardStep(ABC):
    """Paso base del wizard."""

    def __init__(self, state: WizardState):
        self.state = state

    @property
    @abstractmethod
    def title(self) -> str:
        """Título del paso."""
        pass

    @abstractmethod
    def execute(self) -> StepResult:
        """Ejecuta el paso y retorna el resultado."""
        pass

    def echo(self, msg: str) -> None:
        """Imprime mensaje."""
        typer.echo(msg)

    def select(self, message: str, choices: list[str], back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """
        Muestra selector con opción de volver atrás.

        Returns:
            Tupla (resultado, valor_seleccionado)
        """
        if back_option:
            choices = choices + ["<< Volver atrás"]

        result = questionary.select(
            message,
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if result == "<< Volver atrás":
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def checkbox(self, message: str, choices: list, back_option: bool = True) -> tuple[StepResult, Optional[list]]:
        """Muestra checkbox con instrucciones para volver."""
        if back_option:
            self.echo("  (Presiona Esc o deja vacío y Enter para volver atrás)\n")

        result = questionary.checkbox(
            message,
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if not result and back_option:
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def text(self, message: str, validate=None, default: str = "", back_option: bool = True) -> tuple[StepResult, Optional[str]]:
        """Muestra input de texto con opción de volver."""
        if back_option:
            hint = " (dejar vacío para volver)"
            full_message = message
        else:
            hint = ""
            full_message = message

        result = questionary.text(
            full_message,
            validate=validate if not back_option else lambda x: True if x == "" else (validate(x) if validate else True),
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, None
        if result == "" and back_option and default == "":
            return StepResult.BACK, None
        return StepResult.NEXT, result

    def confirm(self, message: str, default: bool = True) -> tuple[StepResult, bool]:
        """Muestra confirmación."""
        result = questionary.confirm(
            message,
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL, False
        return StepResult.NEXT, result


class StepNombre(WizardStep):
    """Paso: Nombre de la cuenca."""

    @property
    def title(self) -> str:
        return "Nombre de la Cuenca"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        result = questionary.text(
            "Nombre de la cuenca:",
            validate=lambda x: len(x) > 0 or "El nombre no puede estar vacío",
            default=self.state.nombre,
            style=WIZARD_STYLE,
        ).ask()

        if result is None:
            return StepResult.CANCEL

        self.state.nombre = result
        return StepResult.NEXT


class StepDatosCuenca(WizardStep):
    """Paso: Datos básicos de la cuenca (área, pendiente, P3,10)."""

    @property
    def title(self) -> str:
        return "Datos de la Cuenca"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        # Área
        default_area = str(self.state.area_ha) if self.state.area_ha > 0 else ""
        res, area = self.text(
            "Área de la cuenca (ha):",
            validate=validate_positive_float,
            default=default_area,
            back_option=True,
        )
        if res != StepResult.NEXT:
            return res
        self.state.area_ha = float(area)

        # Pendiente
        default_slope = str(self.state.slope_pct) if self.state.slope_pct > 0 else ""
        res, slope = self.text(
            "Pendiente media (%):",
            validate=validate_positive_float,
            default=default_slope,
            back_option=True,
        )
        if res == StepResult.BACK:
            # Volver al inicio de este paso (área)
            return self.execute()
        if res != StepResult.NEXT:
            return res
        self.state.slope_pct = float(slope)

        # P3,10
        self.echo("\n  Tip: Consulta la tabla IDF de DINAGUA para tu estación")
        default_p3 = str(self.state.p3_10) if self.state.p3_10 > 0 else ""
        res, p3_10 = self.text(
            "Precipitación P(3h, Tr=10) en mm:",
            validate=validate_positive_float,
            default=default_p3,
            back_option=True,
        )
        if res == StepResult.BACK:
            return self.execute()
        if res != StepResult.NEXT:
            return res
        self.state.p3_10 = float(p3_10)

        return StepResult.NEXT


class StepMetodoEscorrentia(WizardStep):
    """Paso: Selección de método de escorrentía (C o CN)."""

    @property
    def title(self) -> str:
        return "Método de Escorrentía"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, metodo = self.select(
            "Método de escorrentía:",
            choices=[
                "Coeficiente C (racional/GZ) - drenaje urbano",
                "Curva Número CN (SCS) - cuencas rurales/mixtas",
                "Ambos (C y CN) - comparar metodologías",
            ],
        )

        if res != StepResult.NEXT:
            return res

        # Recolectar C si corresponde
        if "Coeficiente C" in metodo or "Ambos" in metodo:
            c_result = self._collect_c()
            if c_result == StepResult.BACK:
                return self.execute()  # Volver a elegir método
            if c_result == StepResult.CANCEL:
                return StepResult.CANCEL

        # Recolectar CN si corresponde
        if "Curva Número" in metodo or "Ambos" in metodo:
            cn_result = self._collect_cn()
            if cn_result == StepResult.BACK:
                if "Ambos" in metodo and self.state.c is not None:
                    # Volver a C
                    self.state.c = None
                    c_result = self._collect_c()
                    if c_result != StepResult.NEXT:
                        return c_result
                    cn_result = self._collect_cn()
                else:
                    return self.execute()
            if cn_result == StepResult.CANCEL:
                return StepResult.CANCEL

        # Verificar que al menos uno fue ingresado
        if self.state.c is None and self.state.cn is None:
            self.echo("  Error: Debes ingresar al menos C o CN")
            return self.execute()

        # Validar consistencia C vs CN si ambos fueron ingresados
        if self.state.c is not None and self.state.cn is not None:
            self._validate_c_cn_consistency()

        return StepResult.NEXT

    def _validate_c_cn_consistency(self) -> None:
        """Valida y advierte sobre inconsistencias entre C y CN."""
        c = self.state.c
        cn = self.state.cn

        # Aproximar el C equivalente desde el CN usando relaciones empíricas
        # Relación aproximada: C ≈ (CN - 40) / 60 para CN entre 40 y 98
        # Esta es una aproximación muy general para fines de advertencia
        if cn >= 40:
            c_approx = (cn - 40) / 60
            c_approx = max(0.1, min(0.95, c_approx))  # Limitar a rango válido

            # Diferencia significativa si es mayor al 30%
            diff = abs(c - c_approx) / c_approx if c_approx > 0 else 0

            if diff > 0.30:
                self.echo("")
                self.echo("  ┌─────────────────────────────────────────────────────────┐")
                self.echo("  │  ⚠  ADVERTENCIA: Posible inconsistencia C vs CN        │")
                self.echo("  └─────────────────────────────────────────────────────────┘")
                self.echo("")
                self.echo(f"    Valor de C ingresado: {c:.2f}")
                self.echo(f"    Valor de CN ingresado: {cn}")
                self.echo(f"    C aproximado desde CN: {c_approx:.2f}")
                self.echo("")

                if c > c_approx:
                    self.echo("    El coeficiente C parece alto respecto al CN.")
                    self.echo("    Esto puede indicar:")
                    self.echo("      - El CN es bajo (suelo permeable) pero C es alto (impermeabilizado)")
                    self.echo("      - Diferentes condiciones de uso de suelo para cada método")
                else:
                    self.echo("    El coeficiente C parece bajo respecto al CN.")
                    self.echo("    Esto puede indicar:")
                    self.echo("      - El CN es alto (suelo impermeable) pero C es bajo (permeable)")
                    self.echo("      - Diferentes condiciones de uso de suelo para cada método")

                self.echo("")
                self.echo("    Los valores se usarán tal como fueron ingresados.")
                self.echo("    Revisa los resultados con cuidado.")
                self.echo("")

        # Advertir sobre combinaciones extremas
        extreme_warning = False
        if c >= 0.8 and cn <= 60:
            extreme_warning = True
            self.echo("")
            self.echo("  ⚠ ADVERTENCIA: C muy alto ({:.2f}) con CN bajo ({})".format(c, cn))
            self.echo("    Esto producirá resultados muy diferentes entre métodos.")
        elif c <= 0.3 and cn >= 85:
            extreme_warning = True
            self.echo("")
            self.echo("  ⚠ ADVERTENCIA: C muy bajo ({:.2f}) con CN alto ({})".format(c, cn))
            self.echo("    Esto producirá resultados muy diferentes entre métodos.")

        if extreme_warning:
            self.echo("")

    def _collect_c(self) -> StepResult:
        """Recolecta coeficiente C."""
        self.echo("\n-- Coeficiente de Escorrentía C --\n")

        res, metodo = self.select(
            "¿Cómo deseas obtener C?",
            choices=[
                "Ingresar valor directamente",
                "Calcular C ponderado por coberturas (Ven Te Chow)",
                "Calcular C ponderado por coberturas (FHWA)",
                "Calcular C ponderado por coberturas (Tabla Uruguay)",
            ],
        )

        if res != StepResult.NEXT:
            return res

        if "directamente" in metodo:
            self.echo("  Tip: C típicos -> Urbano denso: 0.7-0.9, Residencial: 0.4-0.7, Rural: 0.2-0.4")
            res, c_val = self.text(
                "Coeficiente de escorrentía C (0.1-0.95):",
                validate=lambda x: validate_range(x, 0.1, 0.95),
            )
            if res != StepResult.NEXT:
                return res
            self.state.c = float(c_val)
        else:
            # Calcular ponderado
            if "Chow" in metodo:
                table_key = "chow"
            elif "FHWA" in metodo:
                table_key = "fhwa"
            else:
                table_key = "uruguay"

            c_weighted = self._calculate_weighted_c(table_key)
            if c_weighted is None:
                return StepResult.BACK
            self.state.c = c_weighted

        return StepResult.NEXT

    def _calculate_weighted_c(self, table_key: str) -> Optional[float]:
        """Calcula C ponderado (versión simplificada)."""
        from hidropluvial.core.coefficients import (
            C_TABLES, ChowCEntry, FHWACEntry, format_c_table, weighted_c
        )

        table_name, table_data = C_TABLES[table_key]
        first_entry = table_data[0]
        is_chow = isinstance(first_entry, ChowCEntry)
        is_fhwa = isinstance(first_entry, FHWACEntry)
        tr = 2 if is_chow else 10

        if is_chow:
            typer.echo(format_c_table(table_data, table_name, tr, selection_mode=True))
        else:
            typer.echo(format_c_table(table_data, table_name, tr))

        self.echo(f"\n  Área de la cuenca: {self.state.area_ha} ha")
        self.echo("  Asigna coberturas. Selecciona '<< Volver' para cancelar.\n")

        coverage_data = []
        area_remaining = self.state.area_ha

        while area_remaining > 0.001:
            self.echo(f"  Área restante: {area_remaining:.3f} ha ({area_remaining/self.state.area_ha*100:.1f}%)")

            # Construir choices
            choices = []
            for i, e in enumerate(table_data):
                if is_chow:
                    c_val = e.c_tr2
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f} para Tr2)")
                elif is_fhwa:
                    c_val = e.c_base
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")
                else:
                    choices.append(f"{i+1}. {e.category} - {e.description} (C={e.c_recommended:.2f})")

            choices.append("Asignar área restante a una cobertura")
            choices.append("Terminar y calcular")

            res, selection = self.select("Selecciona cobertura:", choices)

            if res != StepResult.NEXT:
                return None

            if "Terminar" in selection:
                break

            if "Asignar área" in selection:
                cov_choices = []
                for i, e in enumerate(table_data):
                    if is_chow:
                        c_val = e.c_tr2
                    elif is_fhwa:
                        c_val = e.c_base
                    else:
                        c_val = e.c_recommended
                    cov_choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")

                res, cov_selection = self.select("Cobertura para área restante:", cov_choices)

                if res == StepResult.NEXT and cov_selection:
                    idx = int(cov_selection.split(".")[0]) - 1
                    entry = table_data[idx]
                    if is_chow:
                        c_val = entry.c_tr2
                    elif is_fhwa:
                        c_val = entry.c_base
                    else:
                        c_val = entry.c_recommended
                    coverage_data.append({
                        "area": area_remaining,
                        "c_val": c_val,
                        "table_index": idx,
                        "description": f"{entry.category}: {entry.description}",
                    })
                    area_remaining = 0
                break

            # Obtener índice
            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]

            res, area_str = self.text(f"Área (ha, max {area_remaining:.3f}):")

            if res != StepResult.NEXT or not area_str:
                continue

            try:
                area_val = float(area_str)
                if area_val <= 0 or area_val > area_remaining:
                    self.echo(f"  Error: El área debe estar entre 0 y {area_remaining:.3f}")
                    continue
            except ValueError:
                self.echo("  Error: Valor inválido")
                continue

            if is_chow:
                c_val = entry.c_tr2
            elif is_fhwa:
                c_val = entry.c_base
            else:
                c_val = entry.c_recommended

            coverage_data.append({
                "area": area_val,
                "c_val": c_val,
                "table_index": idx,
                "description": f"{entry.category}: {entry.description}",
            })
            area_remaining -= area_val
            self.echo(f"  + {area_val:.3f} ha con C={c_val:.2f}")

        if not coverage_data:
            self.echo("  No se asignaron coberturas.")
            return None

        # Calcular C ponderado
        areas = [d["area"] for d in coverage_data]
        coefficients = [d["c_val"] for d in coverage_data]
        c_weighted = weighted_c(areas, coefficients)

        self.state.c_weighted_data = {
            "table_key": table_key,
            "base_tr": tr,
            "items": coverage_data,
        }

        if is_chow:
            self.echo(f"\n  => C ponderado (Tr2) = {c_weighted:.3f}")
            self.echo("     Este valor se ajustará según el Tr de cada análisis.")
        else:
            self.echo(f"\n  => C ponderado = {c_weighted:.3f}")

        return c_weighted

    def _collect_cn(self) -> StepResult:
        """Recolecta Curva Número CN."""
        self.echo("\n-- Curva Número CN --\n")

        res, metodo = self.select(
            "¿Cómo deseas obtener CN?",
            choices=[
                "Ingresar valor directamente",
                "Calcular CN ponderado por coberturas (tablas NRCS)",
            ],
        )

        if res != StepResult.NEXT:
            return res

        if "directamente" in metodo:
            self.echo("  Tip: CN típicos -> Urbano: 85-95, Residencial: 70-85, Bosque: 55-70")
            res, cn_val = self.text(
                "Curva Número CN (30-98):",
                validate=lambda x: validate_range(x, 30, 98),
            )
            if res != StepResult.NEXT:
                return res
            self.state.cn = int(round(float(cn_val)))
        else:
            cn_weighted = self._calculate_weighted_cn()
            if cn_weighted is None:
                return StepResult.BACK
            self.state.cn = cn_weighted

        # Preguntar por parámetros SCS-CN (AMC y Lambda)
        res = self._configure_cn_parameters()
        if res != StepResult.NEXT:
            return res

        return StepResult.NEXT

    def _configure_cn_parameters(self) -> StepResult:
        """Configura AMC y Lambda para el método SCS-CN."""
        self.echo(f"\n  CN base = {self.state.cn}")

        res, configurar = self.confirm(
            "¿Configurar condición de humedad (AMC) y coeficiente Lambda?",
            default=False,
        )

        if res != StepResult.NEXT:
            return res

        if not configurar:
            # Usar valores por defecto
            self.state.amc = "II"
            self.state.lambda_coef = 0.2
            self.echo("  Usando valores por defecto: AMC II, λ = 0.20")
            return StepResult.NEXT

        # Configurar AMC
        self.echo("\n  Condición de Humedad Antecedente (AMC):")
        self.echo("    I  - Suelo seco (5 días sin lluvia, menor escorrentía)")
        self.echo("    II - Condición promedio (default)")
        self.echo("    III - Suelo húmedo (lluvia reciente, mayor escorrentía)")

        amc_choices = [
            "AMC I - Suelo seco",
            "AMC II - Condición promedio (recomendado)",
            "AMC III - Suelo húmedo",
        ]

        res, amc_choice = self.select("Condición AMC:", amc_choices)

        if res != StepResult.NEXT:
            return res

        if "AMC I" in amc_choice:
            self.state.amc = "I"
        elif "AMC III" in amc_choice:
            self.state.amc = "III"
        else:
            self.state.amc = "II"

        # Configurar Lambda
        self.echo("\n  Coeficiente Lambda (λ) para abstracción inicial:")
        self.echo("    Ia = λ × S  (donde S es la retención potencial)")
        self.echo("    λ = 0.20: Valor tradicional SCS")
        self.echo("    λ = 0.05: Áreas urbanas (NRCS actualizado)")

        lambda_choices = [
            "λ = 0.20 - Tradicional SCS (recomendado)",
            "λ = 0.05 - Áreas urbanas/impermeables",
            "Otro valor",
        ]

        res, lambda_choice = self.select("Coeficiente λ:", lambda_choices)

        if res != StepResult.NEXT:
            return res

        if "0.20" in lambda_choice:
            self.state.lambda_coef = 0.2
        elif "0.05" in lambda_choice:
            self.state.lambda_coef = 0.05
        elif "Otro" in lambda_choice:
            res, val = self.text(
                "Valor de λ (0.01-0.30):",
                validate=lambda x: validate_range(x, 0.01, 0.30),
            )
            if res != StepResult.NEXT:
                return res
            if val:
                self.state.lambda_coef = float(val)

        self.echo(f"\n  Configurado: AMC {self.state.amc}, λ = {self.state.lambda_coef}")
        return StepResult.NEXT

    def _calculate_weighted_cn(self) -> Optional[int]:
        """Calcula CN ponderado (versión simplificada)."""
        from hidropluvial.core.coefficients import CN_TABLES, format_cn_table, weighted_cn

        res, soil = self.select(
            "Grupo hidrológico de suelo:",
            choices=[
                "A - Alta infiltración (arena, grava)",
                "B - Moderada infiltración (limo arenoso)",
                "C - Baja infiltración (limo arcilloso)",
                "D - Muy baja infiltración (arcilla)",
            ],
        )

        if res != StepResult.NEXT:
            return None

        soil_group = soil[0]

        self.echo(f"\n  Grupo de suelo: {soil_group}")
        self.echo(f"  Área de la cuenca: {self.state.area_ha} ha")
        self.echo("  Puedes mezclar coberturas urbanas y agrícolas.\n")

        areas = []
        cn_values = []
        area_remaining = self.state.area_ha
        current_table = None

        while area_remaining > 0.001:
            self.echo(f"\n  Área restante: {area_remaining:.3f} ha ({area_remaining/self.state.area_ha*100:.1f}%)")

            res, table_choice = self.select(
                "Agregar cobertura de:",
                choices=[
                    "Tabla Urbana (residencial, comercial, industrial)",
                    "Tabla Agrícola (cultivos, pasturas, bosque)",
                    "Asignar todo el área restante",
                    "Terminar y calcular",
                ],
            )

            if res != StepResult.NEXT:
                return None

            if "Terminar" in table_choice:
                break

            if "Asignar todo" in table_choice:
                res, final_table = self.select(
                    "¿De qué tabla?",
                    choices=["Urbana", "Agrícola"],
                )
                if res != StepResult.NEXT:
                    continue

                table_key = "urban" if "Urbana" in final_table else "agricultural"
                _, table_data = CN_TABLES[table_key]

                cov_choices = []
                for i, e in enumerate(table_data):
                    cn = e.get_cn(soil_group)
                    cond = f" ({e.condition})" if e.condition != "N/A" else ""
                    cov_choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

                res, cov_selection = self.select("Cobertura para área restante:", cov_choices)

                if res == StepResult.NEXT and cov_selection:
                    idx = int(cov_selection.split(".")[0]) - 1
                    entry = table_data[idx]
                    cn = entry.get_cn(soil_group)
                    areas.append(area_remaining)
                    cn_values.append(cn)
                    area_remaining = 0
                break

            # Determinar tabla
            if "Urbana" in table_choice:
                table_key = "urban"
            else:
                table_key = "agricultural"

            table_name, table_data = CN_TABLES[table_key]

            if current_table != table_key:
                typer.echo(format_cn_table(table_data, table_name))
                current_table = table_key

            choices = []
            for i, e in enumerate(table_data):
                cn = e.get_cn(soil_group)
                cond = f" ({e.condition})" if e.condition != "N/A" else ""
                choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

            choices.append("Volver (elegir otra tabla)")

            res, selection = self.select("Selecciona cobertura:", choices, back_option=False)

            if res != StepResult.NEXT or "Volver" in selection:
                continue

            idx = int(selection.split(".")[0]) - 1
            entry = table_data[idx]
            cn = entry.get_cn(soil_group)

            res, area_str = self.text(f"Área para '{entry.description}' (ha, max {area_remaining:.3f}):")

            if res != StepResult.NEXT or not area_str:
                continue

            try:
                area_val = float(area_str)
                if area_val <= 0 or area_val > area_remaining:
                    continue
            except ValueError:
                continue

            areas.append(area_val)
            cn_values.append(cn)
            area_remaining -= area_val
            self.echo(f"  + {area_val:.3f} ha con CN={cn}")

        if not areas:
            self.echo("  No se asignaron coberturas.")
            return None

        cn_weighted = weighted_cn(areas, cn_values)
        cn_rounded = int(round(cn_weighted))
        self.echo(f"\n  => CN ponderado = {cn_weighted:.1f} -> {cn_rounded}")
        return cn_rounded


class StepLongitud(WizardStep):
    """Paso: Longitud del cauce (opcional)."""

    @property
    def title(self) -> str:
        return "Longitud del Cauce"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, tiene = self.confirm("¿Conoces la longitud del cauce principal?", default=True)

        if res != StepResult.NEXT:
            return res

        if tiene:
            default_length = str(int(self.state.length_m)) if self.state.length_m else ""
            res, length = self.text(
                "Longitud del cauce (m):",
                validate=validate_positive_float,
                default=default_length,
            )
            if res == StepResult.BACK:
                return self.execute()
            if res != StepResult.NEXT:
                return res
            if length:
                self.state.length_m = float(length)
        else:
            self.state.length_m = None

        return StepResult.NEXT


class StepMetodosTc(WizardStep):
    """Paso: Métodos de tiempo de concentración."""

    @property
    def title(self) -> str:
        return "Tiempo de Concentración"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        tc_choices = []
        if self.state.c:
            tc_choices.append(questionary.Choice("Desbordes (recomendado cuencas urbanas)", checked=True))
        if self.state.length_m:
            tc_choices.append(questionary.Choice("Kirpich (cuencas rurales)", checked=self.state.c is None))
            tc_choices.append(questionary.Choice("Temez", checked=False))

        if not tc_choices:
            self.echo("  Se necesita longitud de cauce o coeficiente C para calcular Tc")
            return StepResult.BACK

        res, tc_methods = self.checkbox("Métodos de Tc a calcular:", tc_choices)

        if res != StepResult.NEXT:
            return res

        if not tc_methods:
            self.echo("  Debes seleccionar al menos un método de Tc")
            return self.execute()

        self.state.tc_methods = tc_methods

        # Si se seleccionó Desbordes, preguntar por t0
        uses_desbordes = any("Desbordes" in m for m in tc_methods)
        if uses_desbordes:
            res = self._configure_t0()
            if res != StepResult.NEXT:
                return res
        else:
            self.state.t0_min = 5.0  # Valor por defecto (no se usará)

        return StepResult.NEXT

    def _configure_t0(self) -> StepResult:
        """Configura el tiempo de entrada inicial t0 para método Desbordes."""
        self.echo("\n  El método Desbordes usa un tiempo de entrada inicial (t0).")

        res, configurar = self.confirm(
            "¿Configurar t0? (default: 5 min)",
            default=False,
        )

        if res != StepResult.NEXT:
            return res

        if not configurar:
            self.state.t0_min = 5.0
            self.echo("  Usando t0 = 5 min (valor por defecto)")
            return StepResult.NEXT

        self.echo("\n  Tiempo de entrada inicial (t0):")
        self.echo("    t0 = 5 min - Valor típico (default)")
        self.echo("    t0 < 5 min - Cuencas muy urbanizadas")
        self.echo("    t0 > 5 min - Cuencas rurales")

        t0_choices = [
            "5 min - Valor típico (default)",
            "3 min - Cuenca muy urbanizada",
            "10 min - Cuenca rural",
            "Otro valor",
        ]

        res, t0_choice = self.select("Tiempo t0:", t0_choices)

        if res != StepResult.NEXT:
            return res

        if t0_choice:
            if "5 min" in t0_choice:
                self.state.t0_min = 5.0
            elif "3 min" in t0_choice:
                self.state.t0_min = 3.0
            elif "10 min" in t0_choice:
                self.state.t0_min = 10.0
            elif "Otro" in t0_choice:
                res, val = self.text(
                    "Valor de t0 (minutos):",
                    validate=validate_positive_float,
                    default="5",
                )
                if res != StepResult.NEXT:
                    return res
                if val:
                    self.state.t0_min = float(val)

        self.echo(f"\n  Configurado: t0 = {self.state.t0_min} min")
        return StepResult.NEXT


class StepTormenta(WizardStep):
    """Paso: Tipo de tormenta y períodos de retorno."""

    @property
    def title(self) -> str:
        return "Tormenta de Diseño"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        # Tipo de tormenta
        storm_choices = [
            questionary.Choice("GZ (6 horas) - recomendado drenaje urbano", checked=True),
            questionary.Choice("Bloques alternantes - duración según Tc", checked=False),
            questionary.Choice("Bloques 24 horas - obras mayores", checked=False),
            questionary.Choice("Bimodal - tormentas doble pico", checked=False),
            questionary.Choice("Huff (cuartil 2) - basado en datos históricos", checked=False),
            questionary.Choice("SCS Tipo II - distribución SCS 24h", checked=False),
        ]

        res, storm_types = self.checkbox("Tipos de tormenta a analizar:", storm_choices)

        if res != StepResult.NEXT:
            return res

        if not storm_types:
            self.echo("  Debes seleccionar al menos un tipo de tormenta")
            return self.execute()

        # Convertir a códigos
        self.state.storm_codes = []
        for storm_type in storm_types:
            if "GZ" in storm_type:
                self.state.storm_codes.append("gz")
            elif "Bloques alternantes" in storm_type:
                self.state.storm_codes.append("blocks")
            elif "24 horas" in storm_type:
                self.state.storm_codes.append("blocks24")
            elif "Bimodal" in storm_type:
                self.state.storm_codes.append("bimodal")
            elif "Huff" in storm_type:
                self.state.storm_codes.append("huff_q2")
            elif "SCS Tipo II" in storm_type:
                self.state.storm_codes.append("scs_ii")

        # Períodos de retorno
        tr_choices = [
            questionary.Choice("2 años", checked=True),
            questionary.Choice("5 años", checked=False),
            questionary.Choice("10 años", checked=True),
            questionary.Choice("25 años", checked=True),
            questionary.Choice("50 años", checked=False),
            questionary.Choice("100 años", checked=False),
        ]

        res, return_periods = self.checkbox("Períodos de retorno a analizar:", tr_choices)

        if res == StepResult.BACK:
            return self.execute()
        if res != StepResult.NEXT:
            return res

        if not return_periods:
            self.echo("  Debes seleccionar al menos un período de retorno")
            return self.execute()

        self.state.return_periods = [int(tr.split()[0]) for tr in return_periods]

        # Factor X para GZ
        if "gz" in self.state.storm_codes:
            x_result = self._collect_x_factors()
            if x_result == StepResult.BACK:
                return self.execute()
            if x_result != StepResult.NEXT:
                return x_result

        return StepResult.NEXT

    def _collect_x_factors(self) -> StepResult:
        """Recolecta factores X morfológicos."""
        self.echo("\n  Factor X morfológico (forma del hidrograma triangular):")
        self.echo("    X=1.00  Método racional (respuesta rápida)")
        self.echo("    X=1.25  Áreas urbanas con pendiente")
        self.echo("    X=1.67  Método SCS/NRCS")
        self.echo("    X=2.25+ Cuencas rurales/mixtas\n")

        x_choices = [
            questionary.Choice("1.00 - Método racional", checked=True),
            questionary.Choice("1.25 - Urbano con pendiente", checked=True),
            questionary.Choice("1.67 - SCS/NRCS", checked=False),
            questionary.Choice("2.25 - Uso mixto rural/urbano", checked=False),
        ]

        res, x_selected = self.checkbox("Valores de X a analizar:", x_choices)

        if res != StepResult.NEXT:
            return res

        if x_selected:
            self.state.x_factors = [float(x.split(" - ")[0]) for x in x_selected]
        else:
            self.state.x_factors = [1.0]

        return StepResult.NEXT


class StepSalida(WizardStep):
    """Paso: Configuración de salida."""

    @property
    def title(self) -> str:
        return "Configuración de Salida"

    def execute(self) -> StepResult:
        self.echo(f"\n-- {self.title} --\n")

        res, generar = self.confirm("¿Generar reporte LaTeX?", default=True)

        if res != StepResult.NEXT:
            return res

        if generar:
            default_name = self.state.nombre.lower().replace(" ", "_")
            res, output = self.text(
                "Nombre del archivo (sin extensión):",
                default=default_name,
                back_option=False,
            )
            if res != StepResult.NEXT:
                return res
            self.state.output_name = output if output else default_name

        return StepResult.NEXT


class WizardNavigator:
    """Controlador de navegación del wizard."""

    def __init__(self):
        self.state = WizardState()
        self.steps: list[WizardStep] = [
            StepNombre(self.state),
            StepDatosCuenca(self.state),
            StepMetodoEscorrentia(self.state),
            StepLongitud(self.state),
            StepMetodosTc(self.state),
            StepTormenta(self.state),
            StepSalida(self.state),
        ]
        self.current_step = 0

    def run(self) -> Optional[WizardState]:
        """Ejecuta el wizard con navegación."""
        while 0 <= self.current_step < len(self.steps):
            step = self.steps[self.current_step]

            # Mostrar progreso
            typer.echo(f"\n  [Paso {self.current_step + 1}/{len(self.steps)}]")

            result = step.execute()

            if result == StepResult.NEXT:
                self.current_step += 1
            elif result == StepResult.BACK:
                if self.current_step > 0:
                    self.current_step -= 1
                    typer.echo("\n  << Volviendo al paso anterior...")
                else:
                    typer.echo("\n  (Ya estás en el primer paso)")
            elif result == StepResult.CANCEL:
                typer.echo("\n  Wizard cancelado.")
                return None

        if self.current_step >= len(self.steps):
            return self.state
        return None
