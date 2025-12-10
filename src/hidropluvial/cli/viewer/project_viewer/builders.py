"""
Builders para tablas y display del visor de proyectos.
"""

from typing import Optional, Set, List

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.project import Project, Basin

from .state import ActivePanel, PopupMode
from .popups import (
    build_add_basin_popup,
    build_select_project_popup,
    build_select_basin_popup,
    build_edit_basin_popup,
    build_confirm_edit_params_popup,
)


def build_projects_table(
    projects: list[dict],
    selected_idx: int,
    marked_indices: Set[int] = None,
    is_active: bool = True,
    max_rows: int = 8,
) -> Table:
    """
    Construye tabla de proyectos con fila seleccionada destacada.
    """
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()

    # Calcular ventana visible
    n_projects = len(projects)
    if n_projects <= max_rows:
        start_idx = 0
        end_idx = n_projects
    else:
        half = max_rows // 2
        start_idx = selected_idx - half
        end_idx = start_idx + max_rows
        if start_idx < 0:
            start_idx = 0
            end_idx = max_rows
        elif end_idx > n_projects:
            end_idx = n_projects
            start_idx = end_idx - max_rows

    visible_projects = projects[start_idx:end_idx]
    selected_in_visible = selected_idx - start_idx
    visible_marked = {i - start_idx for i in marked_indices if start_idx <= i < end_idx}

    # Título con indicador de foco
    title_style = f"bold {p.primary}" if is_active else f"bold {p.muted}"
    focus_indicator = " ◆" if is_active else ""
    title = f"PROYECTOS ({selected_idx + 1}/{n_projects}){focus_indicator}"

    table = Table(
        title=title,
        title_style=title_style,
        border_style=p.border if is_active else p.muted,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("Nombre", justify="left", min_width=20)
    table.add_column("Cuencas", justify="right", width=8)
    table.add_column("Análisis", justify="right", width=9)
    table.add_column("Autor", justify="left", width=12)
    table.add_column("Ubicación", justify="left", width=12)

    for idx, proj in enumerate(visible_projects):
        real_idx = start_idx + idx
        is_selected = idx == selected_in_visible
        is_marked = idx in visible_marked

        mark = "x" if is_marked else ""

        # Valores
        name = proj.get("name", "")[:22]
        n_basins = proj.get("n_basins", 0)
        n_analyses = proj.get("total_analyses", 0)
        author = (proj.get("author") or "")[:12]
        location = (proj.get("location") or "")[:12]

        if is_selected and is_active:
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style=f"bold {p.marked} reverse" if is_marked else row_style)
            idx_text = Text(f">{real_idx}", style=row_style)
            name_text = Text(name, style=row_style)
            basins_text = Text(str(n_basins), style=row_style)
            analyses_text = Text(str(n_analyses), style=row_style)
            author_text = Text(author, style=row_style)
            location_text = Text(location, style=row_style)
        elif is_marked:
            mark_text = Text(mark, style=f"bold {p.marked}")
            idx_text = Text(str(real_idx), style=p.marked)
            name_text = Text(name, style=p.marked)
            basins_text = Text(str(n_basins), style=p.marked)
            analyses_text = Text(str(n_analyses), style=p.marked)
            author_text = Text(author, style=p.marked)
            location_text = Text(location, style=p.marked)
        elif is_selected and not is_active:
            # Seleccionado pero panel inactivo
            mark_text = Text(mark)
            idx_text = Text(f">{real_idx}", style=f"bold {p.muted}")
            name_text = Text(name, style="bold")
            basins_text = Text(str(n_basins), style=p.number if n_basins > 0 else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)
            author_text = Text(author, style=p.muted)
            location_text = Text(location, style=p.muted)
        else:
            mark_text = Text(mark)
            idx_text = Text(str(real_idx), style=p.muted)
            name_text = Text(name)
            basins_text = Text(str(n_basins), style=p.number if n_basins > 0 else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)
            author_text = Text(author, style=p.muted)
            location_text = Text(location, style=p.muted)

        table.add_row(
            mark_text, idx_text, name_text,
            basins_text, analyses_text, author_text, location_text,
        )

    # Indicador de más elementos
    if n_projects > max_rows:
        if start_idx > 0:
            table.caption = f"↑ {start_idx} más arriba"
        if end_idx < n_projects:
            remaining = n_projects - end_idx
            if table.caption:
                table.caption += f"  |  ↓ {remaining} más abajo"
            else:
                table.caption = f"↓ {remaining} más abajo"
        table.caption_style = p.muted

    return table


def build_basins_table(
    basins: List[Basin],
    selected_idx: int,
    marked_indices: Set[int] = None,
    project_name: str = "",
    is_active: bool = False,
    max_rows: int = 6,
) -> Table:
    """
    Construye tabla de cuencas con mismo estilo que proyectos.

    Muestra solo datos físicos de la cuenca (sin C, CN, Tc que son parte de análisis).
    """
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()
    n_basins = len(basins)

    # Calcular ventana visible
    if n_basins <= max_rows:
        start_idx = 0
        end_idx = n_basins
    else:
        half = max_rows // 2
        start_idx = selected_idx - half
        end_idx = start_idx + max_rows
        if start_idx < 0:
            start_idx = 0
            end_idx = max_rows
        elif end_idx > n_basins:
            end_idx = n_basins
            start_idx = end_idx - max_rows

    visible_basins = basins[start_idx:end_idx] if basins else []
    selected_in_visible = selected_idx - start_idx if basins else 0
    visible_marked = {i - start_idx for i in marked_indices if start_idx <= i < end_idx}

    # Título con indicador de foco
    title_style = f"bold {p.primary}" if is_active else f"bold {p.muted}"
    focus_indicator = " ◆" if is_active else ""
    if n_basins > 0:
        title = f"CUENCAS: {project_name} ({selected_idx + 1}/{n_basins}){focus_indicator}"
    else:
        title = f"CUENCAS: {project_name} (0){focus_indicator}"

    table = Table(
        title=title,
        title_style=title_style,
        border_style=p.border if is_active else p.muted,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas - solo datos físicos de la cuenca
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("Nombre", justify="left", min_width=20)
    table.add_column("Área (ha)", justify="right", width=10)
    table.add_column("Pend (%)", justify="right", width=9)
    table.add_column("Long (m)", justify="right", width=9)
    table.add_column("Análisis", justify="right", width=9)

    if not basins:
        table.add_row(
            "", "", Text("(sin cuencas)", style=f"italic {p.muted}"),
            "", "", "", ""
        )
        return table

    for idx, basin in enumerate(visible_basins):
        real_idx = start_idx + idx
        is_selected = idx == selected_in_visible
        is_marked = idx in visible_marked

        mark = "x" if is_marked else ""

        # Valores - solo datos físicos
        name = basin.name[:22] if len(basin.name) > 22 else basin.name
        area = f"{basin.area_ha:.2f}" if basin.area_ha else "-"
        slope = f"{basin.slope_pct:.2f}" if basin.slope_pct else "-"
        length = f"{basin.length_m:.0f}" if basin.length_m else "-"
        n_analyses = len(basin.analyses) if basin.analyses else 0

        if is_selected and is_active:
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style=f"bold {p.marked} reverse" if is_marked else row_style)
            idx_text = Text(f">{real_idx}", style=row_style)
            name_text = Text(name, style=row_style)
            area_text = Text(area, style=row_style)
            slope_text = Text(slope, style=row_style)
            length_text = Text(length, style=row_style)
            analyses_text = Text(str(n_analyses), style=row_style)
        elif is_marked:
            mark_text = Text(mark, style=f"bold {p.marked}")
            idx_text = Text(str(real_idx), style=p.marked)
            name_text = Text(name, style=p.marked)
            area_text = Text(area, style=p.marked)
            slope_text = Text(slope, style=p.marked)
            length_text = Text(length, style=p.marked)
            analyses_text = Text(str(n_analyses), style=p.marked)
        elif is_selected and not is_active:
            mark_text = Text(mark)
            idx_text = Text(f">{real_idx}", style=f"bold {p.muted}")
            name_text = Text(name, style="bold")
            area_text = Text(area, style=p.number)
            slope_text = Text(slope, style=p.number)
            length_text = Text(length, style=p.number if length != "-" else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)
        else:
            mark_text = Text(mark)
            idx_text = Text(str(real_idx), style=p.muted)
            name_text = Text(name)
            area_text = Text(area, style=p.number)
            slope_text = Text(slope, style=p.number)
            length_text = Text(length, style=p.number if length != "-" else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)

        table.add_row(
            mark_text, idx_text, name_text,
            area_text, slope_text, length_text, analyses_text,
        )

    # Indicador de más elementos
    if n_basins > max_rows:
        if start_idx > 0:
            table.caption = f"↑ {start_idx} más arriba"
        if end_idx < n_basins:
            remaining = n_basins - end_idx
            if table.caption:
                table.caption += f"  |  ↓ {remaining} más abajo"
            else:
                table.caption = f"↓ {remaining} más abajo"
        table.caption_style = p.muted

    return table


def build_nav_bar(
    active_panel: ActivePanel,
    confirm_delete: bool = False,
    delete_count: int = 0,
    has_basins: bool = False,
) -> Text:
    """Construye la barra de navegación según el panel activo."""
    p = get_palette()
    nav = Text()

    if confirm_delete:
        entity = "proyecto(s)" if active_panel == ActivePanel.PROJECTS else "cuenca(s)"
        nav.append(f"  Eliminar {delete_count} {entity}? ", style=f"bold {p.warning}")
        nav.append("[", style=p.muted)
        nav.append("s/y", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("n/Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)
        return nav

    # Tab para cambiar panel
    nav.append("  [", style=p.muted)
    nav.append("Tab", style=f"bold {p.accent}")
    nav.append("] Cambiar panel  ", style=p.muted)

    # Navegación común
    nav.append("[", style=p.muted)
    nav.append("↑↓", style=f"bold {p.primary}")
    nav.append("] Navegar  ", style=p.muted)

    if active_panel == ActivePanel.PROJECTS:
        # Opciones para proyectos
        nav.append("[", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Cuencas  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Espacio", style=f"bold {p.primary}")
        nav.append("] Marcar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("e", style=f"bold {p.primary}")
        nav.append("] Editar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("n", style=f"bold {p.primary}")
        nav.append("] Nuevo  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("d", style=f"bold {p.primary}")
        nav.append("] Eliminar  ", style=p.muted)
    else:
        # Opciones para cuencas
        if has_basins:
            nav.append("[", style=p.muted)
            nav.append("Enter", style=f"bold {p.nav_confirm}")
            nav.append("] Análisis  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("Espacio", style=f"bold {p.primary}")
            nav.append("] Marcar  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("e", style=f"bold {p.primary}")
            nav.append("] Editar  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("d", style=f"bold {p.primary}")
            nav.append("] Eliminar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("n", style=f"bold {p.primary}")
        nav.append("] Nueva  ", style=p.muted)

    nav.append("[", style=p.muted)
    nav.append("q", style=f"bold {p.nav_cancel}")
    nav.append("] Salir", style=p.muted)

    return nav


def build_unified_display(
    projects: list[dict],
    project_idx: int,
    project_marked: Set[int],
    selected_project: Optional[Project],
    basin_idx: int,
    basin_marked: Set[int],
    active_panel: ActivePanel,
    confirm_delete: bool = False,
    delete_count: int = 0,
    popup_mode: PopupMode = PopupMode.NONE,
    popup_idx: int = 0,
    import_source_project: Optional[Project] = None,
) -> Group:
    """Construye el display unificado con dos paneles."""
    from rich.columns import Columns

    p = get_palette()
    has_popup = popup_mode != PopupMode.NONE

    # Tabla de proyectos
    projects_table = build_projects_table(
        projects,
        project_idx,
        project_marked,
        is_active=(active_panel == ActivePanel.PROJECTS) and not has_popup,
        max_rows=8,
    )

    # Tabla de cuencas
    basins = selected_project.basins if selected_project else []
    project_name = projects[project_idx].get("name", "") if projects else ""
    basins_table = build_basins_table(
        basins,
        basin_idx,
        basin_marked,
        project_name=project_name,
        is_active=(active_panel == ActivePanel.BASINS) and not has_popup,
        max_rows=6,
    )

    # Construir popup según el modo
    if popup_mode == PopupMode.ADD_BASIN:
        popup = build_add_basin_popup(popup_idx)
        basins_with_popup = Columns([basins_table, popup], equal=False, expand=True)
        nav = Text("  [n] Nueva  [i] Importar  [↑↓] Navegar  [Enter] OK  [Esc] Cancelar", style=p.muted)
        return Group(
            Text(""),
            projects_table,
            Text(""),
            basins_with_popup,
            Text(""),
            nav,
        )

    elif popup_mode == PopupMode.SELECT_PROJECT:
        current_id = selected_project.id if selected_project else ""
        popup = build_select_project_popup(projects, current_id, popup_idx)
        basins_with_popup = Columns([basins_table, popup], equal=False, expand=True)
        nav = Text("  [↑↓] Navegar  [Enter] Seleccionar  [Esc] Volver", style=p.muted)
        return Group(
            Text(""),
            projects_table,
            Text(""),
            basins_with_popup,
            Text(""),
            nav,
        )

    elif popup_mode == PopupMode.SELECT_BASIN:
        source_basins = import_source_project.basins if import_source_project else []
        source_name = import_source_project.name if import_source_project else ""
        popup = build_select_basin_popup(source_basins, source_name, popup_idx)
        basins_with_popup = Columns([basins_table, popup], equal=False, expand=True)
        nav = Text("  [↑↓] Navegar  [Enter] Importar  [Esc] Volver", style=p.muted)
        return Group(
            Text(""),
            projects_table,
            Text(""),
            basins_with_popup,
            Text(""),
            nav,
        )

    elif popup_mode == PopupMode.EDIT_BASIN:
        # Popup para editar cuenca seleccionada
        selected_basin = basins[basin_idx] if basins and basin_idx < len(basins) else None
        if selected_basin:
            basin_name = selected_basin.name
            n_analyses = len(selected_basin.analyses) if selected_basin.analyses else 0
        else:
            basin_name = ""
            n_analyses = 0
        popup = build_edit_basin_popup(basin_name, n_analyses, popup_idx)
        basins_with_popup = Columns([basins_table, popup], equal=False, expand=True)
        nav = Text("  [m] Metadatos  [p] Parámetros  [↑↓] Navegar  [Enter] OK  [Esc] Cancelar", style=p.muted)
        return Group(
            Text(""),
            projects_table,
            Text(""),
            basins_with_popup,
            Text(""),
            nav,
        )

    elif popup_mode == PopupMode.CONFIRM_EDIT_PARAMS:
        # Popup de confirmación amarillo para editar parámetros
        selected_basin = basins[basin_idx] if basins and basin_idx < len(basins) else None
        if selected_basin:
            basin_name = selected_basin.name
            n_analyses = len(selected_basin.analyses) if selected_basin.analyses else 0
        else:
            basin_name = ""
            n_analyses = 0
        popup = build_confirm_edit_params_popup(basin_name, n_analyses)
        basins_with_popup = Columns([basins_table, popup], equal=False, expand=True)
        nav = Text("  [s/y] Continuar  [n/Esc] Cancelar", style=p.muted)
        return Group(
            Text(""),
            projects_table,
            Text(""),
            basins_with_popup,
            Text(""),
            nav,
        )

    # Barra de navegación normal
    nav = build_nav_bar(
        active_panel,
        confirm_delete,
        delete_count,
        has_basins=len(basins) > 0,
    )

    return Group(
        Text(""),
        projects_table,
        Text(""),
        basins_table,
        Text(""),
        nav,
    )
