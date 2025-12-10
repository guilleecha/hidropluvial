"""
Visor interactivo de proyectos y cuencas.

Módulo refactorizado con estructura:
- state.py: Enums de estado (ActivePanel, PopupMode)
- popups.py: Builders de popups
- builders.py: Builders de tablas y display
- actions.py: Handlers de acciones
- viewer.py: Loop principal interactivo
"""

from .viewer import interactive_project_viewer
from .state import ActivePanel, PopupMode

__all__ = [
    "interactive_project_viewer",
    "ActivePanel",
    "PopupMode",
]
