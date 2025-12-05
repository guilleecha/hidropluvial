# HidroPluvial - Documentación de Metodologías

**Fundamentos teóricos de los métodos implementados**

---

## Contenido

1. [Curvas IDF](#1-curvas-idf)
2. [Tormentas de Diseño](#2-tormentas-de-diseño)
3. [Tiempo de Concentración](#3-tiempo-de-concentración)
4. [Escorrentía](#4-escorrentía)
5. [Hidrogramas](#5-hidrogramas)
6. [Referencias](#6-referencias)

---

## 1. Curvas IDF

### 1.1 Método DINAGUA Uruguay

Las curvas Intensidad-Duración-Frecuencia (IDF) para Uruguay se calculan a partir del valor base P₃,₁₀ (precipitación para 3 horas y período de retorno de 10 años).

#### Fórmula General

```
i = P₃,₁₀ × CT × CA / d
```

Donde:
- `i`: Intensidad de precipitación (mm/hr)
- `P₃,₁₀`: Precipitación base de 3 horas y Tr=10 años (mm)
- `CT`: Factor de duración y frecuencia
- `CA`: Factor de corrección por área (si aplica)
- `d`: Duración de la tormenta (hr)

#### Factor CT (Duración-Frecuencia)

El factor CT depende de la duración y el período de retorno:

| Tr (años) | Factor CT base |
|-----------|----------------|
| 2 | 0.60 |
| 5 | 0.84 |
| 10 | 1.00 |
| 25 | 1.18 |
| 50 | 1.30 |
| 100 | 1.41 |

Para duraciones distintas a 3 horas se aplica el factor de duración:
- d < 3h: CT se incrementa
- d > 3h: CT se reduce

#### Factor CA (Corrección por Área)

Para cuencas mayores a 25 km², se aplica una reducción:

```
CA = 1.0  si A ≤ 25 km²
CA = 0.9  si A ≈ 50 km²
CA = 0.8  si A ≈ 100 km²
```

#### Implementación

```python
from hidropluvial.core.idf import dinagua_intensity_simple, dinagua_depth

# Calcular intensidad
i = dinagua_intensity_simple(p3_10=78, tr=25, duration_hr=1.0)
# Resultado: 53.2 mm/hr

# Calcular precipitación total
P = dinagua_depth(p3_10=78, tr=25, duration_hr=3.0)
# Resultado: 91.9 mm
```

---

## 2. Tormentas de Diseño

### 2.1 Método de Bloques Alternantes

El método de bloques alternantes genera un hietograma sintético que preserva las relaciones de la curva IDF.

#### Algoritmo

1. **Calcular profundidades acumuladas**: Para cada duración `d = n × Δt`, calcular la precipitación acumulada usando la curva IDF:
   ```
   P(d) = i(d) × d
   ```

2. **Obtener incrementos**: Calcular la precipitación incremental para cada intervalo:
   ```
   ΔP(n) = P(n×Δt) - P((n-1)×Δt)
   ```

3. **Ordenar de mayor a menor**: Los incrementos se ordenan de forma descendente.

4. **Distribuir alternadamente**: Se colocan los bloques alternando a izquierda y derecha del pico:
   - Bloque más intenso → posición del pico
   - Segundo bloque → izquierda del pico
   - Tercer bloque → derecha del pico
   - Y así sucesivamente...

#### Variantes Implementadas

| Código | Descripción | Duración | Posición del Pico |
|--------|-------------|----------|-------------------|
| `blocks` | Bloques estándar | Tc × 1.0 - 2.0 | 50% (centro) |
| `gz` | Pico adelantado | 6 horas fijas | 16.7% (1/6) |
| `blocks24` | 24 horas | 24 horas | 50% (centro) |

#### Tormenta GZ (Pico Adelantado)

La tormenta GZ es una variante utilizada en Uruguay donde:
- Duración fija: 6 horas
- Pico al inicio: posición = 1/6 ≈ 16.7%
- Δt = 5 minutos (72 intervalos)

```python
from hidropluvial.core.temporal import alternating_blocks_dinagua

# Generar hietograma GZ para Tr=25
hyetograph = alternating_blocks_dinagua(
    p3_10=78,
    return_period_yr=25,
    duration_hr=6.0,
    dt_min=5.0,
    peak_position=1/6  # Pico adelantado
)

# Acceder a resultados
print(f"P total: {hyetograph.total_depth_mm:.1f} mm")
print(f"i pico: {hyetograph.peak_intensity_mmhr:.1f} mm/hr")
```

### 2.2 Tormenta Bimodal

La tormenta bimodal representa eventos con doble pico, típicos de:
- Sistemas frontales de larga duración
- Regiones costeras tropicales
- Tormentas de convección múltiple

#### Algoritmo

1. Definir dos picos triangulares con posiciones p₁ y p₂
2. Distribuir el volumen total según `volume_split`
3. Para cada pico, crear una distribución triangular:
   - Rama ascendente lineal hasta el pico
   - Rama descendente lineal desde el pico
4. Superponer ambos picos

#### Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `peak1_position` | 0.25 | Posición del primer pico (25% de duración) |
| `peak2_position` | 0.75 | Posición del segundo pico (75%) |
| `volume_split` | 0.5 | Fracción del volumen en primer pico |
| `peak_width_fraction` | 0.15 | Ancho de cada pico |

```python
from hidropluvial.core.temporal import bimodal_dinagua

hyetograph = bimodal_dinagua(
    p3_10=78,
    return_period_yr=25,
    duration_hr=6.0,
    peak1_position=0.25,
    peak2_position=0.75,
    volume_split=0.5
)
```

### 2.3 Distribuciones SCS 24 Horas

Las distribuciones SCS representan la distribución temporal de tormentas de 24 horas desarrolladas por el Soil Conservation Service (ahora NRCS).

#### Tipos de Distribución

| Tipo | Región Climática | Pico |
|------|------------------|------|
| Tipo I | Costa Pacífico | Suave, duración larga |
| Tipo IA | Costa NO Pacífico | Muy suave |
| Tipo II | Interior continental | Fuerte, pico central |
| Tipo III | Costa Atlántico/Golfo | Fuerte, tropical |

#### Implementación

Las distribuciones se leen desde tablas de valores acumulados y se interpolan al intervalo de tiempo requerido.

```python
from hidropluvial.core.temporal import scs_distribution
from hidropluvial.config import StormMethod

hyetograph = scs_distribution(
    total_depth_mm=91.9,
    duration_hr=24.0,
    dt_min=10.0,
    storm_type=StormMethod.SCS_TYPE_II
)
```

### 2.4 Curvas Huff

Las curvas Huff (1967) representan la distribución temporal de tormentas basadas en análisis probabilístico de eventos reales.

#### Cuartiles

| Cuartil | Descripción | Uso Típico |
|---------|-------------|------------|
| Q1 | Pico en primer cuarto | Tormentas convectivas cortas |
| Q2 | Pico en segundo cuarto | Tormentas típicas |
| Q3 | Pico en tercer cuarto | Sistemas frontales |
| Q4 | Pico en último cuarto | Tormentas de larga duración |

---

## 3. Tiempo de Concentración

### 3.1 Método de Kirpich (1940)

Desarrollado para pequeñas cuencas rurales en Tennessee.

#### Fórmula

```
Tc = 0.0195 × L^0.77 × S^(-0.385)
```

Donde:
- `Tc`: Tiempo de concentración (minutos)
- `L`: Longitud del cauce principal (metros)
- `S`: Pendiente del cauce (m/m)

#### Factores de Ajuste

| Superficie | Factor |
|------------|--------|
| Natural | 1.0 |
| Canales con pasto | 2.0 |
| Concreto/asfalto | 0.4 |
| Canales de concreto | 0.2 |

#### Limitaciones

- Desarrollado para cuencas < 80 ha
- Válido para pendientes 3-10%
- No considera impermeabilidad

### 3.2 Método de Témez

Fórmula empírica desarrollada para España y ampliamente usada en Latinoamérica.

#### Fórmula

```
Tc = 0.3 × (L / S^0.25)^0.76
```

Donde:
- `Tc`: Tiempo de concentración (horas)
- `L`: Longitud del cauce (km)
- `S`: Pendiente del cauce (m/m)

#### Aplicación

- Válido para cuencas de 1-3000 km²
- Más conservador que Kirpich para cuencas grandes

### 3.3 Método de Desbordes (DINAGUA)

Desarrollado específicamente para cuencas urbanas uruguayas.

#### Fórmula

```
Tc = t₀ + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)
```

Donde:
- `Tc`: Tiempo de concentración (minutos)
- `t₀`: Tiempo de entrada inicial (minutos)
- `A`: Área de la cuenca (hectáreas)
- `P`: Pendiente media (%)
- `C`: Coeficiente de escorrentía

#### Parámetro t₀

El tiempo de entrada `t₀` representa el tiempo desde que la lluvia cae hasta que entra al sistema de drenaje:

| t₀ | Condición |
|----|-----------|
| 3 min | Urbano muy denso |
| 5 min | Urbano típico (default) |
| 10 min | Suburbano/rural |

#### Consideraciones Importantes

- El Tc **varía con el período de retorno** porque C cambia
- Mayor C → menor Tc
- Debe recalcularse para cada Tr si C depende de Tr (tabla Ven Te Chow)

### 3.4 Método NRCS (TR-55)

Método de velocidades que divide el flujo en tres componentes.

#### Componentes

1. **Flujo Laminar (Sheet Flow)**
   ```
   Tt = 0.007 × (n × L)^0.8 / (P₂^0.5 × S^0.4)
   ```
   - L: máximo ~100 m
   - n: coeficiente de rugosidad
   - P₂: precipitación 2 años, 24h (mm)

2. **Flujo Concentrado Superficial (Shallow Flow)**
   ```
   V = k × S^0.5
   Tt = L / (V × 3600)
   ```
   Valores de k:
   | Superficie | k (m/s) |
   |------------|---------|
   | Pavimentado | 6.20 |
   | Sin pavimentar | 4.92 |
   | Con pasto | 4.57 |

3. **Flujo en Canal (Channel Flow)**
   ```
   V = (1/n) × R^(2/3) × S^(1/2)  [Manning]
   Tt = L / (V × 3600)
   ```

---

## 4. Escorrentía

### 4.1 Método Racional

Método empírico para estimar caudal pico en cuencas pequeñas.

#### Fórmula

```
Q = 0.00278 × Cf × C × i × A
```

Donde:
- `Q`: Caudal pico (m³/s)
- `Cf`: Factor de frecuencia
- `C`: Coeficiente de escorrentía (0-1)
- `i`: Intensidad de lluvia (mm/hr)
- `A`: Área de la cuenca (ha)

#### Factor de Frecuencia Cf

| Tr (años) | Cf |
|-----------|-----|
| 2-10 | 1.00 |
| 25 | 1.10 |
| 50 | 1.20 |
| 100 | 1.25 |

Nota: Cf × C nunca debe exceder 1.0

#### Limitaciones

- Cuencas < 500 ha (ideal < 100 ha)
- Asume intensidad uniforme
- Asume coeficiente C constante
- No genera hidrograma, solo pico

### 4.2 Método SCS Curve Number (CN)

Método desarrollado por el SCS (ahora NRCS) para estimar escorrentía directa.

#### Retención Potencial S

```
S = (25400 / CN) - 254  [mm]
```

Donde CN está entre 30 y 100:
- CN = 100: superficie impermeable
- CN = 30: alta infiltración

#### Abstracción Inicial Ia

```
Ia = λ × S
```

Donde λ (lambda) es el coeficiente de abstracción:
- **λ = 0.20**: Valor tradicional SCS
- **λ = 0.05**: Recomendado para áreas urbanas (Hawkins 2002)

#### Escorrentía Directa Q

```
Q = (P - Ia)² / (P - Ia + S)    si P > Ia
Q = 0                            si P ≤ Ia
```

#### Ajuste por Condición de Humedad Antecedente (AMC)

El CN base se especifica para condiciones AMC II (promedio). Para otras condiciones:

**AMC I (Seco)**: Poco o nada de lluvia los 5 días previos
```
CN_I = CN_II / (2.281 - 0.01281 × CN_II)
```

**AMC III (Húmedo)**: Lluvia significativa los 5 días previos
```
CN_III = CN_II / (0.427 + 0.00573 × CN_II)
```

#### Ejemplo de Ajuste AMC

| CN_II | CN_I (Seco) | CN_III (Húmedo) |
|-------|-------------|-----------------|
| 60 | 40 | 78 |
| 70 | 51 | 85 |
| 80 | 63 | 91 |
| 90 | 78 | 96 |

### 4.3 Precipitación Efectiva (Serie Temporal)

Para generar hidrogramas, se necesita la serie temporal de exceso de lluvia:

```python
from hidropluvial.core.runoff import rainfall_excess_series

# Precipitación acumulada del hietograma
cumulative_mm = hyetograph.cumulative_mm

# Calcular exceso incremental
excess = rainfall_excess_series(
    cumulative_rainfall_mm=np.array(cumulative_mm),
    cn=81,
    lambda_coef=0.2
)
```

---

## 5. Hidrogramas

### 5.1 Hidrograma Unitario Triangular SCS

El SCS desarrolló un hidrograma unitario adimensional simplificado a forma triangular.

#### Parámetros

```
Tp = D/2 + 0.6 × Tc    [Tiempo al pico]
Tb = 2.67 × Tp         [Tiempo base]
qp = 0.208 × A / Tp    [Caudal pico unitario, m³/s/mm]
```

Donde:
- `D`: Duración del exceso de lluvia (hr)
- `Tc`: Tiempo de concentración (hr)
- `A`: Área de la cuenca (km²)

#### Factor X

El factor X modifica la forma del hidrograma:

```
X = Tb / Tp
```

| X | Descripción |
|---|-------------|
| 1.00 | Respuesta rápida (pico alto, corto) |
| 1.25 | Intermedio |
| 1.50 | Respuesta lenta |
| 1.67 | SCS estándar |
| 2.00 | Muy atenuado |

Mayor X → Pico menor pero más prolongado.

### 5.2 Hidrograma Unitario Curvilíneo SCS

Forma más realista basada en hidrogramas observados:
- Rama ascendente cóncava
- Pico redondeado
- Rama descendente convexa con cola exponencial

### 5.3 Convolución

El hidrograma de crecida se obtiene por convolución del exceso de lluvia con el hidrograma unitario:

```
Q(t) = Σ P_exc(i) × UH(t - i)
```

Donde:
- `Q(t)`: Ordenada del hidrograma resultante
- `P_exc(i)`: Exceso de lluvia en intervalo i
- `UH`: Hidrograma unitario

---

## 6. Referencias

### Curvas IDF
- DINAGUA. "Curvas Intensidad-Duración-Frecuencia para Uruguay". Ministerio de Vivienda, Ordenamiento Territorial y Medio Ambiente.

### Tormentas de Diseño
- Chow, V.T., Maidment, D.R., Mays, L.W. (1988). "Applied Hydrology". McGraw-Hill.
- Keifer, C.J., Chu, H.H. (1957). "Synthetic Storm Pattern for Drainage Design". Journal of the Hydraulics Division, ASCE.
- Huff, F.A. (1967). "Time Distribution of Rainfall in Heavy Storms". Water Resources Research.
- SCS (1986). "Urban Hydrology for Small Watersheds". TR-55.

### Tiempo de Concentración
- Kirpich, Z.P. (1940). "Time of Concentration of Small Agricultural Watersheds". Civil Engineering.
- Témez, J.R. (1978). "Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales". MOPU, España.
- DINAGUA. "Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas".

### Escorrentía
- SCS (1972). "National Engineering Handbook, Section 4: Hydrology".
- Hawkins, R.H., et al. (2002). "Continuing Evolution of Rainfall-Runoff and the Curve Number Precedent". ASCE.

### Hidrogramas
- SCS (1972). "National Engineering Handbook, Section 4: Hydrology".
- Mockus, V. (1949). "Estimation of Direct Runoff from Storm Rainfall". SCS-TP-149.

---

*Documentación de Metodologías - HidroPluvial v1.0*
