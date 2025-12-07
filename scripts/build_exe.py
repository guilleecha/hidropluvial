#!/usr/bin/env python
"""
Script para generar el ejecutable de HidroPluvial.

Uso:
    python scripts/build_exe.py

Requisitos:
    pip install pyinstaller

El ejecutable se genera en dist/hidropluvial/
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    # Rutas
    project_root = Path(__file__).parent.parent
    spec_file = project_root / "hidropluvial.spec"
    dist_dir = project_root / "dist" / "hidropluvial"

    print("=" * 60)
    print("  HIDROPLUVIAL - Generador de Ejecutable")
    print("=" * 60)
    print()

    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller no esta instalado.")
        print("Ejecute: pip install pyinstaller")
        sys.exit(1)

    # Verificar spec file
    if not spec_file.exists():
        print(f"ERROR: No se encontro {spec_file}")
        sys.exit(1)

    print(f"Spec file: {spec_file}")
    print()

    # Ejecutar PyInstaller
    print("Compilando ejecutable...")
    print("-" * 60)

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"],
        cwd=project_root,
    )

    if result.returncode != 0:
        print()
        print("ERROR: La compilacion fallo.")
        sys.exit(1)

    print("-" * 60)
    print()

    # Copiar archivos adicionales
    print("Copiando archivos adicionales...")

    # LEEME.txt
    leeme_src = project_root / "dist" / "hidropluvial" / "LEEME.txt"
    if not leeme_src.exists():
        leeme_content = """================================================================================
                    HIDROPLUVIAL - Herramienta de Calculos Hidrologicos
================================================================================

INICIO RAPIDO: Haga doble clic en "EJECUTAR.bat"

Para mas informacion, visite: https://github.com/guilleecha/hidropluvial
================================================================================
"""
        leeme_src.write_text(leeme_content, encoding="utf-8")

    # EJECUTAR.bat
    bat_src = dist_dir / "EJECUTAR.bat"
    if not bat_src.exists():
        bat_content = """@echo off
chcp 65001 > nul
title HidroPluvial - Herramienta de Calculos Hidrologicos
echo.
echo  ============================================
echo   HIDROPLUVIAL - Calculos Hidrologicos
echo  ============================================
echo.
echo  Iniciando asistente interactivo...
echo.
"%~dp0hidropluvial.exe" wizard
echo.
pause
"""
        bat_src.write_text(bat_content, encoding="utf-8")

    # Mostrar resultado
    print()
    print("=" * 60)
    print("  COMPILACION EXITOSA")
    print("=" * 60)
    print()
    print(f"Ejecutable generado en: {dist_dir}")
    print()

    # Mostrar tamaño
    exe_path = dist_dir / "hidropluvial.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"Tamano del ejecutable: {size_mb:.1f} MB")

    # Mostrar contenido
    print()
    print("Contenido de la carpeta:")
    for item in sorted(dist_dir.iterdir()):
        if item.is_file():
            size = item.stat().st_size
            if size > 1024 * 1024:
                print(f"  {item.name:<30} {size / (1024*1024):.1f} MB")
            elif size > 1024:
                print(f"  {item.name:<30} {size / 1024:.1f} KB")
            else:
                print(f"  {item.name:<30} {size} bytes")
        else:
            print(f"  {item.name:<30} [carpeta]")

    print()
    print("Para distribuir, comprima la carpeta 'dist/hidropluvial' en un ZIP.")
    print()


if __name__ == "__main__":
    main()
