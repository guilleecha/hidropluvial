"""
Panel de filtros inline para el visor de análisis.

Permite filtrar sin salir de la vista principal.
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional

from rich.console import Group
from rich.text import Text
from rich.panel import Panel

from hidropluvial.cli.theme import get_palette, get_icons
from .filters import get_unique_values, filter_analyses


@dataclass
class FilterCategory:
    """Categoría de filtro con sus valores."""
    key: str  # Clave interna (tc_method, storm_type, etc.)
    label: str  # Etiqueta visible
    values: List[Any] = field(default_factory=list)  # Valores únicos disponibles
    selected: Set[Any] = field(default_factory=set)  # Valores seleccionados

    def format_value(self, value: Any) -> str:
        """Formatea un valor para mostrar."""
        if self.key == "tc_method":
            return str(value).title()[:12]
        elif self.key == "storm_type":
            return str(value).upper()[:8]
        elif self.key == "return_period":
            return f"TR{value}"
        elif self.key == "x_factor":
            return f"X={value:.2f}"
        return str(value)


@dataclass
class InlineFilterState:
    """Estado del panel de filtros inline."""
    categories: List[FilterCategory] = field(default_factory=list)
    category_idx: int = 0  # Categoría seleccionada
    value_idx: int = 0  # Valor seleccionado dentro de la categoría

    @property
    def current_category(self) -> Optional[FilterCategory]:
        if 0 <= self.category_idx < len(self.categories):
            return self.categories[self.category_idx]
        return None

    def get_filters_dict(self) -> Dict[str, List[Any]]:
        """Retorna diccionario de filtros para aplicar."""
        result = {}
        for cat in self.categories:
            if cat.selected:
                result[cat.key] = list(cat.selected)
        return result

    def has_any_filter(self) -> bool:
        """Retorna True si hay algún filtro activo."""
        return any(cat.selected for cat in self.categories)

    def clear_all(self) -> None:
        """Limpia todos los filtros."""
        for cat in self.categories:
            cat.selected.clear()


def create_filter_state(analyses: list, current_filters: dict = None) -> InlineFilterState:
    """
    Crea el estado inicial del filtro basado en los análisis.

    Args:
        analyses: Lista de análisis para extraer valores únicos
        current_filters: Filtros actualmente activos (para restaurar selección)
    """
    if current_filters is None:
        current_filters = {}

    categories = []

    # Método Tc
    tc_values = get_unique_values(analyses, "tc_method")
    if len(tc_values) > 1:
        categories.append(FilterCategory(
            key="tc_method",
            label="Método Tc",
            values=tc_values,
            selected=set(current_filters.get("tc_method", [])),
        ))

    # Tipo de tormenta
    storm_values = get_unique_values(analyses, "storm_type")
    if len(storm_values) > 1:
        categories.append(FilterCategory(
            key="storm_type",
            label="Tormenta",
            values=storm_values,
            selected=set(current_filters.get("storm_type", [])),
        ))

    # Período de retorno
    tr_values = get_unique_values(analyses, "return_period")
    if len(tr_values) > 1:
        categories.append(FilterCategory(
            key="return_period",
            label="Período TR",
            values=tr_values,
            selected=set(current_filters.get("return_period", [])),
        ))

    # Factor X
    x_values = get_unique_values(analyses, "x_factor")
    if len(x_values) > 1:
        categories.append(FilterCategory(
            key="x_factor",
            label="Factor X",
            values=x_values,
            selected=set(current_filters.get("x_factor", [])),
        ))

    return InlineFilterState(categories=categories)


def build_filter_panel(state: InlineFilterState, filtered_count: int, total_count: int) -> Panel:
    """
    Construye el panel visual de filtros.

    Args:
        state: Estado del filtro
        filtered_count: Cantidad de análisis que pasan el filtro
        total_count: Cantidad total de análisis
    """
    p = get_palette()
    icons = get_icons()

    # Anchos fijos para evitar flickering
    LABEL_WIDTH = 12
    VALUE_WIDTH = 14  # [x]valor + espacios

    elements = []

    # Mostrar cada categoría
    for cat_idx, cat in enumerate(state.categories):
        is_cat_selected = cat_idx == state.category_idx

        # Línea de categoría con ancho fijo
        line = Text()
        line.append("  ", style="")
        line.append(">" if is_cat_selected else " ", style=f"bold {p.primary}" if is_cat_selected else "")
        line.append(" ", style="")

        # Label con ancho fijo
        label_text = f"{cat.label}:"
        line.append(f"{label_text:<{LABEL_WIDTH}}", style=f"bold {p.secondary}" if is_cat_selected else p.muted)

        # Valores de la categoría con ancho fijo
        for val_idx, value in enumerate(cat.values):
            is_val_selected = is_cat_selected and val_idx == state.value_idx
            is_checked = value in cat.selected

            # Estilo del valor
            if is_val_selected:
                val_style = f"bold reverse {p.primary}"
            elif is_checked:
                val_style = f"bold {p.accent}"
            else:
                val_style = ""

            # Checkbox
            check = icons.check if is_checked else " "
            check_style = f"bold {p.success}" if is_checked else p.muted

            # Formato: [x]valor con ancho fijo
            formatted_value = cat.format_value(value)
            # Calcular padding: VALUE_WIDTH - 3 (para [x]) - len(valor)
            value_padded = f"{formatted_value:<{VALUE_WIDTH - 3}}"

            line.append(f"[{check}]", style=check_style)
            line.append(value_padded, style=val_style)

        elements.append(line)

    elements.append(Text(""))

    # Contador de resultados con ancho fijo
    count_line = Text()
    count_line.append("  Resultados: ", style=p.muted)
    if filtered_count == total_count:
        count_text = f"{total_count} análisis (sin filtro)"
        count_line.append(f"{count_text:<30}", style=p.number)
    else:
        count_line.append(f"{filtered_count}", style=f"bold {p.accent}")
        rest_text = f" de {total_count} análisis"
        count_line.append(f"{rest_text:<25}", style=p.muted)
    elements.append(count_line)

    elements.append(Text(""))

    # Navegación con ancho fijo
    nav = Text()
    nav.append("  [", style=p.muted)
    nav.append("↑↓", style=f"bold {p.accent}")
    nav.append("] Categoría  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("←→", style=f"bold {p.accent}")
    nav.append("] Valor  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Espacio", style=f"bold {p.accent}")
    nav.append("] Toggle  ", style=p.muted)
    # Siempre mostrar [c] Limpiar para mantener ancho constante
    c_style = f"bold {p.accent}" if state.has_any_filter() else p.muted
    nav.append("[", style=p.muted)
    nav.append("c", style=c_style)
    nav.append("] Limpiar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Enter", style=f"bold {p.nav_confirm}")
    nav.append("] Aplicar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Esc", style=f"bold {p.nav_cancel}")
    nav.append("] Cancelar", style=p.muted)
    elements.append(nav)

    return Panel(
        Group(*elements),
        title=f"[bold {p.primary}] Filtrar Análisis [/]",
        border_style=p.border,
        padding=(0, 1),
    )


def handle_filter_key(key: str, state: InlineFilterState) -> Optional[str]:
    """
    Maneja teclas en modo filtro.

    Returns:
        None para continuar, "apply" para aplicar, "cancel" para cancelar
    """
    if not state.categories:
        return "cancel"

    cat = state.current_category

    if key == 'esc':
        return "cancel"

    elif key == 'enter':
        return "apply"

    elif key == 'c':
        # Limpiar todos los filtros
        state.clear_all()

    elif key == 'up':
        # Categoría anterior
        if state.category_idx > 0:
            state.category_idx -= 1
            state.value_idx = 0

    elif key == 'down':
        # Categoría siguiente
        if state.category_idx < len(state.categories) - 1:
            state.category_idx += 1
            state.value_idx = 0

    elif key == 'left':
        # Valor anterior
        if cat and state.value_idx > 0:
            state.value_idx -= 1

    elif key == 'right':
        # Valor siguiente
        if cat and state.value_idx < len(cat.values) - 1:
            state.value_idx += 1

    elif key == 'space' or key == ' ':
        # Toggle valor actual
        if cat and 0 <= state.value_idx < len(cat.values):
            value = cat.values[state.value_idx]
            if value in cat.selected:
                cat.selected.remove(value)
            else:
                cat.selected.add(value)

    return None
