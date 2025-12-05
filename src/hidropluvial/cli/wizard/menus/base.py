"""
Clase base para menus del wizard.
"""

from abc import ABC, abstractmethod
from typing import Optional

import typer
import questionary

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.wizard.styles import WIZARD_STYLE
from hidropluvial.session import Session, SessionManager


class BaseMenu(ABC):
    """Clase base abstracta para menus interactivos."""

    def __init__(self):
        self._manager: Optional[SessionManager] = None

    @property
    def manager(self) -> SessionManager:
        """Lazy loading del session manager."""
        if self._manager is None:
            self._manager = get_session_manager()
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

    def header(self, title: str, width: int = 65) -> None:
        """Muestra un encabezado formateado."""
        self.echo(f"\n{'='*width}")
        self.echo(f"  {title}")
        self.echo(f"{'='*width}")

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
    """Menu que opera sobre una sesion especifica."""

    def __init__(self, session: Session):
        super().__init__()
        self._session = session

    @property
    def session(self) -> Session:
        """Sesion actual."""
        return self._session

    def reload_session(self) -> None:
        """Recarga la sesion desde el manager."""
        self._session = self.manager.get_session(self._session.id)
