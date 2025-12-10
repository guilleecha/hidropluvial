"""
Definicion de paletas de colores y gestion de temas.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from rich.console import Console
from rich.theme import Theme


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
    note: str         # Notas informativas (cyan distintivo)
    suggestion: str   # Sugerencias y recomendaciones

    # Colores para datos
    number: str       # Números y valores
    unit: str         # Unidades
    label: str        # Etiquetas

    # Bordes y separadores
    border: str       # Color de bordes
    header_bg: str    # Fondo de encabezados (para tablas)

    # Colores para tablas de coeficientes
    table_header: str    # Encabezados de tabla
    table_category: str  # Categorías en tablas
    table_highlight: str # Valores destacados en tablas

    # Colores para navegación interactiva
    nav_confirm: str     # Tecla de confirmación (Enter)
    nav_cancel: str      # Tecla de cancelación (Esc)
    nav_key: str         # Teclas de navegación (flechas, shortcuts)
    input_text: str      # Texto de entrada del usuario

    # Colores para estados de selección
    marked: str          # Items marcados para eliminación
    selected: str        # Item actualmente seleccionado/cursor


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
    note="#5fd7d7",         # Cyan brillante para notas
    suggestion="#5faf5f",   # Verde sugerencia (distintivo)
    number="#d7af5f",       # Amarillo para números
    unit="#87af87",         # Verde para unidades
    label="#afafaf",        # Gris claro para etiquetas
    border="#5f5f5f",       # Gris oscuro para bordes
    header_bg="#3a3a3a",    # Fondo oscuro para headers
    table_header="#5f87af", # Azul para headers de tabla
    table_category="#87afaf",  # Cyan para categorías
    table_highlight="#d7af5f", # Amarillo para valores destacados
    nav_confirm="#87af87",  # Verde para Enter/confirmar
    nav_cancel="#d75f5f",   # Rojo para Esc/cancelar
    nav_key="#af87af",      # Púrpura para teclas de navegación
    input_text="#ffffff",   # Blanco para texto de entrada
    marked="#d75f5f",       # Rojo para items marcados
    selected="#5f87af",     # Azul para item seleccionado
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
    note="#66d9ef",         # Cyan Monokai para notas
    suggestion="#a6e22e",   # Verde lima sugerencia
    number="#fd971f",       # Naranja
    unit="#a6e22e",         # Verde
    label="#f8f8f2",        # Blanco
    border="#49483e",       # Gris oscuro
    header_bg="#272822",    # Fondo Monokai
    table_header="#66d9ef", # Cyan para headers
    table_category="#a6e22e",  # Verde lima para categorías
    table_highlight="#fd971f", # Naranja para destacados
    nav_confirm="#a6e22e",  # Verde lima para Enter
    nav_cancel="#f92672",   # Rosa/rojo para Esc
    nav_key="#ae81ff",      # Púrpura para navegación
    input_text="#f8f8f2",   # Blanco para texto de entrada
    marked="#f92672",       # Rosa/rojo para items marcados
    selected="#66d9ef",     # Cyan para item seleccionado
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
    note="#88c0d0",         # Cyan Nord para notas
    suggestion="#a3be8c",   # Verde Nord sugerencia
    number="#d08770",       # Naranja
    unit="#a3be8c",         # Verde
    label="#d8dee9",        # Gris claro
    border="#3b4252",       # Gris oscuro
    header_bg="#2e3440",    # Fondo Nord
    table_header="#88c0d0", # Cyan para headers
    table_category="#81a1c1",  # Azul claro para categorías
    table_highlight="#d08770", # Naranja para destacados
    nav_confirm="#a3be8c",  # Verde para Enter
    nav_cancel="#bf616a",   # Rojo para Esc
    nav_key="#b48ead",      # Púrpura para navegación
    input_text="#eceff4",   # Blanco Nord para entrada
    marked="#bf616a",       # Rojo Nord para items marcados
    selected="#88c0d0",     # Cyan Nord para item seleccionado
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
    note="#5fafff",         # Azul para notas
    suggestion="#87d787",   # Verde suave sugerencia
    number="#ffffff",       # Blanco
    unit="#909090",         # Gris
    label="#909090",        # Gris
    border="#404040",       # Gris muy oscuro
    header_bg="#303030",    # Fondo oscuro
    table_header="#5fafff", # Azul para headers
    table_category="#b0b0b0",  # Gris claro para categorías
    table_highlight="#5fafff", # Azul para destacados
    nav_confirm="#87d787",  # Verde para Enter
    nav_cancel="#ff8787",   # Rojo para Esc
    nav_key="#5fafff",      # Azul para navegación
    input_text="#ffffff",   # Blanco para entrada
    marked="#ff8787",       # Rojo para items marcados
    selected="#5fafff",     # Azul para item seleccionado
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
                # Colores base
                "primary": p.primary,
                "secondary": p.secondary,
                "accent": p.accent,
                "success": p.success,
                "warning": p.warning,
                "error": p.error,
                "info": p.info,
                "muted": p.muted,
                "note": p.note,
                "suggestion": p.suggestion,
                "number": p.number,
                "unit": p.unit,
                "label": p.label,
                # Estilos compuestos
                "title": f"bold {p.primary}",
                "subtitle": p.secondary,
                "header": f"bold {p.primary}",
                "value": f"bold {p.number}",
                "param": p.label,
                # Tablas
                "table.header": f"bold {p.table_header}",
                "table.category": p.table_category,
                "table.highlight": f"bold {p.table_highlight}",
                # Navegación
                "nav.confirm": f"bold {p.nav_confirm}",
                "nav.cancel": f"bold {p.nav_cancel}",
                "nav.key": f"bold {p.nav_key}",
                "input": f"bold {p.input_text}",
                "input.cursor": f"blink bold {p.input_text}",
                # Estados de selección
                "marked": p.marked,
                "marked.bold": f"bold {p.marked}",
                "marked.reverse": f"bold {p.marked} reverse",
                "selected": f"bold {p.selected}",
            })
            cls._console = Console(theme=custom_theme)
        return cls._console


# Funciones de acceso global
def get_console() -> Console:
    """Obtiene la consola Rich con tema aplicado."""
    return CLITheme.get_console()


def get_palette() -> ColorPalette:
    """Obtiene la paleta de colores actual."""
    return CLITheme.get_palette()
