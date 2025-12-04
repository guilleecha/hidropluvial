# HidroPluvial - Documentación de Desarrollo

## Resumen del Proyecto

HidroPluvial es una herramienta Python para cálculos hidrológicos orientada a Uruguay, con soporte para el método DINAGUA y generación de reportes LaTeX.

---

## Estado Actual (Diciembre 2024)

### Fases Completadas

#### Fase 1: Módulos Core de Cálculo ✅

| Módulo | Archivo | Estado | Descripción |
|--------|---------|--------|-------------|
| IDF Uruguay | `core/idf.py` | ✅ Completo | Método DINAGUA con CT, CA, P3,10 por departamento |
| IDF Internacional | `core/idf.py` | ✅ Completo | Sherman, Bernard, Koutsoyiannis |
| Temporal | `core/temporal.py` | ✅ Completo | Bloques Alternantes, Chicago, SCS, Huff, Bimodal |
| Tiempo Concentración | `core/tc.py` | ✅ Completo | Kirpich, NRCS, Témez, California, FAA, Kinematic |
| Escorrentía | `core/runoff.py` | ✅ Completo | SCS-CN, Método Racional con Cf |
| Hidrogramas | `core/hydrograph.py` | ✅ Completo | SCS triangular/curvilinear, Snyder, Clark |

#### Fase 2: Integración DINAGUA + Distribuciones Temporales ✅

- `alternating_blocks_dinagua()` - Bloques alternantes usando IDF DINAGUA
- `bimodal_storm()` - Tormenta bimodal triangular
- `bimodal_chicago()` - Tormenta bimodal con método Chicago
- `generate_hyetograph_dinagua()` - Función principal para hietogramas Uruguay

#### Fase 2.5: Generación de Gráficos TikZ/PGFPlots ✅

| Función | Descripción |
|---------|-------------|
| `generate_hydrograph_tikz()` | Hidrograma con una o más series |
| `generate_hydrograph_comparison_tikz()` | Comparación de hidrogramas (Sin/Con MCE) |
| `generate_hyetograph_tikz()` | Hietograma con barras invertidas |
| `hydrograph_result_to_tikz()` | Convierte HydrographResult a LaTeX |
| `hyetograph_result_to_tikz()` | Convierte HyetographResult a LaTeX |

Ver guía completa: `docs/guia_graficos.md`

#### CLI Implementado ✅

```bash
# Comandos disponibles
hidropluvial idf uruguay <P3_10> <duracion> --tr <periodo>
hidropluvial idf tabla-uy <P3_10> --area <km2>
hidropluvial idf departamentos
hidropluvial storm uruguay <P3_10> <duracion> --tr <periodo>
hidropluvial storm bimodal <profundidad> <duracion>
hidropluvial tc kirpich <longitud> <desnivel>
hidropluvial runoff scs <precipitacion> <cn>
```

---

## Estructura del Proyecto

```
hidropluvial/
├── .venv/                      # Entorno virtual Python
├── .mcp.json                   # Configuración servidores MCP (no versionado)
├── .gitignore                  # Archivos excluidos de git
├── docs/
│   ├── SPEC.md                 # Especificación técnica completa
│   ├── SPEC_seccion_2.2_Uruguay_IDF.md  # Detalle método DINAGUA
│   ├── DESARROLLO.md           # Este archivo
│   └── guia_graficos.md        # Guía de generación de gráficos TikZ
├── examples/
│   ├── hidrogramas_comp.tex    # Ejemplo hidrograma comparativo
│   ├── hidrogramas_con_MCE.tex # Ejemplo hidrogramas con MCE
│   └── hyetogram.tex           # Ejemplo hietograma
├── src/hidropluvial/
│   ├── __init__.py
│   ├── __main__.py             # Entry point para python -m
│   ├── cli.py                  # Interfaz de línea de comandos (Typer)
│   ├── config.py               # Modelos Pydantic
│   ├── core/
│   │   ├── __init__.py         # Exports públicos
│   │   ├── idf.py              # Curvas IDF (DINAGUA + internacionales)
│   │   ├── temporal.py         # Distribuciones temporales
│   │   ├── tc.py               # Tiempo de concentración
│   │   ├── runoff.py           # Escorrentía SCS-CN y Racional
│   │   └── hydrograph.py       # Hidrogramas unitarios
│   ├── reports/
│   │   ├── __init__.py         # Exports públicos
│   │   └── charts.py           # Generación de gráficos TikZ/PGFPlots
│   └── data/
│       ├── scs_distributions.json
│       ├── huff_curves.json
│       ├── cn_tables.json
│       └── unit_hydrographs.json
├── tests/
│   ├── test_idf.py
│   ├── test_idf_uruguay.py
│   ├── test_runoff.py
│   ├── test_temporal_dinagua.py
│   └── test_charts.py          # Tests de generación de gráficos
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── CLAUDE.md
```

---

## Cómo Ejecutar

### Configuración Inicial

```bash
# Activar entorno virtual
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Instalar en modo desarrollo
pip install -e .

# Verificar instalación
python -m hidropluvial --help
```

### Ejecutar Tests

```bash
# Todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_idf_uruguay.py -v
pytest tests/test_temporal_dinagua.py -v

# Con cobertura
pytest tests/ --cov=hidropluvial --cov-report=html
```

### Ejemplos de Uso CLI

```bash
# IDF Uruguay - Montevideo, Tr=25 años, duración 3hr
python -m hidropluvial idf uruguay 78 3 --tr 25

# IDF Uruguay con corrección por área (50 km²)
python -m hidropluvial idf uruguay 78 3 --tr 25 --area 50

# Generar tabla IDF completa
python -m hidropluvial idf tabla-uy 78 -o tabla_montevideo.json

# Ver valores P3,10 por departamento
python -m hidropluvial idf departamentos

# Generar hietograma DINAGUA
python -m hidropluvial storm uruguay 78 3 --tr 25 --dt 10

# Tormenta bimodal
python -m hidropluvial storm bimodal 100 6 --dt 15
```

---

## Notas Técnicas Importantes

### Fórmula CT (Factor por Período de Retorno)

```
CT(Tr) = 0.5786 - 0.4312 × log₁₀[ln(Tr / (Tr - 1))]
```

**Valores calculados:**
| Tr (años) | CT |
|-----------|------|
| 2 | 0.647 |
| 5 | 0.860 |
| 10 | 1.000 |
| 25 | 1.178 |
| 50 | 1.309 |
| 100 | 1.440 |

> **Nota:** Los valores tabulados en la especificación original (0.87, 0.955, etc.) no coinciden con la fórmula matemática. Se implementó la fórmula exacta que da CT(10) = 1.0 como punto de referencia.

### Fórmula CA (Factor por Área de Cuenca)

```
CA(Ac,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × Ac))
```

- Para Ac ≤ 1 km²: CA = 1.0
- Para Ac > 300 km²: Genera warning

### Ecuaciones de Intensidad DINAGUA

**Para d < 3 horas:**
```
I(d) = [P₃,₁₀ × CT(Tr)] × 0.6208 / (d + 0.0137)^0.5639
```

**Para d ≥ 3 horas:**
```
I(d) = [P₃,₁₀ × CT(Tr)] × 1.0287 / (d + 1.0293)^0.8083
```

---

## Próximos Pasos (Fase 3)

### 3.1 Generación de Reportes LaTeX

- [ ] Crear templates Jinja2 para reportes
- [ ] Integrar Matplotlib PGF para gráficos
- [ ] Implementar compilación PDF automática
- [ ] Templates para:
  - Memoria de cálculo IDF
  - Hietograma de diseño
  - Hidrograma de crecida
  - Reporte completo de cuenca

### 3.2 Mejoras CLI

- [ ] Comando `report` para generar reportes
- [ ] Exportación a CSV/Excel
- [ ] Gráficos ASCII en terminal
- [ ] Modo interactivo

### 3.3 Validación y Documentación

- [ ] Agregar más tests de integración
- [ ] Documentación de API (Sphinx/MkDocs)
- [ ] Ejemplos de uso en Jupyter notebooks
- [ ] Validación contra casos de estudio reales

### 3.4 Funcionalidades Adicionales (Opcional)

- [ ] GUI simple (Streamlit o Gradio)
- [ ] Soporte para otros países/métodos regionales
- [ ] Integración con GIS (shapefiles de cuencas)
- [ ] Base de datos de estaciones pluviométricas

---

## Tests Actuales

**Total: 98 tests - Todos pasando ✅**

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| test_idf.py | 11 | IDF Sherman, conversiones |
| test_idf_uruguay.py | 20 | DINAGUA CT, CA, intensidad, tabla |
| test_runoff.py | 20 | SCS-CN, AMC, Racional |
| test_temporal_dinagua.py | 23 | Bloques alternantes, bimodal |
| test_charts.py | 24 | Gráficos TikZ hidrogramas/hietogramas |

---

## Dependencias Principales

```
numpy>=1.24.0
scipy>=1.11.0
pandas>=2.0.0
pydantic>=2.0.0
typer>=0.9.0
jinja2>=3.1.0
matplotlib>=3.7.0
pytest>=7.0.0
```

---

## Configuración MCP (Model Context Protocol)

El proyecto soporta servidores MCP para integración con herramientas externas.

### Ubicación de archivos de configuración

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| `.mcp.json` | Raíz del proyecto | Configuración específica del proyecto (no versionado) |
| `claude_desktop_config.json` | `%APPDATA%\Claude\` (Windows) | Configuración global Claude Desktop |
| `settings.json` | `~/.claude/` | Configuración global Claude Code |

### Servidores MCP disponibles

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<tu-token>"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "env": {
        "CONTEXT7_API_KEY": "<tu-api-key>"
      }
    }
  }
}
```

### Crear configuración MCP

1. Crear archivo `.mcp.json` en la raíz del proyecto
2. Agregar servidores con sus credenciales
3. Reiniciar Claude Code para activar
4. **Importante:** `.mcp.json` está en `.gitignore` para proteger credenciales

### Repositorio GitHub

- **URL:** https://github.com/guilleecha/hidropluvial

---

## Contacto y Referencias

- **Especificación técnica:** `docs/SPEC.md`
- **Método DINAGUA:** `docs/SPEC_seccion_2.2_Uruguay_IDF.md`
- **Guía de gráficos:** `docs/guia_graficos.md`
- **Referencias:**
  - Rodríguez Fontal (1980) - Curvas IDF Uruguay
  - DINAGUA/MTOP - Manual de Drenaje Pluvial Urbano
  - SCS TR-55 - Urban Hydrology for Small Watersheds
