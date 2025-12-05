"""
Menus interactivos para el wizard.
"""

from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
from hidropluvial.cli.wizard.menus.session_management import SessionManagementMenu
from hidropluvial.cli.wizard.menus.continue_session import ContinueSessionMenu

# Funciones de conveniencia para mantener compatibilidad
def continue_session_menu() -> None:
    """Menu para continuar con una sesion existente."""
    menu = ContinueSessionMenu()
    menu.show()


def manage_sessions_menu() -> None:
    """Menu para gestionar sesiones."""
    menu = SessionManagementMenu()
    menu.show()


__all__ = [
    "PostExecutionMenu",
    "AddAnalysisMenu",
    "SessionManagementMenu",
    "ContinueSessionMenu",
    "continue_session_menu",
    "manage_sessions_menu",
]
