"""
Clase base para menus del wizard.
"""

from abc import ABC, abstractmethod
from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.project import get_project_manager, ProjectManager
from hidropluvial.cli.theme import (
    print_header, print_section, print_success, print_warning,
    print_error, print_info, print_note, print_basin_info, print_project_info,
)


class BaseMenu(ABC):
    """Clase base abstracta para menus interactivos."""

    def __init__(self):
        self._manager: Optional[ProjectManager] = None

    @property
    def manager(self) -> ProjectManager:
        """Lazy loading del project manager."""
        if self._manager is None:
            self._manager = get_project_manager()
        return self._manager

    @property
    def style(self):
        """Estilo de questionary."""
        return WIZARD_STYLE

    @abstractmethod
    def show(self) -> None:
        """Muestra el menu. Debe ser implementado por subclases."""
        pass

    def echo(self, message: str) -> None:
        """Wrapper para typer.echo."""
        typer.echo(message)

    def header(self, title: str, subtitle: str = None) -> None:
        """Muestra un encabezado formateado con estilo."""
        print_header(title, subtitle)

    def section(self, title: str) -> None:
        """Muestra título de sección."""
        print_section(title)

    def success(self, message: str) -> None:
        """Muestra mensaje de éxito."""
        print_success(message)

    def warning(self, message: str) -> None:
        """Muestra advertencia."""
        print_warning(message)

    def error(self, message: str) -> None:
        """Muestra error."""
        print_error(message)

    def info(self, message: str) -> None:
        """Muestra información."""
        print_info(message)

    def note(self, message: str) -> None:
        """Muestra nota destacada."""
        print_note(message)

    def basin_info(self, basin, project_name: str = None) -> None:
        """Muestra información de cuenca en panel estilizado."""
        trs = None
        if hasattr(basin, 'analyses') and basin.analyses:
            trs = sorted(set(a.storm.return_period for a in basin.analyses))

        print_basin_info(
            basin_name=basin.name,
            basin_id=basin.id,
            project_name=project_name,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            n_analyses=len(basin.analyses) if hasattr(basin, 'analyses') else None,
            return_periods=trs,
            c=basin.c if hasattr(basin, 'c') else None,
            cn=basin.cn if hasattr(basin, 'cn') else None,
        )

    def project_info(self, project) -> None:
        """Muestra información de proyecto en panel estilizado."""
        n_analyses = sum(len(b.analyses) for b in project.basins) if project.basins else 0

        print_project_info(
            project_name=project.name,
            project_id=project.id,
            n_basins=len(project.basins) if project.basins else 0,
            n_analyses=n_analyses,
            description=project.description if hasattr(project, 'description') else None,
            author=project.author if hasattr(project, 'author') else None,
            location=project.location if hasattr(project, 'location') else None,
        )

    def session_info(self, basin) -> None:
        """Muestra información de cuenca en panel estilizado (legacy compatibility)."""
        trs = None
        if hasattr(basin, 'analyses') and basin.analyses:
            trs = sorted(set(a.storm.return_period for a in basin.analyses))

        print_basin_info(
            basin_name=basin.name,
            basin_id=basin.id,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            n_analyses=len(basin.analyses) if hasattr(basin, 'analyses') else None,
            return_periods=trs,
            c=basin.c if hasattr(basin, 'c') else None,
            cn=basin.cn if hasattr(basin, 'cn') else None,
        )

    def select(self, message: str, choices: list[str]) -> Optional[str]:
        """Muestra un menu de seleccion."""
        return questionary.select(
            message,
            choices=choices,
            style=self.style,
        ).ask()

    def checkbox(self, message: str, choices: list) -> Optional[list]:
        """Muestra un menu de checkbox."""
        return questionary.checkbox(
            message,
            choices=choices,
            style=self.style,
        ).ask()

    def confirm(self, message: str, default: bool = True) -> bool:
        """Muestra confirmacion."""
        result = questionary.confirm(
            message,
            default=default,
            style=self.style,
        ).ask()
        return result if result is not None else False

    def text(self, message: str, default: str = "") -> Optional[str]:
        """Solicita texto."""
        return questionary.text(
            message,
            default=default,
            style=self.style,
        ).ask()

    def ask_float(self, prompt: str, current: Optional[float]) -> Optional[float]:
        """Solicita un valor float, retorna None si no cambia."""
        default_str = f"{current:.2f}" if current else ""
        val = self.text(prompt, default=default_str)
        if val is None:
            return None
        val = val.strip()
        if val == "" or val == default_str:
            return None
        try:
            return float(val)
        except ValueError:
            self.echo(f"  Valor invalido, se mantiene {current}")
            return None

    def ask_int(self, prompt: str, current: Optional[int]) -> Optional[int]:
        """Solicita un valor int, retorna None si no cambia."""
        default_str = str(current) if current else ""
        val = self.text(prompt, default=default_str)
        if val is None:
            return None
        val = val.strip()
        if val == "" or val == default_str:
            return None
        try:
            return int(val)
        except ValueError:
            self.echo(f"  Valor invalido, se mantiene {current}")
            return None


class SessionMenu(BaseMenu):
    """Menu que opera sobre una cuenca especifica."""

    def __init__(self, basin):
        super().__init__()
        from hidropluvial.models import Basin
        self._basin = basin

    @property
    def basin(self):
        """Basin object."""
        return self._basin

    def reload_session(self) -> None:
        """Recarga la cuenca desde el manager (no-op for now)."""
        # Basin objects are typically managed by project, so this is a no-op
        # Subclasses that need reloading should override this
        pass

    def show_analysis_cards(self, analyses: list = None, name: str = None) -> None:
        """
        Muestra el visor interactivo de fichas de analisis.

        Args:
            analyses: Lista de analisis (default: self.basin.analyses)
            name: Nombre a mostrar (default: self.basin.name)
        """
        if analyses is None:
            analyses = self._basin.analyses
        if name is None:
            name = self._basin.name

        if not analyses:
            self.echo("  No hay analisis disponibles.")
            return

        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer
        interactive_hydrograph_viewer(analyses, name)
