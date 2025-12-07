# HidroPluvial - Herramienta de Cálculos Hidrológicos

## Descripción
Herramienta Python para cálculos hidrológicos con generación automática de reportes LaTeX.

## Branches de GitHub
- **`master`**: Versión estable, solo para releases
- **`develop`**: Desarrollo activo, nuevas funcionalidades

Flujo de trabajo:
1. Desarrollar en `develop`
2. Cuando esté estable, merge a `master`
3. Crear tags de versión en `master`

## Documentación Principal
- **LEER PRIMERO:** `docs/SPEC.md` - Especificación técnica completa
- `docs/DESARROLLO.md` - Estado del proyecto, estructura, configuración MCP
- `docs/METODOLOGIAS.md` - Fundamentos teóricos de los métodos implementados
- `docs/MANUAL_USUARIO.md` - Guía práctica con ejemplos
- `docs/INSTALACION.md` - Guía de instalación desde cero
- `docs/guia_graficos.md` - Guía de generación de gráficos TikZ/PGFPlots

## Stack Tecnológico
- Python 3.11+
- Typer (CLI)
- Pydantic v2 (validación)
- NumPy/SciPy (cálculos)
- Matplotlib PGF (gráficos)
- Jinja2 (templates LaTeX)
- SQLite (persistencia)

## Estructura del Proyecto
```
hidropluvial/
├── CLAUDE.md          # Este archivo
├── pyproject.toml     # Configuración del proyecto
├── docs/
│   └── SPEC.md        # Especificación técnica completa
├── src/
│   └── hidropluvial/  # Código fuente
└── tests/             # Tests
```

## Comandos Útiles
```bash
# Instalar en modo desarrollo
pip install -e .

# Ejecutar tests
pytest

# Ejecutar CLI
python -m hidropluvial --help
```

## Prioridad de Desarrollo
1. ✅ Módulo IDF (`core/idf.py`)
2. ✅ Distribuciones temporales (`core/temporal.py`)
3. ✅ Tiempo de concentración (`core/tc.py`)
4. ✅ Escorrentía SCS-CN (`core/runoff.py`)
5. ✅ Hidrogramas (`core/hydrograph.py`)
6. ✅ Gráficos TikZ (`reports/charts.py`)
7. Templates Jinja2 para reportes (`reports/templates/`)

## Base de Datos

HidroPluvial usa SQLite para persistencia de datos:

```
~/.hidropluvial/
├── hidropluvial.db    # Base de datos SQLite
├── projects/          # (legacy) Archivos JSON
└── sessions/          # (legacy) Sesiones JSON
```

### Módulos de datos
- `database.py` - Capa de acceso a datos SQLite
- `migration.py` - Migración de JSON a SQLite
- `project.py` - Modelos Pydantic (Project, Basin)
- `session.py` - Modelos legacy (Session, AnalysisRun)

### Migración de datos existentes
```bash
python -m hidropluvial.migration
```

## Configuración MCP
El archivo `.mcp.json` en la raíz contiene la configuración de servidores MCP (GitHub, Context7).
**No se versiona** para proteger credenciales. Ver `docs/DESARROLLO.md` para detalles.