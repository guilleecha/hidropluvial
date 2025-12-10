"""
Sistema de paneles interactivos con shortcuts de teclado.

Reemplaza questionary con paneles visuales donde las opciones
se seleccionan con teclas numéricas o letras.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any, Union
from enum import Enum

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_icons, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PanelOption:
    """Una opción en un panel de selección."""
    label: str
    value: Any
    shortcut: str = ""  # Tecla de acceso rápido (1-9, a-z)
    checked: bool = False  # Para checkbox
    hint: str = ""  # Descripción adicional


@dataclass
class PanelState:
    """Estado del panel interactivo."""
    title: str
    message: str = ""
    options: List[PanelOption] = field(default_factory=list)
    selected_idx: int = 0
    mode: str = "select"  # "select", "checkbox", "text", "confirm"
    input_buffer: str = ""
    input_hint: str = ""
    input_default: str = ""
    confirm_default: bool = True
    error_message: str = ""
    info_panel: Optional[Any] = None  # Panel de info adicional arriba


# ============================================================================
# Display Builders
# ============================================================================

def build_options_panel(state: PanelState) -> Panel:
    """Construye el panel de opciones con shortcuts."""
    p = get_palette()
    icons = get_icons()

    content = Text()

    if state.mode == "select":
        # Opciones con números/letras como shortcuts
        for i, opt in enumerate(state.options):
            shortcut = opt.shortcut or str(i + 1)
            is_selected = i == state.selected_idx

            # Shortcut
            content.append("  [", style=p.muted)
            content.append(shortcut, style=f"bold {p.accent}")
            content.append("] ", style=p.muted)

            # Opción
            if is_selected:
                content.append(f"> {opt.label}", style=f"bold {p.primary}")
            else:
                content.append(f"  {opt.label}")

            # Hint
            if opt.hint:
                content.append(f"  {opt.hint}", style=p.muted)

            content.append("\n")

    elif state.mode == "checkbox":
        # Checkboxes con espacio para marcar
        for i, opt in enumerate(state.options):
            shortcut = opt.shortcut or str(i + 1)
            is_cursor = i == state.selected_idx

            # Shortcut
            content.append("  [", style=p.muted)
            content.append(shortcut, style=f"bold {p.accent}")
            content.append("] ", style=p.muted)

            # Checkbox
            if opt.checked:
                content.append(f"[{icons.check}]", style=f"bold {p.success}")
            else:
                content.append("[ ]", style=p.muted)

            content.append(" ")

            # Opción
            if is_cursor:
                content.append(opt.label, style=f"bold {p.primary}")
            elif opt.checked:
                content.append(opt.label, style="bold")
            else:
                content.append(opt.label)

            content.append("\n")

    elif state.mode == "text":
        # Campo de texto
        content.append("  ", style=p.muted)
        if state.input_hint:
            content.append(f"{state.input_hint}\n\n", style=p.info)

        content.append("  > ", style=f"bold {p.accent}")
        content.append(state.input_buffer, style=f"bold {p.input_text}")
        content.append("_", style=f"blink bold {p.input_text}")
        content.append("\n")

        if state.input_default:
            content.append(f"\n  (default: {state.input_default})", style=p.muted)

    elif state.mode == "confirm":
        # Confirmación Sí/No
        yes_style = f"bold {p.success}" if state.confirm_default else p.muted
        no_style = p.muted if state.confirm_default else f"bold {p.warning}"

        content.append("  [", style=p.muted)
        content.append("s", style=f"bold {p.accent}")
        content.append("] ", style=p.muted)
        content.append("Sí", style=yes_style)

        content.append("    [", style=p.muted)
        content.append("n", style=f"bold {p.accent}")
        content.append("] ", style=p.muted)
        content.append("No", style=no_style)

        if state.confirm_default:
            content.append("  (Enter = Sí)", style=p.muted)
        else:
            content.append("  (Enter = No)", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.primary}]{state.title}[/]",
        border_style=p.border,
        padding=(1, 2),
    )


def build_nav_bar(state: PanelState) -> Text:
    """Construye la barra de navegación inferior."""
    p = get_palette()
    nav = Text()

    if state.mode == "select":
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

    elif state.mode == "checkbox":
        nav.append("  [", style=p.muted)
        nav.append("a-z", style=f"bold {p.nav_key}")
        nav.append("] Marcar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Space", style=f"bold {p.nav_key}")
        nav.append("] Toggle  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("↑↓", style=f"bold {p.nav_key}")
        nav.append("] Navegar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Volver", style=p.muted)

    elif state.mode == "text":
        nav.append("  [", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Volver", style=p.muted)

    elif state.mode == "confirm":
        nav.append("  [", style=p.muted)
        nav.append("s", style=f"bold {p.nav_confirm}")
        nav.append("/", style=p.muted)
        nav.append("n", style=f"bold {p.nav_cancel}")
        nav.append("] Seleccionar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar", style=p.muted)

    return nav


def build_error_text(state: PanelState) -> Text:
    """Construye texto de error si existe."""
    p = get_palette()
    icons = get_icons()

    if not state.error_message:
        return Text("")

    return Text(f"  {icons.cross} {state.error_message}", style=f"bold {p.error}")


def build_display(state: PanelState) -> Group:
    """Construye el display completo."""
    elements = [Text("")]

    # Panel de info adicional (si existe)
    if state.info_panel:
        elements.append(state.info_panel)
        elements.append(Text(""))

    # Mensaje principal
    if state.message:
        p = get_palette()
        elements.append(Text(f"  {state.message}", style=p.info))
        elements.append(Text(""))

    # Panel de opciones
    elements.append(build_options_panel(state))

    # Error
    error = build_error_text(state)
    if error:
        elements.append(error)

    # Navegación
    elements.append(Text(""))
    elements.append(build_nav_bar(state))

    return Group(*elements)


# ============================================================================
# Interactive Functions
# ============================================================================

def panel_select(
    title: str,
    options: List[PanelOption],
    message: str = "",
    info_panel: Any = None,
) -> Optional[Any]:
    """
    Muestra un panel de selección única.

    Args:
        title: Título del panel
        options: Lista de PanelOption
        message: Mensaje informativo
        info_panel: Panel de información adicional (opcional)

    Returns:
        Valor seleccionado o None si cancela
    """
    console = get_console()
    from rich.live import Live

    # Asignar shortcuts con letras (a, b, c, ...)
    for i, opt in enumerate(options):
        if not opt.shortcut:
            opt.shortcut = chr(ord('a') + i)

    state = PanelState(
        title=title,
        message=message,
        options=options,
        mode="select",
        info_panel=info_panel,
    )

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state)
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_opts = len(state.options)

            if key == 'esc':
                clear_screen()
                return None

            elif key == 'enter':
                clear_screen()
                return state.options[state.selected_idx].value

            elif key == 'up':
                state.selected_idx = (state.selected_idx - 1) % n_opts

            elif key == 'down':
                state.selected_idx = (state.selected_idx + 1) % n_opts

            else:
                # Buscar por shortcut
                for i, opt in enumerate(state.options):
                    if opt.shortcut.lower() == key.lower():
                        clear_screen()
                        return opt.value

            display = build_display(state)
            live.update(display, refresh=True)

    clear_screen()
    return None


def panel_checkbox(
    title: str,
    options: List[PanelOption],
    message: str = "",
    info_panel: Any = None,
    min_selections: int = 0,
) -> Optional[List[Any]]:
    """
    Muestra un panel de selección múltiple.

    Args:
        title: Título del panel
        options: Lista de PanelOption (usar checked=True para preseleccionar)
        message: Mensaje informativo
        info_panel: Panel de información adicional (opcional)
        min_selections: Mínimo de selecciones requeridas

    Returns:
        Lista de valores seleccionados o None si cancela
    """
    console = get_console()
    from rich.live import Live

    # Asignar shortcuts con letras (a, b, c, ...)
    for i, opt in enumerate(options):
        if not opt.shortcut:
            opt.shortcut = chr(ord('a') + i)

    state = PanelState(
        title=title,
        message=message,
        options=options,
        mode="checkbox",
        info_panel=info_panel,
    )

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state)
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_opts = len(state.options)

            if key == 'esc':
                clear_screen()
                return None

            elif key == 'enter':
                # Verificar mínimo de selecciones
                selected = [o.value for o in state.options if o.checked]
                if len(selected) < min_selections:
                    state.error_message = f"Selecciona al menos {min_selections}"
                else:
                    clear_screen()
                    return selected

            elif key == 'up':
                state.selected_idx = (state.selected_idx - 1) % n_opts
                state.error_message = ""

            elif key == 'down':
                state.selected_idx = (state.selected_idx + 1) % n_opts
                state.error_message = ""

            elif key == 'space':
                state.options[state.selected_idx].checked = not state.options[state.selected_idx].checked
                state.error_message = ""

            else:
                # Buscar por shortcut y toggle
                for i, opt in enumerate(state.options):
                    if opt.shortcut.lower() == key.lower():
                        opt.checked = not opt.checked
                        state.selected_idx = i
                        state.error_message = ""
                        break

            display = build_display(state)
            live.update(display, refresh=True)

    clear_screen()
    return None


def panel_text(
    title: str,
    message: str = "",
    hint: str = "",
    default: str = "",
    validator: Optional[Callable[[str], Union[bool, str]]] = None,
    info_panel: Any = None,
) -> Optional[str]:
    """
    Muestra un panel de entrada de texto.

    Args:
        title: Título del panel
        message: Mensaje informativo
        hint: Sugerencia para el campo
        default: Valor por defecto
        validator: Función de validación (retorna True o mensaje de error)
        info_panel: Panel de información adicional (opcional)

    Returns:
        Texto ingresado o None si cancela
    """
    console = get_console()
    from rich.live import Live

    state = PanelState(
        title=title,
        message=message,
        mode="text",
        input_hint=hint,
        input_default=default,
        info_panel=info_panel,
    )

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state)
        live.update(display, refresh=True)

        while True:
            key = get_key()

            if key == 'esc':
                clear_screen()
                return None

            elif key == 'enter':
                value = state.input_buffer.strip()
                if not value and default:
                    value = default

                # Validar
                if validator:
                    result = validator(value)
                    if result is not True:
                        state.error_message = result if isinstance(result, str) else "Valor inválido"
                        display = build_display(state)
                        live.update(display, refresh=True)
                        continue

                clear_screen()
                return value

            elif key == 'backspace':
                state.input_buffer = state.input_buffer[:-1]
                state.error_message = ""

            elif isinstance(key, str) and len(key) == 1 and (key.isprintable() or key in '.-'):
                state.input_buffer += key
                state.error_message = ""

            display = build_display(state)
            live.update(display, refresh=True)

    clear_screen()
    return None


def build_confirm_popup(title: str, default: bool = True) -> Panel:
    """Construye un popup compacto de confirmación."""
    p = get_palette()

    content = Text()

    # Opciones Sí/No en una línea
    yes_style = f"bold reverse {p.success}" if default else ""
    no_style = "" if default else f"bold reverse {p.error}"

    content.append("  [", style=p.muted)
    content.append("s", style=f"bold {p.success}")
    content.append("] ", style=p.muted)
    content.append(" Sí ", style=yes_style)

    content.append("   [", style=p.muted)
    content.append("n", style=f"bold {p.error}")
    content.append("] ", style=p.muted)
    content.append(" No ", style=no_style)

    content.append("   [", style=p.muted)
    content.append("Enter", style=f"bold {p.primary}")
    content.append("]", style=p.muted)
    content.append(f" = {'Sí' if default else 'No'}", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.accent}] {title} [/]",
        border_style=p.accent,
        box=box.DOUBLE,
        padding=(0, 2),
    )


def panel_confirm(
    title: str,
    message: str = "",
    default: bool = True,
    info_panel: Any = None,
    as_popup: bool = False,
) -> Optional[bool]:
    """
    Muestra un panel de confirmación Sí/No.

    Args:
        title: Título/pregunta
        message: Mensaje adicional
        default: Valor por defecto (True = Sí)
        info_panel: Panel de información adicional (opcional)
        as_popup: Si True, muestra como popup compacto sin limpiar pantalla

    Returns:
        True/False o None si cancela
    """
    console = get_console()
    from rich.live import Live

    if as_popup:
        # Modo popup compacto
        popup = build_confirm_popup(title, default)

        with Live(console=console, auto_refresh=False, screen=False) as live:
            live.update(Group(Text(""), popup), refresh=True)

            while True:
                key = get_key()

                if key == 'esc':
                    return None
                elif key == 'enter':
                    return default
                elif key == 's' or key == 'y':
                    return True
                elif key == 'n':
                    return False

        return None

    # Modo pantalla completa (original)
    state = PanelState(
        title=title,
        message=message,
        mode="confirm",
        confirm_default=default,
        info_panel=info_panel,
    )

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state)
        live.update(display, refresh=True)

        while True:
            key = get_key()

            if key == 'esc':
                clear_screen()
                return None

            elif key == 'enter':
                clear_screen()
                return state.confirm_default

            elif key == 's' or key == 'y':
                clear_screen()
                return True

            elif key == 'n':
                clear_screen()
                return False

            display = build_display(state)
            live.update(display, refresh=True)

    clear_screen()
    return None


def panel_alert_confirm(
    title: str,
    message: str,
    default: bool = True,
    yes_label: str = "Sí",
    no_label: str = "No",
) -> Optional[bool]:
    """
    Muestra un panel de confirmación estilo alerta (borde doble, magenta/warning).

    Similar al diálogo de confirmación de cancelación pero personalizable.

    Args:
        title: Título del panel
        message: Mensaje de alerta (se muestra con icono de warning)
        default: Valor por defecto (True = Sí)
        yes_label: Etiqueta del botón Sí
        no_label: Etiqueta del botón No

    Returns:
        True si confirma, False si rechaza, None si cancela (Esc)
    """
    from rich import box
    from rich.live import Live

    console = get_console()
    p = get_palette()
    icons = get_icons()

    # Construir contenido del panel
    content = Text()
    content.append(f"\n    [{icons.warning}] ", style=f"bold {p.warning}")
    content.append(f"{message}\n\n", style=f"{p.warning}")
    content.append("    [", style=p.muted)
    content.append("s", style=f"bold {p.success}")
    content.append(f"] {yes_label}    ", style=p.muted)
    content.append("[", style=p.muted)
    content.append("n", style=f"bold {p.error}")
    content.append(f"] {no_label}", style=p.muted)
    if default:
        content.append("  (Enter = Sí)", style=p.muted)
    else:
        content.append("  (Enter = No)", style=p.muted)
    content.append("\n", style=p.muted)

    panel = Panel(
        content,
        title=f"[bold {p.warning}] {title} [/]",
        border_style=p.warning,
        box=box.DOUBLE,
        padding=(0, 2),
    )

    nav_text = Text()
    nav_text.append("\n  [s/n] Seleccionar  [Enter] Confirmar  [Esc] Cancelar", style=p.muted)

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        live.update(Group(Text(""), panel, nav_text), refresh=True)

        while True:
            key = get_key()

            if key == 'esc':
                clear_screen()
                return None
            elif key == 'enter':
                clear_screen()
                return default
            elif key == 's' or key == 'y':
                clear_screen()
                return True
            elif key == 'n':
                clear_screen()
                return False


# ============================================================================
# Convenience Functions
# ============================================================================

def quick_select(
    title: str,
    choices: List[str],
    message: str = "",
) -> Optional[str]:
    """Atajo para selección simple con lista de strings."""
    options = [PanelOption(label=c, value=c) for c in choices]
    return panel_select(title, options, message)


def quick_checkbox(
    title: str,
    choices: List[str],
    defaults: List[str] = None,
    message: str = "",
    min_selections: int = 1,
) -> Optional[List[str]]:
    """Atajo para checkbox con lista de strings."""
    defaults = defaults or []
    options = [
        PanelOption(label=c, value=c, checked=c in defaults)
        for c in choices
    ]
    return panel_checkbox(title, options, message, min_selections=min_selections)
