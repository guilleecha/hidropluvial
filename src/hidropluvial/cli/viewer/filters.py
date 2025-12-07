"""
Lógica de filtrado para el visor interactivo.

Funciones para filtrar análisis por múltiples criterios.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.cli.viewer.terminal import clear_screen


def get_unique_values(analyses: list, field: str) -> list:
    """Obtiene valores unicos de un campo en los analisis."""
    values = set()
    for a in analyses:
        if field == "tc_method":
            values.add(a.tc.method)
        elif field == "storm_type":
            values.add(a.storm.type)
        elif field == "return_period":
            values.add(a.storm.return_period)
        elif field == "x_factor":
            if a.hydrograph.x_factor:
                values.add(a.hydrograph.x_factor)
    return sorted(values, key=lambda x: str(x))


def filter_analyses(analyses: list, filters: dict) -> list:
    """Filtra analisis con selección múltiple (OR dentro de cada campo, AND entre campos)."""
    result = analyses

    for field, values in filters.items():
        if not values:
            continue

        if field == "tc_method":
            result = [a for a in result if a.tc.method in values]
        elif field == "storm_type":
            result = [a for a in result if a.storm.type in values]
        elif field == "return_period":
            result = [a for a in result if a.storm.return_period in values]
        elif field == "x_factor":
            result = [a for a in result if a.hydrograph.x_factor in values]

    return result


def build_filter_summary_table(all_analyses: list, current_filters: dict) -> Table:
    """
    Construye tabla normalizada de variables disponibles para filtrar.
    Variables como columnas, valores como filas.
    """
    p = get_palette()

    tc_methods = get_unique_values(all_analyses, "tc_method")
    storm_types = get_unique_values(all_analyses, "storm_type")
    return_periods = get_unique_values(all_analyses, "return_period")
    x_factors = get_unique_values(all_analyses, "x_factor")

    # Filtros activos (para marcar)
    active_tc = set(current_filters.get("tc_method", []))
    active_storm = set(current_filters.get("storm_type", []))
    active_tr = set(current_filters.get("return_period", []))
    active_x = set(current_filters.get("x_factor", []))

    table = Table(
        show_header=True,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Método Tc", width=12)
    table.add_column("Tormenta", width=10)
    table.add_column("TR", width=6, justify="right")
    table.add_column("Factor X", width=10, justify="right")

    # Determinar número máximo de filas
    max_rows = max(len(tc_methods), len(storm_types), len(return_periods), len(x_factors) or 1)

    for i in range(max_rows):
        # Método Tc
        if i < len(tc_methods):
            tc_val = tc_methods[i]
            tc_style = f"bold {p.accent}" if tc_val in active_tc else ""
            tc_text = Text(tc_val.title(), style=tc_style)
        else:
            tc_text = Text("")

        # Tormenta
        if i < len(storm_types):
            storm_val = storm_types[i]
            storm_style = f"bold {p.accent}" if storm_val in active_storm else ""
            storm_text = Text(storm_val.upper(), style=storm_style)
        else:
            storm_text = Text("")

        # TR
        if i < len(return_periods):
            tr_val = return_periods[i]
            tr_style = f"bold {p.accent}" if tr_val in active_tr else ""
            tr_text = Text(str(tr_val), style=tr_style)
        else:
            tr_text = Text("")

        # Factor X
        if x_factors and i < len(x_factors):
            x_val = x_factors[i]
            x_style = f"bold {p.accent}" if x_val in active_x else ""
            x_text = Text(f"{x_val:.2f}", style=x_style)
        else:
            x_text = Text("-" if i == 0 and not x_factors else "")

        table.add_row(tc_text, storm_text, tr_text, x_text)

    return table


def show_filter_menu(console: Console, all_analyses: list, current_filters: dict) -> tuple:
    """
    Muestra menu de filtros con selección múltiple.
    Retorna los nuevos filtros y lista filtrada.
    """
    import questionary
    from questionary import Choice
    from hidropluvial.cli.wizard.styles import get_wizard_style

    p = get_palette()

    # Obtener valores unicos
    tc_methods = get_unique_values(all_analyses, "tc_method")
    storm_types = get_unique_values(all_analyses, "storm_type")
    return_periods = get_unique_values(all_analyses, "return_period")
    x_factors = get_unique_values(all_analyses, "x_factor")

    new_filters = {}

    clear_screen()
    console.print()

    # Mostrar tabla resumen
    summary_table = build_filter_summary_table(all_analyses, current_filters)
    console.print(Panel(
        summary_table,
        title=Text(" Filtrar Análisis ", style=f"bold {p.primary}"),
        title_align="left",
        border_style=p.primary,
        box=box.ROUNDED,
    ))
    console.print()

    # Opción de limpiar filtros si hay filtros activos
    if current_filters:
        action = questionary.select(
            "Acción:",
            choices=["Modificar filtros", "Limpiar todos los filtros", "Cancelar"],
            style=get_wizard_style(),
        ).ask()

        if action == "Limpiar todos los filtros":
            return {}, all_analyses
        elif action == "Cancelar":
            return current_filters, filter_analyses(all_analyses, current_filters)

    console.print(f"  [dim]Usa ESPACIO para seleccionar, ENTER para confirmar[/dim]")
    console.print()

    # Filtro por metodo Tc (si hay más de 1)
    if len(tc_methods) > 1:
        choices = [
            Choice(
                m.title(),
                checked=m in current_filters.get("tc_method", [])
            )
            for m in tc_methods
        ]
        result = questionary.checkbox(
            "Métodos Tc (vacío = todos):",
            choices=choices,
            style=get_wizard_style(),
        ).ask()
        if result:
            new_filters["tc_method"] = [r.lower() for r in result]

    # Filtro por tipo de tormenta
    if len(storm_types) > 1:
        choices = [
            Choice(
                s.upper(),
                checked=s in current_filters.get("storm_type", [])
            )
            for s in storm_types
        ]
        result = questionary.checkbox(
            "Tipos de tormenta (vacío = todos):",
            choices=choices,
            style=get_wizard_style(),
        ).ask()
        if result:
            new_filters["storm_type"] = [r.lower() for r in result]

    # Filtro por periodo de retorno
    if len(return_periods) > 1:
        choices = [
            Choice(
                f"TR {tr}",
                checked=tr in current_filters.get("return_period", [])
            )
            for tr in return_periods
        ]
        result = questionary.checkbox(
            "Períodos de retorno (vacío = todos):",
            choices=choices,
            style=get_wizard_style(),
        ).ask()
        if result:
            new_filters["return_period"] = [int(r.replace("TR ", "")) for r in result]

    # Filtro por factor X
    if len(x_factors) > 1:
        choices = [
            Choice(
                f"X={x:.2f}",
                checked=x in current_filters.get("x_factor", [])
            )
            for x in x_factors
        ]
        result = questionary.checkbox(
            "Factor X (vacío = todos):",
            choices=choices,
            style=get_wizard_style(),
        ).ask()
        if result:
            new_filters["x_factor"] = [float(r.replace("X=", "")) for r in result]

    # Aplicar filtros
    filtered = filter_analyses(all_analyses, new_filters)

    return new_filters, filtered


def format_active_filters(active_filters: dict) -> str:
    """Formatea los filtros activos para mostrar en el título."""
    if not active_filters:
        return ""

    filter_parts = []
    if "tc_method" in active_filters and active_filters["tc_method"]:
        tc_str = ", ".join(m.title() for m in active_filters["tc_method"])
        filter_parts.append(f"Tc={tc_str}")
    if "storm_type" in active_filters and active_filters["storm_type"]:
        storm_str = ", ".join(s.upper() for s in active_filters["storm_type"])
        filter_parts.append(f"Torm={storm_str}")
    if "return_period" in active_filters and active_filters["return_period"]:
        tr_str = ", ".join(str(tr) for tr in active_filters["return_period"])
        filter_parts.append(f"TR={tr_str}")
    if "x_factor" in active_filters and active_filters["x_factor"]:
        x_str = ", ".join(f"{x:.2f}" for x in active_filters["x_factor"])
        filter_parts.append(f"X={x_str}")

    if filter_parts:
        return f" [Filtro: {', '.join(filter_parts)}]"
    return ""
