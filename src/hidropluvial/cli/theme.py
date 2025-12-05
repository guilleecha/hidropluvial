"""
Sistema de temas para la interfaz CLI de HidroPluvial.

Proporciona una paleta de colores consistente y funciones de formato
para mejorar la legibilidad de la salida en terminal.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


class ThemeName(Enum):
    """Temas disponibles."""
    DEFAULT = "default"
    MONOKAI = "monokai"
    NORD = "nord"
    MINIMAL = "minimal"


@dataclass
class ColorPalette:
    """Paleta de colores para un tema."""
    # Colores principales
    primary: str      # Color principal (títulos, destacados)
    secondary: str    # Color secundario (subtítulos)
    accent: str       # Color de acento (valores importantes)

    # Colores semánticos
    success: str      # Éxito, completado
    warning: str      # Advertencia
    error: str        # Error
    info: str         # Información
    muted: str        # Texto secundario/atenuado

    # Colores para datos
    number: str       # Números y valores
    unit: str         # Unidades
    label: str        # Etiquetas

    # Bordes y separadores
    border: str       # Color de bordes
    header_bg: str    # Fondo de encabezados (para tablas)


# Tema por defecto - Estilo "programador" con colores pasteles
THEME_DEFAULT = ColorPalette(
    primary="#5f87af",      # Azul suave
    secondary="#87afaf",    # Cyan apagado
    accent="#af87af",       # Púrpura suave
    success="#87af87",      # Verde suave
    warning="#d7af5f",      # Amarillo/naranja suave
    error="#d75f5f",        # Rojo suave
    info="#5f87af",         # Azul info
    muted="#808080",        # Gris
    number="#d7af5f",       # Amarillo para números
    unit="#87af87",         # Verde para unidades
    label="#afafaf",        # Gris claro para etiquetas
    border="#5f5f5f",       # Gris oscuro para bordes
    header_bg="#3a3a3a",    # Fondo oscuro para headers
)

# Tema Monokai - Inspirado en el esquema de colores Monokai
THEME_MONOKAI = ColorPalette(
    primary="#66d9ef",      # Cyan
    secondary="#a6e22e",    # Verde lima
    accent="#ae81ff",       # Púrpura
    success="#a6e22e",      # Verde
    warning="#e6db74",      # Amarillo
    error="#f92672",        # Rosa/rojo
    info="#66d9ef",         # Cyan
    muted="#75715e",        # Gris/marrón
    number="#fd971f",       # Naranja
    unit="#a6e22e",         # Verde
    label="#f8f8f2",        # Blanco
    border="#49483e",       # Gris oscuro
    header_bg="#272822",    # Fondo Monokai
)

# Tema Nord - Colores fríos y suaves
THEME_NORD = ColorPalette(
    primary="#88c0d0",      # Cyan Nord
    secondary="#81a1c1",    # Azul claro
    accent="#b48ead",       # Púrpura
    success="#a3be8c",      # Verde
    warning="#ebcb8b",      # Amarillo
    error="#bf616a",        # Rojo
    info="#5e81ac",         # Azul
    muted="#4c566a",        # Gris
    number="#d08770",       # Naranja
    unit="#a3be8c",         # Verde
    label="#d8dee9",        # Gris claro
    border="#3b4252",       # Gris oscuro
    header_bg="#2e3440",    # Fondo Nord
)

# Tema Minimal - Solo grises y un acento
THEME_MINIMAL = ColorPalette(
    primary="#ffffff",      # Blanco
    secondary="#b0b0b0",    # Gris claro
    accent="#5fafff",       # Azul único como acento
    success="#87d787",      # Verde suave
    warning="#ffd787",      # Amarillo suave
    error="#ff8787",        # Rojo suave
    info="#5fafff",         # Azul
    muted="#606060",        # Gris oscuro
    number="#ffffff",       # Blanco
    unit="#909090",         # Gris
    label="#909090",        # Gris
    border="#404040",       # Gris muy oscuro
    header_bg="#303030",    # Fondo oscuro
)

# Mapeo de nombres a temas
THEMES = {
    ThemeName.DEFAULT: THEME_DEFAULT,
    ThemeName.MONOKAI: THEME_MONOKAI,
    ThemeName.NORD: THEME_NORD,
    ThemeName.MINIMAL: THEME_MINIMAL,
}


class CLITheme:
    """Gestor de tema para la CLI."""

    _instance: Optional["CLITheme"] = None
    _palette: ColorPalette = THEME_DEFAULT
    _console: Optional[Console] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_theme(cls, theme: ThemeName) -> None:
        """Establece el tema activo."""
        cls._palette = THEMES.get(theme, THEME_DEFAULT)
        cls._console = None  # Resetear console para recrear con nuevo tema

    @classmethod
    def get_palette(cls) -> ColorPalette:
        """Obtiene la paleta de colores actual."""
        return cls._palette

    @classmethod
    def get_console(cls) -> Console:
        """Obtiene la consola Rich con el tema aplicado."""
        if cls._console is None:
            p = cls._palette
            custom_theme = Theme({
                "primary": p.primary,
                "secondary": p.secondary,
                "accent": p.accent,
                "success": p.success,
                "warning": p.warning,
                "error": p.error,
                "info": p.info,
                "muted": p.muted,
                "number": p.number,
                "unit": p.unit,
                "label": p.label,
                "title": f"bold {p.primary}",
                "subtitle": p.secondary,
                "header": f"bold {p.primary}",
                "value": f"bold {p.number}",
                "param": p.label,
            })
            cls._console = Console(theme=custom_theme)
        return cls._console


# Instancia global para acceso fácil
def get_console() -> Console:
    """Obtiene la consola Rich con tema aplicado."""
    return CLITheme.get_console()


def get_palette() -> ColorPalette:
    """Obtiene la paleta de colores actual."""
    return CLITheme.get_palette()


# ============================================================================
# Funciones de formato
# ============================================================================


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


def create_results_table(
    title: str = None,
    columns: list[tuple[str, str]] = None,  # [(nombre, justify), ...]
) -> Table:
    """Crea una tabla estilizada para resultados."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    if columns:
        for name, justify in columns:
            table.add_column(name, justify=justify)

    return table


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


def format_number(value: float, decimals: int = 2) -> str:
    """Formatea un número con precisión especificada."""
    if abs(value) >= 1000:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def print_separator(char: str = "─", width: int = 60) -> None:
    """Imprime un separador."""
    console = get_console()
    p = get_palette()
    console.print(char * width, style=p.border)


def print_header(text: str, subtitle: str = None) -> None:
    """Imprime un encabezado."""
    console = get_console()
    console.print(styled_header(text, subtitle))


def print_step(step_num: int, total: int, title: str) -> None:
    """Imprime indicador de paso del wizard."""
    console = get_console()
    p = get_palette()

    text = Text()
    text.append(f"[{step_num}/{total}] ", style=p.muted)
    text.append(title, style=f"bold {p.secondary}")
    console.print(text)


def print_field(label: str, value, unit: str = None, indent: int = 2) -> None:
    """Imprime un campo con valor."""
    console = get_console()
    prefix = " " * indent
    console.print(prefix, styled_label(label, value, unit))


def print_success(text: str) -> None:
    """Imprime mensaje de éxito."""
    console = get_console()
    console.print(styled_success(text))


def print_warning(text: str) -> None:
    """Imprime advertencia."""
    console = get_console()
    console.print(styled_warning(text))


def print_error(text: str) -> None:
    """Imprime error."""
    console = get_console()
    console.print(styled_error(text))


def print_info(text: str) -> None:
    """Imprime información."""
    console = get_console()
    console.print(styled_info(text))


def print_section(title: str) -> None:
    """Imprime título de sección."""
    console = get_console()
    p = get_palette()
    console.print()
    console.print(f"-- {title} --", style=f"bold {p.secondary}")
    console.print()


def print_result_row(label: str, value, unit: str = None, highlight: bool = False) -> None:
    """Imprime una fila de resultado."""
    console = get_console()
    p = get_palette()

    style = f"bold {p.accent}" if highlight else p.number
    text = Text()
    text.append(f"  {label}: ", style=p.label)
    text.append(str(value), style=style)
    if unit:
        text.append(f" {unit}", style=p.unit)
    console.print(text)


def print_summary_box(title: str, items: list[tuple[str, str, str]]) -> None:
    """Imprime un cuadro de resumen.

    Args:
        title: Título del cuadro
        items: Lista de tuplas (label, value, unit)
    """
    console = get_console()
    p = get_palette()

    lines = []
    for label, value, unit in items:
        line = Text()
        line.append(f"{label}: ", style=p.label)
        line.append(str(value), style=f"bold {p.number}")
        if unit:
            line.append(f" {unit}", style=p.unit)
        lines.append(line)

    content = Text("\n").join(lines)

    panel = Panel(
        content,
        title=title,
        title_align="left",
        border_style=p.border,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def print_analysis_summary(
    cuenca: str,
    area: float,
    tc_method: str,
    tc_min: float,
    storm: str,
    tr: int,
    qpeak: float,
    volume: float,
    tp: float = None,
) -> None:
    """Imprime resumen de un análisis."""
    console = get_console()
    p = get_palette()

    # Título
    title = Text()
    title.append(f"Analisis: ", style=p.label)
    title.append(f"{cuenca}", style=f"bold {p.primary}")
    title.append(f" | ", style=p.muted)
    title.append(f"{tc_method}", style=p.secondary)
    title.append(f" | ", style=p.muted)
    title.append(f"{storm} Tr{tr}", style=p.secondary)

    console.print(title)

    # Resultados
    results = Text()
    results.append(f"  Qp = ", style=p.label)
    results.append(f"{qpeak:.2f}", style=f"bold {p.accent}")
    results.append(f" m3/s", style=p.unit)
    results.append(f"  |  ", style=p.muted)
    results.append(f"Vol = ", style=p.label)
    results.append(f"{volume:.4f}", style=f"bold {p.number}")
    results.append(f" hm3", style=p.unit)
    if tp:
        results.append(f"  |  ", style=p.muted)
        results.append(f"Tp = ", style=p.label)
        results.append(f"{tp:.1f}", style=f"bold {p.number}")
        results.append(f" min", style=p.unit)

    console.print(results)


def print_banner() -> None:
    """Imprime el banner de HidroPluvial."""
    console = get_console()
    p = get_palette()

    banner = """
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Analisis                |
|         Calculos hidrologicos para Uruguay                  |
+-------------------------------------------------------------+
"""
    console.print(banner, style=p.primary)


def print_completion_banner(n_analyses: int, session_id: str) -> None:
    """Imprime banner de finalización."""
    console = get_console()
    p = get_palette()

    console.print()
    console.print("=" * 60, style=p.border)

    title = Text()
    title.append("  ANALISIS COMPLETADO", style=f"bold {p.success}")
    console.print(title)

    console.print("=" * 60, style=p.border)

    info = Text()
    info.append(f"\n  Analisis generados: ", style=p.label)
    info.append(f"{n_analyses}", style=f"bold {p.number}")
    info.append(f"\n  Sesion guardada: ", style=p.label)
    info.append(f"{session_id}", style=f"bold {p.accent}")
    console.print(info)
    console.print()


def create_analysis_table(show_method: bool = True) -> Table:
    """Crea tabla para resultados de análisis."""
    p = get_palette()

    columns = []
    if show_method:
        columns.append(("Metodo Tc", "left"))
    columns.extend([
        ("Tr", "center"),
        ("Tc", "right"),
        ("tp", "right"),
        ("Tp", "right"),
        ("Qp", "right"),
        ("Vol", "right"),
    ])

    table = Table(
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE,
        show_header=True,
        padding=(0, 1),
    )

    for name, justify in columns:
        table.add_column(name, justify=justify)

    return table


def create_projects_table(title: str = None) -> Table:
    """Crea tabla para listar proyectos."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Cuencas", justify="right", style=p.number)
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def create_basins_table(title: str = None) -> Table:
    """Crea tabla para listar cuencas."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Area (ha)", justify="right", style=p.number)
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def create_sessions_table(title: str = None) -> Table:
    """Crea tabla para listar sesiones legacy."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def print_projects_table(projects: list[dict], title: str = "PROYECTOS") -> None:
    """Imprime tabla de proyectos."""
    console = get_console()
    p = get_palette()

    if not projects:
        console.print(f"  No hay proyectos.", style=p.muted)
        return

    table = create_projects_table(title)

    for proj in projects:
        name = proj['name'][:35] if len(proj['name']) > 35 else proj['name']
        table.add_row(
            proj['id'],
            name,
            str(proj.get('n_basins', 0)),
            str(proj.get('total_analyses', 0)),
        )

    console.print(table)


def print_basins_table(basins, title: str = "CUENCAS") -> None:
    """Imprime tabla de cuencas."""
    console = get_console()
    p = get_palette()

    if not basins:
        console.print(f"  No hay cuencas.", style=p.muted)
        return

    table = create_basins_table(title)

    for basin in basins:
        name = basin.name[:35] if len(basin.name) > 35 else basin.name
        table.add_row(
            basin.id,
            name,
            f"{basin.area_ha:.1f}",
            str(len(basin.analyses)),
        )

    console.print(table)


def print_sessions_table(sessions: list[dict], title: str = "SESIONES LEGACY") -> None:
    """Imprime tabla de sesiones legacy."""
    console = get_console()
    p = get_palette()

    if not sessions:
        console.print(f"  No hay sesiones.", style=p.muted)
        return

    table = create_sessions_table(title)

    for sess in sessions:
        name = sess['name'][:35] if len(sess['name']) > 35 else sess['name']
        table.add_row(
            sess['id'],
            name,
            str(sess.get('n_analyses', 0)),
        )

    console.print(table)
