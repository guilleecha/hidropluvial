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
        self.echo("  Selecciona uno o ambos métodos (espacio para marcar):\n")

        res, metodos = self.checkbox(
            "Métodos de escorrentía:",
            choices=[
                {"name": "Coeficiente C (racional) - drenaje urbano", "value": "C", "checked": True},
                {"name": "Curva Número CN (SCS) - cuencas rurales/mixtas", "value": "CN"},
            ],
        )

        if res != StepResult.NEXT:
            return res

        if not metodos:
            self.error("Debes seleccionar al menos un método")
            return self.execute()

        usar_c = "C" in metodos
        usar_cn = "CN" in metodos

        # Recolectar C si corresponde
        if usar_c:
            c_result = self._collect_c()
            if c_result == StepResult.BACK:
                return self.execute()  # Volver a elegir método
            if c_result == StepResult.CANCEL:
                return StepResult.CANCEL

        # Recolectar CN si corresponde
        if usar_cn:
            cn_result = self._collect_cn()
            if cn_result == StepResult.BACK:
                if usar_c and self.state.c is not None:
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
            self.error("Debes ingresar al menos C o CN")
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
        """Recolecta coeficiente C con opciones rápidas."""
        self.echo("\n-- Coeficiente de Escorrentía C --\n")

        # Menú con presets rápidos + opciones detalladas
        res, metodo = self.select(
            "¿Cómo deseas definir C?",
            choices=[
                # Presets rápidos
                "Urbano denso (C = 0.85) - comercial, industrial, alta densidad",
                "Residencial (C = 0.65) - viviendas, densidad media",
                "Mixto urbano-rural (C = 0.50) - suburbano, baja densidad",
                "Rural/Agrícola (C = 0.35) - pasturas, cultivos",
                # Separador visual
                "─────────────────────────────────────────────",
                # Opciones detalladas
                "Ingresar valor directo",
                "Definir coberturas detalladas (Ven Te Chow)",
                "Definir coberturas detalladas (FHWA)",
                "Definir coberturas detalladas (Tabla Uruguay)",
            ],
        )

        if res != StepResult.NEXT:
            return res

        # Presets rápidos
        if "Urbano denso" in metodo:
            self.state.c = 0.85
            self.info(f"C = 0.85 (Urbano denso)")
        elif "Residencial" in metodo:
            self.state.c = 0.65
            self.info(f"C = 0.65 (Residencial)")
        elif "Mixto" in metodo:
            self.state.c = 0.50
            self.info(f"C = 0.50 (Mixto urbano-rural)")
        elif "Rural" in metodo:
            self.state.c = 0.35
            self.info(f"C = 0.35 (Rural/Agrícola)")
        elif "───" in metodo:
            # Separador seleccionado, volver a mostrar menú
            return self._collect_c()
        elif "directo" in metodo:
            self.suggestion("C típicos: Urbano denso 0.7-0.9, Residencial 0.4-0.7, Rural 0.2-0.4")
            res, c_val = self.text(
                "Coeficiente de escorrentía C (0.1-0.95):",
                validate=lambda x: validate_range(x, 0.1, 0.95),
            )
            if res != StepResult.NEXT:
                return res
            self.state.c = float(c_val)
        else:
            # Calcular ponderado con visor detallado
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
        """Calcula C ponderado con visor interactivo."""
        from hidropluvial.core.coefficients import (
            C_TABLES, ChowCEntry, FHWACEntry, weighted_c
        )
        from hidropluvial.cli.viewer.coverage_viewer import (
            interactive_coverage_viewer, CoverageRow
        )
        from hidropluvial.cli.theme import print_coverage_assignments_table

        table_name, table_data = C_TABLES[table_key]
        first_entry = table_data[0]
        is_chow = isinstance(first_entry, ChowCEntry)
        is_fhwa = isinstance(first_entry, FHWACEntry)

        def get_c_value(entry):
            if is_chow:
                return entry.c_tr2
            elif is_fhwa:
                return entry.c_base
            return entry.c_recommended

        # Construir filas para el visor
        rows = []
        for i, entry in enumerate(table_data):
            c_val = get_c_value(entry)
            rows.append(CoverageRow(
                index=i,
                category=entry.category,
                description=entry.description,
                value=c_val,
                value_label="C",
            ))

        # Mostrar visor interactivo
        coverage_data = interactive_coverage_viewer(
            rows=rows,
            total_area=self.state.area_ha,
            value_label="C",
            table_name=f"Tabla {table_name}",
        )

        if not coverage_data:
            self.echo("  No se asignaron coberturas.")
            return None

        # Calcular C ponderado final
        areas = [d["area"] for d in coverage_data]
        coefficients = [d["c_val"] for d in coverage_data]
        c_weighted = weighted_c(areas, coefficients)

        # Mostrar resultado final
        print_coverage_assignments_table(
            coverage_data, self.state.area_ha, "C", c_weighted,
            title="Resultado Final"
        )

        # Guardar datos de ponderación
        base_tr = 2 if is_chow else None
        self.state.c_weighted_data = {
            "table_key": table_key,
            "base_tr": base_tr,
            "items": coverage_data,
        }

        if is_chow:
            self.echo("  Este valor se ajustará según el Tr de cada análisis.")

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
            self.suggestion("CN típicos: Urbano 85-95, Residencial 70-85, Bosque 55-70")
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
        """Calcula CN ponderado con visor interactivo y soporte para múltiples grupos de suelo."""
        from hidropluvial.core.coefficients import CN_TABLES, weighted_cn
        from hidropluvial.cli.viewer.coverage_viewer import (
            interactive_coverage_viewer, CoverageRow
        )
        from hidropluvial.cli.theme import print_coverage_assignments_table

        table_name, table_data = CN_TABLES["unified"]

        # Construir filas para el visor (usando grupo B como referencia inicial)
        rows = []
        for i, entry in enumerate(table_data):
            cn_b = entry.get_cn("B")
            cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
            rows.append(CoverageRow(
                index=i,
                category=entry.category,
                description=f"{entry.description}{cond}",
                value=cn_b,
                value_label="CN",
            ))

        # Callback para obtener CN según grupo de suelo
        def get_cn_for_soil(idx: int, soil_group: str) -> int:
            return table_data[idx].get_cn(soil_group)

        # Mostrar visor interactivo
        coverage_data = interactive_coverage_viewer(
            rows=rows,
            total_area=self.state.area_ha,
            value_label="CN",
            table_name=f"Tabla {table_name}",
            on_get_cn_for_soil=get_cn_for_soil,
        )

        if not coverage_data:
            self.echo("  No se asignaron coberturas.")
            return None

        # Calcular CN ponderado final
        cn_weighted = weighted_cn(
            [d["area"] for d in coverage_data],
            [d["cn_val"] for d in coverage_data]
        )
        cn_rounded = int(round(cn_weighted))

        # Mostrar resultado final
        print_coverage_assignments_table(
            coverage_data, self.state.area_ha, "CN", cn_weighted,
            title="Resultado Final"
        )

        self.echo(f"  CN redondeado: {cn_rounded}")

        return cn_rounded
