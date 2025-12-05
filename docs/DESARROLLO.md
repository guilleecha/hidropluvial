# HidroPluvial - Documentación de Desarrollo

## Resumen del Proyecto

HidroPluvial es una herramienta Python para cálculos hidrológicos orientada a Uruguay, con soporte para el método DINAGUA y generación de reportes LaTeX.

---

## Estado Actual (Diciembre 2024)

### Tests: 709 pasando

```bash
pytest tests/ -v
```

---

## Estructura del Proyecto

```
hidropluvial/
├── src/hidropluvial/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py               # Modelos Pydantic
│   ├── session.py              # Gestión de sesiones
│   ├── core/
│   │   ├── __init__.py
│   │   ├── idf.py              # Curvas IDF (DINAGUA + internacionales)
│   │   ├── temporal.py         # Distribuciones temporales
│   │   ├── tc.py               # Tiempo de concentración
│   │   ├── runoff.py           # Escorrentía SCS-CN y Racional
│   │   ├── hydrograph.py       # Hidrogramas unitarios
│   │   └── coefficients.py     # Tablas C y CN
│   ├── cli/
│   │   ├── __init__.py         # App principal Typer
│   │   ├── formatters.py       # Utilidades de formato
│   │   ├── idf.py              # Comandos IDF
│   │   ├── storm.py            # Comandos tormenta
│   │   ├── tc.py               # Comandos Tc
│   │   ├── runoff.py           # Comandos escorrentía
│   │   ├── hydrograph.py       # Comandos hidrograma
│   │   ├── export.py           # Comandos exportación
│   │   ├── session/            # Subpaquete sesiones
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # create, list, show, tc, edit, delete
│   │   │   ├── analyze.py      # analyze
│   │   │   ├── batch.py        # batch
│   │   │   ├── report.py       # report
│   │   │   ├── export.py       # export Excel
│   │   │   └── preview.py      # preview con sparklines
│   │   └── wizard/             # Subpaquete wizard interactivo
│   │       ├── __init__.py
│   │       ├── main.py         # Menú principal
│   │       ├── config.py       # WizardConfig
│   │       ├── runner.py       # AnalysisRunner
│   │       └── menus/          # Submenús modulares
│   └── reports/
│       ├── __init__.py
│       ├── charts.py           # Gráficos TikZ/PGFPlots
│       ├── generator.py        # Generador de reportes
│       └── templates/          # Templates Jinja2
├── tests/
├── docs/
│   ├── SPEC.md                 # Especificación técnica
│   ├── COEFICIENTES.md         # Tablas C y CN
│   ├── guia_graficos.md        # Gráficos TikZ
│   ├── MANUAL_USUARIO.md       # Manual práctico
│   ├── METODOLOGIAS.md         # Fundamentos teóricos
│   └── INSTALACION.md          # Guía de instalación
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## Comandos de Desarrollo

```bash
# Activar entorno
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Instalar en modo desarrollo
pip install -e .

# Ejecutar tests
pytest tests/ -v

# CLI
hp --help
hp wizard
```

---

## Branches de GitHub

- **`master`**: Versión estable, solo para releases
- **`develop`**: Desarrollo activo, nuevas funcionalidades

---

## Dependencias

```
numpy>=1.24.0
scipy>=1.11.0
pydantic>=2.0.0
typer>=0.9.0
jinja2>=3.1.0
pyyaml>=6.0
questionary>=2.0.0
plotext>=5.2.0
rich>=13.0.0
pandas>=2.0.0
openpyxl>=3.1.0
```

---

## Repositorio

- **GitHub:** https://github.com/guilleecha/hidropluvial
