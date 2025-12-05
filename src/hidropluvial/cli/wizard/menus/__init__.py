"""
Menus interactivos para el wizard.
"""

from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
from hidropluvial.cli.wizard.menus.project_management import ProjectManagementMenu
from hidropluvial.cli.wizard.menus.continue_project import ContinueProjectMenu
from hidropluvial.cli.wizard.menus.export_menu import ExportMenu, ExportBasinSelector

# Aliases para compatibilidad con código legacy
SessionManagementMenu = ProjectManagementMenu
ContinueSessionMenu = ContinueProjectMenu
ExportSessionSelector = ExportBasinSelector


# Funciones de conveniencia
def continue_project_menu() -> None:
    """Menu para continuar con un proyecto/cuenca existente."""
    menu = ContinueProjectMenu()
    menu.show()


def manage_projects_menu() -> None:
    """Menu para gestionar proyectos y cuencas."""
    menu = ProjectManagementMenu()
    menu.show()


def export_basin_menu() -> None:
    """Menu para exportar una cuenca."""
    menu = ExportBasinSelector()
    menu.show()


# Aliases legacy
continue_session_menu = continue_project_menu
manage_sessions_menu = manage_projects_menu
export_session_menu = export_basin_menu


__all__ = [
    # Nuevos nombres
    "PostExecutionMenu",
    "AddAnalysisMenu",
    "ProjectManagementMenu",
    "ContinueProjectMenu",
    "ExportMenu",
    "ExportBasinSelector",
    "continue_project_menu",
    "manage_projects_menu",
    "export_basin_menu",
    # Legacy aliases
    "SessionManagementMenu",
    "ContinueSessionMenu",
    "ExportSessionSelector",
    "continue_session_menu",
    "manage_sessions_menu",
    "export_session_menu",
]
