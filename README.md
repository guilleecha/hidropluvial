# HidroPluvial

**Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-98%20passed-green.svg)]()

---

## Características

- **Curvas IDF** - Método DINAGUA Uruguay con factores CT y CA
- **Hietogramas** - Bloques alternantes, Chicago, SCS Tipo I/II/III, Huff, Bimodal
- **Tiempo de concentración** - Kirpich, Témez, Desbordes (DINAGUA)
- **Escorrentía** - SCS Curve Number, Método Racional
- **Hidrogramas** - SCS triangular/curvilíneo, Triangular con factor X, Snyder, Clark
- **Sistema de Sesiones** - Flujo de trabajo integrado para múltiples análisis comparativos
- **Reportes LaTeX** - Memorias de cálculo con gráficos TikZ/PGFPlots
- **Exportación** - CSV, JSON, figuras TikZ standalone

---

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/guilleecha/hidropluvial.git
cd hidropluvial

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Instalar en modo desarrollo
pip install -e .

# Verificar instalación
python -m hidropluvial --help
```

---

## Uso Rápido

### Calcular intensidad IDF (Uruguay)

```bash
# Montevideo (P3,10 = 78mm), duración 3 horas, Tr = 25 años
python -m hidropluvial idf uruguay 78 3 --tr 25
```

**Salida:**
```
==================================================
  METODO DINAGUA URUGUAY
==================================================
  P3,10 base:              78.0 mm
  Periodo retorno:           25 años
  Duracion:                3.00 hr
==================================================
  Factor CT:             1.1781
  Factor CA:             1.0000
==================================================
  INTENSIDAD:            30.63 mm/hr
  PRECIPITACION:         91.90 mm
==================================================
```

### Generar hietograma de diseño

```bash
python -m hidropluvial storm uruguay 78 3 --tr 25 --dt 5
```

### Generar reporte LaTeX

```bash
python -m hidropluvial report idf 78 -o informe_idf.tex --author "Ing. Pérez"
```

### Exportar a CSV

```bash
python -m hidropluvial export idf-csv 78 -o tabla_idf.csv
```

---

## Comandos CLI

### `idf` - Curvas Intensidad-Duración-Frecuencia

| Comando | Descripción |
|---------|-------------|
| `idf uruguay <P3_10> <dur> --tr <T>` | Intensidad método DINAGUA |
| `idf tabla-uy <P3_10>` | Tabla IDF completa |
| `idf departamentos` | Valores P₃,₁₀ por departamento |
| `idf sherman <dur> <T>` | Intensidad método Sherman |

**Ejemplos:**
```bash
# IDF Uruguay con corrección por área de cuenca
python -m hidropluvial idf uruguay 78 3 --tr 25 --area 50

# Tabla IDF completa exportada a JSON
python -m hidropluvial idf tabla-uy 78 -o tabla.json

# Ver P3,10 de todos los departamentos
python -m hidropluvial idf departamentos
```

### `storm` - Tormentas de Diseño

| Comando | Descripción |
|---------|-------------|
| `storm uruguay <P3_10> <dur>` | Hietograma DINAGUA |
| `storm bimodal <depth> --duration <hr>` | Tormenta doble pico |
| `storm scs <depth> --storm-type II` | Distribución SCS |
| `storm chicago <depth>` | Método Chicago |

**Ejemplos:**
```bash
# Hietograma bloques alternantes
python -m hidropluvial storm uruguay 78 3 --tr 25 --dt 5

# Tormenta bimodal (6 horas, picos en 25% y 75%)
python -m hidropluvial storm bimodal 100 --duration 6 --peak1 0.25 --peak2 0.75

# Distribución SCS Tipo II (24 horas)
python -m hidropluvial storm scs 150 --duration 24 --storm-type II
```

### `tc` - Tiempo de Concentración

| Comando | Descripción |
|---------|-------------|
| `tc kirpich <L> <S>` | Fórmula Kirpich |
| `tc temez <L> <S>` | Fórmula Témez |
| `tc desbordes <A> <S> <C>` | Método Desbordes (DINAGUA) |

**Ejemplos:**
```bash
# Kirpich: L=2000m, S=0.02
python -m hidropluvial tc kirpich 2000 0.02

# Témez: L=5km, S=0.015
python -m hidropluvial tc temez 5 0.015

# Desbordes (DINAGUA): A=62ha, S=3.41%, C=0.62
python -m hidropluvial tc desbordes 62 3.41 0.62
```

### `hydrograph` - Generación de Hidrogramas

| Comando | Descripción |
|---------|-------------|
| `hydrograph scs` | Hidrograma completo método SCS |
| `hydrograph gz` | Hidrograma completo método GZ (Uruguay) |

**Ejemplos:**
```bash
# Hidrograma SCS completo
python -m hidropluvial hydrograph scs --area 1 --length 1000 --slope 0.02 \
    --p3_10 83 --cn 81 --tr 25

# Hidrograma GZ (metodología drenaje urbano Uruguay)
python -m hidropluvial hydrograph gz --area 62 --slope 3.41 --c 0.62 \
    --p3_10 83 --tr 2 --x 1.0
```

El método GZ integra:
- Tc por Método de los Desbordes
- Tormenta de 6 horas con pico adelantado (1ra hora)
- Hidrograma triangular con factor X ajustable

**Valores típicos de X:**
| Factor X | Uso típico |
|----------|------------|
| 1.00 | Áreas urbanas internas |
| 1.25 | Áreas urbanas (gran pendiente) |
| 1.67 | Método SCS/NRCS estándar |
| 2.25 | Uso mixto rural/urbano |

### `runoff` - Escorrentía

| Comando | Descripción |
|---------|-------------|
| `runoff cn <P> <CN>` | Método SCS Curve Number |
| `runoff rational <C> <i> <A>` | Método Racional |

**Ejemplos:**
```bash
# SCS-CN: P=100mm, CN=75, AMC II
python -m hidropluvial runoff cn 100 75

# SCS-CN con condición húmeda (AMC III)
python -m hidropluvial runoff cn 100 75 --amc III

# Racional: C=0.6, i=50mm/hr, A=10ha
python -m hidropluvial runoff rational 0.6 50 10
```

### `report` - Generación de Reportes LaTeX

| Comando | Descripción |
|---------|-------------|
| `report idf <P3_10>` | Memoria de cálculo IDF |
| `report storm <P3_10> <dur>` | Memoria de hietograma |

**Ejemplos:**
```bash
# Reporte IDF completo
python -m hidropluvial report idf 78 -o informe_idf.tex --author "Ing. García"

# Reporte de tormenta de diseño
python -m hidropluvial report storm 78 3 --tr 25 -o informe_storm.tex
```

### `export` - Exportación de Datos

| Comando | Descripción |
|---------|-------------|
| `export idf-csv <P3_10>` | Tabla IDF a CSV |
| `export storm-csv <P3_10> <dur>` | Hietograma a CSV |
| `export storm-tikz <P3_10> <dur>` | Figura TikZ standalone |

**Ejemplos:**
```bash
# Exportar tabla IDF
python -m hidropluvial export idf-csv 78 -o idf.csv

# Exportar hietograma para Excel
python -m hidropluvial export storm-csv 78 3 --tr 25 -o storm.csv

# Exportar figura para incluir en documento LaTeX
python -m hidropluvial export storm-tikz 78 3 --tr 25 -o figura.tex
```

### `session` - Sistema de Sesiones (Análisis Comparativo)

El sistema de sesiones permite definir una cuenca y ejecutar múltiples análisis con diferentes combinaciones de métodos, comparando resultados y generando reportes automáticos.

| Comando | Descripción |
|---------|-------------|
| `session create <nombre>` | Crear nueva sesión con datos de cuenca |
| `session list` | Listar todas las sesiones |
| `session show <id>` | Ver detalles de una sesión |
| `session tc <id>` | Calcular Tc con múltiples métodos |
| `session analyze <id>` | Ejecutar análisis completo |
| `session summary <id>` | Ver tabla comparativa |
| `session batch <yaml>` | Ejecutar desde archivo YAML |
| `session report <id>` | Generar reporte LaTeX |
| `session delete <id>` | Eliminar sesión |

#### Flujo de Trabajo Típico

```bash
# 1. Crear sesión con datos de la cuenca
python -m hidropluvial session create "Cuenca Norte" \
    --area 62 --slope 3.41 --p3_10 83 --c 0.62 --length 800

# 2. Calcular Tc con múltiples métodos
python -m hidropluvial session tc abc123 --methods "kirpich,desbordes"

# 3. Ejecutar análisis con diferentes combinaciones
python -m hidropluvial session analyze abc123 --tc desbordes --storm gz --tr 2 --x 1.0
python -m hidropluvial session analyze abc123 --tc desbordes --storm gz --tr 10 --x 1.0
python -m hidropluvial session analyze abc123 --tc kirpich --storm gz --tr 2 --x 1.25

# 4. Ver tabla comparativa
python -m hidropluvial session summary abc123

# 5. Generar reporte LaTeX
python -m hidropluvial session report abc123 -o memoria_calculo.tex --author "Ing. García"
```

#### Análisis Batch desde YAML

Para proyectos con muchas combinaciones, usar un archivo de configuración:

```yaml
# cuenca.yaml
session:
  name: "Proyecto Drenaje Sur"
  cuenca:
    nombre: "Arroyo Las Piedras"
    area_ha: 62
    slope_pct: 3.41
    p3_10: 83
    c: 0.62
    cn: 81
    length_m: 800

tc_methods:
  - kirpich
  - desbordes

analyses:
  - storm: gz
    tr: [2, 10, 25]
    x: [1.0, 1.25]
  - storm: blocks
    tr: [10, 25]
```

```bash
# Ejecutar todas las combinaciones
python -m hidropluvial session batch cuenca.yaml
```

Esto ejecutará automáticamente:
- 2 métodos de Tc × 3 períodos de retorno × 2 factores X = 12 análisis GZ
- 2 métodos de Tc × 2 períodos de retorno = 4 análisis blocks
- **Total: 16 análisis comparativos**

#### Ejemplo de Salida (Summary)

```
====================================================================================================
  RESUMEN COMPARATIVO - Cuenca Norte
====================================================================================================
  ID       | Tc           |  Tc(min) | Tormenta   |   Tr |     X |   P(mm) |   Q(mm) |  Qp(m³/s) |  Tp(min)
  ------------------------------------------------------------------------------------------------
  d36d2306 | desbordes    |     22.6 | gz         |    2 |  1.00 |    68.6 |    42.5 |     6.748 |     80.0
  7de6650b | desbordes    |     22.6 | gz         |   10 |  1.00 |   105.9 |    65.7 |    10.426 |     80.0
  bc416b51 | kirpich      |     12.3 | gz         |    2 |  1.00 |    68.6 |    42.5 |     9.092 |     70.0
====================================================================================================

  Caudal máximo: 10.426 m³/s (desbordes + gz Tr10)
  Caudal mínimo: 6.748 m³/s (desbordes + gz Tr2)
  Variación: 54.5%
```

---

## Uso como Librería Python

### Curvas IDF

```python
from hidropluvial.core import dinagua_intensity, generate_dinagua_idf_table

# Calcular intensidad puntual
result = dinagua_intensity(p3_10=78, return_period_yr=25, duration_hr=3)
print(f"Intensidad: {result.intensity_mmhr:.2f} mm/hr")
print(f"Precipitación: {result.depth_mm:.2f} mm")

# Generar tabla completa
tabla = generate_dinagua_idf_table(p3_10=78, area_km2=50)
```

### Hietogramas

```python
from hidropluvial.core import alternating_blocks_dinagua, bimodal_storm

# Bloques alternantes DINAGUA
hietograma = alternating_blocks_dinagua(
    p3_10=78,
    return_period_yr=25,
    duration_hr=3,
    dt_min=5
)

print(f"Precipitación total: {hietograma.total_depth_mm:.2f} mm")
print(f"Intensidad pico: {hietograma.peak_intensity_mmhr:.2f} mm/hr")

# Tormenta bimodal
bimodal = bimodal_storm(
    total_depth_mm=100,
    duration_hr=6,
    dt_min=5,
    peak1_position=0.25,
    peak2_position=0.75
)
```

### Escorrentía SCS-CN

```python
from hidropluvial.core import calculate_scs_runoff
from hidropluvial.config import AntecedentMoistureCondition

result = calculate_scs_runoff(
    rainfall_mm=100,
    cn=75,
    lambda_coef=0.2,
    amc=AntecedentMoistureCondition.AVERAGE
)

print(f"Escorrentía: {result.runoff_mm:.2f} mm")
print(f"Abstracción inicial: {result.initial_abstraction_mm:.2f} mm")
```

### Generación de Gráficos TikZ

```python
from hidropluvial.core import alternating_blocks_dinagua
from hidropluvial.reports import hyetograph_result_to_tikz

# Generar hietograma
hietograma = alternating_blocks_dinagua(78, 25, 3, 5)

# Convertir a código TikZ
tikz = hyetograph_result_to_tikz(
    hietograma,
    caption="Hietograma de diseño - Tr = 25 años",
    label="fig:hietograma"
)

# Guardar archivo
with open("hietograma.tex", "w") as f:
    f.write(tikz)
```

---

## Valores P₃,₁₀ por Departamento (Uruguay)

| Departamento | P₃,₁₀ (mm) | Departamento | P₃,₁₀ (mm) |
|--------------|------------|--------------|------------|
| Artigas | 95 | Maldonado | 83 |
| Canelones | 80 | Montevideo | 78 |
| Cerro Largo | 95 | Paysandú | 90 |
| Colonia | 78 | Río Negro | 88 |
| Durazno | 88 | Rivera | 95 |
| Flores | 85 | Rocha | 85 |
| Florida | 85 | Salto | 92 |
| Lavalleja | 85 | San José | 80 |
| | | Soriano | 85 |
| | | Tacuarembó | 92 |
| | | Treinta y Tres | 90 |

> **Nota:** Para proyectos críticos, considerar mayorar 5-10% por efectos del cambio climático.

---

## Fórmulas Principales

### Factor por Período de Retorno (CT)

$$C_T(T_r) = 0.5786 - 0.4312 \times \log_{10}\left[\ln\left(\frac{T_r}{T_r - 1}\right)\right]$$

### Factor por Área de Cuenca (CA)

$$C_A(A_c, d) = 1.0 - 0.3549 \times d^{-0.4272} \times \left(1.0 - e^{-0.005792 \times A_c}\right)$$

### Intensidad DINAGUA

Para d < 3 horas:
$$I(d) = \frac{P_{3,10} \times C_T \times C_A \times 0.6208}{(d + 0.0137)^{0.5639}}$$

Para d ≥ 3 horas:
$$I(d) = \frac{P_{3,10} \times C_T \times C_A \times 1.0287}{(d + 1.0293)^{0.8083}}$$

### Tiempo de Concentración - Método Desbordes (DINAGUA)

$$T_c = T_0 + 6.625 \times A^{0.3} \times P^{-0.39} \times C^{-0.45}$$

Donde:
- $T_c$: tiempo de concentración (min)
- $T_0$: tiempo de entrada (típicamente 5 min)
- $A$: área de la cuenca (ha)
- $P$: pendiente media (%)
- $C$: coeficiente de escorrentía

### Hidrograma Unitario Triangular con Factor X

$$T_p = 0.5 \times \Delta t + 0.6 \times T_c$$

$$q_p = 0.278 \times \frac{A}{T_p} \times \frac{2}{1 + X}$$

$$T_b = (1 + X) \times T_p$$

Donde:
- $T_p$: tiempo al pico (hr)
- $q_p$: caudal pico unitario (m³/s por mm de escorrentía)
- $T_b$: tiempo base (hr)
- $A$: área de cuenca (km²)
- $X$: factor morfológico (1.0 para urbano, 1.67 para SCS estándar)

### Escorrentía SCS-CN

$$Q = \frac{(P - I_a)^2}{P - I_a + S} \quad \text{para } P > I_a$$

Donde:
- $S = \frac{25400}{CN} - 254$ (retención potencial, mm)
- $I_a = \lambda \times S$ (abstracción inicial, típicamente λ = 0.2)

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [Manual de Usuario](docs/manual.pdf) | Guía completa en PDF |
| [Especificación Técnica](docs/SPEC.md) | Detalle de métodos y fórmulas |
| [Guía de Desarrollo](docs/DESARROLLO.md) | Estado del proyecto y roadmap |
| [Guía de Gráficos](docs/guia_graficos.md) | Generación de figuras TikZ |

---

## Tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=hidropluvial --cov-report=html
```

**Estado actual:** 98 tests pasando ✅

---

## Estructura del Proyecto

```
hidropluvial/
├── src/hidropluvial/
│   ├── core/
│   │   ├── idf.py          # Curvas IDF (DINAGUA + internacionales)
│   │   ├── temporal.py     # Distribuciones temporales (bloques, SCS, bimodal)
│   │   ├── tc.py           # Tiempo de concentración (Kirpich, Desbordes, etc.)
│   │   ├── runoff.py       # Escorrentía (SCS-CN, Racional)
│   │   └── hydrograph.py   # Hidrogramas (SCS, triangular con X)
│   ├── reports/
│   │   ├── charts.py       # Gráficos TikZ/PGFPlots
│   │   ├── generator.py    # Generador de reportes LaTeX
│   │   └── templates/      # Templates Jinja2
│   ├── session.py          # Sistema de sesiones y análisis comparativo
│   ├── cli.py              # Interfaz de comandos
│   └── config.py           # Configuraciones y modelos Pydantic
├── tests/                  # Tests unitarios (98 tests)
├── docs/                   # Documentación técnica
└── examples/               # Ejemplos (YAML, LaTeX)
```

---

## Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

---

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abrir un issue primero para discutir cambios mayores.

## Referencias

- Rodríguez Fontal (1980) - Curvas IDF Uruguay
- DINAGUA/MTOP - Manual de Drenaje Pluvial Urbano
- SCS TR-55 - Urban Hydrology for Small Watersheds
- FHWA HDS-2 - Highway Hydrology
