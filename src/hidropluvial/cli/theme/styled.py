"""
Funciones para crear objetos Text estilizados (no imprimen directamente).
"""

from rich.panel import Panel
from rich.text import Text
from rich import box

from hidropluvial.cli.theme.palette import get_palette


def styled_header(text: str, subtitle: str = None) -> Panel:
    """Crea un encabezado estilizado."""
    p = get_palette()
    content = Text(text, style=f"bold {p.primary}")
    if subtitle:
        content.append(f"\n{subtitle}", style=p.muted)

    return Panel(
        content,
        border_style=p.border,
        box=box.ROUNDED,
        padding=(0, 2),
    )


def styled_title(text: str) -> Text:
    """Crea un título estilizado."""
    p = get_palette()
    return Text(text, style=f"bold {p.primary}")


def styled_subtitle(text: str) -> Text:
    """Crea un subtítulo estilizado."""
    p = get_palette()
    return Text(text, style=p.secondary)


def styled_value(value, unit: str = None) -> Text:
    """Formatea un valor numérico con unidad opcional."""
    p = get_palette()
    text = Text()
    text.append(str(value), style=f"bold {p.number}")
    if unit:
        text.append(f" {unit}", style=p.unit)
    return text


def styled_label(label: str, value, unit: str = None) -> Text:
    """Formatea una etiqueta con valor."""
    p = get_palette()
    text = Text()
    text.append(f"{label}: ", style=p.label)
    text.append(str(value), style=f"bold {p.number}")
    if unit:
        text.append(f" {unit}", style=p.unit)
    return text


def styled_success(text: str) -> Text:
    """Texto de éxito."""
    p = get_palette()
    return Text(f"[+] {text}", style=p.success)


def styled_warning(text: str) -> Text:
    """Texto de advertencia."""
    p = get_palette()
    return Text(f"[!] {text}", style=p.warning)


def styled_error(text: str) -> Text:
    """Texto de error."""
    p = get_palette()
    return Text(f"[x] {text}", style=p.error)


def styled_info(text: str) -> Text:
    """Texto informativo."""
    p = get_palette()
    return Text(f"[i] {text}", style=p.info)


def styled_muted(text: str) -> Text:
    """Texto atenuado."""
    p = get_palette()
    return Text(text, style=p.muted)


def styled_note(text: str) -> Text:
    """Nota informativa con icono distintivo."""
    p = get_palette()
    result = Text()
    result.append("NOTA: ", style=f"bold {p.note}")
    result.append(text, style=p.note)
    return result


def styled_suggestion(text: str) -> Text:
    """Sugerencia o recomendación con icono distintivo."""
    p = get_palette()
    result = Text()
    result.append(">> ", style=f"bold {p.suggestion}")
    result.append(text, style=p.suggestion)
    return result


def styled_suggestion_box(lines: list[str], title: str = "SUGERENCIA") -> Panel:
    """Crea un panel de sugerencia con múltiples líneas."""
    p = get_palette()
    content = Text()
    for i, line in enumerate(lines):
        if i > 0:
            content.append("\n")
        content.append(line, style=p.suggestion)

    return Panel(
        content,
        title=f"[bold {p.suggestion}]{title}[/]",
        title_align="left",
        border_style=p.suggestion,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def styled_note_box(lines: list[str], title: str = "NOTA") -> Panel:
    """Crea un panel de nota con múltiples líneas."""
    p = get_palette()
    content = Text()
    for i, line in enumerate(lines):
        if i > 0:
            content.append("\n")
        content.append(line, style=p.note)

    return Panel(
        content,
        title=f"[bold {p.note}]{title}[/]",
        title_align="left",
        border_style=p.note,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def create_summary_panel(title: str, content: str) -> Panel:
    """Crea un panel de resumen."""
    p = get_palette()
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=p.border,
        box=box.ROUNDED,
        padding=(0, 1),
    )


# =============================================================================
# Navigation Bar Helpers
# =============================================================================

def styled_nav_key(key: str, label: str = "") -> Text:
    """
    Crea un segmento de tecla de navegación estilizado.

    Args:
        key: Tecla (ej: "Enter", "Esc", "↑↓", "a-z")
        label: Descripción de la acción (ej: "Confirmar", "Volver")

    Returns:
        Text estilizado: [key] label
    """
    p = get_palette()
    text = Text()
    text.append("[", style=p.muted)
    text.append(key, style=f"bold {p.nav_key}")
    text.append("]", style=p.muted)
    if label:
        text.append(f" {label}", style=p.muted)
    return text


def styled_nav_confirm(key: str = "Enter", label: str = "Confirmar") -> Text:
    """Crea segmento de tecla de confirmación."""
    p = get_palette()
    text = Text()
    text.append("[", style=p.muted)
    text.append(key, style=f"bold {p.nav_confirm}")
    text.append("]", style=p.muted)
    if label:
        text.append(f" {label}", style=p.muted)
    return text


def styled_nav_cancel(key: str = "Esc", label: str = "Volver") -> Text:
    """Crea segmento de tecla de cancelación."""
    p = get_palette()
    text = Text()
    text.append("[", style=p.muted)
    text.append(key, style=f"bold {p.nav_cancel}")
    text.append("]", style=p.muted)
    if label:
        text.append(f" {label}", style=p.muted)
    return text


def styled_nav_bar(
    items: list[tuple[str, str]],
    confirm_key: str = None,
    cancel_key: str = None,
    indent: int = 2,
) -> Text:
    """
    Crea una barra de navegación completa y estilizada.

    Args:
        items: Lista de tuplas (key, label) para teclas normales
        confirm_key: Si se proporciona, agrega tecla de confirmación con este label
        cancel_key: Si se proporciona, agrega tecla de cancelación con este label
        indent: Espacios de indentación inicial

    Returns:
        Text con la barra de navegación completa

    Example:
        styled_nav_bar(
            [("↑↓", "Navegar"), ("a-z", "Seleccionar")],
            confirm_key="Confirmar",
            cancel_key="Volver"
        )
        # Resultado: "  [↑↓] Navegar  [a-z] Seleccionar  [Enter] Confirmar  [Esc] Volver"
    """
    p = get_palette()
    nav = Text()
    nav.append(" " * indent)

    # Agregar items normales
    for key, label in items:
        nav.append_text(styled_nav_key(key, label))
        nav.append("  ")

    # Agregar confirmación
    if confirm_key:
        nav.append_text(styled_nav_confirm("Enter", confirm_key))
        nav.append("  ")

    # Agregar cancelación
    if cancel_key:
        nav.append_text(styled_nav_cancel("Esc", cancel_key))

    return nav


def styled_nav_bar_select() -> Text:
    """Barra de navegación estándar para paneles de selección."""
    return styled_nav_bar(
        [("a-z", "Seleccionar"), ("↑↓", "Navegar")],
        confirm_key="Confirmar",
        cancel_key="Volver",
    )


def styled_nav_bar_checkbox() -> Text:
    """Barra de navegación estándar para paneles de checkbox."""
    return styled_nav_bar(
        [("a-z", "Marcar"), ("Space", "Toggle"), ("↑↓", "Navegar")],
        confirm_key="Confirmar",
        cancel_key="Volver",
    )


def styled_nav_bar_text() -> Text:
    """Barra de navegación estándar para entrada de texto."""
    return styled_nav_bar(
        [],
        confirm_key="Confirmar",
        cancel_key="Volver",
    )


def styled_nav_bar_confirm() -> Text:
    """Barra de navegación estándar para confirmación Sí/No."""
    p = get_palette()
    nav = Text()
    nav.append("  [", style=p.muted)
    nav.append("s", style=f"bold {p.nav_confirm}")
    nav.append("/", style=p.muted)
    nav.append("n", style=f"bold {p.nav_cancel}")
    nav.append("] Seleccionar  ", style=p.muted)
    nav.append_text(styled_nav_confirm("Enter", "Confirmar"))
    return nav


def styled_delete_confirm(count: int, entity: str = "item(s)") -> Text:
    """
    Crea la barra de confirmación para eliminación.

    Args:
        count: Número de items a eliminar
        entity: Nombre de la entidad (ej: "cuenca(s)", "proyecto(s)")

    Returns:
        Text con mensaje de confirmación estilizado
    """
    p = get_palette()
    nav = Text()
    nav.append(f"  Eliminar {count} {entity}? ", style=f"bold {p.warning}")
    nav.append("[", style=p.muted)
    nav.append("s/y", style=f"bold {p.nav_confirm}")
    nav.append("] Confirmar  ", style=p.muted)
    nav.append("[", style=p.muted)
    nav.append("n/Esc", style=f"bold {p.nav_cancel}")
    nav.append("] Cancelar", style=p.muted)
    return nav


def styled_marked_text(text: str, is_selected: bool = False) -> Text:
    """
    Crea texto estilizado para items marcados para eliminación.

    Args:
        text: Texto a mostrar
        is_selected: Si el item también está seleccionado

    Returns:
        Text con estilo de marcado
    """
    p = get_palette()
    if is_selected:
        return Text(text, style=f"bold {p.marked} reverse")
    return Text(text, style=p.marked)


def styled_input_field(label: str, value: str, show_cursor: bool = True) -> Text:
    """
    Crea un campo de entrada estilizado.

    Args:
        label: Etiqueta del campo
        value: Valor actual del campo
        show_cursor: Si mostrar cursor parpadeante

    Returns:
        Text con campo de entrada estilizado
    """
    p = get_palette()
    text = Text()
    text.append(f"  {label}: ", style=f"bold {p.accent}")
    text.append(value, style=f"bold {p.input_text}")
    if show_cursor:
        text.append("_", style=f"blink bold {p.input_text}")
    return text


def styled_warning_message(text: str) -> Text:
    """Crea un mensaje de advertencia para estados vacíos o sin datos."""
    p = get_palette()
    return Text(f"  {text}", style=p.warning)
