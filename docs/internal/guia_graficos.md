# Guía de Generación de Gráficos TikZ/PGFPlots

Esta guía explica cómo usar el módulo `reports.charts` para generar gráficos LaTeX compatibles con TikZ/PGFPlots.

## Requisitos LaTeX

En el preámbulo del documento LaTeX, incluir:

```latex
\usepackage{pgfplots}
\usepackage{float}
\pgfplotsset{compat=1.18}
```

## Instalación

```bash
pip install -e .
```

## Importación

```python
from hidropluvial.reports import (
    generate_hydrograph_tikz,
    generate_hydrograph_comparison_tikz,
    generate_hyetograph_tikz,
    generate_hyetograph_filled_tikz,
    hydrograph_result_to_tikz,
    hyetograph_result_to_tikz,
    HydrographSeries,
)
```

---

## 1. Hietogramas

### 1.1 Hietograma básico (barras sin relleno)

```python
from hidropluvial.core.temporal import alternating_blocks_dinagua
from hidropluvial.reports import hyetograph_result_to_tikz

# Generar hietograma DINAGUA
# P3,10 = 78 mm (Montevideo), Tr = 25 años, duración 6 horas, dt = 5 min
result = alternating_blocks_dinagua(
    p3_10=78,
    return_period_yr=25,
    duration_hr=6,
    dt_min=5
)

# Convertir a TikZ
tikz = hyetograph_result_to_tikz(
    result,
    caption='Hietograma de diseño para período de retorno de 25 años.',
    label='fig:hietograma_tr25',
    title=r'Hietograma de Diseño - $T_r=25$ años'
)

# Guardar a archivo
with open('hietograma.tex', 'w', encoding='utf-8') as f:
    f.write(tikz)
```

### 1.2 Hietograma con relleno

```python
from hidropluvial.reports import generate_hyetograph_filled_tikz

tikz = generate_hyetograph_filled_tikz(
    time_min=[5, 10, 15, 20, 25, 30],
    intensity_mmhr=[10, 30, 80, 30, 15, 5],
    caption='Hietograma con relleno',
    label='fig:hyeto_filled',
    fill_color='blue!30'  # Color de relleno
)
```

### 1.3 Hietograma desde datos propios

```python
from hidropluvial.reports import generate_hyetograph_tikz

# Datos propios
tiempos = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]  # minutos
intensidades = [5, 10, 20, 50, 100, 150, 100, 50, 20, 10, 5, 2]  # mm/h

tikz = generate_hyetograph_tikz(
    time_min=tiempos,
    intensity_mmhr=intensidades,
    caption='Tormenta de diseño',
    label='fig:storm',
    title='Hietograma Personalizado',
    xlabel='Tiempo',
    ylabel='Intensidad (mm/h)',
    ymax=180,  # Límite Y manual (opcional)
    bar_width=4  # Ancho de barras (opcional)
)
```

---

## 2. Hidrogramas

### 2.1 Hidrograma simple

```python
from hidropluvial.core.hydrograph import generate_hydrograph
from hidropluvial.config import HydrographMethod
from hidropluvial.reports import hydrograph_result_to_tikz
import numpy as np

# Exceso de lluvia (mm por intervalo)
rainfall_excess = np.array([0, 2, 5, 10, 8, 4, 2, 1, 0.5])

# Generar hidrograma SCS
result = generate_hydrograph(
    rainfall_excess_mm=rainfall_excess,
    method=HydrographMethod.SCS_CURVILINEAR,
    area_km2=5.0,
    tc_hr=1.5,
    dt_hr=0.1
)

# Convertir a TikZ
tikz = hydrograph_result_to_tikz(
    result,
    caption='Hidrograma de crecida',
    label='fig:hidrograma'
)
```

### 2.2 Comparación de hidrogramas (Sin/Con MCE)

Este es el formato más común para comparar escenarios:

```python
from hidropluvial.reports import generate_hydrograph_comparison_tikz

# Datos de dos escenarios
tiempo = list(range(0, 481, 5))  # 0 a 480 min, cada 5 min

# Escenario sin medidas de control (pico más alto)
caudal_sin_mce = [...]  # tus datos

# Escenario con medidas de control (pico reducido)
caudal_con_mce = [...]  # tus datos

tikz = generate_hydrograph_comparison_tikz(
    time_min_1=tiempo,
    flow_m3s_1=caudal_sin_mce,
    time_min_2=tiempo,
    flow_m3s_2=caudal_con_mce,
    label_1='Sin MCE',      # Rojo, discontinuo
    label_2='Con MCE',      # Negro, sólido
    caption='Comparación de hidrogramas con y sin medidas de control.',
    label='fig:hidrograma_comparacion'
)
```

### 2.3 Hidrograma con múltiples series

```python
from hidropluvial.reports import generate_hydrograph_tikz, HydrographSeries

# Definir series
series = [
    HydrographSeries(
        time_min=tiempo,
        flow_m3s=caudal_actual,
        label='Condición actual',
        color='red',
        style='dashed'
    ),
    HydrographSeries(
        time_min=tiempo,
        flow_m3s=caudal_proyectado,
        label='Proyección 2050',
        color='blue',
        style='dotted'
    ),
    HydrographSeries(
        time_min=tiempo,
        flow_m3s=caudal_mitigado,
        label='Con mitigación',
        color='black',
        style='solid'
    ),
]

tikz = generate_hydrograph_tikz(
    series,
    caption='Análisis de escenarios hidrológicos',
    label='fig:escenarios',
    legend_pos='north east',
    ymax=50  # Límite Y manual
)
```

---

## 3. Parámetros comunes

### Dimensiones y estilo

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `width` | `\textwidth` | Ancho del gráfico |
| `height` | `8cm` | Alto del gráfico |
| `legend_pos` | `north east` | Posición de leyenda |
| `ymax` | Auto | Límite superior eje Y |

### Etiquetas LaTeX

| Parámetro | Descripción |
|-----------|-------------|
| `caption` | Título de la figura |
| `label` | Etiqueta para `\ref{}` |
| `title` | Título dentro del gráfico |
| `xlabel` | Etiqueta eje X |
| `ylabel` | Etiqueta eje Y |

### Estilos de línea (hidrogramas)

| Estilo | Descripción |
|--------|-------------|
| `solid` | Línea continua |
| `dashed` | Línea discontinua |
| `dotted` | Línea punteada |

### Colores disponibles

Cualquier color LaTeX: `black`, `red`, `blue`, `green`, `orange`, `purple`, `gray`, etc.
También mezclas: `blue!50`, `red!30!black`, etc.

---

## 4. Ejemplo completo: Memoria de cálculo

```python
from hidropluvial.core.temporal import alternating_blocks_dinagua
from hidropluvial.core.runoff import scs_runoff_series
from hidropluvial.core.hydrograph import generate_hydrograph
from hidropluvial.config import HydrographMethod
from hidropluvial.reports import hyetograph_result_to_tikz, hydrograph_result_to_tikz
import numpy as np

# === 1. Parámetros de entrada ===
P3_10 = 78          # mm (Montevideo)
Tr = 25             # años
duracion = 6        # horas
dt_min = 5          # minutos
area_km2 = 2.5      # km²
CN = 80             # Número de curva
tc_hr = 0.75        # Tiempo de concentración (horas)

# === 2. Generar hietograma ===
hietograma = alternating_blocks_dinagua(
    p3_10=P3_10,
    return_period_yr=Tr,
    duration_hr=duracion,
    dt_min=dt_min
)

# === 3. Calcular escorrentía ===
precipitacion = np.array(hietograma.depth_mm)
escorrentia = scs_runoff_series(precipitacion, CN)

# === 4. Generar hidrograma ===
hidrograma = generate_hydrograph(
    rainfall_excess_mm=escorrentia,
    method=HydrographMethod.SCS_CURVILINEAR,
    area_km2=area_km2,
    tc_hr=tc_hr,
    dt_hr=dt_min/60
)

# === 5. Generar código LaTeX ===
tex_hietograma = hyetograph_result_to_tikz(
    hietograma,
    caption=f'Hietograma de diseño para $T_r={Tr}$ años.',
    label='fig:hietograma',
    title=f'Hietograma - $T_r={Tr}$ años'
)

tex_hidrograma = hydrograph_result_to_tikz(
    hidrograma,
    caption=f'Hidrograma de crecida para $T_r={Tr}$ años.',
    label='fig:hidrograma'
)

# === 6. Guardar archivos ===
with open('figuras/hietograma.tex', 'w', encoding='utf-8') as f:
    f.write(tex_hietograma)

with open('figuras/hidrograma.tex', 'w', encoding='utf-8') as f:
    f.write(tex_hidrograma)

# === 7. Resumen ===
print(f"Precipitación total: {hietograma.total_depth_mm:.1f} mm")
print(f"Intensidad pico: {hietograma.peak_intensity_mmhr:.1f} mm/h")
print(f"Caudal pico: {hidrograma.peak_flow_m3s:.2f} m³/s")
print(f"Tiempo al pico: {hidrograma.time_to_peak_hr:.2f} h")
```

---

## 5. Incluir en documento LaTeX

```latex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[spanish]{babel}
\usepackage{pgfplots}
\usepackage{float}
\pgfplotsset{compat=1.18}

\begin{document}

\section{Análisis Hidrológico}

\subsection{Hietograma de Diseño}
\input{figuras/hietograma.tex}

Como se observa en la Figura \ref{fig:hietograma}, la intensidad máxima...

\subsection{Hidrograma de Crecida}
\input{figuras/hidrograma.tex}

El hidrograma resultante (Figura \ref{fig:hidrograma}) muestra un caudal pico de...

\end{document}
```

---

## 6. Formato del eje X (tiempo en horas)

El módulo automáticamente formatea el eje X en horas (0:00, 1:00, 2:00...) con intervalos apropiados según la duración:

| Duración | Intervalo de ticks |
|----------|-------------------|
| ≤ 3 h | 30 min |
| ≤ 6 h | 1 h |
| ≤ 12 h | 2 h |
| ≤ 24 h | 4 h |
| > 24 h | 6 h |

---

## 7. Solución de problemas

### Caracteres especiales en LaTeX

Para texto con caracteres especiales en títulos:

```python
# Usar raw strings (r'...') para LaTeX
title=r'Tormenta $T_r=10$ años'

# O escapar backslashes
title='Tormenta $T_r=10$ a\\~nos'
```

### Gráficos muy anchos

```python
tikz = generate_hyetograph_tikz(
    ...,
    width='0.8\\textwidth',  # Reducir ancho
    height='6cm'             # Reducir alto
)
```

### Leyenda superpuesta con datos

```python
tikz = generate_hydrograph_tikz(
    ...,
    legend_pos='south east'  # Mover leyenda
)
```

Posiciones disponibles: `north east`, `north west`, `south east`, `south west`, `outer north east`
