"""
Calculador de tiempo de concentración (Tc).

Proporciona métodos para calcular Tc usando diferentes fórmulas:
- Kirpich
- Temez
- Desbordes
- NRCS (velocidades)
"""

from typing import Optional, Tuple, TYPE_CHECKING

from hidropluvial.core import kirpich, desbordes, temez
from hidropluvial.core.tc import nrcs_velocity_method

if TYPE_CHECKING:
    from hidropluvial.models import Basin


class TcCalculator:
    """Calculador de tiempo de concentración."""

    def __init__(self, basin: "Basin", c: Optional[float] = None, length: Optional[float] = None):
        """
        Args:
            basin: Cuenca
            c: Coeficiente de escorrentía C
            length: Longitud del cauce principal (m)
        """
        self.basin = basin
        self.c = c
        self.length = length

    def calculate_with_params(self, method: str) -> Tuple[Optional[float], dict]:
        """
        Calcula Tc según el método y retorna parámetros usados.

        Args:
            method: Nombre del método ("kirpich", "temez", "desbordes", "nrcs")

        Returns:
            Tupla (tc_hr, parameters) o (None, {}) si no se puede calcular
        """
        method = method.lower()

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

        elif method == "nrcs":
            # NRCS usa segmentos guardados en la cuenca
            if self.basin.nrcs_segments:
                p2_mm = self.basin.p2_mm or 50.0
                tc_hr = nrcs_velocity_method(self.basin.nrcs_segments, p2_mm)
                return tc_hr, {"p2_mm": p2_mm, "n_segments": len(self.basin.nrcs_segments)}

        return None, {}

    def calculate_and_save(self, method: str, menu) -> bool:
        """
        Calcula un único método de Tc y lo guarda en la cuenca.

        Args:
            method: Nombre del método
            menu: Instancia del menú para interacción con usuario

        Returns:
            True si se calculó exitosamente, False en caso contrario.
        """
        from hidropluvial.database import get_database
        from hidropluvial.models import TcResult
        from hidropluvial.cli.wizard.menus.add_analysis.nrcs_config import NRCSConfigurator

        db = get_database()
        method = method.lower()

        # NRCS requiere configurar segmentos primero
        if method == "nrcs":
            if not self.basin.nrcs_segments:
                configurator = NRCSConfigurator(self.basin, menu)
                if not configurator.configure():
                    return False

        # Kirpich y Temez requieren longitud
        if method in ("kirpich", "temez") and not self.length:
            menu.echo(f"\n  El método {method.capitalize()} requiere la longitud del cauce principal.\n")
            length_str = menu.text("Longitud del cauce (metros):", default="")
            if not length_str:
                menu.warning("Longitud requerida para este método")
                return False
            try:
                self.length = float(length_str)
                # Guardar en la cuenca
                self.basin.length_m = self.length
                db.update_basin(self.basin.id, length_m=self.length)
                menu.success(f"Longitud guardada: {self.length} m")
            except ValueError:
                menu.error("Valor inválido")
                return False

        # Desbordes requiere C
        if method == "desbordes" and not self.c:
            menu.echo(f"\n  El método Desbordes requiere el coeficiente de escorrentía C.\n")
            c_str = menu.text("Coeficiente C (0.1 - 1.0):", default="")
            if not c_str:
                menu.warning("Coeficiente C requerido para este método")
                return False
            try:
                self.c = float(c_str)
                if not 0.1 <= self.c <= 1.0:
                    menu.warning("C debe estar entre 0.1 y 1.0")
                    self.c = None
                    return False
                # Guardar en la cuenca
                self.basin.c = self.c
                db.update_basin(self.basin.id, c=self.c)
                menu.success(f"Coeficiente C guardado: {self.c}")
            except ValueError:
                menu.error("Valor inválido")
                return False

        tc_hr, tc_params = self.calculate_with_params(method)
        if tc_hr:
            db.add_tc_result(self.basin.id, method, tc_hr, tc_params)
            # Agregar al modelo en memoria
            result = TcResult(method=method, tc_hr=tc_hr, tc_min=tc_hr * 60, parameters=tc_params)
            self.basin.add_tc_result(result)
            method_display = format_method_name(method)
            menu.success(f"Tc ({method_display}): {result.tc_min:.1f} min")
            return True
        return False


def format_method_name(method: str) -> str:
    """Formatea el nombre del método para mostrar."""
    method_lower = method.lower()
    if method_lower == "nrcs":
        return "NRCS"
    elif method_lower == "scs":
        return "SCS"
    return method.capitalize()


def get_available_tc_methods(tc_existentes: list[str]) -> list[str]:
    """
    Retorna métodos de Tc disponibles (no calculados aún).

    Solo retorna métodos que se pueden calcular con los datos actuales
    o que pueden solicitar los datos faltantes interactivamente.
    """
    tc_choices = []
    tc_lower = [tc.lower() for tc in tc_existentes]

    # Desbordes: requiere C (se puede solicitar interactivamente)
    if "desbordes" not in tc_lower:
        tc_choices.append("Desbordes")

    # Kirpich: requiere longitud (se puede solicitar interactivamente)
    if "kirpich" not in tc_lower:
        tc_choices.append("Kirpich")

    # Temez: requiere longitud (se puede solicitar interactivamente)
    if "temez" not in tc_lower:
        tc_choices.append("Temez")

    # NRCS: siempre disponible (usa segmentos propios)
    if "nrcs" not in tc_lower:
        tc_choices.append("NRCS")

    return tc_choices
