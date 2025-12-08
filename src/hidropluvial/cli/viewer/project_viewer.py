"""
Visor interactivo de proyectos.

Permite navegar entre proyectos usando:
- Flechas arriba/abajo: cambiar proyecto seleccionado
- Espacio: marcar/desmarcar para eliminacion multiple
- i: invertir seleccion
- d: eliminar marcados (o actual si no hay marcados)
- e: editar nombre/metadatos del proyecto
- Enter: ver cuencas del proyecto
- n: crear nuevo proyecto
- q/ESC: salir
"""

from typing import Callable, Optional, Set

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from rich import box

from hidropluvial.cli.theme import get_palette
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.project import ProjectManager


def build_projects_table(
    projects: list[dict],
    selected_idx: int,
    marked_indices: Set[int] = None,
) -> Table:
    """
    Construye tabla de proyectos con fila seleccionada destacada.
    """
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()

    table = Table(
        title="PROYECTOS",
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas
    table.add_column("", justify="center", width=1)  # Marca
    table.add_column("#", justify="right", width=3)
    table.add_column("ID", justify="left", width=8)
    table.add_column("Nombre", justify="left", min_width=20)
    table.add_column("Cuencas", justify="right", width=8)
    table.add_column("Analisis", justify="right", width=9)
    table.add_column("Autor", justify="left", width=15)
    table.add_column("Ubicacion", justify="left", width=15)

    for idx, proj in enumerate(projects):
        is_selected = idx == selected_idx
        is_marked = idx in marked_indices

        # Marca de seleccion
        mark = "x" if is_marked else ""

        # Valores
        proj_id = proj.get("id", "")[:8]
        name = proj.get("name", "")[:25]
        n_basins = proj.get("n_basins", 0)
        n_analyses = proj.get("total_analyses", 0)
        author = (proj.get("author") or "")[:15]
        location = (proj.get("location") or "")[:15]

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            mark_text = Text(mark, style="bold red reverse" if is_marked else row_style)
            idx_text = Text(f">{idx}", style=row_style)
            id_text = Text(proj_id, style=row_style)
            name_text = Text(name, style=row_style)
            basins_text = Text(str(n_basins), style=row_style)
            analyses_text = Text(str(n_analyses), style=row_style)
            author_text = Text(author, style=row_style)
            location_text = Text(location, style=row_style)
        elif is_marked:
            mark_text = Text(mark, style="bold red")
            idx_text = Text(str(idx), style="red")
            id_text = Text(proj_id, style="red")
            name_text = Text(name, style="red")
            basins_text = Text(str(n_basins), style="red")
            analyses_text = Text(str(n_analyses), style="red")
            author_text = Text(author, style="red")
            location_text = Text(location, style="red")
        else:
            mark_text = Text(mark)
            idx_text = Text(str(idx), style=p.muted)
            id_text = Text(proj_id, style=p.muted)
            name_text = Text(name)
            basins_text = Text(str(n_basins), style=p.number if n_basins > 0 else p.muted)
            analyses_text = Text(str(n_analyses), style=p.number if n_analyses > 0 else p.muted)
            author_text = Text(author, style=p.muted)
            location_text = Text(location, style=p.muted)

        table.add_row(
            mark_text, idx_text, id_text, name_text,
            basins_text, analyses_text, author_text, location_text,
        )

    return table


def build_projects_display(
    projects: list[dict],
    current_idx: int,
    max_visible_rows: int,
    marked_indices: Set[int] = None,
    confirm_delete: bool = False,
    delete_count: int = 0,
) -> Group:
    """Construye el display completo para Live update."""
    if marked_indices is None:
        marked_indices = set()

    p = get_palette()
    n_projects = len(projects)

    # Calcular ventana visible
    if n_projects <= max_visible_rows:
        start_idx = 0
        end_idx = n_projects
    else:
        half = max_visible_rows // 2
        start_idx = current_idx - half
        end_idx = start_idx + max_visible_rows

        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible_rows
        elif end_idx > n_projects:
            end_idx = n_projects
            start_idx = end_idx - max_visible_rows

    visible_projects = projects[start_idx:end_idx]
    selected_in_visible = current_idx - start_idx

    # Ajustar marked_indices para la vista
    visible_marked = {i - start_idx for i in marked_indices if start_idx <= i < end_idx}

    # Encabezado
    header_text = Text()
    header_text.append(f"  Proyectos ", style=f"bold {p.secondary}")
    header_text.append(f"({current_idx + 1}/{n_projects})", style=p.muted)
    if n_projects > max_visible_rows:
        header_text.append(f" [mostrando {start_idx + 1}-{end_idx}]", style=f"dim {p.muted}")
    if marked_indices:
        header_text.append(f" [{len(marked_indices)} marcados]", style="bold red")

    # Tabla
    table = build_projects_table(visible_projects, selected_in_visible, visible_marked)

    # Info del seleccionado
    proj = projects[current_idx]
    info_text = Text()
    info_text.append("  Seleccionado: ", style=p.muted)
    info_text.append(f"[{current_idx}] ", style=f"bold {p.primary}")
    info_text.append(f"{proj.get('name', '')} ", style="bold")
    info_text.append(f"({proj.get('n_basins', 0)} cuencas, {proj.get('total_analyses', 0)} analisis)")
    if proj.get("description"):
        desc_preview = proj["description"][:40] + "..." if len(proj["description"]) > 40 else proj["description"]
        info_text.append(f" - {desc_preview}", style=f"italic {p.muted}")

    # Navegacion
    nav_text = Text()
    if confirm_delete:
        nav_text.append(f"  Eliminar {delete_count} proyecto(s)? ", style=f"bold {p.accent}")
        nav_text.append("[", style=p.muted)
        nav_text.append("s/y", style="bold green")
        nav_text.append("] Confirmar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n/Esc", style="bold red")
        nav_text.append("] Cancelar", style=p.muted)
    else:
        nav_text.append("  [", style=p.muted)
        nav_text.append("^^v", style=f"bold {p.primary}")
        nav_text.append("] Navegar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("Espacio", style=f"bold {p.primary}")
        nav_text.append("] Marcar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("d", style=f"bold {p.primary}")
        nav_text.append("] Eliminar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("e", style=f"bold {p.primary}")
        nav_text.append("] Editar  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("n", style=f"bold {p.primary}")
        nav_text.append("] Nuevo  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("Enter", style=f"bold {p.primary}")
        nav_text.append("] Cuencas  ", style=p.muted)
        nav_text.append("[", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Salir", style=p.muted)

    return Group(
        Text(""),
        header_text,
        Text(""),
        table,
        Text(""),
        info_text,
        nav_text,
    )


def interactive_project_viewer(
    project_manager: ProjectManager,
    max_visible_rows: int = 20,
) -> None:
    """
    Visor interactivo de proyectos.

    Navegacion:
    - Flechas arriba/abajo: cambiar proyecto seleccionado
    - Espacio: marcar/desmarcar para eliminacion
    - i: invertir seleccion
    - d: eliminar marcados (o actual si no hay marcados)
    - e: editar nombre/metadatos del proyecto
    - Enter: ver cuencas del proyecto
    - n: crear nuevo proyecto
    - q/ESC: salir
    """
    console = Console()
    p = get_palette()

    projects = project_manager.list_projects()
    if not projects:
        console.print("\n  No hay proyectos.\n", style="yellow")
        return

    current_idx = 0
    pending_delete = False
    marked_indices: Set[int] = set()

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_projects_display(
            projects, current_idx, max_visible_rows,
            marked_indices=marked_indices,
        )
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_projects = len(projects)

            if n_projects == 0:
                live.update(Text("\n  No quedan proyectos. Presiona q para salir.\n", style="yellow"), refresh=True)
                if key in ('q', 'esc'):
                    break
                continue

            # Modo confirmacion de eliminacion
            if pending_delete:
                if key in ('s', 'y'):
                    # Confirmar eliminacion
                    indices_to_delete = sorted(marked_indices if marked_indices else [current_idx], reverse=True)

                    for idx in indices_to_delete:
                        if idx < len(projects):
                            proj_id = projects[idx]["id"]
                            project_manager.delete_project(proj_id)

                    # Recargar lista
                    projects = project_manager.list_projects()
                    marked_indices.clear()
                    n_projects = len(projects)
                    if current_idx >= n_projects:
                        current_idx = max(0, n_projects - 1)
                    pending_delete = False

                elif key in ('n', 'esc'):
                    pending_delete = False
                else:
                    continue
            else:
                # Navegacion normal
                if key in ('q', 'esc'):
                    break
                elif key == 'up':
                    current_idx = (current_idx - 1) % n_projects
                elif key == 'down':
                    current_idx = (current_idx + 1) % n_projects
                elif key == 'space':
                    if current_idx in marked_indices:
                        marked_indices.remove(current_idx)
                    else:
                        marked_indices.add(current_idx)
                elif key == 'i':
                    all_indices = set(range(n_projects))
                    marked_indices = all_indices - marked_indices
                elif key == 'd':
                    pending_delete = True
                elif key == 'e':
                    # Editar proyecto
                    live.stop()
                    proj = projects[current_idx]
                    _edit_project(project_manager, proj["id"])
                    projects = project_manager.list_projects()
                    clear_screen()
                    live.start()
                elif key == 'n':
                    # Nuevo proyecto
                    live.stop()
                    _create_new_project(project_manager)
                    projects = project_manager.list_projects()
                    clear_screen()
                    live.start()
                elif key == 'enter':
                    # Ver cuencas del proyecto
                    live.stop()
                    proj = projects[current_idx]
                    _view_project_basins(project_manager, proj["id"])
                    projects = project_manager.list_projects()
                    clear_screen()
                    live.start()
                else:
                    continue

            # Ajustar indice si esta fuera de rango
            if n_projects > 0 and current_idx >= n_projects:
                current_idx = n_projects - 1

            delete_count = len(marked_indices) if marked_indices else 1

            display = build_projects_display(
                projects, current_idx, max_visible_rows,
                marked_indices=marked_indices,
                confirm_delete=pending_delete,
                delete_count=delete_count,
            )
            live.update(display, refresh=True)

    clear_screen()


def _edit_project(project_manager: ProjectManager, project_id: str) -> None:
    """Edita metadatos de un proyecto."""
    import questionary
    from hidropluvial.cli.wizard.styles import get_text_kwargs

    clear_screen()
    project = project_manager.get_project(project_id)
    if not project:
        print("\n  Proyecto no encontrado.\n")
        return

    print(f"\n  Editando proyecto: {project.name}\n")

    new_name = questionary.text(
        "Nombre:",
        default=project.name,
        **get_text_kwargs(),
    ).ask()

    if new_name and new_name != project.name:
        project.name = new_name

    new_desc = questionary.text(
        "Descripcion:",
        default=project.description or "",
        **get_text_kwargs(),
    ).ask()

    if new_desc is not None:
        project.description = new_desc

    new_author = questionary.text(
        "Autor:",
        default=project.author or "",
        **get_text_kwargs(),
    ).ask()

    if new_author is not None:
        project.author = new_author

    new_location = questionary.text(
        "Ubicacion:",
        default=project.location or "",
        **get_text_kwargs(),
    ).ask()

    if new_location is not None:
        project.location = new_location

    project_manager.save_project(project)
    print("\n  Proyecto actualizado.\n")
    questionary.press_any_key_to_continue("Presiona cualquier tecla...").ask()


def _create_new_project(project_manager: ProjectManager) -> None:
    """Crea un nuevo proyecto."""
    import questionary
    from hidropluvial.cli.wizard.styles import get_text_kwargs

    clear_screen()
    print("\n  Crear nuevo proyecto\n")

    name = questionary.text(
        "Nombre del proyecto:",
        validate=lambda x: len(x.strip()) > 0 or "El nombre no puede estar vacio",
        **get_text_kwargs(),
    ).ask()

    if not name:
        return

    description = questionary.text(
        "Descripcion (opcional):",
        default="",
        **get_text_kwargs(),
    ).ask() or ""

    author = questionary.text(
        "Autor (opcional):",
        default="",
        **get_text_kwargs(),
    ).ask() or ""

    location = questionary.text(
        "Ubicacion (opcional):",
        default="",
        **get_text_kwargs(),
    ).ask() or ""

    project = project_manager.create_project(
        name=name,
        description=description,
        author=author,
        location=location,
    )

    print(f"\n  Proyecto creado: {project.name} [{project.id}]\n")
    questionary.press_any_key_to_continue("Presiona cualquier tecla...").ask()


def _view_project_basins(project_manager: ProjectManager, project_id: str) -> None:
    """Muestra visor de cuencas del proyecto."""
    from hidropluvial.cli.viewer.basin_viewer import interactive_basin_viewer

    project = project_manager.get_project(project_id)
    if not project:
        print("\n  Proyecto no encontrado.\n")
        return

    interactive_basin_viewer(project_manager, project)
