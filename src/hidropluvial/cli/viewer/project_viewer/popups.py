"""
Builders de popups para el visor de proyectos.
"""

from typing import List

from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.project import Basin


def build_add_basin_popup(popup_idx: int = 0) -> Table:
    """Construye el popup para agregar cuenca."""
    p = get_palette()

    options = [
        {"key": "n", "label": "Nueva cuenca", "hint": "Configurar desde cero"},
        {"key": "i", "label": "Importar cuenca", "hint": "Desde otro proyecto"},
    ]

    table = Table(
        title="Agregar Cuenca",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)   # Marcador
    table.add_column("", width=5)   # Shortcut
    table.add_column("", width=20)  # Label
    table.add_column("", width=25)  # Hint

    for idx, opt in enumerate(options):
        is_selected = idx == popup_idx
        key = opt["key"]
        label = opt["label"]
        hint = opt["hint"]

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            key_text = Text(f"[{key}]", style=row_style)
            label_text = Text(label, style=row_style)
            hint_text = Text(hint, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            key_text = Text(f"[{key}]", style=f"bold {p.accent}")
            label_text = Text(label, style="")
            hint_text = Text(hint, style=p.muted)

        table.add_row(marker, key_text, label_text, hint_text)

    # Fila de navegación
    table.add_row(
        Text("", style=p.muted),
        Text("", style=p.muted),
        Text("[↑↓] Navegar  [Enter] OK  [Esc] Cancelar", style=p.muted),
        Text("", style=p.muted),
    )

    return table


def build_select_project_popup(
    projects: List[dict],
    current_project_id: str,
    popup_idx: int = 0,
    max_visible: int = 6,
) -> Table:
    """Construye el popup para seleccionar proyecto de origen."""
    p = get_palette()

    # Filtrar proyectos (excluir el actual y los sin cuencas)
    available = get_importable_projects(projects, current_project_id)

    if not available:
        table = Table(
            title="Importar Cuenca",
            title_style=f"bold {p.accent}",
            border_style=p.accent,
            box=box.DOUBLE,
            show_header=False,
            padding=(0, 1),
        )
        table.add_column("", width=50)
        table.add_row(Text("No hay otros proyectos con cuencas", style=p.warning))
        table.add_row(Text("[Esc] Volver", style=p.muted))
        return table

    # Calcular ventana visible
    n_items = len(available)
    if n_items <= max_visible:
        start_idx = 0
        end_idx = n_items
    else:
        half = max_visible // 2
        start_idx = popup_idx - half
        end_idx = start_idx + max_visible
        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible
        elif end_idx > n_items:
            end_idx = n_items
            start_idx = end_idx - max_visible

    visible = available[start_idx:end_idx]
    selected_in_visible = popup_idx - start_idx

    table = Table(
        title=f"Seleccionar Proyecto ({popup_idx + 1}/{n_items})",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)   # Marcador
    table.add_column("", width=25)  # Nombre
    table.add_column("", width=15)  # Cuencas

    for idx, proj in enumerate(visible):
        is_selected = idx == selected_in_visible
        name = proj["name"]
        n_basins = proj["n_basins"]

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            name_text = Text(name[:22], style=row_style)
            count_text = Text(f"{n_basins} cuencas", style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            name_text = Text(name[:22], style="")
            count_text = Text(f"{n_basins} cuencas", style=p.muted)

        table.add_row(marker, name_text, count_text)

    # Indicador de scroll
    scroll_hint = ""
    if start_idx > 0:
        scroll_hint += "↑ "
    if end_idx < n_items:
        scroll_hint += "↓"

    table.add_row(
        Text("", style=p.muted),
        Text(f"[↑↓] Navegar  [Enter] OK  [Esc] Volver {scroll_hint}", style=p.muted),
        Text("", style=p.muted),
    )

    return table


def build_select_basin_popup(
    basins: List[Basin],
    source_project_name: str,
    popup_idx: int = 0,
    max_visible: int = 6,
) -> Table:
    """Construye el popup para seleccionar cuenca a importar."""
    p = get_palette()

    if not basins:
        table = Table(
            title="Seleccionar Cuenca",
            title_style=f"bold {p.accent}",
            border_style=p.accent,
            box=box.DOUBLE,
            show_header=False,
            padding=(0, 1),
        )
        table.add_column("", width=50)
        table.add_row(Text("El proyecto no tiene cuencas", style=p.warning))
        table.add_row(Text("[Esc] Volver", style=p.muted))
        return table

    # Calcular ventana visible
    n_items = len(basins)
    if n_items <= max_visible:
        start_idx = 0
        end_idx = n_items
    else:
        half = max_visible // 2
        start_idx = popup_idx - half
        end_idx = start_idx + max_visible
        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible
        elif end_idx > n_items:
            end_idx = n_items
            start_idx = end_idx - max_visible

    visible = basins[start_idx:end_idx]
    selected_in_visible = popup_idx - start_idx

    table = Table(
        title=f"Cuencas de: {source_project_name[:20]}",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)   # Marcador
    table.add_column("", width=22)  # Nombre
    table.add_column("", width=10)  # Área
    table.add_column("", width=12)  # Análisis

    for idx, basin in enumerate(visible):
        is_selected = idx == selected_in_visible
        name = basin.name[:20]
        area = f"{basin.area_ha:.1f} ha"
        n_analyses = len(basin.analyses) if basin.analyses else 0
        analyses_str = f"{n_analyses} análisis"

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            name_text = Text(name, style=row_style)
            area_text = Text(area, style=row_style)
            analyses_text = Text(analyses_str, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            name_text = Text(name, style="")
            area_text = Text(area, style=p.muted)
            analyses_text = Text(analyses_str, style=p.muted)

        table.add_row(marker, name_text, area_text, analyses_text)

    # Indicador de scroll
    scroll_hint = ""
    if start_idx > 0:
        scroll_hint += "↑ "
    if end_idx < n_items:
        scroll_hint += "↓"

    table.add_row(
        Text("", style=p.muted),
        Text(f"[↑↓] Nav  [Enter] Importar  [Esc] Volver {scroll_hint}", style=p.muted),
        Text("", style=p.muted),
        Text("", style=p.muted),
    )

    return table


def get_importable_projects(projects: List[dict], current_project_id: str) -> List[dict]:
    """Retorna proyectos disponibles para importar (excluyendo actual y sin cuencas)."""
    return [
        proj for proj in projects
        if proj["id"] != current_project_id and proj["n_basins"] > 0
    ]


def build_confirm_edit_params_popup(basin_name: str, n_analyses: int) -> Table:
    """Construye el popup de confirmación para editar parámetros (alerta amarilla)."""
    p = get_palette()

    table = Table(
        title="⚠ Advertencia",
        title_style=f"bold {p.warning}",
        border_style=p.warning,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=50)

    table.add_row(Text(f"Cuenca: {basin_name[:30]}", style="bold"))
    table.add_row(Text(""))
    table.add_row(Text(
        f"Se eliminarán {n_analyses} análisis existentes",
        style=f"bold {p.warning}"
    ))
    table.add_row(Text("al modificar los parámetros físicos.", style=p.warning))
    table.add_row(Text(""))
    table.add_row(Text(
        "[s/y] Continuar    [n/Esc] Cancelar",
        style=p.muted
    ))

    return table


def build_edit_basin_popup(basin_name: str, n_analyses: int, popup_idx: int = 0) -> Table:
    """Construye el popup para editar cuenca."""
    p = get_palette()

    options = [
        {
            "key": "m",
            "label": "Editar metadatos",
            "hint": "Nombre, notas (no afecta análisis)",
        },
        {
            "key": "p",
            "label": "Editar parámetros",
            "hint": f"Área, pendiente... (elimina {n_analyses} análisis)" if n_analyses > 0 else "Área, pendiente, P3,10...",
        },
    ]

    table = Table(
        title=f"Editar: {basin_name[:20]}",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)   # Marcador
    table.add_column("", width=5)   # Shortcut
    table.add_column("", width=20)  # Label
    table.add_column("", width=30)  # Hint

    for idx, opt in enumerate(options):
        is_selected = idx == popup_idx
        key = opt["key"]
        label = opt["label"]
        hint = opt["hint"]

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            key_text = Text(f"[{key}]", style=row_style)
            label_text = Text(label, style=row_style)
            hint_text = Text(hint, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            key_text = Text(f"[{key}]", style=f"bold {p.accent}")
            label_text = Text(label, style="")
            hint_text = Text(hint, style=p.muted)

        table.add_row(marker, key_text, label_text, hint_text)

    # Fila de navegación
    table.add_row(
        Text("", style=p.muted),
        Text("", style=p.muted),
        Text("[↑↓] Navegar  [Enter] OK  [Esc] Cancelar", style=p.muted),
        Text("", style=p.muted),
    )

    return table
