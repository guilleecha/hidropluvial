# HidroPluvial

**Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-783%20passed-green.svg)]()

---

## Tabla de Contenidos

- [Características](#características)
- [Instalación](#instalación-rápida)
- [Uso](#uso)
- [Metodologías Implementadas](#metodologías-implementadas)
  - [Curvas IDF](#1-curvas-idf-dinagua-uruguay)
  - [Tiempo de Concentración](#2-tiempo-de-concentración)
  - [Escorrentía](#3-escorrentía)
  - [Hidrogramas](#4-hidrogramas-unitarios)
- [Documentación](#documentación)
- [Referencias Bibliográficas](#referencias-bibliográficas)

---

## Características

- **Curvas IDF** - Método DINAGUA Uruguay con factores CT y CA
- **Hietogramas** - Bloques alternantes (GZ), Chicago, SCS Tipo I/II/III, Huff, Bimodal
- **Tiempo de concentración** - Kirpich, Témez, Desbordes (DINAGUA), NRCS TR-55
- **Escorrentía** - SCS Curve Number (con AMC y λ configurable), Método Racional
- **Hidrogramas** - SCS triangular/curvilíneo, Triangular con factor X
- **Visor interactivo** - Hietograma + hidrograma combinados con navegación por teclado
- **Gestión de Proyectos** - Organización jerárquica Proyecto → Cuencas → Análisis
- **Reportes LaTeX** - Memorias de cálculo con gráficos TikZ/PGFPlots
- **Exportación** - Excel, CSV, fichas técnicas PDF

---

## Instalación Rápida

```bash
git clone https://github.com/guilleecha/hidropluvial.git
cd hidropluvial
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
hp --help
```

> Ver [docs/INSTALACION.md](docs/INSTALACION.md) para guía completa incluyendo LaTeX.

---

## Uso

### Wizard Interactivo

La forma principal de usar HidroPluvial es a través del wizard:

```bash
hp wizard
```

```
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Análisis                |
|         Cálculos hidrológicos para Uruguay                  |
+-------------------------------------------------------------+

? ¿Qué deseas hacer?
> 1. Nueva cuenca (análisis guiado)
  2. Crear nuevo proyecto
  3. Continuar proyecto/cuenca existente
  4. Gestionar proyectos y cuencas
  5. Ver comandos disponibles
  6. Salir
```

### Visor de Gráficos

El visor interactivo muestra hietograma e hidrograma combinados:

```
┌─────────────────────────────────────────────────────────────┐
│           Hietograma - P=106mm, imax=54mm/h                 │
│  60 ┤   ████                                                │
│  20 ┤███████████████                                        │
├─────────────────────────────────────────────────────────────┤
│           Hidrograma - Qp=12 m³/s, Tp=35min                 │
│  12 ┤          ×                                            │
│   4 ┤        ╱   ╲                                          │
└─────────────────────────────────────────────────────────────┘
[1/12] Kirpich + GZ Tr10

[←] Anterior  [→] Siguiente  [q] Salir
```

---

## Metodologías Implementadas

### 1. Curvas IDF (DINAGUA Uruguay)

Cálculo de intensidades de precipitación según metodología Rodríguez Fontal (1980).

**Fórmulas:**

```
CT(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]

CA(A,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × A))

I(d<3h) = P₃,₁₀ × CT × 0.6208 / (d + 0.0137)^0.5639
I(d≥3h) = P₃,₁₀ × CT × 1.0287 / (d + 1.0293)^0.8083
```

**Código:** [`src/hidropluvial/core/idf.py`](src/hidropluvial/core/idf.py)

```python
def dinagua_ct(return_period_yr: float) -> float:
    """Factor de corrección por período de retorno (CT)."""
    Tr = return_period_yr
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))
```

> Los valores P₃,₁₀ por departamento están disponibles en [docs/metodologias/idf.md](docs/metodologias/idf.md)

---

### 2. Tiempo de Concentración

#### Kirpich (1940)

Para cuencas rurales pequeñas (< 80 ha).

```
tc = 0.0195 × L^0.77 × S^(-0.385)  [tc: min, L: m, S: m/m]
```

**Código:** [`src/hidropluvial/core/tc.py:40-81`](src/hidropluvial/core/tc.py)

```python
def kirpich(length_m: float, slope: float, surface_type: str = "natural") -> float:
    """Calcula Tc usando fórmula Kirpich (1940)."""
    tc_min = 0.0195 * (length_m ** 0.77) * (slope ** -0.385)
    return tc_min / 60.0  # horas
```

#### Témez (1978)

Para cuencas de 1-3000 km² (España/Latinoamérica).

```
tc = 0.3 × (L / S^0.25)^0.76  [tc: hr, L: km, S: m/m]
```

**Código:** [`src/hidropluvial/core/tc.py:224-245`](src/hidropluvial/core/tc.py)

```python
def temez(length_km: float, slope: float) -> float:
    """Calcula Tc usando fórmula Témez."""
    tc_hr = 0.3 * ((length_km / (slope ** 0.25)) ** 0.76)
    return tc_hr
```

#### Desbordes (DINAGUA Uruguay)

Para cuencas urbanas uruguayas.

```
Tc = t₀ + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)  [Tc: min]
```

Donde:
- t₀: Tiempo de entrada (típ. 5 min)
- A: Área (ha)
- P: Pendiente (%)
- C: Coeficiente de escorrentía

**Código:** [`src/hidropluvial/core/tc.py:301-334`](src/hidropluvial/core/tc.py)

```python
def desbordes(area_ha: float, slope_pct: float, c: float, t0_min: float = 5.0) -> float:
    """Calcula Tc usando Método de los Desbordes (DINAGUA Uruguay)."""
    tc_min = t0_min + 6.625 * (area_ha ** 0.3) * (slope_pct ** -0.39) * (c ** -0.45)
    return tc_min / 60.0  # horas
```

#### NRCS TR-55

Método de velocidades por segmentos (sheet flow, shallow flow, channel flow).

```
Tc = Tt_sheet + Tt_shallow + Tt_channel

Tt_sheet = 0.007 × (n×L)^0.8 / (P₂^0.5 × S^0.4)  [hr]
Tt_shallow = L / (k × S^0.5 × 3600)              [hr]
Tt_channel = L / (V × 3600)                      [hr, Manning]
```

**Código:** [`src/hidropluvial/core/tc.py:84-221`](src/hidropluvial/core/tc.py)

---

### 3. Escorrentía

#### SCS Curve Number (CN)

Método del Soil Conservation Service para precipitación efectiva.

```
S = (25400 / CN) - 254  [mm]
Ia = λ × S
Q = (P - Ia)² / (P - Ia + S)  para P > Ia
```

Donde:
- CN: Número de curva (30-100)
- λ: 0.20 (tradicional) o 0.05 (Hawkins 2002)
- Ia: Abstracción inicial

**Código:** [`src/hidropluvial/core/runoff.py`](src/hidropluvial/core/runoff.py)

```python
def scs_potential_retention(cn: int | float) -> float:
    """S = (25400 / CN) - 254  [mm]"""
    return (25400 / cn) - 254

def scs_runoff(rainfall_mm: float, cn: int | float, lambda_coef: float = 0.2) -> float:
    """Q = (P - Ia)² / (P - Ia + S) para P > Ia"""
    S = scs_potential_retention(cn)
    Ia = lambda_coef * S
    if rainfall_mm <= Ia:
        return 0.0
    return ((rainfall_mm - Ia) ** 2) / (rainfall_mm - Ia + S)
```

#### Método Racional

Para caudales pico en cuencas pequeñas (< 80 ha).

```
Q = 0.00278 × C × i × A  [Q: m³/s, i: mm/h, A: ha]
```

---

### 4. Hidrogramas Unitarios

#### SCS Triangular

```
tlag = 0.6 × Tc
Tp = D/2 + tlag = D/2 + 0.6×Tc
Tb = 2.67 × Tp
Qp = 2.08 × A × Q / Tp  [Qp: m³/s, A: km², Q: mm, Tp: hr]
```

El factor 2.08 es la conversión del factor 484 de unidades imperiales a métricas.

**Código:** [`src/hidropluvial/core/hydrograph.py:40-80`](src/hidropluvial/core/hydrograph.py)

```python
def scs_lag_time(tc_hr: float) -> float:
    """tlag = 0.6 × Tc"""
    return 0.6 * tc_hr

def scs_time_to_peak(tc_hr: float, dt_hr: float) -> float:
    """Tp = ΔD/2 + 0.6×Tc"""
    return dt_hr / 2 + scs_lag_time(tc_hr)

def scs_time_base(tp_hr: float) -> float:
    """Tb = 2.67 × Tp"""
    return 2.67 * tp_hr
```

#### Triangular con Factor X

Permite ajustar la forma del hidrograma según uso del suelo.

```
Tp = 0.5 × D + 0.6 × Tc
Qp = 0.278 × A / Tp × 2 / (1 + X)
Tb = (1 + X) × Tp
```

| Factor X | Aplicación |
|----------|------------|
| 1.00 | Racional / urbano interno |
| 1.25 | Urbano (gran pendiente) |
| 1.67 | NRCS estándar |
| 2.25 | Mixto rural/urbano |
| 3.33 | Rural sinuoso |

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Manual práctico con ejemplos paso a paso |
| [INSTALACION.md](docs/INSTALACION.md) | Guía completa de instalación |
| [COEFICIENTES.md](docs/COEFICIENTES.md) | Tablas de coeficientes C y CN |
| [METODOLOGIAS.md](docs/METODOLOGIAS.md) | Índice de fundamentos teóricos |

### Documentación Técnica Detallada

| Documento | Contenido |
|-----------|-----------|
| [metodologias/idf.md](docs/metodologias/idf.md) | Curvas IDF DINAGUA, Sherman, Bernard |
| [metodologias/tc.md](docs/metodologias/tc.md) | Tiempo de concentración |
| [metodologias/storms.md](docs/metodologias/storms.md) | Tormentas de diseño |
| [metodologias/runoff.md](docs/metodologias/runoff.md) | Escorrentía SCS-CN |
| [metodologias/hydrograph.md](docs/metodologias/hydrograph.md) | Hidrogramas unitarios |

---

## Comandos CLI

```bash
# Wizard interactivo (recomendado)
hp wizard

# Gestión de cuencas
hp basin list
hp basin show <id>
hp basin export <id> --format xlsx
hp basin report <id> --pdf

# Consultas IDF
hp idf departamentos
hp idf uruguay 78 3 --tr 25

# Tiempo de concentración
hp tc kirpich 800 0.0341
hp tc desbordes 62 3.41 0.62

# Escorrentía
hp runoff cn 100 81
hp runoff cn-table --group B
```

---

## Tests

```bash
pytest tests/ -v
```

Estado: **783 tests pasando**

---

## Referencias Bibliográficas

### Normativa Uruguay
- **Rodríguez Fontal, E.** (1980). "Método para curvas IDF en Uruguay". DINAGUA.
- **DINAGUA/MVOTMA**. "Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas".
- **HHA-FING UdelaR** (2019). "Guía Metodológica: Hidrología e Hidráulica Aplicada".

### Documentación NRCS/SCS
- **NRCS** (1986). "Urban Hydrology for Small Watersheds". Technical Release 55 (TR-55).
- **NRCS** (2004). "National Engineering Handbook, Part 630: Hydrology".

### Literatura Técnica
- **Chow, V.T., Maidment, D.R., Mays, L.W.** (1988). "Applied Hydrology". McGraw-Hill.
- **Kirpich, Z.P.** (1940). "Time of Concentration of Small Agricultural Watersheds". Civil Engineering, Vol. 10, No. 6.
- **Témez, J.R.** (1978). "Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales". MOPU, España.
- **Hawkins, R.H. et al.** (2002). "Curve Number Hydrology: State of the Practice". ASCE.
- **Snyder, F.F.** (1938). "Synthetic Unit-Graphs". Trans. AGU.

---

## Licencia

MIT License - Ver [LICENSE](LICENSE)
