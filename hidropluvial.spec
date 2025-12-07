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
    # Templates LaTeX si existen
]

# Verificar si hay templates
templates_dir = SRC_DIR / "hidropluvial" / "reports" / "templates"
if templates_dir.exists():
    datas.append((str(templates_dir / "*"), "hidropluvial/reports/templates"))

# Imports ocultos que PyInstaller podría no detectar
hiddenimports = [
    "hidropluvial",
    "hidropluvial.cli",
    "hidropluvial.cli.main",
    "hidropluvial.cli.wizard",
    "hidropluvial.core",
    "hidropluvial.config",
    "questionary",
    "prompt_toolkit",
    "wcwidth",
    "numpy",
    "scipy",
    "scipy.special",
    "scipy.interpolate",
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
    excludes=[
        # Excluir módulos no necesarios para reducir tamaño
        "tkinter",
        "matplotlib",  # Solo si no se usa para gráficos en CLI
        "PIL",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
    ],
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
    upx=True,  # Comprimir con UPX si está disponible
    console=True,  # Aplicación de consola (necesario para CLI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Descomentar si hay icono
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
