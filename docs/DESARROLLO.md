# HidroPluvial - Documentación de Desarrollo

## Resumen del Proyecto

HidroPluvial es una herramienta Python para cálculos hidrológicos orientada a Uruguay, con soporte para el método DINAGUA y generación de reportes LaTeX.

---

## Estado Actual (Diciembre 2024)

### Tests: 724 pasando

```bash
pytest tests/ -v
```

### Últimas Actualizaciones

- **Gestión de Proyectos/Cuencas**: Nueva arquitectura jerárquica (Project → Basin)
- **Parámetros de hidrograma**: tp (tiempo pico unitario), tb (tiempo base), Tp (tiempo pico resultado)
- **Unidades mejoradas**: Volumen en hm³, caudal con 2 cifras significativas
- **Organización de gráficos**: Subdirectorios por tipo (hidrogramas/, hietogramas/)

---

## Estructura del Proyecto

```
hidropluvial/
├── src/hidropluvial/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py               # Modelos Pydantic
│   ├── session.py              # Gestión de sesiones (legacy)
│   ├── project.py              # Gestión de proyectos y cuencas
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
│   │   ├── formatters.py       # Utilidades de formato (format_flow, format_volume_hm3)
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
│   │   │   ├── report.py       # report (con fichas técnicas)
│   │   │   ├── export.py       # export Excel
│   │   │   └── preview.py      # preview con sparklines
│   │   └── wizard/             # Subpaquete wizard interactivo
│   │       ├── __init__.py
│   │       ├── main.py         # Menú principal
│   │       ├── config.py       # WizardConfig
│   │       ├── runner.py       # AnalysisRunner (retorna Project, Basin)
│   │       └── menus/          # Submenús modulares
│   │           ├── base.py
│   │           ├── post_execution.py
│   │           ├── add_analysis.py
│   │           ├── continue_project.py
│   │           ├── project_management.py
│   │           ├── export_menu.py
│   │           └── cuenca_editor.py
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

---

## Arquitectura de Datos

### Jerarquía Project → Basin

```
Project (Estudio/Trabajo)
├── name: "Estudio Drenaje Barrio X"
├── description: "Análisis de crecidas..."
├── author: "Ing. García"
├── basins: [
│   Basin (Cuenca 1)
│   ├── name: "Cuenca Alta"
│   ├── area_ha, slope_pct, p3_10, c, cn
│   ├── tc_results: [TcResult...]
│   └── analyses: [AnalysisRun...]
│
│   Basin (Cuenca 2)
│   └── ...
]
```

### Compatibilidad con Sesiones Legacy

- `Session` sigue siendo el modelo usado por los comandos CLI
- `Basin.from_session()` convierte Session → Basin
- `Basin.to_session()` convierte Basin → Session
- El wizard usa internamente Project/Basin pero mantiene compatibilidad

### Parámetros del Hidrograma

| Parámetro | Descripción | Fórmula |
|-----------|-------------|---------|
| `tp` | Tiempo pico del hidrograma unitario | tp = ΔD/2 + 0.6×Tc |
| `tb` | Tiempo base del hidrograma unitario | tb = 2.67 × tp |
| `Tp` | Tiempo pico del hidrograma resultante | De la convolución |

### Unidades de Salida

| Magnitud | Unidad | Formato |
|----------|--------|---------|
| Caudal (Qp) | m³/s | 2 cifras significativas |
| Volumen | hm³ | 1 hm³ = 1,000,000 m³ |
| Tiempo | min | Entero o 1 decimal |

---

## Changelog Reciente

### v1.1.0 (Diciembre 2024)
- Nueva arquitectura Project/Basin
- Parámetros tp, tb, Tp en resultados
- Volumen en hm³, caudal con 2 cifras significativas
- Organización de gráficos en subdirectorios
- 724 tests pasando
