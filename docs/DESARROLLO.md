# HidroPluvial - Documentación de Desarrollo

## Resumen del Proyecto

HidroPluvial es una herramienta Python para cálculos hidrológicos orientada a Uruguay, con soporte para el método DINAGUA y generación de reportes LaTeX.

---

## Estado Actual (Diciembre 2024)

### Tests: 142 pasando

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| test_idf.py | 11 | IDF Sherman, conversiones |
| test_idf_uruguay.py | 20 | DINAGUA CT, CA, intensidad, tabla |
| test_runoff.py | 20 | SCS-CN, AMC, Racional |
| test_temporal_dinagua.py | 23 | Bloques alternantes, bimodal |
| test_charts.py | 24 | Gráficos TikZ hidrogramas/hietogramas |
| test_session.py | 24 | SessionManager CRUD, modelos |
| test_wizard.py | 20 | Wizard menus, runner, integración |

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
│   │   ├── report.py           # Comandos reporte
│   │   ├── export.py           # Comandos exportación
│   │   ├── session/            # Subpaquete sesiones
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # create, list, show, tc, edit, delete
│   │   │   ├── analyze.py      # analyze
│   │   │   ├── batch.py        # batch
│   │   │   ├── report.py       # report
│   │   │   └── preview.py      # preview con sparklines
│   │   └── wizard/             # Subpaquete wizard interactivo
│   │       ├── __init__.py
│   │       ├── main.py         # Menú principal
│   │       ├── menus.py        # PostExecutionMenu, continue_session
│   │       └── runner.py       # AnalysisRunner, AdditionalAnalysisRunner
│   └── reports/
│       ├── __init__.py
│       ├── charts.py           # Gráficos TikZ/PGFPlots
│       ├── generator.py        # Generador de reportes
│       └── templates/          # Templates Jinja2
├── tests/
│   ├── conftest.py
│   ├── test_idf.py
│   ├── test_idf_uruguay.py
│   ├── test_runoff.py
│   ├── test_temporal_dinagua.py
│   ├── test_charts.py
│   ├── test_session.py
│   └── test_wizard.py
├── docs/
│   ├── SPEC.md                 # Especificación técnica
│   ├── CLI.md                  # Referencia CLI
│   ├── WIZARD.md               # Guía wizard interactivo
│   ├── SESIONES.md             # Sistema de sesiones
│   ├── COEFICIENTES.md         # Tablas C y CN
│   └── guia_graficos.md        # Gráficos TikZ
├── examples/
│   ├── cuenca_ejemplo.yaml     # Ejemplo batch
│   ├── template.tex            # Template LaTeX
│   └── reporte_fichas/         # Ejemplo reporte
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## CLI Implementado

### Comandos principales

```bash
# Wizard interactivo
hp wizard

# Sesiones
hp session create <nombre> --area <ha> --slope <pct> --p3_10 <mm> --c <val>
hp session list
hp session show <id>
hp session tc <id> --methods "kirpich,desbordes"
hp session analyze <id> --tc <metodo> --storm <tipo> --tr <periodo>
hp session preview <id>
hp session summary <id>
hp session edit <id> --area <nuevo_valor>
hp session batch <archivo.yaml>
hp session report <id> -o <archivo.tex>
hp session delete <id>

# IDF
hp idf uruguay <P3_10> <duracion> --tr <periodo>
hp idf tabla-uy <P3_10>
hp idf departamentos

# Tormentas
hp storm uruguay <P3_10> <duracion> --tr <periodo>
hp storm bimodal-uy <P3_10> --tr <periodo>
hp storm gz <P3_10> --tr <periodo>

# Tiempo de concentración
hp tc kirpich <longitud> <pendiente>
hp tc desbordes <area> <pendiente> <c>

# Escorrentía
hp runoff cn <precipitacion> <cn>
hp runoff rational <c> <i> <area>
hp runoff weighted-c --area <ha>
hp runoff weighted-cn --area <ha> --soil <grupo>

# Hidrogramas
hp hydrograph scs --area <km2> --cn <val> --tr <periodo>
hp hydrograph gz --area <ha> --c <val> --tr <periodo>

# Reportes y exportación
hp report idf <P3_10> -o <archivo.tex>
hp export idf-csv <P3_10> -o <archivo.csv>
```

---

## Funcionalidades Recientes

### Wizard Interactivo
- Menú principal con opciones: nuevo análisis, continuar sesión, consultar IDF, ponderadores
- PostExecutionMenu con preview sparklines, filtros, edición de cuenca
- Ponderadores C y CN con selección interactiva de coberturas

### Sistema de Sesiones
- Persistencia JSON en `~/.hidropluvial/sessions/`
- Edición de parámetros de cuenca con advertencia de invalidación
- Clonación de sesiones para análisis de sensibilidad
- Preview con sparklines en terminal (plotext)
- Filtrado por Tr, X, método Tc, tipo de tormenta

### Reportes LaTeX
- Fichas técnicas por análisis (tabla + hietograma + hidrograma)
- Templates Jinja2 personalizables
- Gráficos TikZ/PGFPlots integrados

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
python -m hidropluvial --help
hp --help
```

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
```

---

## Repositorio

- **GitHub:** https://github.com/guilleecha/hidropluvial
