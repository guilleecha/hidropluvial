"""
Menus interactivos para el wizard.
"""

from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
from hidropluvial.cli.wizard.menus.project_management import ProjectManagementMenu
from hidropluvial.cli.wizard.menus.basin_management import BasinManagementMenu
from hidropluvial.cli.wizard.menus.continue_project import ContinueProjectMenu
from hidropluvial.cli.wizard.menus.export_menu import ExportMenu, ExportBasinSelector


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


__all__ = [
    "PostExecutionMenu",
    "AddAnalysisMenu",
    "ProjectManagementMenu",
    "BasinManagementMenu",
    "ContinueProjectMenu",
    "ExportMenu",
    "ExportBasinSelector",
    "continue_project_menu",
    "manage_projects_menu",
    "export_basin_menu",
]
