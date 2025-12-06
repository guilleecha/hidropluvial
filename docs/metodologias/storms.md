# Tormentas de Diseño (Hietogramas)

Este documento describe los métodos implementados para generar hietogramas de diseño (distribuciones temporales de lluvia) en hidropluvial.

## Conceptos Fundamentales

### ¿Qué es un Hietograma?

Un **hietograma** es la representación gráfica de la distribución temporal de la precipitación durante una tormenta. Es la entrada fundamental para el cálculo de hidrogramas de crecida.

```
Intensidad (mm/hr)
    │
    │      ████
    │    ████████
    │  ████████████
    │████████████████
    └─────────────────→ Tiempo
```

### Parámetros Clave

| Parámetro | Símbolo | Descripción |
|-----------|---------|-------------|
| Precipitación total | P | Lámina total de lluvia (mm) |
| Duración | D | Duración total de la tormenta (hr) |
| Intervalo | Δt | Paso de tiempo del hietograma (min) |
| Período de retorno | Tr | Frecuencia de diseño (años) |
| Posición del pico | r | Fracción de D donde ocurre intensidad máxima |

---

## Métodos Implementados

### 1. Bloques Alternantes (Alternating Block Method)

**Referencia:** Chow, V.T., Maidment, D.R., Mays, L.W. (1988). *Applied Hydrology*

#### Descripción

El método más utilizado para drenaje urbano. Genera un hietograma sintético que preserva las intensidades de la curva IDF para todas las duraciones.

#### Algoritmo

1. Calcular profundidades acumuladas desde la curva IDF:
   $$P_i = I(t_i, Tr) \cdot t_i$$

2. Obtener incrementos de profundidad:
   $$\Delta P_i = P_i - P_{i-1}$$

3. Ordenar incrementos de mayor a menor

4. Colocar alternando alrededor del pico (izquierda-derecha)

#### Uso en hidropluvial

```python
from hidropluvial.core import alternating_blocks_dinagua

# Tormenta GZ (6 horas, pico al inicio)
hyetograph = alternating_blocks_dinagua(
    p3_10=83.0,           # P(3h, Tr=10) en mm
    return_period_yr=25,  # Período de retorno
    duration_hr=6.0,      # Duración total
    dt_min=5.0,           # Intervalo de tiempo
    peak_position=1/6,    # Pico en primer sexto (tormenta GZ)
)
```

#### Parámetro: Posición del Pico

| peak_position | Descripción | Aplicación |
|---------------|-------------|------------|
| 0.167 (1/6) | Pico al inicio | Tormenta GZ Uruguay |
| 0.375 | Primer tercio | Zonas costeras |
| 0.5 | Centro | Estándar/conservador |

---

### 2. Tormenta Chicago (Keifer & Chu, 1957)

**Referencia:** Keifer, C.J., Chu, H.H. (1957). "Synthetic Storm Pattern for Drainage Design". *Journal of the Hydraulics Division*, ASCE.

#### Descripción

Método analítico que genera un hietograma continuo derivado directamente de la curva IDF tipo Sherman.

#### Ecuaciones

Para curva IDF Sherman: $i = \frac{a}{(t + b)^c}$

**Antes del pico** (t medido hacia atrás desde el pico):
$$i_b = \frac{a \cdot [(1-c) \cdot (t_b/r) + b]}{[(t_b/r) + b]^{c+1}}$$

**Después del pico** (t medido hacia adelante):
$$i_a = \frac{a \cdot [(1-c) \cdot (t_a/(1-r)) + b]}{[(t_a/(1-r)) + b]^{c+1}}$$

Donde:
- $r$ = coeficiente de avance (posición del pico)
- $a, b, c$ = parámetros de la curva IDF Sherman

#### Uso en hidropluvial

```python
from hidropluvial.core import chicago_storm
from hidropluvial.config import ShermanCoefficients

coeffs = ShermanCoefficients(k=1200, m=0.15, c=10, n=0.75)

hyetograph = chicago_storm(
    total_depth_mm=80.0,
    duration_hr=2.0,
    dt_min=5.0,
    idf_coeffs=coeffs,
    return_period_yr=25,
    advancement_coef=0.375,  # Pico en 37.5% de la duración
)
```

---

### 3. Distribuciones SCS 24 Horas

**Referencia:** USDA-SCS (1986). *Urban Hydrology for Small Watersheds*, TR-55.

#### Descripción

Distribuciones estándar de 24 horas desarrolladas por el Soil Conservation Service (ahora NRCS) basadas en datos históricos de EE.UU.

#### Tipos de Tormenta

| Tipo | Región Típica | Características |
|------|---------------|-----------------|
| **I** | Costa Pacífico | Lluvias prolongadas, baja intensidad |
| **IA** | Costa NO EE.UU. | Similar a I, menor intensidad pico |
| **II** | Este EE.UU. / Uruguay | Tormentas convectivas intensas |
| **III** | Costa Atlántico Sur | Tormentas tropicales |

#### Distribución Acumulada (Tipo II)

| t/24 | P/P24 |
|------|-------|
| 0.0 | 0.000 |
| 0.25 | 0.048 |
| 0.375 | 0.080 |
| 0.458 | 0.120 |
| 0.50 | 0.663 |
| 0.542 | 0.735 |
| 0.625 | 0.800 |
| 0.75 | 0.880 |
| 1.0 | 1.000 |

#### Uso en hidropluvial

```python
from hidropluvial.core import scs_distribution
from hidropluvial.config import StormMethod

hyetograph = scs_distribution(
    total_depth_mm=120.0,
    duration_hr=24.0,
    dt_min=10.0,
    storm_type=StormMethod.SCS_TYPE_II,
)
```

---

### 4. Distribuciones Huff (1967)

**Referencia:** Huff, F.A. (1967). "Time Distribution of Rainfall in Heavy Storms". *Water Resources Research*.

#### Descripción

Distribuciones probabilísticas basadas en análisis de tormentas históricas en Illinois. Clasificadas por cuartil donde ocurre la mayor precipitación.

#### Cuartiles

| Cuartil | Pico en | Aplicación |
|---------|---------|------------|
| Q1 | 0-25% | Tormentas cortas intensas |
| Q2 | 25-50% | Más común en tormentas medianas |
| Q3 | 50-75% | Tormentas largas |
| Q4 | 75-100% | Tormentas de frente frío |

#### Niveles de Probabilidad

Cada cuartil tiene curvas para probabilidades 10%, 50% y 90%:
- **10%**: Patrón más extremo (pico más pronunciado)
- **50%**: Patrón mediano (recomendado para diseño)
- **90%**: Patrón más uniforme

#### Uso en hidropluvial

```python
from hidropluvial.core import huff_distribution

hyetograph = huff_distribution(
    total_depth_mm=60.0,
    duration_hr=3.0,
    dt_min=5.0,
    quartile=2,       # Pico en segundo cuartil
    probability=50,   # Mediana
)
```

---

### 5. Tormentas Bimodales (Doble Pico)

#### Descripción

Hietogramas con dos picos de intensidad, útiles para representar:
- Tormentas frontales de larga duración
- Cuencas con respuesta rápida y lenta combinadas
- Regiones con patrones de lluvia bimodales

#### Variantes Implementadas

1. **bimodal_storm**: Picos triangulares simples
2. **bimodal_dinagua**: Con IDF DINAGUA Uruguay
3. **bimodal_chicago**: Superposición de dos tormentas Chicago

#### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| peak1_position | Posición del primer pico | 0.25 |
| peak2_position | Posición del segundo pico | 0.75 |
| volume_split | Fracción de volumen en primer pico | 0.5 |
| peak_width_fraction | Ancho de cada pico | 0.15 |

#### Uso en hidropluvial

```python
from hidropluvial.core import bimodal_dinagua

hyetograph = bimodal_dinagua(
    p3_10=83.0,
    return_period_yr=25,
    duration_hr=6.0,
    dt_min=5.0,
    peak1_position=0.25,
    peak2_position=0.75,
    volume_split=0.5,
)
```

---

## Tormenta GZ (Estándar Uruguay)

### Descripción

La **Tormenta GZ** es el estándar recomendado por DINAGUA Uruguay para diseño de drenaje urbano. Es una tormenta de bloques alternantes con características específicas:

- **Duración**: 6 horas
- **Posición del pico**: 1/6 de la duración (primera hora)
- **Curva IDF**: DINAGUA basada en P(3h, Tr=10)

### Justificación

1. **Duración 6h**: Cubre el tiempo de concentración de la mayoría de cuencas urbanas
2. **Pico al inicio**: Conservador, genera caudales pico mayores
3. **Basada en P3,10**: Parámetro disponible en todo Uruguay

### Implementación

```python
from hidropluvial.core import alternating_blocks_dinagua

# Tormenta GZ estándar
gz_storm = alternating_blocks_dinagua(
    p3_10=83.0,           # Montevideo
    return_period_yr=10,
    duration_hr=6.0,
    dt_min=5.0,
    peak_position=1/6,    # Característica GZ
)
```

---

## Curvas IDF DINAGUA

### Ecuación Base

La intensidad se calcula a partir de P(3h, Tr=10):

$$i(d, Tr) = i_{3,10} \cdot F_d(d) \cdot F_{Tr}(Tr)$$

Donde:
- $i_{3,10} = P_{3,10} / 3$ (intensidad base en mm/hr)
- $F_d(d)$ = factor de duración
- $F_{Tr}(Tr)$ = factor de período de retorno

### Factor de Duración

$$F_d(d) = \left(\frac{3}{d}\right)^{0.75}$$

Para d en horas.

### Factor de Período de Retorno

| Tr (años) | $F_{Tr}$ |
|-----------|----------|
| 2 | 0.68 |
| 5 | 0.86 |
| 10 | 1.00 |
| 25 | 1.17 |
| 50 | 1.30 |
| 100 | 1.45 |

### Precipitación Total

$$P(d, Tr) = i(d, Tr) \cdot d$$

---

## Comparación de Métodos

### Por Aplicación

| Método | Aplicación Principal | Ventajas | Limitaciones |
|--------|---------------------|----------|--------------|
| **Bloques Alt.** | Drenaje urbano | Simple, conservador | Hietograma escalonado |
| **Chicago** | Diseño con IDF Sherman | Continuo, teóricamente consistente | Requiere IDF tipo Sherman |
| **SCS 24h** | Cuencas rurales, obras mayores | Basado en datos reales | Solo 24h, origen EE.UU. |
| **Huff** | Análisis probabilístico | Flexibilidad por cuartiles | Origen regional (Illinois) |
| **Bimodal** | Tormentas complejas | Representa patrones reales | Más parámetros |

### Por Duración Recomendada

| Duración | Método Recomendado |
|----------|-------------------|
| < 2 horas | Bloques alternantes |
| 2-6 horas | Bloques alternantes, Chicago |
| 6-12 horas | Huff, SCS (escalado) |
| 24 horas | SCS Tipo II |

---

## Estructura de Datos

### HyetographResult

```python
@dataclass
class HyetographResult:
    time_min: list[float]        # Tiempos centrales (min)
    intensity_mmhr: list[float]  # Intensidades (mm/hr)
    depth_mm: list[float]        # Profundidades incrementales (mm)
    cumulative_mm: list[float]   # Profundidades acumuladas (mm)
    method: str                  # Nombre del método
    total_depth_mm: float        # Precipitación total (mm)
    peak_intensity_mmhr: float   # Intensidad máxima (mm/hr)
```

---

## Archivos de Datos

Los datos tabulados se almacenan en `src/hidropluvial/data/`:

- `scs_distributions.json`: Distribuciones SCS tipos I, IA, II, III
- `huff_curves.json`: Curvas Huff Q1-Q4 con probabilidades 10%, 50%, 90%

### Formato SCS

```json
{
  "scs_type_ii": {
    "time_hr": [0.0, 0.5, 1.0, ...],
    "ratio": [0.0, 0.011, 0.022, ...]
  }
}
```

### Formato Huff

```json
{
  "huff_q2": {
    "probability_50": {
      "time_pct": [0, 5, 10, ...],
      "rain_pct": [0, 3, 8, ...]
    }
  }
}
```

---

## Referencias Bibliográficas

1. **Chow, V.T., Maidment, D.R., Mays, L.W.** (1988). *Applied Hydrology*. McGraw-Hill.

2. **Keifer, C.J., Chu, H.H.** (1957). "Synthetic Storm Pattern for Drainage Design". *Journal of the Hydraulics Division*, ASCE, 83(HY4).

3. **USDA-SCS** (1986). *Urban Hydrology for Small Watersheds*. Technical Release 55 (TR-55).

4. **Huff, F.A.** (1967). "Time Distribution of Rainfall in Heavy Storms". *Water Resources Research*, 3(4), 1007-1019.

5. **DINAGUA** (2011). *Manual de Drenaje Urbano para la República Oriental del Uruguay*. MVOTMA.

6. **Témez, J.R.** (1978). *Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales*. MOPU, España.
