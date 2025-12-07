"""
Sistema de iconos para la CLI.

Proporciona iconos Unicode con fallback automático a ASCII
si el terminal no soporta Unicode.
"""

import sys
from dataclasses import dataclass
from typing import Optional


def _detect_unicode_support() -> bool:
    """Detecta si el terminal soporta caracteres Unicode."""
    try:
        encoding = getattr(sys.stdout, 'encoding', None) or 'ascii'
        # Probar con varios caracteres Unicode que usaremos
        test_chars = "❯◉○✓✗▸◂■□"
        test_chars.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


@dataclass
class IconSet:
    """Conjunto de iconos para la interfaz."""
    # Navegación y selección
    pointer: str          # Puntero en listas (opción actual)
    pointer_alt: str      # Puntero alternativo
    selected: str         # Item seleccionado (checkbox)
    unselected: str       # Item no seleccionado (checkbox)

    # Estados
    success: str          # Éxito/completado
    error: str            # Error/fallo
    warning: str          # Advertencia
    info: str             # Información
    question: str         # Pregunta

    # Navegación de menú
    back: str             # Volver atrás
    forward: str          # Avanzar
    up: str               # Subir
    down: str             # Bajar

    # Acciones
    add: str              # Agregar
    remove: str           # Eliminar
    edit: str             # Editar
    save: str             # Guardar

    # Indicadores
    bullet: str           # Viñeta
    arrow_right: str      # Flecha derecha
    arrow_left: str       # Flecha izquierda
    check: str            # Check/marca
    cross: str            # Cruz/X
    dot: str              # Punto

    # Separadores
    separator: str        # Separador horizontal
    pipe: str             # Pipe vertical


# Iconos Unicode (terminales modernos)
ICONS_UNICODE = IconSet(
    # Navegación y selección
    pointer="❯",
    pointer_alt="▸",
    selected="◉",
    unselected="○",

    # Estados
    success="✓",
    error="✗",
    warning="⚠",
    info="ℹ",
    question="?",

    # Navegación de menú
    back="←",
    forward="→",
    up="↑",
    down="↓",

    # Acciones
    add="+",
    remove="−",
    edit="✎",
    save="💾",

    # Indicadores
    bullet="•",
    arrow_right="→",
    arrow_left="←",
    check="✓",
    cross="✗",
    dot="·",

    # Separadores
    separator="─",
    pipe="│",
)


# Iconos ASCII (fallback para terminales sin Unicode)
ICONS_ASCII = IconSet(
    # Navegación y selección
    pointer=">",
    pointer_alt=">",
    selected="[x]",
    unselected="[ ]",

    # Estados
    success="[+]",
    error="[x]",
    warning="[!]",
    info="[i]",
    question="?",

    # Navegación de menú
    back="<-",
    forward="->",
    up="^",
    down="v",

    # Acciones
    add="+",
    remove="-",
    edit="*",
    save="[S]",

    # Indicadores
    bullet="*",
    arrow_right="->",
    arrow_left="<-",
    check="[+]",
    cross="[x]",
    dot=".",

    # Separadores
    separator="-",
    pipe="|",
)


# Cache del IconSet activo
_active_icons: Optional[IconSet] = None
_unicode_supported: Optional[bool] = None


def get_icons() -> IconSet:
    """Obtiene el conjunto de iconos apropiado para el terminal."""
    global _active_icons, _unicode_supported

    if _active_icons is None:
        _unicode_supported = _detect_unicode_support()
        _active_icons = ICONS_UNICODE if _unicode_supported else ICONS_ASCII

    return _active_icons


def supports_unicode() -> bool:
    """Retorna True si el terminal soporta Unicode."""
    global _unicode_supported

    if _unicode_supported is None:
        _unicode_supported = _detect_unicode_support()

    return _unicode_supported


def reset_icons_cache() -> None:
    """Resetea el cache de iconos (útil para tests)."""
    global _active_icons, _unicode_supported
    _active_icons = None
    _unicode_supported = None


# Acceso directo a iconos comunes
def icon(name: str) -> str:
    """Obtiene un icono por nombre."""
    icons = get_icons()
    return getattr(icons, name, "")
