"""
Configuración NRCS para wizard de tiempo de concentración.

Módulo auxiliar con funciones para configurar el método NRCS (TR-55)
de velocidades para calcular tiempo de concentración.
"""

from hidropluvial.cli.wizard.styles import validate_positive_float
from hidropluvial.cli.wizard.steps.base import WizardStep, WizardState, StepResult
from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment
from hidropluvial.core.tc import SHEET_FLOW_N, SHALLOW_FLOW_K


class NRCSConfigMixin:
    """Mixin con métodos de configuración NRCS para WizardStep."""

    def _configure_nrcs(self) -> StepResult:
        """Configura segmentos para el método NRCS de velocidades."""
        self.echo("\n  ┌─────────────────────────────────────────────────────────────┐")
        self.echo("  │           MÉTODO NRCS - VELOCIDADES (TR-55)                  │")
        self.echo("  ├─────────────────────────────────────────────────────────────┤")
        self.echo("  │  El método divide el recorrido del agua en segmentos:        │")
        self.echo("  │                                                              │")
        self.echo("  │  1. FLUJO LAMINAR (Sheet Flow)                               │")
        self.echo("  │     ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈                                     │")
        self.echo("  │     Agua dispersa sobre superficie (máx 100m)                │")
        self.echo("  │                                                              │")
        self.echo("  │  2. FLUJO CONCENTRADO (Shallow Flow)                         │")
        self.echo("  │     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~                             │")
        self.echo("  │     Escorrentía en cunetas, zanjas pequeñas                  │")
        self.echo("  │                                                              │")
        self.echo("  │  3. FLUJO EN CANAL (Channel Flow)                            │")
        self.echo("  │     ══════════════════════════                               │")
        self.echo("  │     Arroyos, canales definidos                               │")
        self.echo("  └─────────────────────────────────────────────────────────────┘")

        # Primero configurar P2 para flujo laminar
        res = self._configure_p2()
        if res != StepResult.NEXT:
            return res

        self.state.nrcs_segments = []

        while True:
            self.echo(f"\n  Segmentos definidos: {len(self.state.nrcs_segments)}")
            if self.state.nrcs_segments:
                self._show_segments_summary()

            segment_choices = [
                "Agregar flujo laminar (sheet flow)",
                "Agregar flujo concentrado (shallow flow)",
                "Agregar flujo en canal (channel flow)",
            ]
            if self.state.nrcs_segments:
                segment_choices.append("Terminar configuración")

            res, choice = self.select("¿Qué tipo de segmento agregar?", segment_choices)

            if res == StepResult.BACK:
                if self.state.nrcs_segments:
                    # Eliminar último segmento
                    self.state.nrcs_segments.pop()
                    self.echo("  Último segmento eliminado")
                    continue
                else:
                    return StepResult.BACK
            if res != StepResult.NEXT:
                return res

            if "Terminar" in choice:
                break
            elif "laminar" in choice:
                res = self._add_sheet_flow_segment()
            elif "concentrado" in choice:
                res = self._add_shallow_flow_segment()
            elif "canal" in choice:
                res = self._add_channel_flow_segment()

            if res == StepResult.BACK:
                continue  # Volver al menú de segmentos
            if res != StepResult.NEXT:
                return res

        if not self.state.nrcs_segments:
            self.echo("  Debes agregar al menos un segmento")
            return self._configure_nrcs()

        # Mostrar resumen final
        self._show_nrcs_summary()
        return StepResult.NEXT

    def _configure_p2(self) -> StepResult:
        """Configura P2 (precipitación 2 años, 24h) para flujo laminar."""
        self.echo("\n  El flujo laminar requiere P₂ (precipitación de 2 años, 24 horas).")

        # Estimar P2 desde P3,10 si está disponible
        p2_estimated = None
        if self.state.p3_10:
            # Relación aproximada: P2,24h ≈ P3,10 × 0.5 (factor conservador)
            # Basado en curvas IDF DINAGUA: Tr=2 tiene CT≈0.6 vs Tr=10 con CT=1.0
            p2_estimated = self.state.p3_10 * 0.5
            self.echo(f"  Estimación desde P₃,₁₀ = {self.state.p3_10} mm:")
            self.echo(f"    P₂,₂₄ₕ ≈ {p2_estimated:.1f} mm (factor 0.5)")

        p2_choices = []
        if p2_estimated:
            p2_choices.append(f"Usar estimado: {p2_estimated:.1f} mm")
        p2_choices.extend([
            "50 mm - Valor típico Uruguay",
            "40 mm - Zona semiárida",
            "60 mm - Zona húmeda",
            "Ingresar valor conocido",
        ])

        res, p2_choice = self.select("Precipitación P₂ (2 años, 24h):", p2_choices)

        if res != StepResult.NEXT:
            return res

        if "estimado" in p2_choice.lower():
            self.state.p2_mm = p2_estimated
        elif "50 mm" in p2_choice:
            self.state.p2_mm = 50.0
        elif "40 mm" in p2_choice:
            self.state.p2_mm = 40.0
        elif "60 mm" in p2_choice:
            self.state.p2_mm = 60.0
        elif "Ingresar" in p2_choice:
            res, val = self.text(
                "Valor de P₂ (mm):",
                validate=validate_positive_float,
                default="50",
            )
            if res != StepResult.NEXT:
                return res
            if val:
                self.state.p2_mm = float(val)

        self.echo(f"\n  Configurado: P₂ = {self.state.p2_mm} mm")
        return StepResult.NEXT

    def _add_sheet_flow_segment(self) -> StepResult:
        """Agrega un segmento de flujo laminar."""
        self.echo("\n  ── FLUJO LAMINAR (Sheet Flow) ──")
        self.echo("  Agua dispersa sobre superficie, típicamente primeros 30-100m")
        self.echo("  Longitud máxima: 100m\n")

        # Longitud
        res, length_str = self.text(
            "Longitud del tramo (m, máx 100):",
            validate=lambda x: self._validate_range(x, 1, 100),
            default="50",
        )
        if res != StepResult.NEXT:
            return res

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        res, slope_str = self.text(
            "Pendiente (m/m):",
            validate=lambda x: self._validate_range(x, 0.001, 0.5),
            default=f"{self.state.slope_pct / 100:.3f}",
        )
        if res != StepResult.NEXT:
            return res

        # Coeficiente n
        self.echo("\n  Coeficientes de Manning para flujo laminar:")
        n_choices = [
            f"Superficie lisa (concreto, asfalto) - n = {SHEET_FLOW_N['smooth']:.3f}",
            f"Suelo desnudo/barbecho - n = {SHEET_FLOW_N['fallow']:.2f}",
            f"Pasto corto - n = {SHEET_FLOW_N['short_grass']:.2f}",
            f"Pasto denso - n = {SHEET_FLOW_N['dense_grass']:.2f}",
            f"Bosque ralo - n = {SHEET_FLOW_N['light_woods']:.2f}",
            f"Bosque denso - n = {SHEET_FLOW_N['dense_woods']:.2f}",
            "Ingresar valor personalizado",
        ]

        res, n_choice = self.select("Tipo de superficie:", n_choices)
        if res != StepResult.NEXT:
            return res

        if "lisa" in n_choice.lower():
            n_value = SHEET_FLOW_N["smooth"]
        elif "barbecho" in n_choice.lower():
            n_value = SHEET_FLOW_N["fallow"]
        elif "corto" in n_choice.lower():
            n_value = SHEET_FLOW_N["short_grass"]
        elif "denso" in n_choice.lower() and "pasto" in n_choice.lower():
            n_value = SHEET_FLOW_N["dense_grass"]
        elif "ralo" in n_choice.lower():
            n_value = SHEET_FLOW_N["light_woods"]
        elif "denso" in n_choice.lower():
            n_value = SHEET_FLOW_N["dense_woods"]
        else:
            res, n_str = self.text(
                "Valor de n:",
                validate=lambda x: self._validate_range(x, 0.01, 1.0),
                default="0.15",
            )
            if res != StepResult.NEXT:
                return res
            n_value = float(n_str)

        # Crear segmento
        segment = SheetFlowSegment(
            length_m=float(length_str),
            n=n_value,
            slope=float(slope_str),
            p2_mm=self.state.p2_mm,
        )
        self.state.nrcs_segments.append(segment)

        self.echo(f"\n  ✓ Agregado: Flujo laminar L={length_str}m, n={n_value:.3f}, S={slope_str}")
        return StepResult.NEXT

    def _add_shallow_flow_segment(self) -> StepResult:
        """Agrega un segmento de flujo concentrado superficial."""
        self.echo("\n  ── FLUJO CONCENTRADO (Shallow Flow) ──")
        self.echo("  Escorrentía en cunetas, zanjas pequeñas, surcos\n")

        # Longitud
        res, length_str = self.text(
            "Longitud del tramo (m):",
            validate=lambda x: self._validate_range(x, 1, 5000),
            default="200",
        )
        if res != StepResult.NEXT:
            return res

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        res, slope_str = self.text(
            "Pendiente (m/m):",
            validate=lambda x: self._validate_range(x, 0.001, 0.5),
            default=f"{self.state.slope_pct / 100:.3f}",
        )
        if res != StepResult.NEXT:
            return res

        # Tipo de superficie
        self.echo("\n  Velocidades según tipo de superficie:")
        surface_choices = [
            f"Pavimentado - k = {SHALLOW_FLOW_K['paved']:.2f} m/s",
            f"Sin pavimentar - k = {SHALLOW_FLOW_K['unpaved']:.2f} m/s",
            f"Con pasto - k = {SHALLOW_FLOW_K['grassed']:.2f} m/s",
            f"Pasto corto - k = {SHALLOW_FLOW_K['short_grass']:.2f} m/s",
        ]

        res, surface_choice = self.select("Tipo de superficie:", surface_choices)
        if res != StepResult.NEXT:
            return res

        if "Pavimentado" in surface_choice:
            surface = "paved"
        elif "Sin pavimentar" in surface_choice:
            surface = "unpaved"
        elif "Con pasto" in surface_choice:
            surface = "grassed"
        else:
            surface = "short_grass"

        # Crear segmento
        segment = ShallowFlowSegment(
            length_m=float(length_str),
            slope=float(slope_str),
            surface=surface,
        )
        self.state.nrcs_segments.append(segment)

        self.echo(f"\n  ✓ Agregado: Flujo concentrado L={length_str}m, superficie={surface}")
        return StepResult.NEXT

    def _add_channel_flow_segment(self) -> StepResult:
        """Agrega un segmento de flujo en canal."""
        self.echo("\n  ── FLUJO EN CANAL (Channel Flow) ──")
        self.echo("  Arroyos, canales definidos, colectores\n")

        # Longitud
        res, length_str = self.text(
            "Longitud del tramo (m):",
            validate=lambda x: self._validate_range(x, 1, 10000),
            default="500",
        )
        if res != StepResult.NEXT:
            return res

        # Pendiente
        self.echo(f"\n  Pendiente: usar valor decimal (ej: 0.005 = 0.5%)")
        res, slope_str = self.text(
            "Pendiente (m/m):",
            validate=lambda x: self._validate_range(x, 0.0001, 0.2),
            default=f"{self.state.slope_pct / 100:.4f}",
        )
        if res != StepResult.NEXT:
            return res

        # Coeficiente n de Manning
        self.echo("\n  Coeficientes de Manning para canales:")
        channel_n_choices = [
            "Canal de concreto liso - n = 0.013",
            "Canal de concreto revestido - n = 0.017",
            "Canal de tierra limpio - n = 0.022",
            "Canal de tierra con vegetación - n = 0.030",
            "Arroyo natural limpio - n = 0.035",
            "Arroyo con vegetación - n = 0.050",
            "Arroyo sinuoso con poza - n = 0.070",
            "Ingresar valor personalizado",
        ]

        res, n_choice = self.select("Tipo de canal:", channel_n_choices)
        if res != StepResult.NEXT:
            return res

        n_values = {
            "liso": 0.013,
            "revestido": 0.017,
            "limpio": 0.022,
            "tierra con": 0.030,
            "natural limpio": 0.035,
            "con vegetación": 0.050,
            "sinuoso": 0.070,
        }

        n_value = None
        for key, val in n_values.items():
            if key in n_choice.lower():
                n_value = val
                break

        if n_value is None:
            res, n_str = self.text(
                "Valor de n:",
                validate=lambda x: self._validate_range(x, 0.01, 0.15),
                default="0.035",
            )
            if res != StepResult.NEXT:
                return res
            n_value = float(n_str)

        # Radio hidráulico
        self.echo("\n  Radio hidráulico R = Área / Perímetro mojado")
        self.echo("  Valores típicos: 0.3-0.5m (cunetas), 0.5-1.5m (canales), 1-3m (arroyos)")

        res, r_str = self.text(
            "Radio hidráulico (m):",
            validate=lambda x: self._validate_range(x, 0.05, 5.0),
            default="0.5",
        )
        if res != StepResult.NEXT:
            return res

        # Crear segmento
        segment = ChannelFlowSegment(
            length_m=float(length_str),
            n=n_value,
            slope=float(slope_str),
            hydraulic_radius_m=float(r_str),
        )
        self.state.nrcs_segments.append(segment)

        self.echo(f"\n  ✓ Agregado: Canal L={length_str}m, n={n_value:.3f}, R={r_str}m")
        return StepResult.NEXT

    def _show_segments_summary(self) -> None:
        """Muestra resumen de segmentos configurados."""
        self.echo("  ┌───────────────────────────────────────────┐")
        for i, seg in enumerate(self.state.nrcs_segments, 1):
            if isinstance(seg, SheetFlowSegment):
                self.echo(f"  │ {i}. Laminar: L={seg.length_m}m, n={seg.n:.3f}          │")
            elif isinstance(seg, ShallowFlowSegment):
                self.echo(f"  │ {i}. Concentrado: L={seg.length_m}m, {seg.surface}    │")
            elif isinstance(seg, ChannelFlowSegment):
                self.echo(f"  │ {i}. Canal: L={seg.length_m}m, n={seg.n:.3f}, R={seg.hydraulic_radius_m}m │")
        self.echo("  └───────────────────────────────────────────┘")

    def _show_nrcs_summary(self) -> None:
        """Muestra resumen final de configuración NRCS."""
        from hidropluvial.core.tc import nrcs_velocity_method

        tc_hr = nrcs_velocity_method(self.state.nrcs_segments, self.state.p2_mm)
        tc_min = tc_hr * 60

        self.echo("\n  ═══════════════════════════════════════════")
        self.echo("  RESUMEN MÉTODO NRCS")
        self.echo("  ───────────────────────────────────────────")
        self.echo(f"  Segmentos: {len(self.state.nrcs_segments)}")
        self.echo(f"  P₂ (2 años, 24h): {self.state.p2_mm} mm")
        self.echo(f"  Tc calculado: {tc_min:.1f} min ({tc_hr:.2f} hr)")
        self.echo("  ═══════════════════════════════════════════")

    def _validate_range(self, value: str, min_val: float, max_val: float) -> bool | str:
        """Valida que el valor esté en el rango especificado."""
        try:
            v = float(value)
            if v < min_val:
                return f"Debe ser >= {min_val}"
            if v > max_val:
                return f"Debe ser <= {max_val}"
            return True
        except ValueError:
            return "Debe ser un número válido"
