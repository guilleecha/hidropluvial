# Distribución de HidroPluvial

Guía para generar el ejecutable Windows (.exe) para distribución.

## Requisitos

```bash
pip install pyinstaller
```

## Generar ejecutable

### Opción 1: Script automatizado

```bash
python scripts/build_exe.py
```

### Opción 2: PyInstaller directo

```bash
pyinstaller hidropluvial.spec --noconfirm
```

## Resultado

El ejecutable se genera en `dist/hidropluvial/`:

```
dist/hidropluvial/
├── hidropluvial.exe      # Ejecutable principal (~23 MB)
├── EJECUTAR.bat          # Lanzador para usuarios
├── LEEME.txt             # Instrucciones
└── _internal/            # Dependencias (~150 MB)
```

**Tamaño total:** ~175 MB (comprimido ~60 MB)

## Distribución

1. Comprimir la carpeta `dist/hidropluvial/` en ZIP
2. Distribuir el archivo ZIP
3. El usuario descomprime y ejecuta `EJECUTAR.bat`

## Uso para el usuario final

### Inicio rápido
1. Descomprimir ZIP en cualquier carpeta
2. Doble clic en `EJECUTAR.bat`
3. Seguir el asistente interactivo

### Uso avanzado (terminal)
```cmd
hidropluvial.exe --help
hidropluvial.exe wizard
hidropluvial.exe tc kirpich --length 1500 --slope 2.5
```

## Optimización de tamaño

El tamaño actual incluye NumPy, SciPy y otras dependencias científicas.
Para reducir:

1. **Excluir matplotlib** (si no se usa para gráficos CLI):
   - Ya excluido en el spec actual

2. **Usar UPX** (compresión de binarios):
   ```bash
   # Instalar UPX: https://github.com/upx/upx/releases
   # PyInstaller lo usará automáticamente si está en PATH
   ```

3. **One-file mode** (opcional):
   ```bash
   pyinstaller hidropluvial.spec --onefile
   ```
   - Genera un solo .exe (~80 MB)
   - Más lento al iniciar (debe extraer)

## Notas

- El ejecutable es para Windows 64-bit
- Requiere Windows 10 o superior
- Para reportes PDF se necesita LaTeX instalado (MiKTeX/TeX Live)
- Los archivos de datos (JSON) están incluidos en el ejecutable

## CI/CD (GitHub Actions)

Para automatizar el build en cada release:

```yaml
# .github/workflows/build-exe.yml
name: Build Windows Executable

on:
  release:
    types: [created]

jobs:
  build:
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
        run: pyinstaller hidropluvial.spec --noconfirm

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: hidropluvial-windows
          path: dist/hidropluvial/
```
