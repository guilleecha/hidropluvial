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
