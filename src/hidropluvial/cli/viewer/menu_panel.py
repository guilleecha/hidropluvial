"""
Sistema de menús interactivos con paneles y shortcuts.

Proporciona menús visuales que se actualizan en la misma vista,
usando shortcuts de letras para navegación rápida.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any, Dict
from enum import Enum

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_icons, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key


@dataclass
class MenuItem:
    """Un ítem de menú."""
    key: str  # Shortcut (letra)
    label: str  # Texto a mostrar
    action: Optional[Callable] = None  # Función a ejecutar
    value: Any = None  # Valor a retornar si no hay action
    hint: str = ""  # Descripción adicional
    separator: bool = False  # Es un separador visual
    disabled: bool = False  # Deshabilitado


@dataclass
class MenuState:
    """Estado del menú."""
    title: str
    items: List[MenuItem]
    subtitle: str = ""
    info_panel: Optional[Any] = None  # Panel de info adicional
    message: str = ""
    selected_idx: int = 0  # Para navegación con flechas


def build_menu_panel(state: MenuState) -> Panel:
    """Construye el panel del menú."""
    p = get_palette()
    icons = get_icons()

    content = Text()

    for idx, item in enumerate(state.items):
        if item.separator:
            content.append(f"\n  {'─' * 40}\n", style=p.muted)
            continue

        is_selected = idx == state.selected_idx
        is_disabled = item.disabled

        # Shortcut
        if is_disabled:
            content.append(f"  [{item.key}] ", style=f"dim {p.muted}")
        elif is_selected:
            content.append(f"  [{item.key}] ", style=f"bold {p.accent}")
        else:
            content.append(f"  [{item.key}] ", style=f"bold {p.accent}")

        # Label
        if is_disabled:
            content.append(f"{item.label}", style=f"dim {p.muted}")
        elif is_selected:
            content.append(f"> {item.label}", style=f"bold {p.primary}")
        else:
            content.append(f"  {item.label}", style="")

        # Hint
        if item.hint and not is_disabled:
            content.append(f"  {item.hint}", style=p.muted)

        content.append("\n")

    return Panel(
        content,
        title=f"[bold {p.primary}]{state.title}[/]",
        subtitle=f"[{p.muted}]{state.subtitle}[/]" if state.subtitle else None,
        border_style=p.border,
        padding=(1, 2),
    )


def build_menu_nav(state: MenuState) -> Text:
    """Construye la barra de navegación."""
    p = get_palette()
    nav = Text()

    nav.append("  [", style=p.muted)
    nav.append("a-z", style=f"bold {p.nav_key}")
    nav.append("] Seleccionar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("↑↓", style=f"bold {p.nav_key}")
    nav.append("] Navegar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Enter", style=f"bold {p.nav_confirm}")
    nav.append("] Confirmar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("Esc", style=f"bold {p.nav_cancel}")
    nav.append("] Volver", style=p.muted)

    return nav


def build_menu_message(state: MenuState) -> Text:
    """Construye texto de mensaje."""
    p = get_palette()
    if not state.message:
        return Text("")

    return Text(f"  {state.message}", style=p.info)


def build_menu_display(state: MenuState) -> Group:
    """Construye el display completo."""
    elements = [Text("")]

    # Panel de info adicional (si existe)
    if state.info_panel:
        elements.append(state.info_panel)
        elements.append(Text(""))

    # Panel de menú
    elements.append(build_menu_panel(state))

    # Mensaje
    msg = build_menu_message(state)
    if msg:
        elements.append(msg)

    # Navegación
    elements.append(Text(""))
    elements.append(build_menu_nav(state))

    return Group(*elements)


def get_next_valid_idx(items: List[MenuItem], current: int, direction: int) -> int:
    """Obtiene el siguiente índice válido (no separador, no disabled)."""
    n = len(items)
    idx = current

    for _ in range(n):
        idx = (idx + direction) % n
        if not items[idx].separator and not items[idx].disabled:
            return idx

    return current


def menu_panel(
    title: str,
    items: List[MenuItem],
    subtitle: str = "",
    info_panel: Any = None,
    allow_back: bool = True,
    as_popup: bool = False,
) -> Optional[Any]:
    """
    Muestra un menú interactivo con panel.

    Args:
        title: Título del menú
        items: Lista de MenuItem
        subtitle: Subtítulo opcional
        info_panel: Panel de información adicional
        allow_back: Permitir volver con Esc
        as_popup: Si True, no limpia la pantalla (para overlays)

    Returns:
        - El valor del item seleccionado
        - None si presiona Esc y allow_back=True
        - Ejecuta action() si el item tiene una función
    """
    console = get_console()
    from rich.live import Live

    state = MenuState(
        title=title,
        items=items,
        subtitle=subtitle,
        info_panel=info_panel,
    )

    # Posicionar en primer item válido
    if items[0].separator or items[0].disabled:
        state.selected_idx = get_next_valid_idx(items, 0, 1)

    if not as_popup:
        clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_menu_display(state)
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_items = len(state.items)

            if key == 'esc':
                if allow_back:
                    return None
                continue

            elif key == 'enter':
                item = state.items[state.selected_idx]
                if not item.separator and not item.disabled:
                    if item.action:
                        return item.action()
                    return item.value

            elif key == 'up':
                state.selected_idx = get_next_valid_idx(
                    state.items, state.selected_idx, -1
                )
                state.message = ""

            elif key == 'down':
                state.selected_idx = get_next_valid_idx(
                    state.items, state.selected_idx, 1
                )
                state.message = ""

            else:
                # Buscar por shortcut
                for idx, item in enumerate(state.items):
                    if item.key.lower() == key.lower() and not item.separator and not item.disabled:
                        if item.action:
                            return item.action()
                        return item.value

            display = build_menu_display(state)
            live.update(display, refresh=True)

    return None


def quick_menu(
    title: str,
    options: Dict[str, str],
    subtitle: str = "",
) -> Optional[str]:
    """
    Atajo para crear un menú simple.

    Args:
        title: Título del menú
        options: Dict de {shortcut: label}
        subtitle: Subtítulo opcional

    Returns:
        El shortcut seleccionado o None
    """
    items = [
        MenuItem(key=k, label=v, value=k)
        for k, v in options.items()
    ]
    return menu_panel(title, items, subtitle)


# ============================================================================
# Menús predefinidos comunes
# ============================================================================

def confirm_menu(
    title: str,
    message: str = "",
    default_yes: bool = True,
) -> Optional[bool]:
    """Menú de confirmación Sí/No."""
    items = [
        MenuItem(key="s", label="Sí", value=True),
        MenuItem(key="n", label="No", value=False),
    ]

    result = menu_panel(
        title=title,
        items=items,
        subtitle=message,
    )

    if result is None:
        return False if default_yes else None

    return result


def add_basin_menu() -> Optional[str]:
    """Menú para agregar cuenca."""
    items = [
        MenuItem(key="n", label="Nueva cuenca", value="new", hint="Crear desde cero"),
        MenuItem(key="i", label="Importar cuenca", value="import", hint="Desde archivo"),
        MenuItem(key="d", label="Duplicar existente", value="duplicate", hint="Copiar otra cuenca"),
    ]

    return menu_panel(
        title="Agregar Cuenca",
        items=items,
        subtitle="Selecciona cómo crear la cuenca",
    )


# ============================================================================
# Popup Menu (overlay sobre contenido existente)
# ============================================================================

def build_popup_panel(state: MenuState, width: int = 50) -> Panel:
    """Construye el panel popup centrado."""
    p = get_palette()
    icons = get_icons()

    content = Text()

    for idx, item in enumerate(state.items):
        if item.separator:
            content.append(f"  {'─' * (width - 6)}\n", style=p.muted)
            continue

        is_selected = idx == state.selected_idx
        is_disabled = item.disabled

        # Indicador de selección
        if is_selected:
            content.append(" > ", style=f"bold {p.accent}")
        else:
            content.append("   ", style="")

        # Shortcut
        if is_disabled:
            content.append(f"[{item.key}] ", style=f"dim {p.muted}")
        else:
            content.append(f"[{item.key}] ", style=f"bold {p.accent}")

        # Label
        if is_disabled:
            content.append(f"{item.label}", style=f"dim {p.muted}")
        elif is_selected:
            content.append(f"{item.label}", style=f"bold {p.primary}")
        else:
            content.append(f"{item.label}", style="")

        # Hint
        if item.hint and not is_disabled:
            remaining = width - len(item.label) - len(item.key) - 10
            if remaining > 0:
                content.append(f"  {item.hint[:remaining]}", style=p.muted)

        content.append("\n")

    # Navegación compacta
    content.append("\n")
    content.append("  [↑↓] Navegar  [Enter] OK  [Esc] Cancelar", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.accent}]{state.title}[/]",
        subtitle=f"[{p.muted}]{state.subtitle}[/]" if state.subtitle else None,
        border_style=p.accent,
        box=box.DOUBLE,
        padding=(0, 1),
        width=width,
    )


def popup_menu(
    title: str,
    items: List[MenuItem],
    subtitle: str = "",
    background: Any = None,
    width: int = 50,
) -> Optional[Any]:
    """
    Muestra un menú popup/overlay sobre el contenido existente.

    A diferencia de menu_panel, este NO hace clear_screen y se muestra
    como una ventana emergente centrada.

    Args:
        title: Título del popup
        items: Lista de MenuItem
        subtitle: Subtítulo opcional
        background: Elemento Rich a mostrar como fondo (ej: la tabla del form)
        width: Ancho del popup

    Returns:
        - El valor del item seleccionado
        - None si presiona Esc
    """
    console = get_console()
    from rich.live import Live
    from rich.align import Align
    from rich.columns import Columns

    state = MenuState(
        title=title,
        items=items,
        subtitle=subtitle,
    )

    # Posicionar en primer item válido
    if items and (items[0].separator or items[0].disabled):
        state.selected_idx = get_next_valid_idx(items, 0, 1)

    def build_popup_display():
        popup = build_popup_panel(state, width)
        # Centrar el popup
        centered = Align.center(popup, vertical="middle")

        if background:
            # Mostrar fondo atenuado + popup centrado
            return Group(
                Text(""),  # Espacio superior
                centered,
            )
        return Group(Text(""), centered)

    # No hacer clear_screen para mantener el contexto visual
    # Solo limpiar y redibujar

    with Live(console=console, auto_refresh=False, screen=True) as live:
        display = build_popup_display()
        live.update(display, refresh=True)

        while True:
            key = get_key()

            if key == 'esc':
                return None

            elif key == 'enter':
                item = state.items[state.selected_idx]
                if not item.separator and not item.disabled:
                    if item.action:
                        return item.action()
                    return item.value

            elif key == 'up':
                state.selected_idx = get_next_valid_idx(
                    state.items, state.selected_idx, -1
                )

            elif key == 'down':
                state.selected_idx = get_next_valid_idx(
                    state.items, state.selected_idx, 1
                )

            else:
                # Buscar por shortcut
                for idx, item in enumerate(state.items):
                    if item.key.lower() == key.lower() and not item.separator and not item.disabled:
                        if item.action:
                            return item.action()
                        return item.value

            display = build_popup_display()
            live.update(display, refresh=True)

    return None


def popup_input(
    title: str,
    default: str = "",
    hint: str = "",
    width: int = 50,
) -> Optional[str]:
    """
    Muestra un popup para entrada de texto.

    Args:
        title: Título/pregunta
        default: Valor por defecto
        hint: Texto de ayuda
        width: Ancho del popup

    Returns:
        El texto ingresado o None si cancela
    """
    console = get_console()
    from rich.live import Live
    from rich.align import Align

    p = get_palette()
    input_buffer = default

    def build_input_popup():
        content = Text()
        content.append(f"  {title}\n\n", style=f"bold {p.primary}")

        if hint:
            content.append(f"  {hint}\n\n", style=p.muted)

        # Campo de entrada
        content.append("  > ", style=f"bold {p.accent}")
        content.append(input_buffer, style=f"bold {p.input_text}")
        content.append("_", style=f"blink bold {p.input_text}")
        content.append("\n\n")

        # Navegación
        nav = Text()
        nav.append("  [", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)
        content.append_text(nav)

        panel = Panel(
            content,
            border_style=p.accent,
            box=box.DOUBLE,
            padding=(0, 1),
            width=width,
        )
        return Align.center(panel, vertical="middle")

    with Live(console=console, auto_refresh=False, screen=True) as live:
        display = Group(Text(""), build_input_popup())
        live.update(display, refresh=True)

        while True:
            key = get_key()

            if key == 'esc':
                return None

            elif key == 'enter':
                return input_buffer.strip()

            elif key == 'backspace':
                input_buffer = input_buffer[:-1]

            elif isinstance(key, str) and len(key) == 1 and (key.isprintable() or key in '.-'):
                input_buffer += key

            display = Group(Text(""), build_input_popup())
            live.update(display, refresh=True)

    return None
