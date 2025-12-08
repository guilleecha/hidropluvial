# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para HidroPluvial.

Para generar el ejecutable:
    pyinstaller hidropluvial.spec

El ejecutable se genera en dist/hidropluvial/
"""

import sys
from pathlib import Path

# Ruta base del proyecto
BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

block_cipher = None

# Archivos de datos a incluir
datas = [
    # Archivos JSON con tablas de coeficientes
    (str(SRC_DIR / "hidropluvial" / "data" / "*.json"), "hidropluvial/data"),
]

# Verificar si hay templates LaTeX
templates_dir = SRC_DIR / "hidropluvial" / "reports" / "templates"
if templates_dir.exists():
    datas.append((str(templates_dir / "*"), "hidropluvial/reports/templates"))

# Hidden imports - todos los módulos del paquete
hiddenimports = [
    # =========================================
    # Módulos principales de hidropluvial
    # =========================================
    "hidropluvial",
    "hidropluvial.config",
    "hidropluvial.database",
    "hidropluvial.project",

    # Core - cálculos hidrológicos
    "hidropluvial.core",
    "hidropluvial.core.coefficients",
    "hidropluvial.core.hydrograph",
    "hidropluvial.core.idf",
    "hidropluvial.core.runoff",
    "hidropluvial.core.tc",
    "hidropluvial.core.temporal",

    # Models - Pydantic
    "hidropluvial.models",
    "hidropluvial.models.analysis",
    "hidropluvial.models.base",
    "hidropluvial.models.basin",
    "hidropluvial.models.coverage",
    "hidropluvial.models.hydrograph",
    "hidropluvial.models.project",
    "hidropluvial.models.storm",
    "hidropluvial.models.tc",

    # Database - SQLite
    "hidropluvial.database",
    "hidropluvial.database.connection",
    "hidropluvial.database.projects",
    "hidropluvial.database.basins",
    "hidropluvial.database.analyses",

    # Data - carga de coeficientes
    "hidropluvial.data",
    "hidropluvial.data.coefficient_loader",

    # Reports - generación LaTeX
    "hidropluvial.reports",
    "hidropluvial.reports.charts",
    "hidropluvial.reports.compiler",
    "hidropluvial.reports.generator",
    "hidropluvial.reports.palettes",
    "hidropluvial.reports.methodology",
    "hidropluvial.reports.methodology.hydrograph",
    "hidropluvial.reports.methodology.runoff",
    "hidropluvial.reports.methodology.storms",
    "hidropluvial.reports.methodology.tc",

    # =========================================
    # CLI - interfaz de línea de comandos
    # =========================================
    "hidropluvial.cli",
    "hidropluvial.cli.commands",
    "hidropluvial.cli.common",
    "hidropluvial.cli.export",
    "hidropluvial.cli.formatters",
    "hidropluvial.cli.hydrograph",
    "hidropluvial.cli.idf",
    "hidropluvial.cli.interactive_viewer",
    "hidropluvial.cli.output_manager",
    "hidropluvial.cli.preview",
    "hidropluvial.cli.report",
    "hidropluvial.cli.runoff",
    "hidropluvial.cli.storm",
    "hidropluvial.cli.tc",
    "hidropluvial.cli.validators",

    # CLI Basin
    "hidropluvial.cli.basin",
    "hidropluvial.cli.basin.commands",
    "hidropluvial.cli.basin.export",
    "hidropluvial.cli.basin.preview",
    "hidropluvial.cli.basin.report",

    # CLI Project
    "hidropluvial.cli.project",
    "hidropluvial.cli.project.base",
    "hidropluvial.cli.project.basin",
    "hidropluvial.cli.project.report",

    # CLI Theme
    "hidropluvial.cli.theme",
    "hidropluvial.cli.theme.icons",
    "hidropluvial.cli.theme.palette",
    "hidropluvial.cli.theme.printing",
    "hidropluvial.cli.theme.styled",
    "hidropluvial.cli.theme.tables",

    # CLI Viewer
    "hidropluvial.cli.viewer",
    "hidropluvial.cli.viewer.basin_viewer",
    "hidropluvial.cli.viewer.components",
    "hidropluvial.cli.viewer.filters",
    "hidropluvial.cli.viewer.main",
    "hidropluvial.cli.viewer.plots",
    "hidropluvial.cli.viewer.project_viewer",
    "hidropluvial.cli.viewer.table_viewer",
    "hidropluvial.cli.viewer.terminal",

    # CLI Wizard
    "hidropluvial.cli.wizard",
    "hidropluvial.cli.wizard.config",
    "hidropluvial.cli.wizard.main",
    "hidropluvial.cli.wizard.runner",
    "hidropluvial.cli.wizard.styles",

    # CLI Wizard Menus
    "hidropluvial.cli.wizard.menus",
    "hidropluvial.cli.wizard.menus.add_analysis",
    "hidropluvial.cli.wizard.menus.base",
    "hidropluvial.cli.wizard.menus.basin_management",
    "hidropluvial.cli.wizard.menus.continue_project",
    "hidropluvial.cli.wizard.menus.cuenca_editor",
    "hidropluvial.cli.wizard.menus.export_menu",
    "hidropluvial.cli.wizard.menus.post_execution",

    # CLI Wizard Steps
    "hidropluvial.cli.wizard.steps",
    "hidropluvial.cli.wizard.steps.base",
    "hidropluvial.cli.wizard.steps.datos_cuenca",
    "hidropluvial.cli.wizard.steps.escorrentia",
    "hidropluvial.cli.wizard.steps.nrcs_config",
    "hidropluvial.cli.wizard.steps.tc_tormenta",

    # =========================================
    # Dependencias externas
    # =========================================

    # Questionary / Prompt Toolkit (CLI interactivo)
    "questionary",
    "questionary.prompts",
    "questionary.prompts.select",
    "questionary.prompts.checkbox",
    "questionary.prompts.text",
    "questionary.prompts.confirm",
    "prompt_toolkit",
    "prompt_toolkit.application",
    "prompt_toolkit.application.current",
    "prompt_toolkit.buffer",
    "prompt_toolkit.document",
    "prompt_toolkit.enums",
    "prompt_toolkit.filters",
    "prompt_toolkit.formatted_text",
    "prompt_toolkit.history",
    "prompt_toolkit.input",
    "prompt_toolkit.key_binding",
    "prompt_toolkit.key_binding.bindings",
    "prompt_toolkit.key_binding.key_processor",
    "prompt_toolkit.keys",
    "prompt_toolkit.layout",
    "prompt_toolkit.lexers",
    "prompt_toolkit.output",
    "prompt_toolkit.renderer",
    "prompt_toolkit.search",
    "prompt_toolkit.selection",
    "prompt_toolkit.shortcuts",
    "prompt_toolkit.styles",
    "prompt_toolkit.validation",
    "prompt_toolkit.widgets",
    "wcwidth",
    "pygments",
    "pygments.lexers",
    "pygments.styles",

    # Rich (tablas y formato)
    "rich",
    "rich.console",
    "rich.table",
    "rich.text",
    "rich.panel",
    "rich.box",
    "rich.live",
    "rich.spinner",
    "rich.progress",
    "rich.style",
    "rich.theme",
    "rich.markup",

    # Typer / Click (CLI framework)
    "typer",
    "typer.main",
    "typer.core",
    "click",
    "click.core",
    "click.decorators",
    "click.exceptions",
    "click.types",

    # Pydantic (validación)
    "pydantic",
    "pydantic.fields",
    "pydantic.main",
    "pydantic.types",
    "pydantic_core",

    # NumPy / SciPy (cálculos)
    "numpy",
    "numpy.core",
    "numpy.core._methods",
    "numpy.core._dtype_ctypes",
    "numpy.lib",
    "numpy.lib.format",
    "numpy.random",
    "scipy",
    "scipy.special",
    "scipy.special._ufuncs",
    "scipy.special._cdflib",
    "scipy.interpolate",
    "scipy.integrate",

    # Pandas (tablas)
    "pandas",
    "pandas.core",
    "pandas.core.frame",
    "pandas._libs",
    "pandas._libs.lib",

    # Otros
    "yaml",
    "jinja2",
    "jinja2.environment",
    "jinja2.loaders",
    "openpyxl",
    "openpyxl.workbook",
    "openpyxl.worksheet",
    "plotext",
    "sqlite3",
]

# Excluir módulos no necesarios para reducir tamaño
excludes = [
    "tkinter",
    "matplotlib",
    "PIL",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
    "docutils",
    "_tkinter",
    "test",
    "unittest",
]

a = Analysis(
    [str(SRC_DIR / "hidropluvial" / "__main__.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hidropluvial",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE_DIR / "assets" / "icon.ico") if (BASE_DIR / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="hidropluvial",
)
