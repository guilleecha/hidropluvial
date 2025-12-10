"""
Configuración de segmentos para el método NRCS de velocidades.

Permite configurar interactivamente los segmentos de flujo:
- Sheet Flow (flujo laminar)
- Shallow Flow (flujo concentrado)
- Channel Flow (flujo en canal)
"""

from typing import Optional, TYPE_CHECKING

from hidropluvial.config import SheetFlowSegment, ShallowFlowSegment, ChannelFlowSegment
from hidropluvial.core.tc import nrcs_velocity_method, SHEET_FLOW_N, SHALLOW_FLOW_K

if TYPE_CHECKING:
    from hidropluvial.models import Basin


class NRCSConfigurator:
    """Configurador interactivo de segmentos NRCS."""

    def __init__(self, basin: "Basin", menu):
        """
        Args:
            basin: Cuenca a configurar
            menu: Instancia del menú padre (para usar echo, select, etc.)
        """
        self.basin = basin
        self.menu = menu

    def configure(self) -> bool:
        """
        Configura segmentos para el método NRCS de velocidades.

        Returns:
            True si se configuró exitosamente, False si se canceló.
        """
        self.menu.echo("\n  ┌─────────────────────────────────────────────────────────────┐")
        self.menu.echo("  │           MÉTODO NRCS - VELOCIDADES (TR-55)                  │")
        self.menu.echo("  ├─────────────────────────────────────────────────────────────┤")
        self.menu.echo("  │  El método divide el recorrido del agua en segmentos:        │")
        self.menu.echo("  │                                                              │")
        self.menu.echo("  │  1. FLUJO LAMINAR (Sheet Flow) - máx 100m                    │")
        self.menu.echo("  │  2. FLUJO CONCENTRADO (Shallow Flow) - cunetas, zanjas       │")
        self.menu.echo("  │  3. FLUJO EN CANAL (Channel Flow) - arroyos, canales         │")
        self.menu.echo("  └─────────────────────────────────────────────────────────────┘")

        # Configurar P2
        p2_mm = self._configure_p2()
        if p2_mm is None:
            return False

        segments = []

        while True:
            self.menu.echo(f"\n  Segmentos definidos: {len(segments)}")
            if segments:
                self._show_segments_summary(segments)

            segment_choices = [
                "Agregar flujo laminar (sheet flow)",
                "Agregar flujo concentrado (shallow flow)",
                "Agregar flujo en canal (channel flow)",
            ]
            if segments:
                segment_choices.append("Terminar configuración")
            segment_choices.append("← Cancelar")

            choice = self.menu.select("¿Qué tipo de segmento agregar?", segment_choices)

            if choice is None or "Cancelar" in choice:
                return False
            if "Terminar" in choice:
                break
            elif "laminar" in choice:
                segment = self._add_sheet_flow_segment(p2_mm)
                if segment:
                    segments.append(segment)
            elif "concentrado" in choice:
                segment = self._add_shallow_flow_segment()
                if segment:
                    segments.append(segment)
            elif "canal" in choice:
                segment = self._add_channel_flow_segment()
                if segment:
                    segments.append(segment)

        if not segments:
            self.menu.warning("Debes agregar al menos un segmento")
            return False

        # Guardar en la base de datos
        from hidropluvial.database import get_database
        db = get_database()
        db.set_nrcs_segments(self.basin.id, segments, p2_mm)

        # Actualizar modelo en memoria
        self.basin.nrcs_segments = segments
        self.basin.p2_mm = p2_mm

        # Mostrar resumen
        tc_hr = nrcs_velocity_method(segments, p2_mm)
        self.menu.echo("\n  ═══════════════════════════════════════════")
        self.menu.echo("  RESUMEN MÉTODO NRCS")
        self.menu.echo("  ───────────────────────────────────────────")
        self.menu.echo(f"  Segmentos: {len(segments)}")
        self.menu.echo(f"  P₂ (2 años, 24h): {p2_mm} mm")
        self.menu.echo(f"  Tc calculado: {tc_hr * 60:.1f} min ({tc_hr:.2f} hr)")
        self.menu.echo("  ═══════════════════════════════════════════")

        return True

    def _configure_p2(self) -> Optional[float]:
        """Configura P2 (precipitación 2 años, 24h) para flujo laminar."""
        self.menu.echo("\n  El flujo laminar requiere P₂ (precipitación de 2 años, 24 horas).")

        # Estimar P2 desde P3,10 si está disponible
        p2_estimated = None
        if self.basin.p3_10:
            p2_estimated = self.basin.p3_10 * 0.5
            self.menu.echo(f"  Estimación desde P3,10 = {self.basin.p3_10} mm:")
            self.menu.echo(f"    P2,24h ≈ {p2_estimated:.1f} mm (factor 0.5)")

        p2_choices = []
        if p2_estimated:
            p2_choices.append(f"Usar estimado: {p2_estimated:.1f} mm")
        p2_choices.extend([
            "50 mm - Valor típico Uruguay",
            "40 mm - Zona semiárida",
            "60 mm - Zona húmeda",
            "Ingresar valor conocido",
            "← Cancelar",
        ])

        p2_choice = self.menu.select("Precipitación P₂ (2 años, 24h):", p2_choices)

        if p2_choice is None or "Cancelar" in p2_choice:
            return None

        if "estimado" in p2_choice.lower():
            return p2_estimated
        elif "50 mm" in p2_choice:
            return 50.0
        elif "40 mm" in p2_choice:
            return 40.0
        elif "60 mm" in p2_choice:
            return 60.0
        elif "Ingresar" in p2_choice:
            val = self.menu.text("Valor de P₂ (mm):", default="50")
            if val:
                try:
                    return float(val)
                except ValueError:
                    self.menu.error("Valor inválido")
                    return None
        return 50.0

    def _add_sheet_flow_segment(self, p2_mm: float) -> Optional[SheetFlowSegment]:
        """Agrega un segmento de flujo laminar."""
        self.menu.echo("\n  ── FLUJO LAMINAR (Sheet Flow) ──")
        self.menu.echo("  Agua dispersa sobre superficie, típicamente primeros 30-100m")
        self.menu.echo("  Longitud máxima: 100m\n")

        # Longitud
        length_str = self.menu.text("Longitud del tramo (m, máx 100):", default="50")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0 or length > 100:
                self.menu.error("Longitud debe estar entre 1 y 100 m")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Pendiente
        self.menu.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        slope_str = self.menu.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.3f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.menu.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Coeficiente n
        self.menu.echo("\n  Coeficientes de Manning para flujo laminar:")
        n_choices = [
            f"Superficie lisa (concreto, asfalto) - n = {SHEET_FLOW_N['smooth']:.3f}",
            f"Suelo desnudo/barbecho - n = {SHEET_FLOW_N['fallow']:.2f}",
            f"Pasto corto - n = {SHEET_FLOW_N['short_grass']:.2f}",
            f"Pasto denso - n = {SHEET_FLOW_N['dense_grass']:.2f}",
            f"Bosque ralo - n = {SHEET_FLOW_N['light_woods']:.2f}",
            f"Bosque denso - n = {SHEET_FLOW_N['dense_woods']:.2f}",
            "Ingresar valor personalizado",
        ]

        n_choice = self.menu.select("Tipo de superficie:", n_choices)
        if not n_choice:
            return None

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
            n_str = self.menu.text("Valor de n:", default="0.15")
            if not n_str:
                return None
            try:
                n_value = float(n_str)
            except ValueError:
                self.menu.error("Valor inválido")
                return None

        segment = SheetFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            p2_mm=p2_mm,
        )
        self.menu.success(f"Agregado: Flujo laminar L={length}m, n={n_value:.3f}, S={slope:.3f}")
        return segment

    def _add_shallow_flow_segment(self) -> Optional[ShallowFlowSegment]:
        """Agrega un segmento de flujo concentrado superficial."""
        self.menu.echo("\n  ── FLUJO CONCENTRADO (Shallow Flow) ──")
        self.menu.echo("  Escorrentía en cunetas, zanjas pequeñas, surcos\n")

        # Longitud
        length_str = self.menu.text("Longitud del tramo (m):", default="200")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0:
                self.menu.error("Longitud debe ser positiva")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Pendiente
        self.menu.echo(f"\n  Pendiente: usar valor decimal (ej: 0.02 = 2%)")
        slope_str = self.menu.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.3f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.menu.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Tipo de superficie
        self.menu.echo("\n  Velocidades según tipo de superficie:")
        surface_choices = [
            f"Pavimentado - k = {SHALLOW_FLOW_K['paved']:.2f} m/s",
            f"Sin pavimentar - k = {SHALLOW_FLOW_K['unpaved']:.2f} m/s",
            f"Con pasto - k = {SHALLOW_FLOW_K['grassed']:.2f} m/s",
            f"Pasto corto - k = {SHALLOW_FLOW_K['short_grass']:.2f} m/s",
        ]

        surface_choice = self.menu.select("Tipo de superficie:", surface_choices)
        if not surface_choice:
            return None

        if "Pavimentado" in surface_choice:
            surface = "paved"
        elif "Sin pavimentar" in surface_choice:
            surface = "unpaved"
        elif "Con pasto" in surface_choice:
            surface = "grassed"
        else:
            surface = "short_grass"

        segment = ShallowFlowSegment(
            length_m=length,
            slope=slope,
            surface=surface,
        )
        self.menu.success(f"Agregado: Flujo concentrado L={length}m, superficie={surface}")
        return segment

    def _add_channel_flow_segment(self) -> Optional[ChannelFlowSegment]:
        """Agrega un segmento de flujo en canal."""
        self.menu.echo("\n  ── FLUJO EN CANAL (Channel Flow) ──")
        self.menu.echo("  Arroyos, canales definidos, colectores\n")

        # Longitud
        length_str = self.menu.text("Longitud del tramo (m):", default="500")
        if not length_str:
            return None
        try:
            length = float(length_str)
            if length <= 0:
                self.menu.error("Longitud debe ser positiva")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Pendiente
        self.menu.echo(f"\n  Pendiente: usar valor decimal (ej: 0.005 = 0.5%)")
        slope_str = self.menu.text("Pendiente (m/m):", default=f"{self.basin.slope_pct / 100:.4f}")
        if not slope_str:
            return None
        try:
            slope = float(slope_str)
            if slope <= 0 or slope >= 1:
                self.menu.error("Pendiente debe estar entre 0 y 1")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        # Coeficiente n de Manning
        self.menu.echo("\n  Coeficientes de Manning para canales:")
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

        n_choice = self.menu.select("Tipo de canal:", channel_n_choices)
        if not n_choice:
            return None

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
            n_str = self.menu.text("Valor de n:", default="0.035")
            if not n_str:
                return None
            try:
                n_value = float(n_str)
            except ValueError:
                self.menu.error("Valor inválido")
                return None

        # Radio hidráulico
        self.menu.echo("\n  Radio hidráulico R = Área / Perímetro mojado")
        self.menu.echo("  Valores típicos: 0.3-0.5m (cunetas), 0.5-1.5m (canales), 1-3m (arroyos)")

        r_str = self.menu.text("Radio hidráulico (m):", default="0.5")
        if not r_str:
            return None
        try:
            r_value = float(r_str)
            if r_value <= 0:
                self.menu.error("Radio debe ser positivo")
                return None
        except ValueError:
            self.menu.error("Valor inválido")
            return None

        segment = ChannelFlowSegment(
            length_m=length,
            n=n_value,
            slope=slope,
            hydraulic_radius_m=r_value,
        )
        self.menu.success(f"Agregado: Canal L={length}m, n={n_value:.3f}, R={r_value}m")
        return segment

    def _show_segments_summary(self, segments: list) -> None:
        """Muestra resumen de segmentos configurados."""
        self.menu.echo("  ┌───────────────────────────────────────────┐")
        for i, seg in enumerate(segments, 1):
            if isinstance(seg, SheetFlowSegment):
                self.menu.echo(f"  │ {i}. Laminar: L={seg.length_m}m, n={seg.n:.3f}           │")
            elif isinstance(seg, ShallowFlowSegment):
                self.menu.echo(f"  │ {i}. Concentrado: L={seg.length_m}m, {seg.surface}     │")
            elif isinstance(seg, ChannelFlowSegment):
                self.menu.echo(f"  │ {i}. Canal: L={seg.length_m}m, n={seg.n:.3f}, R={seg.hydraulic_radius_m}m  │")
        self.menu.echo("  └───────────────────────────────────────────┘")
