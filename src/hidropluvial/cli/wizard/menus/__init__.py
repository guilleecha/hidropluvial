"""
Menus interactivos para el wizard.
"""

from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu
from hidropluvial.cli.wizard.menus.basin_management import BasinManagementMenu
from hidropluvial.cli.wizard.menus.export_menu import ExportMenu, ExportBasinSelector


def export_basin_menu() -> None:
    """Menu para exportar una cuenca."""
    menu = ExportBasinSelector()
    menu.show()


__all__ = [
    "PostExecutionMenu",
    "AddAnalysisMenu",
    "BasinManagementMenu",
    "ExportMenu",
    "ExportBasinSelector",
    "export_basin_menu",
]
