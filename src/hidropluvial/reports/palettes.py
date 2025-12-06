"""
Paletas de colores para gráficos LaTeX/TikZ.

Proporciona esquemas de colores predefinidos para usar en los gráficos
de hidrogramas, hietogramas y comparaciones.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class ColorPalette:
    """Define una paleta de colores para gráficos."""
    name: str
    description: str
    colors: list[str]
    styles: list[str]
    fill_color: str = "blue!30"
    hyetograph_bar: str = "blue!70"

    def get_color(self, index: int) -> str:
        """Obtiene color por índice (cíclico)."""
        return self.colors[index % len(self.colors)]

    def get_style(self, index: int) -> str:
        """Obtiene estilo por índice (cíclico)."""
        return self.styles[index % len(self.styles)]


# Paletas predefinidas
PALETTES = {
    "default": ColorPalette(
        name="default",
        description="Paleta estándar con colores distinguibles",
        colors=[
            "black", "red", "blue", "green!60!black", "orange", "purple",
            "brown", "cyan", "magenta", "olive"
        ],
        styles=[
            "solid", "dashed", "dotted", "dashdotted", "solid",
            "dashed", "dotted", "dashdotted", "solid", "dashed"
        ],
        fill_color="blue!30",
        hyetograph_bar="blue!70",
    ),

    "professional": ColorPalette(
        name="professional",
        description="Paleta sobria para documentos técnicos",
        colors=[
            "black", "gray!60", "blue!80!black", "red!80!black",
            "green!60!black", "orange!80!black"
        ],
        styles=[
            "solid", "dashed", "solid", "dashed", "solid", "dashed"
        ],
        fill_color="gray!20",
        hyetograph_bar="gray!50",
    ),

    "colorful": ColorPalette(
        name="colorful",
        description="Paleta vibrante con colores saturados",
        colors=[
            "blue", "red", "green!80!black", "orange", "purple",
            "cyan", "magenta", "yellow!80!black", "pink", "teal"
        ],
        styles=[
            "solid", "solid", "solid", "solid", "solid",
            "solid", "solid", "solid", "solid", "solid"
        ],
        fill_color="cyan!30",
        hyetograph_bar="blue!60",
    ),

    "grayscale": ColorPalette(
        name="grayscale",
        description="Escala de grises para impresión B/N",
        colors=[
            "black", "gray!70", "gray!40", "gray!20",
            "black", "gray!70", "gray!40", "gray!20"
        ],
        styles=[
            "solid", "dashed", "dotted", "dashdotted",
            "densely dashed", "densely dotted", "loosely dashed", "loosely dotted"
        ],
        fill_color="gray!15",
        hyetograph_bar="gray!40",
    ),

    "contrast": ColorPalette(
        name="contrast",
        description="Alto contraste, solo línea continua",
        colors=[
            "blue!90!black", "red!90!black", "green!70!black",
            "orange!90!black", "purple!90!black", "cyan!80!black"
        ],
        styles=[
            "very thick", "thick", "very thick", "thick", "very thick", "thick"
        ],
        fill_color="blue!20",
        hyetograph_bar="blue!50",
    ),

    "hydrology": ColorPalette(
        name="hydrology",
        description="Paleta temática para hidrología (azules/verdes)",
        colors=[
            "blue!80!black", "cyan!70!black", "teal!80!black",
            "green!60!black", "blue!50!black", "cyan!50!black"
        ],
        styles=[
            "solid", "dashed", "dotted", "dashdotted", "solid", "dashed"
        ],
        fill_color="cyan!25",
        hyetograph_bar="blue!60",
    ),
}


class PaletteType(str, Enum):
    """Tipos de paleta disponibles."""
    DEFAULT = "default"
    PROFESSIONAL = "professional"
    COLORFUL = "colorful"
    GRAYSCALE = "grayscale"
    CONTRAST = "contrast"
    HYDROLOGY = "hydrology"


def get_palette(name: str = "default") -> ColorPalette:
    """
    Obtiene una paleta por nombre.

    Args:
        name: Nombre de la paleta

    Returns:
        ColorPalette correspondiente

    Raises:
        ValueError: Si la paleta no existe
    """
    name = name.lower()
    if name not in PALETTES:
        available = ", ".join(PALETTES.keys())
        raise ValueError(f"Paleta '{name}' no encontrada. Disponibles: {available}")
    return PALETTES[name]


def list_palettes() -> list[dict]:
    """
    Lista todas las paletas disponibles.

    Returns:
        Lista de diccionarios con info de cada paleta
    """
    return [
        {
            "name": p.name,
            "description": p.description,
            "n_colors": len(p.colors),
        }
        for p in PALETTES.values()
    ]


# Paleta activa global (para uso interno)
_active_palette: Optional[ColorPalette] = None


def set_active_palette(name: str) -> None:
    """Establece la paleta activa globalmente."""
    global _active_palette
    _active_palette = get_palette(name)


def get_active_palette() -> ColorPalette:
    """Obtiene la paleta activa (default si no se estableció)."""
    global _active_palette
    if _active_palette is None:
        _active_palette = PALETTES["default"]
    return _active_palette


def get_series_colors(palette: str = None) -> list[str]:
    """
    Obtiene la lista de colores para series.

    Args:
        palette: Nombre de paleta (None usa la activa)

    Returns:
        Lista de colores LaTeX/TikZ
    """
    if palette:
        return get_palette(palette).colors
    return get_active_palette().colors


def get_series_styles(palette: str = None) -> list[str]:
    """
    Obtiene la lista de estilos para series.

    Args:
        palette: Nombre de paleta (None usa la activa)

    Returns:
        Lista de estilos TikZ
    """
    if palette:
        return get_palette(palette).styles
    return get_active_palette().styles
