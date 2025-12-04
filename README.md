# HidroPluvial

**Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-98%20passed-green.svg)]()

---

## Características

- **Curvas IDF** - Método DINAGUA Uruguay con factores CT y CA
- **Hietogramas** - Bloques alternantes, Chicago, SCS Tipo I/II/III, Huff
- **Tiempo de concentración** - Kirpich, NRCS, Témez, California, FAA
- **Escorrentía** - SCS Curve Number, Método Racional
- **Hidrogramas** - SCS triangular/curvilíneo, Snyder, Clark
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

**Ejemplos:**
```bash
# Kirpich: L=2000m, S=0.02
python -m hidropluvial tc kirpich 2000 0.02

# Témez: L=5km, S=0.015
python -m hidropluvial tc temez 5 0.015
```

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
│   │   ├── idf.py          # Curvas IDF
│   │   ├── temporal.py     # Distribuciones temporales
│   │   ├── tc.py           # Tiempo de concentración
│   │   ├── runoff.py       # Escorrentía
│   │   └── hydrograph.py   # Hidrogramas
│   ├── reports/
│   │   ├── charts.py       # Gráficos TikZ
│   │   ├── generator.py    # Generador reportes
│   │   └── templates/      # Templates Jinja2
│   └── cli.py              # Interfaz de comandos
├── tests/                  # Tests unitarios
├── docs/                   # Documentación
└── examples/               # Ejemplos LaTeX
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
