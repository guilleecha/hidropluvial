"""
Paso del wizard para selección de método de escorrentía (C y CN).
"""

from typing import Optional

import typer

from hidropluvial.cli.wizard.styles import validate_range
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult


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
