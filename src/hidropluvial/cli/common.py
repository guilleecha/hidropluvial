"""
Imports y utilidades comunes para módulos CLI.

Este módulo consolida los imports más usados en los comandos CLI
para reducir duplicación y facilitar mantenimiento.
"""

from typing import Annotated, Optional

import typer

# Re-exportar theme functions
from hidropluvial.cli.theme import (
    print_header,
    print_section,
    print_separator,
    print_field,
    print_note,
    print_success,
    print_warning,
    print_error,
    print_info,
    get_console,
    get_palette,
)

# Re-exportar validators
from hidropluvial.cli.validators import (
    validate_p310,
    validate_duration,
    validate_return_period,
    validate_area,
    validate_length,
    validate_slope,
    validate_c_coefficient,
    validate_cn,
)

__all__ = [
    # Typing
    "Annotated",
    "Optional",
    # Typer
    "typer",
    # Theme functions
    "print_header",
    "print_section",
    "print_separator",
    "print_field",
    "print_note",
    "print_success",
    "print_warning",
    "print_error",
    "print_info",
    "get_console",
    "get_palette",
    # Validators
    "validate_p310",
    "validate_duration",
    "validate_return_period",
    "validate_area",
    "validate_length",
    "validate_slope",
    "validate_c_coefficient",
    "validate_cn",
]
