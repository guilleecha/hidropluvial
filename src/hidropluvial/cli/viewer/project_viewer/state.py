"""
Estado y enums para el visor de proyectos.
"""

from enum import Enum


class ActivePanel(Enum):
    """Panel activo en la vista."""
    PROJECTS = "projects"
    BASINS = "basins"


class PopupMode(Enum):
    """Modo del popup activo."""
    NONE = "none"
    # Agregar cuenca
    ADD_BASIN = "add_basin"           # Nivel 1: Nueva o Importar
    SELECT_PROJECT = "select_project"  # Nivel 2: Elegir proyecto
    SELECT_BASIN = "select_basin"      # Nivel 3: Elegir cuenca
    # Editar cuenca
    EDIT_BASIN = "edit_basin"         # Elegir: Metadatos o Parámetros
    CONFIRM_EDIT_PARAMS = "confirm_edit_params"  # Confirmación para editar params
    # Crear proyecto
    CREATE_PROJECT = "create_project"  # Formulario para nuevo proyecto
