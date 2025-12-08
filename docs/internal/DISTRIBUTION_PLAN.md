# HidroPluvial - Plan de Distribución

## Resumen

Este documento detalla los 3 métodos de distribución para HidroPluvial:

1. **PyPI** - `pip install hidropluvial`
2. **Ejecutable Windows** - `.exe` standalone
3. **Instalador Windows** - `.msi` con wizard

---

## 1. Distribución PyPI

### Requisitos previos
- Cuenta en [PyPI](https://pypi.org/account/register/)
- Cuenta en [Test PyPI](https://test.pypi.org/account/register/) (para pruebas)
- Token de API de PyPI

### Configuración actual

El `pyproject.toml` ya está configurado correctamente:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hidropluvial"
version = "0.1.0"
# ...

[project.scripts]
hidropluvial = "hidropluvial.cli:app"
hp = "hidropluvial.cli:app"
```

### Pasos para publicar

```bash
# 1. Instalar herramientas de build
pip install build twine

# 2. Construir paquete
python -m build

# 3. Verificar el paquete
twine check dist/*

# 4. Subir a Test PyPI (prueba)
twine upload --repository testpypi dist/*

# 5. Probar instalación desde Test PyPI
pip install --index-url https://test.pypi.org/simple/ hidropluvial

# 6. Subir a PyPI (producción)
twine upload dist/*
```

### Automatización con GitHub Actions

Ver sección de CI/CD más abajo.

### Versionamiento

Usar [Semantic Versioning](https://semver.org/):
- `0.1.0` → `0.1.1` (patch: bugfixes)
- `0.1.0` → `0.2.0` (minor: nuevas features)
- `0.1.0` → `1.0.0` (major: breaking changes)

Actualizar versión en:
1. `pyproject.toml` → `version = "x.y.z"`
2. Crear tag en git: `git tag v0.1.0`

---

## 2. Ejecutable Windows (PyInstaller)

### Objetivo
Generar un ejecutable `.exe` que no requiera Python instalado.

### Estructura de salida

```
dist/
└── hidropluvial/
    ├── hidropluvial.exe      # Ejecutable principal
    ├── python311.dll         # Runtime Python
    ├── hidropluvial/         # Módulos del paquete
    │   └── data/             # Archivos JSON
    └── [otras DLLs]
```

### Spec file actualizado

```python
# hidropluvial.spec
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para HidroPluvial.

Generar ejecutable:
    pyinstaller hidropluvial.spec

Generar ejecutable único (más lento de iniciar):
    pyinstaller hidropluvial.spec --onefile
"""

import sys
from pathlib import Path

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

block_cipher = None

# Datos a incluir
datas = [
    # Archivos JSON con tablas de coeficientes
    (str(SRC_DIR / "hidropluvial" / "data"), "hidropluvial/data"),
]

# Templates LaTeX si existen
templates_dir = SRC_DIR / "hidropluvial" / "reports" / "templates"
if templates_dir.exists():
    datas.append((str(templates_dir), "hidropluvial/reports/templates"))

# Hidden imports
hiddenimports = [
    # Core
    "hidropluvial",
    "hidropluvial.cli",
    "hidropluvial.cli.main",
    "hidropluvial.cli.wizard",
    "hidropluvial.cli.wizard.main",
    "hidropluvial.cli.wizard.runner",
    "hidropluvial.cli.wizard.config",
    "hidropluvial.cli.viewer",
    "hidropluvial.cli.viewer.table_viewer",
    "hidropluvial.cli.viewer.project_viewer",
    "hidropluvial.cli.viewer.basin_viewer",
    "hidropluvial.core",
    "hidropluvial.config",
    "hidropluvial.database",
    "hidropluvial.models",
    "hidropluvial.project",

    # Dependencias que PyInstaller puede no detectar
    "questionary",
    "prompt_toolkit",
    "prompt_toolkit.application",
    "prompt_toolkit.key_binding",
    "prompt_toolkit.styles",
    "wcwidth",
    "pygments",
    "rich",
    "rich.console",
    "rich.table",
    "rich.live",

    # Científicas
    "numpy",
    "numpy.core._methods",
    "numpy.lib.format",
    "scipy",
    "scipy.special",
    "scipy.special._ufuncs",
    "scipy.interpolate",
    "pandas",
    "pandas._libs",

    # Otras
    "pydantic",
    "pydantic.fields",
    "typer",
    "click",
    "yaml",
    "openpyxl",
    "jinja2",
    "plotext",
]

# Excluir módulos innecesarios para reducir tamaño
excludes = [
    "tkinter",
    "matplotlib",  # Usamos plotext para terminal
    "PIL",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
    "docutils",
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
```

### Comandos de build

```bash
# Instalar PyInstaller
pip install pyinstaller

# Build estándar (carpeta con múltiples archivos)
pyinstaller hidropluvial.spec

# Build onefile (un solo .exe, más lento de iniciar)
pyinstaller hidropluvial.spec --onefile

# El ejecutable estará en dist/hidropluvial/
```

### Prueba del ejecutable

```bash
# Desde la carpeta dist/hidropluvial/
.\hidropluvial.exe --help
.\hidropluvial.exe wizard
```

### Tamaño estimado
- Carpeta completa: ~150-200 MB
- OneFile: ~80-100 MB (comprimido)

---

## 3. Instalador Windows (MSI/NSIS)

### Opción A: Inno Setup (Recomendado)

[Inno Setup](https://jrsoftware.org/isinfo.php) es gratuito y genera instaladores profesionales.

#### Instalación de Inno Setup
1. Descargar de https://jrsoftware.org/isdl.php
2. Instalar con opciones por defecto

#### Script de Inno Setup

```iss
; hidropluvial.iss
; Inno Setup Script para HidroPluvial

#define MyAppName "HidroPluvial"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "HidroPluvial Team"
#define MyAppURL "https://github.com/guilleecha/hidropluvial"
#define MyAppExeName "hidropluvial.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=HidroPluvial-{#MyAppVersion}-Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Agregar al PATH del sistema"; GroupDescription: "Opciones adicionales:"

[Files]
Source: "dist\hidropluvial\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[Registry]
; Agregar al PATH si se selecciona
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath('{app}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
```

#### Generar instalador

```bash
# Primero generar el ejecutable
pyinstaller hidropluvial.spec

# Luego compilar el instalador (desde línea de comandos)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" hidropluvial.iss

# El instalador estará en installer/HidroPluvial-0.1.0-Setup.exe
```

### Opción B: NSIS (Alternativa)

[NSIS](https://nsis.sourceforge.io/) es otra opción popular pero con sintaxis más compleja.

### Opción C: WiX Toolset (MSI nativo)

Para generar `.msi` nativo de Windows, usar [WiX Toolset](https://wixtoolset.org/).
Más complejo pero genera instaladores MSI estándar de Windows.

---

## 4. CI/CD con GitHub Actions

### Workflow completo

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  # ============================================
  # Build y publicar en PyPI
  # ============================================
  pypi:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install build tools
        run: pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*

  # ============================================
  # Build ejecutable Windows
  # ============================================
  windows-exe:
    name: Build Windows Executable
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pyinstaller

      - name: Build executable
        run: pyinstaller hidropluvial.spec

      - name: Create ZIP
        run: |
          Compress-Archive -Path dist/hidropluvial -DestinationPath dist/HidroPluvial-Windows.zip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-exe
          path: dist/HidroPluvial-Windows.zip

  # ============================================
  # Build instalador Windows
  # ============================================
  windows-installer:
    name: Build Windows Installer
    runs-on: windows-latest
    needs: windows-exe
    steps:
      - uses: actions/checkout@v4

      - name: Download executable
        uses: actions/download-artifact@v4
        with:
          name: windows-exe

      - name: Extract executable
        run: |
          Expand-Archive -Path HidroPluvial-Windows.zip -DestinationPath dist/

      - name: Install Inno Setup
        run: |
          choco install innosetup -y

      - name: Build installer
        run: |
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" hidropluvial.iss

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-installer
          path: installer/*.exe

  # ============================================
  # Crear GitHub Release
  # ============================================
  release:
    name: Create Release
    runs-on: ubuntu-latest
    needs: [pypi, windows-exe, windows-installer]
    steps:
      - uses: actions/checkout@v4

      - name: Download Windows EXE
        uses: actions/download-artifact@v4
        with:
          name: windows-exe
          path: release/

      - name: Download Windows Installer
        uses: actions/download-artifact@v4
        with:
          name: windows-installer
          path: release/

      - name: Get version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          name: HidroPluvial v${{ steps.version.outputs.VERSION }}
          draft: false
          prerelease: false
          files: |
            release/HidroPluvial-Windows.zip
            release/HidroPluvial-*-Setup.exe
          body: |
            ## HidroPluvial v${{ steps.version.outputs.VERSION }}

            ### Instalación

            **Opción 1: pip (requiere Python 3.11+)**
            ```bash
            pip install hidropluvial
            ```

            **Opción 2: Instalador Windows**
            Descargar `HidroPluvial-${{ steps.version.outputs.VERSION }}-Setup.exe`

            **Opción 3: Ejecutable portable**
            Descargar y extraer `HidroPluvial-Windows.zip`

            ### Cambios
            Ver [CHANGELOG.md](CHANGELOG.md)
```

### Secrets necesarios en GitHub

1. Ir a Settings → Secrets and variables → Actions
2. Agregar:
   - `PYPI_API_TOKEN`: Token de API de PyPI

---

## 5. Proceso de Release

### Checklist pre-release

- [ ] Todos los tests pasan
- [ ] Documentación actualizada
- [ ] CHANGELOG.md actualizado
- [ ] Versión actualizada en `pyproject.toml`

### Comandos para release

```bash
# 1. Asegurar que estás en develop y actualizado
git checkout develop
git pull

# 2. Actualizar versión en pyproject.toml
# Editar: version = "0.2.0"

# 3. Actualizar CHANGELOG.md

# 4. Commit de versión
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.2.0"

# 5. Merge a master
git checkout master
git merge develop

# 6. Crear tag
git tag -a v0.2.0 -m "Release v0.2.0"

# 7. Push todo
git push origin master
git push origin v0.2.0

# 8. Volver a develop
git checkout develop
git merge master
git push origin develop
```

### El workflow de GitHub Actions hará automáticamente:
1. Build del paquete Python
2. Publicación en PyPI
3. Build del ejecutable Windows
4. Build del instalador Windows
5. Crear Release en GitHub con todos los archivos

---

## 6. Archivos necesarios

### Crear: assets/icon.ico

Necesitas un icono para el instalador. Opciones:
1. Crear uno con herramientas online (favicon.io, etc.)
2. Usar un icono genérico temporal

### Crear: CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-XX-XX

### Added
- Initial release
- Wizard interactivo para cálculos hidrológicos
- Generación de reportes LaTeX
- Exportación a Excel
- Métodos de Tc: Kirpich, Temez, Desbordes, NRCS
- Tormentas: GZ, Bloques alternantes, Bimodal
- Hidrogramas: SCS, Triangular con factor X

### Fixed
- N/A

### Changed
- N/A
```

### Crear: .github/workflows/release.yml

(El contenido está en la sección 4)

### Crear: hidropluvial.iss

(El contenido está en la sección 3)

---

## 7. Resumen de tareas

| Tarea | Prioridad | Estado |
|-------|-----------|--------|
| Actualizar hidropluvial.spec | Alta | ✅ Completado |
| Crear assets/icon.ico | Media | ⏳ Pendiente (opcional) |
| Crear CHANGELOG.md | Alta | ✅ Completado |
| Crear hidropluvial.iss | Media | ✅ Completado |
| Crear .github/workflows/release.yml | Alta | ✅ Completado |
| Configurar PYPI_API_TOKEN en GitHub | Alta | ⏳ Pendiente |
| Probar build local de PyInstaller | Alta | ⏳ Pendiente |
| Probar build local de Inno Setup | Media | ⏳ Pendiente |
| Hacer primer release v0.1.0 | Alta | ⏳ Pendiente |

---

## 8. Checklist para primer release (v0.1.0)

### Preparación (una vez)

```bash
# 1. Configurar PyPI API Token en GitHub
#    - Ir a https://pypi.org/manage/account/token/
#    - Crear token con scope "Entire account" o proyecto específico
#    - En GitHub: Settings → Secrets → Actions → New repository secret
#    - Nombre: PYPI_API_TOKEN, Valor: el token

# 2. (Opcional) Crear icono
#    - Crear assets/icon.ico (256x256 px mínimo)
#    - Si no existe, el ejecutable se genera sin icono personalizado
```

### Probar build local (recomendado antes del primer release)

```bash
# 1. Instalar dependencias de build
pip install pyinstaller

# 2. Build del ejecutable
pyinstaller hidropluvial.spec

# 3. Probar ejecutable
.\dist\hidropluvial\hidropluvial.exe --help
.\dist\hidropluvial\hidropluvial.exe wizard

# 4. (Opcional) Probar instalador localmente
#    - Instalar Inno Setup: https://jrsoftware.org/isdl.php
#    - Ejecutar: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" hidropluvial.iss
#    - Probar: installer\HidroPluvial-0.1.0-Setup.exe
```

### Proceso de release

```bash
# 1. Asegurar que estás en develop y actualizado
git checkout develop
git pull origin develop

# 2. Verificar que los tests pasan
pytest

# 3. Actualizar versión en pyproject.toml si es necesario
#    version = "0.1.0"

# 4. Actualizar CHANGELOG.md con la fecha
#    ## [0.1.0] - 2024-XX-XX

# 5. Commit de release
git add -A
git commit -m "chore: prepare release v0.1.0"

# 6. Merge a master
git checkout master
git pull origin master
git merge develop

# 7. Crear tag (esto dispara el workflow)
git tag -a v0.1.0 -m "Release v0.1.0"

# 8. Push
git push origin master
git push origin v0.1.0

# 9. Volver a develop
git checkout develop
git merge master
git push origin develop
```

### El workflow automático hará:

1. ✅ Build del paquete Python y publicación en PyPI
2. ✅ Build del ejecutable Windows con PyInstaller
3. ✅ Build del instalador Windows con Inno Setup
4. ✅ Crear Release en GitHub con todos los artifacts

### Verificación post-release

```bash
# Verificar PyPI (esperar ~5 minutos)
pip install hidropluvial==0.1.0

# Verificar GitHub Release
# https://github.com/tu-usuario/hidropluvial/releases

# Descargar y probar instalador Windows
```

---

## 9. Troubleshooting

### PyInstaller falla con "ModuleNotFoundError"

Agregar el módulo faltante a `hiddenimports` en `hidropluvial.spec`.

### El instalador no encuentra archivos

Verificar que `pyinstaller hidropluvial.spec` se ejecutó correctamente y que `dist/hidropluvial/` existe.

### El workflow de GitHub falla

1. Verificar que `PYPI_API_TOKEN` está configurado correctamente
2. Revisar los logs del workflow en GitHub Actions
3. Asegurar que la versión en `pyproject.toml` no existe ya en PyPI

### El ejecutable es muy grande

- Revisar `excludes` en el spec file
- Considerar usar UPX para comprimir (ya habilitado)
- Usar `--onefile` genera un archivo único pero más lento de iniciar
