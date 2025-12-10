"""
Punto de entrada principal del wizard.

Usa imports diferidos para mejorar tiempo de inicio.
"""

from typing import Optional, TYPE_CHECKING

import typer

# Imports diferidos - solo para type hints
if TYPE_CHECKING:
    from hidropluvial.project import Project


def _build_banner_panel():
    """Construye el panel del banner para mostrar en el menú."""
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from hidropluvial.cli.theme import get_palette

    p = get_palette()

    # ASCII art logo estilizado
    logo = r"""
   ╦ ╦╦╔╦╗╦═╗╔═╗╔═╗╦  ╦ ╦╦  ╦╦╔═╗╦
   ╠═╣║ ║║╠╦╝║ ║╠═╝║  ║ ║╚╗╔╝║╠═╣║
   ╩ ╩╩═╩╝╩╚═╚═╝╩  ╩═╝╚═╝ ╚╝ ╩╩ ╩╩═╝
"""

    # Contenido del banner
    content = Text()
    content.append(logo, style=f"bold {p.primary}")
    content.append("\n")
    content.append("      ≋≋≋  ", style=f"{p.accent}")
    content.append("Cálculos Hidrológicos", style=f"bold {p.secondary}")
    content.append("  ≋≋≋\n", style=f"{p.accent}")
    content.append("              Uruguay", style=p.muted)

    # Panel con diseño mejorado
    return Panel(
        content,
        border_style=p.primary,
        box=box.DOUBLE,
        padding=(0, 2),
        width=52,
    )


def wizard_main() -> None:
    """
    Asistente interactivo para crear analisis hidrologicos.
    """
    from hidropluvial.cli.theme import print_info
    from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem

    # Construir banner para mostrar con el menú
    banner = _build_banner_panel()

    while True:
        # Menu principal simplificado
        items = [
            MenuItem(
                key="e",
                label="Entrar",
                value="enter",
                hint="Gestionar proyectos y cuencas"
            ),
            MenuItem(key="separator1", label="", separator=True),
            MenuItem(
                key="c",
                label="Configuración",
                value="settings",
                hint="Ajustes de la herramienta"
            ),
            MenuItem(key="q", label="Salir", value="exit"),
        ]

        choice = menu_panel(
            title="Menú Principal",
            items=items,
            info_panel=banner,
            allow_back=False,
        )

        if choice is None or choice == "exit":
            print_info("Hasta pronto!")
            raise typer.Exit()

        try:
            if choice == "enter":
                _enter_tool()
            elif choice == "settings":
                _settings_menu()
        except SystemExit:
            # Capturar typer.Exit para volver al menu principal
            pass


def _enter_tool() -> None:
    """Entrada principal a la herramienta - visor de proyectos."""
    from hidropluvial.cli.viewer.project_viewer import interactive_project_viewer
    from hidropluvial.cli.viewer.panel_input import panel_confirm
    from hidropluvial.cli.theme import print_info
    from hidropluvial.project import get_project_manager

    project_manager = get_project_manager()
    projects = project_manager.list_projects()

    if not projects:
        # No hay proyectos - ofrecer crear uno
        print_info("\n  No hay proyectos guardados.")

        create = panel_confirm(
            title="¿Crear un nuevo proyecto?",
            default=True,
        )

        if create:
            project = _create_project_quick()
            if project:
                # Entrar al visor con el nuevo proyecto
                interactive_project_viewer(project_manager)
        return

    interactive_project_viewer(project_manager)


def _settings_menu() -> None:
    """Menú de configuración (placeholder para desarrollo futuro)."""
    from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
    from hidropluvial.cli.theme import print_info

    items = [
        MenuItem(
            key="u",
            label="Unidades",
            value="units",
            hint="Sistema métrico / imperial (próximamente)"
        ),
        MenuItem(
            key="t",
            label="Tema",
            value="theme",
            hint="Colores de la interfaz (próximamente)"
        ),
        MenuItem(key="separator1", label="", separator=True),
        MenuItem(
            key="i",
            label="Información",
            value="info",
            hint="Versión y créditos"
        ),
    ]

    choice = menu_panel(
        title="Configuración",
        items=items,
        allow_back=True,
    )

    if choice == "units":
        print_info("Configuración de unidades - próximamente")
    elif choice == "theme":
        print_info("Configuración de tema - próximamente")
    elif choice == "info":
        _show_info()


def _show_info() -> None:
    """Muestra información sobre la herramienta."""
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from hidropluvial.cli.theme import get_console, get_palette

    console = get_console()
    p = get_palette()

    info = Text()
    info.append("HidroPluvial\n", style=f"bold {p.primary}")
    info.append("Herramienta de Cálculos Hidrológicos\n\n", style=p.secondary)
    info.append("Versión: ", style=p.label)
    info.append("1.0.0\n", style=p.number)
    info.append("Autor: ", style=p.label)
    info.append("Guillermo Haynes\n", style="")
    info.append("Licencia: ", style=p.label)
    info.append("MIT\n\n", style="")
    info.append("Metodologías implementadas:\n", style=f"bold {p.secondary}")
    info.append("  • Método Racional (Chow, FHWA)\n", style="")
    info.append("  • SCS-CN para escorrentía\n", style="")
    info.append("  • Hidrogramas: SCS, Clark, Snyder\n", style="")
    info.append("  • IDF según DINAGUA Uruguay\n", style="")

    panel = Panel(
        info,
        title="Información",
        title_align="left",
        border_style=p.primary,
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def _create_project_quick() -> Optional["Project"]:
    """Crea un proyecto de forma rápida (solo nombre obligatorio)."""
    from hidropluvial.cli.theme import print_section, print_success
    from hidropluvial.cli.viewer.panel_input import panel_text, panel_confirm
    from hidropluvial.project import get_project_manager

    print_section("Nuevo Proyecto")

    name = panel_text(
        title="Nombre del proyecto",
        hint="Identificador único para este proyecto",
    )

    if not name:
        return None

    # Preguntar si quiere agregar más detalles
    add_details = panel_confirm(
        title="¿Agregar descripción, autor y ubicación?",
        default=False,
    )

    description = ""
    author = ""
    location = ""

    if add_details:
        description = panel_text(
            title="Descripción",
            hint="Opcional",
        ) or ""

        author = panel_text(
            title="Autor",
            hint="Opcional",
        ) or ""

        location = panel_text(
            title="Ubicación",
            hint="Opcional",
        ) or ""

    project_manager = get_project_manager()
    project = project_manager.create_project(
        name=name,
        description=description,
        author=author,
        location=location,
    )

    print_success(f"Proyecto creado: {project.name} [{project.id}]")
    return project
