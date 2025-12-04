"""
Wizard - Asistente interactivo para analisis hidrologicos.

Estructura:
- config.py: Clase WizardConfig para recolectar datos
- runner.py: Clase AnalysisRunner para ejecutar analisis
- menus.py: Menus interactivos post-ejecucion
- main.py: Punto de entrada principal
"""

from hidropluvial.cli.wizard.main import wizard_main

__all__ = ["wizard_main"]
