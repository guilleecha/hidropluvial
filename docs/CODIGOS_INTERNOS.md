# HidroPluvial - Códigos Internos y Referencias

**Documentación técnica vinculando teoría y código fuente**

---

## Contenido

1. [Curvas IDF (Intensidad-Duración-Frecuencia)](#curvas-idf)
2. [Tiempo de Concentración](#tiempo-de-concentración)
3. [Métodos de Escorrentía](#métodos-de-escorrentía)
4. [Distribuciones Temporales de Lluvia](#distribuciones-temporales)
5. [Hidrogramas Unitarios](#hidrogramas-unitarios)
6. [Tablas de Coeficientes](#tablas-de-coeficientes)
7. [Referencias Bibliográficas Completas](#referencias-bibliográficas)

---

## Curvas IDF

### Metodología DINAGUA Uruguay

**Archivo:** `src/hidropluvial/core/idf/dinagua.py`

La metodología DINAGUA (Rodríguez Fontal, 1980) calcula la precipitación acumulada mediante:

```
P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)
```

#### Factor de Duración Cd(d)

**Código:** `dinagua.py:45-75`

```python
def dinagua_cd(duration_hr: float) -> float:
    """
    Factor de corrección por duración Cd(d).

    Para d ≤ 3 horas:
        Cd = 0.546 × d^0.526

    Para d > 3 horas:
        Cd = 0.456 + 0.181 × d
    """
```

**Referencia:** Rodríguez Fontal (1980). Estudio de Precipitaciones Máximas en Uruguay. DINAGUA.

#### Factor de Período de Retorno Ct(Tr)

**Código:** `dinagua.py:78-105`

```python
def dinagua_ct(return_period_yr: float) -> float:
    """
    Factor de corrección por período de retorno Ct(Tr).

    Ct = 0.2 + 0.53 × log₁₀(Tr)

    Válido para Tr entre 2 y 100 años.
    """
```

#### Factor de Área CA(A,d)

**Código:** `dinagua.py:108-145`

```python
def dinagua_ca(area_km2: float, duration_hr: float) -> float:
    """
    Factor de corrección por área de cuenca CA(A,d).

    CA = 1 - (0.001 × A^0.6) × (1 - e^(-0.3×d))

    Para A < 25 km² se considera CA = 1.0
    """
```

#### Valores P₃,₁₀ por Departamento

**Código:** `dinagua.py:15-40`

```python
P3_10_URUGUAY = {
    "montevideo": 78,
    "canelones": 80,
    "maldonado": 85,
    "colonia": 78,
    "san_jose": 80,
    "flores": 85,
    "florida": 85,
    "lavalleja": 90,
    "rocha": 90,
    "treinta_y_tres": 95,
    "cerro_largo": 95,
    "rivera": 95,
    "artigas": 95,
    "salto": 90,
    "paysandu": 85,
    "rio_negro": 85,
    "soriano": 80,
    "durazno": 85,
    "tacuarembo": 90,
}
```

---

## Tiempo de Concentración

### Método Kirpich (1940)

**Archivo:** `src/hidropluvial/core/tc/kirpich.py`

**Código:** `kirpich.py:8-49`

```python
def kirpich(
    length_m: float,
    slope: float,
    surface_type: str = "natural",
) -> float:
    """
    Calcula Tc usando fórmula Kirpich (1940).

    tc = 0.0195 × L^0.77 × S^(-0.385)

    Donde:
        tc: tiempo de concentración (min)
        L: longitud del cauce principal (m)
        S: pendiente media del cauce (m/m)

    Factores de ajuste por superficie:
        - 'natural': ×1.0
        - 'grassy': ×2.0 (canales con pasto)
        - 'concrete': ×0.4 (superficies de concreto/asfalto)
        - 'concrete_channel': ×0.2 (canales de concreto)
    """
    adjustment_factors = {
        "natural": 1.0,
        "grassy": 2.0,
        "concrete": 0.4,
        "concrete_channel": 0.2,
    }

    factor = adjustment_factors.get(surface_type, 1.0)
    tc_min = 0.0195 * (length_m ** 0.77) * (slope ** -0.385)
    tc_min *= factor

    return tc_min / 60.0  # Convertir a horas
```

**Referencia:** Kirpich, Z.P. (1940). Time of concentration of small agricultural watersheds. Civil Engineering, 10(6), 362.

**Aplicabilidad:** Cuencas agrícolas pequeñas (<80 ha), desarrollo original en Tennessee.

---

### Método Témez (1978)

**Archivo:** `src/hidropluvial/core/tc/empirical.py`

**Código:** `empirical.py:12-33`

```python
def temez(length_km: float, slope: float) -> float:
    """
    Calcula Tc usando fórmula Témez (España/Latinoamérica).

    tc = 0.3 × (L / S^0.25)^0.76

    Donde:
        tc: tiempo de concentración (hr)
        L: longitud del cauce principal (km)
        S: pendiente media (m/m)

    Válido para cuencas de 1-3000 km².
    """
    tc_hr = 0.3 * ((length_km / (slope ** 0.25)) ** 0.76)
    return tc_hr
```

**Referencia:** Témez, J.R. (1978). Cálculo hidrometeorológico de caudales máximos en pequeñas cuencas naturales. MOPU, España.

---

### Método Desbordes (DINAGUA Uruguay)

**Archivo:** `src/hidropluvial/core/tc/empirical.py`

**Código:** `empirical.py:89-123`

```python
def desbordes(
    area_ha: float,
    slope_pct: float,
    c: float,
    t0_min: float = 5.0,
) -> float:
    """
    Calcula Tc usando Método de los Desbordes (DINAGUA Uruguay).

    Tc = T0 + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)

    Donde:
        Tc: tiempo de concentración (min)
        T0: tiempo de entrada inicial (min), default 5
        A: área de la cuenca (ha)
        P: pendiente media de la cuenca (%)
        C: coeficiente de escorrentía (0-1)

    Recomendado en el "Manual de Diseño para Sistemas de Drenaje
    de Aguas Pluviales Urbanas" de DINAGUA.
    """
    tc_min = t0_min + 6.625 * (area_ha ** 0.3) * (slope_pct ** -0.39) * (c ** -0.45)
    return tc_min / 60.0  # Convertir a horas
```

**Referencia:** DINAGUA (2011). Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas. Uruguay.

**Aplicabilidad:** Cuencas urbanas, recomendado oficialmente para Uruguay.

---

### Método NRCS TR-55 (Velocidades)

**Archivo:** `src/hidropluvial/core/tc/nrcs.py`

#### Flujo Laminar (Sheet Flow)

**Código:** `nrcs.py:25-60`

```python
def nrcs_sheet_flow(
    length_m: float,
    n_manning: float,
    slope: float,
    p2_mm: float,
) -> float:
    """
    Tiempo de viaje para flujo laminar (sheet flow).

    Tt = 0.007 × (nL)^0.8 / (P2^0.5 × S^0.4)

    Donde:
        Tt: tiempo de viaje (hr)
        n: coeficiente de Manning
        L: longitud del flujo (m), máximo 100m recomendado
        P2: precipitación 24hr, Tr=2 años (mm)
        S: pendiente del terreno (m/m)
    """
```

**Coeficientes n típicos para sheet flow:**

| Superficie | n |
|------------|---|
| Pavimento liso | 0.011 |
| Suelo desnudo compactado | 0.05 |
| Césped denso | 0.24 |
| Bosque con sotobosque | 0.40 |

**Código constantes:** `nrcs.py` → `constants.py:15-30`

#### Flujo Superficial Concentrado (Shallow Concentrated)

**Código:** `nrcs.py:63-95`

```python
def nrcs_shallow_flow(
    length_m: float,
    slope: float,
    surface_type: str = "unpaved",
) -> float:
    """
    Tiempo de viaje para flujo superficial concentrado.

    V = k × S^0.5

    Donde:
        V: velocidad (m/s)
        k: coeficiente según superficie
        S: pendiente (m/m)

    Coeficientes k:
        - 'paved': 6.20 (superficies pavimentadas)
        - 'unpaved': 4.92 (superficies no pavimentadas)
    """
```

#### Flujo en Canal (Channel Flow)

**Código:** `nrcs.py:98-135`

```python
def nrcs_channel_flow(
    length_m: float,
    slope: float,
    n_manning: float,
    hydraulic_radius_m: float,
) -> float:
    """
    Tiempo de viaje para flujo en canal usando Manning.

    V = (1/n) × R^(2/3) × S^(1/2)

    Donde:
        V: velocidad (m/s)
        n: coeficiente de Manning del canal
        R: radio hidráulico (m)
        S: pendiente del canal (m/m)
    """
```

**Referencia:** USDA-NRCS (1986). Urban Hydrology for Small Watersheds. Technical Release 55 (TR-55). Chapter 3.

---

## Métodos de Escorrentía

### Método Racional

**Archivo:** `src/hidropluvial/core/runoff/rational.py`

**Código:** `rational.py:45-75`

```python
def rational_peak_flow(
    c: float,
    intensity_mmhr: float,
    area_ha: float,
) -> float:
    """
    Calcula caudal pico usando Método Racional.

    Qp = C × i × A / 360

    Donde:
        Qp: caudal pico (m³/s)
        C: coeficiente de escorrentía (adimensional)
        i: intensidad de lluvia (mm/h)
        A: área de la cuenca (ha)

    El factor 360 convierte las unidades:
        (mm/h) × (ha) / 360 = m³/s
    """
    return c * intensity_mmhr * area_ha / 360.0
```

**Referencia:** Chow, V.T., Maidment, D.R., Mays, L.W. (1988). Applied Hydrology. McGraw-Hill. Section 14.3.

---

### Método SCS-CN (Curve Number)

**Archivo:** `src/hidropluvial/core/runoff/scs.py`

#### Retención Potencial

**Código:** `scs.py:38-53`

```python
def scs_potential_retention(cn: int | float) -> float:
    """
    Calcula retención potencial máxima S.

    S = (25400 / CN) - 254  [mm]

    Args:
        cn: Número de curva (30-100)

    Returns:
        Retención potencial S en mm
    """
    return (25400 / cn) - 254
```

#### Abstracción Inicial

**Código:** `scs.py:56-69`

```python
def scs_initial_abstraction(s_mm: float, lambda_coef: float = 0.2) -> float:
    """
    Calcula abstracción inicial Ia.

    Ia = λ × S

    Args:
        s_mm: Retención potencial S en mm
        lambda_coef: Coeficiente λ
            - 0.20: valor tradicional SCS
            - 0.05: valor actualizado (Hawkins et al., 2002)

    Returns:
        Abstracción inicial en mm
    """
    return lambda_coef * s_mm
```

#### Escorrentía Directa

**Código:** `scs.py:72-104`

```python
def scs_runoff(
    rainfall_mm: float,
    cn: int | float,
    lambda_coef: float = 0.2,
) -> float:
    """
    Calcula escorrentía directa usando método SCS-CN.

    Q = (P - Ia)² / (P - Ia + S)    para P > Ia
    Q = 0                            para P ≤ Ia

    Donde:
        Q: escorrentía directa (mm)
        P: precipitación total (mm)
        Ia: abstracción inicial (mm)
        S: retención potencial (mm)
    """
    S = scs_potential_retention(cn)
    Ia = scs_initial_abstraction(S, lambda_coef)

    if rainfall_mm > Ia:
        return ((rainfall_mm - Ia) ** 2) / (rainfall_mm - Ia + S)
    return 0.0
```

#### Ajuste por AMC

**Código:** `scs.py:107-140`

```python
def adjust_cn_for_amc(
    cn_ii: int | float,
    amc: AntecedentMoistureCondition,
) -> float:
    """
    Ajusta CN para condición antecedente de humedad.

    AMC I (seco):
        CN_I = CN_II / (2.281 - 0.01281 × CN_II)

    AMC III (húmedo):
        CN_III = CN_II / (0.427 + 0.00573 × CN_II)

    Clasificación AMC (estación de crecimiento):
        AMC I:   Lluvia 5 días < 35 mm
        AMC II:  Lluvia 5 días = 35-53 mm
        AMC III: Lluvia 5 días > 53 mm
    """
```

**Referencias:**
- USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55. Chapter 2.
- Hawkins, R.H. et al. (2002). Runoff probability, storm depth, and curve numbers. Journal of Irrigation and Drainage Engineering, 128(6), 329-336.

---

## Distribuciones Temporales

### Bloques Alternantes

**Archivo:** `src/hidropluvial/core/temporal/blocks.py`

**Código:** `blocks.py:15-80`

```python
def alternating_blocks(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    idf_func: Callable[[float], float],
) -> HyetographResult:
    """
    Genera hietograma usando método de bloques alternantes.

    Procedimiento:
    1. Dividir duración en intervalos dt
    2. Calcular profundidad acumulada para cada duración
       usando la curva IDF
    3. Calcular profundidad incremental para cada intervalo
    4. Ordenar bloques de mayor a menor
    5. Redistribuir alternando: centro, izquierda, derecha...

    El resultado es un hietograma con el pico en el centro
    y bloques decrecientes hacia ambos extremos.
    """
```

**Referencia:** Chow, V.T., Maidment, D.R., Mays, L.W. (1988). Applied Hydrology. McGraw-Hill. Section 14.4.

---

### Tormenta Chicago

**Archivo:** `src/hidropluvial/core/temporal/chicago.py`

**Código:** `chicago.py:25-95`

```python
def chicago_storm(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    idf_coeffs: ShermanCoefficients,
    return_period_yr: float,
    advancement_coef: float = 0.375,
) -> HyetographResult:
    """
    Genera hietograma usando método Chicago (Keifer & Chu, 1957).

    La tormenta Chicago deriva la distribución temporal directamente
    de la curva IDF, asegurando que cualquier duración parcial
    tiene la intensidad correcta según la IDF.

    Parámetros:
        advancement_coef (r): posición del pico (0-1)
            - r = 0.375: pico al 37.5% (típico)
            - r = 0.5: pico centrado

    Intensidad antes del pico (tb = tiempo al pico):
        i(t) = a × [(1-b)/r × t^(-b) + c]

    Intensidad después del pico:
        i(t) = a × [(1-b)/(1-r) × t^(-b) + c]

    Donde a, b, c son coeficientes Sherman de la IDF:
        i = a / (d + b)^c
    """
```

**Referencia:** Keifer, C.J. & Chu, H.H. (1957). Synthetic Storm Pattern for Drainage Design. ASCE Journal of the Hydraulics Division, 83(HY4), 1-25.

---

### Distribución SCS 24 horas

**Archivo:** `src/hidropluvial/core/temporal/scs.py`

**Código:** `scs.py:15-80`

```python
def scs_distribution(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    storm_type: StormMethod,
) -> HyetographResult:
    """
    Genera hietograma usando distribución SCS 24 horas.

    Tipos de tormenta SCS:
        - Type I:   Costa Pacífico, lluvias frontales suaves
        - Type IA:  Costa Pacífico norte, muy suave
        - Type II:  Interior USA, tormentas convectivas
        - Type III: Golfo de México, tormentas tropicales

    Para Uruguay se recomienda Type II por similitud
    con tormentas convectivas de verano.

    La distribución se lee de tablas normalizadas
    (tiempo vs. fracción acumulada) y se interpola
    al intervalo dt requerido.
    """
```

**Datos:** `src/hidropluvial/data/scs_distributions.json`

**Referencia:** USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55. Chapter 4.

---

### Tormenta Bimodal

**Archivo:** `src/hidropluvial/core/temporal/bimodal.py`

**Código:** `bimodal.py:18-99`

```python
def bimodal_storm(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    peak1_position: float = 0.25,
    peak2_position: float = 0.75,
    volume_split: float = 0.5,
    peak_width_fraction: float = 0.15,
) -> HyetographResult:
    """
    Genera hietograma bimodal (doble pico).

    Parámetros:
        peak1_position: posición del primer pico (0-1), default 0.25
        peak2_position: posición del segundo pico (0-1), default 0.75
        volume_split: fracción del volumen en el primer pico (0-1)
        peak_width_fraction: ancho de cada pico como fracción de duración

    Cada pico se genera usando distribución triangular.
    Los picos se superponen y normalizan para mantener
    el volumen total exacto.

    Aplicaciones:
        - Cuencas urbanas con impermeabilidad mixta
        - Regiones costeras tropicales
        - Tormentas frontales de larga duración
    """
```

**Referencia:** Desarrollo propio basado en observaciones de tormentas en Uruguay.

---

## Hidrogramas Unitarios

### Hidrograma Triangular SCS

**Archivo:** `src/hidropluvial/core/hydrograph/scs.py`

**Código:** `scs.py:25-80`

```python
def scs_triangular_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
) -> HydrographOutput:
    """
    Genera hidrograma unitario triangular SCS.

    Parámetros del hidrograma:
        tp = 0.6 × Tc                    tiempo al pico (hr)
        tb = tp + tr = 2.67 × tp         tiempo base (hr)
        Qp = 0.208 × A / tp              caudal pico (m³/s/mm)

    Donde:
        A: área de la cuenca (km²)
        Tc: tiempo de concentración (hr)
        tr: tiempo de recesión = 1.67 × tp

    El factor 0.208 corresponde a un coeficiente de pico
    Cp = 484 (unidades inglesas), convertido a SI.
    """
```

**Referencia:** USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55. Chapter 5.

---

### Hidrograma Triangular con Factor X

**Archivo:** `src/hidropluvial/core/hydrograph/triangular_x.py`

**Código:** `triangular_x.py:15-85`

```python
def triangular_uh_x(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    x_factor: float = 1.67,
) -> HydrographOutput:
    """
    Genera hidrograma unitario triangular con factor X (Porto, 1995).

    El factor X permite ajustar la forma del hidrograma
    según las características de la cuenca:

        tp = 0.6 × Tc                    tiempo al pico (hr)
        tb = tp × (1 + X)                tiempo base (hr)
        Qp = 2 × V / tb                  caudal pico normalizado

    Valores típicos de X:
        X = 1.00: Cuenca urbana densa (método racional)
        X = 1.25: Cuenca urbana con pendiente
        X = 1.67: NRCS estándar (tb = 2.67×tp)
        X = 2.25: Cuenca mixta rural/urbana
        X = 3.33: Cuenca rural con cauces sinuosos
        X = 5.50: Cuenca rural con baja pendiente
        X = 12.0: Llanuras, pendiente muy baja

    El factor X representa la relación:
        X = tr / tp

    Donde tr es el tiempo de recesión.
    """
```

**Referencia:** Porto, R., Zahed Filho, K., Tucci, C., Bidone, F. (1995). Drenagem Urbana. En: Tucci, C.E.M. (Ed.), Hidrologia: Ciência e Aplicação. ABRH/EDUSP. Cap. 21.

---

### Convolución

**Archivo:** `src/hidropluvial/core/hydrograph/convolution.py`

**Código:** `convolution.py:15-65`

```python
def convolve_uh(
    rainfall_excess: np.ndarray,
    unit_hydrograph: np.ndarray,
    dt_hr: float,
) -> np.ndarray:
    """
    Convolución del exceso de lluvia con el hidrograma unitario.

    El hidrograma de crecida se calcula como:

        Q(t) = Σ P_i × U(t - τ_i)

    Donde:
        Q(t): caudal en tiempo t (m³/s)
        P_i: exceso de lluvia en intervalo i (mm)
        U(t): ordenada del hidrograma unitario (m³/s/mm)
        τ_i: tiempo del intervalo i

    Implementación usando numpy.convolve() con modo 'full'
    para obtener la respuesta completa.
    """
    return np.convolve(rainfall_excess, unit_hydrograph) * dt_hr
```

**Referencia:** Chow, V.T., Maidment, D.R., Mays, L.W. (1988). Applied Hydrology. McGraw-Hill. Section 7.4.

---

## Tablas de Coeficientes

### Coeficiente C - Método Racional

**Archivo:** `src/hidropluvial/core/coefficients/tables_c.py`

#### Tabla FHWA HEC-22

**Código:** `tables_c.py:14-39`

```python
FHWA_C_TABLE = [
    # Zonas desarrolladas
    FHWACEntry("Comercial", "Centro comercial/negocios", 0.85),
    FHWACEntry("Comercial", "Vecindario comercial", 0.60),
    FHWACEntry("Industrial", "Industria liviana", 0.65),
    FHWACEntry("Industrial", "Industria pesada", 0.75),
    # Residencial
    FHWACEntry("Residencial", "Unifamiliar (lotes >1000 m2)", 0.40),
    FHWACEntry("Residencial", "Unifamiliar (lotes 500-1000 m2)", 0.50),
    FHWACEntry("Residencial", "Unifamiliar (lotes <500 m2)", 0.60),
    FHWACEntry("Residencial", "Multifamiliar/Apartamentos", 0.70),
    # Superficies
    FHWACEntry("Superficies", "Asfalto/Concreto", 0.85),
    FHWACEntry("Superficies", "Techos", 0.85),
    FHWACEntry("Superficies", "Grava/Ripio", 0.32),
    # Áreas verdes
    FHWACEntry("Cesped arenoso", "Pendiente plana <2%", 0.08),
    FHWACEntry("Cesped arenoso", "Pendiente media 2-7%", 0.12),
    FHWACEntry("Cesped arcilloso", "Pendiente plana <2%", 0.15),
    FHWACEntry("Cesped arcilloso", "Pendiente media 2-7%", 0.20),
]
```

**Referencia:** FHWA (2001). Urban Drainage Design Manual. Hydraulic Engineering Circular No. 22 (HEC-22). Federal Highway Administration.

#### Tabla Ven Te Chow

**Código:** `tables_c.py:44-69`

```python
# Valores de C para diferentes periodos de retorno
#                                                    Tr2   Tr5   Tr10  Tr25  Tr50  Tr100
VEN_TE_CHOW_C_TABLE = [
    ChowCEntry("Comercial", "Centro comercial denso",    0.75, 0.80, 0.85, 0.88, 0.90, 0.95),
    ChowCEntry("Comercial", "Vecindario comercial",      0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Residencial", "Unifamiliar",             0.25, 0.30, 0.35, 0.40, 0.45, 0.50),
    ChowCEntry("Residencial", "Suburbano",               0.20, 0.25, 0.30, 0.35, 0.40, 0.45),
    ChowCEntry("Industrial", "Liviana",                  0.50, 0.55, 0.60, 0.65, 0.70, 0.80),
    ChowCEntry("Superficies", "Pavimento asfaltico",     0.70, 0.75, 0.80, 0.85, 0.90, 0.95),
    ChowCEntry("Cesped arenoso", "Plano (<2%)",          0.05, 0.08, 0.10, 0.13, 0.15, 0.18),
    ChowCEntry("Cesped arcilloso", "Medio (2-7%)",       0.18, 0.21, 0.25, 0.29, 0.34, 0.37),
]
```

**Referencia:** Chow, V.T. (1964). Handbook of Applied Hydrology. McGraw-Hill. Table 5.5.2.

---

### Curva Número CN - Método SCS

**Archivo:** `src/hidropluvial/core/coefficients/tables_cn.py`

**Código:** `tables_cn.py:11-45`

```python
SCS_CN_TABLE = [
    # ===== ÁREAS URBANAS =====
    # Residencial por tamaño de lote
    CNEntry("Residencial", "Lotes 500 m² (65% impermeable)", "N/A", 77, 85, 90, 92),
    CNEntry("Residencial", "Lotes 1000 m² (38% impermeable)", "N/A", 61, 75, 83, 87),
    CNEntry("Residencial", "Lotes 2000 m² (25% impermeable)", "N/A", 54, 70, 80, 85),
    # Comercial e industrial
    CNEntry("Comercial", "Distritos comerciales (85% imp)", "N/A", 89, 92, 94, 95),
    CNEntry("Industrial", "Distritos industriales (72% imp)", "N/A", 81, 88, 91, 93),
    # Superficies
    CNEntry("Superficies", "Pavimento impermeable", "N/A", 98, 98, 98, 98),
    CNEntry("Superficies", "Grava", "N/A", 76, 85, 89, 91),
    # Espacios abiertos
    CNEntry("Espacios abiertos", "Césped >75% cubierto", "Buena", 39, 61, 74, 80),
    CNEntry("Espacios abiertos", "Césped 50-75% cubierto", "Regular", 49, 69, 79, 84),
    # ===== ÁREAS AGRÍCOLAS =====
    CNEntry("Cultivos", "Hileras rectas", "Buena", 67, 78, 85, 89),
    CNEntry("Cultivos", "Hileras en contorno", "Buena", 65, 75, 82, 86),
    CNEntry("Pasturas", "Continua", "Buena", 39, 61, 74, 80),
    CNEntry("Bosque", "Con mantillo", "Buena", 30, 55, 70, 77),
]
```

**Grupos Hidrológicos:**

| Grupo | Descripción | Tasa Infiltración |
|-------|-------------|-------------------|
| A | Arena profunda, loess, limos agregados | > 7.6 mm/h |
| B | Limo arenoso, franco arenoso | 3.8 - 7.6 mm/h |
| C | Limo arcilloso, franco arcilloso | 1.3 - 3.8 mm/h |
| D | Arcilla, suelos expansivos, nivel freático alto | < 1.3 mm/h |

**Referencia:** USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55. Chapter 2, Tables 2-2a, 2-2b, 2-2c.

---

## Referencias Bibliográficas

### Hidrología General

1. **Chow, V.T., Maidment, D.R., Mays, L.W.** (1988). *Applied Hydrology*. McGraw-Hill, New York. ISBN: 0-07-010810-2.

2. **Chow, V.T.** (1964). *Handbook of Applied Hydrology*. McGraw-Hill, New York.

### Metodología Uruguay

3. **DINAGUA** (2011). *Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas*. Dirección Nacional de Aguas, Uruguay.

4. **Rodríguez Fontal** (1980). *Estudio de Precipitaciones Máximas en Uruguay*. DINAGUA, Montevideo.

### SCS/NRCS

5. **USDA-SCS** (1986). *Urban Hydrology for Small Watersheds*. Technical Release 55 (TR-55). Soil Conservation Service, U.S. Department of Agriculture.

6. **USDA-NRCS** (2004). *National Engineering Handbook, Part 630: Hydrology*. Natural Resources Conservation Service.

7. **Hawkins, R.H., Ward, T.J., Woodward, D.E., Van Mullem, J.A.** (2009). *Curve Number Hydrology: State of the Practice*. ASCE, Reston, VA.

### Tiempo de Concentración

8. **Kirpich, Z.P.** (1940). Time of concentration of small agricultural watersheds. *Civil Engineering*, 10(6), 362.

9. **Témez, J.R.** (1978). *Cálculo hidrometeorológico de caudales máximos en pequeñas cuencas naturales*. MOPU, España.

### Tormentas de Diseño

10. **Keifer, C.J. & Chu, H.H.** (1957). Synthetic Storm Pattern for Drainage Design. *ASCE Journal of the Hydraulics Division*, 83(HY4), 1-25.

### Hidrogramas

11. **Porto, R., Zahed Filho, K., Tucci, C., Bidone, F.** (1995). Drenagem Urbana. En: Tucci, C.E.M. (Ed.), *Hidrologia: Ciência e Aplicação*. ABRH/EDUSP, Porto Alegre.

12. **Snyder, F.F.** (1938). Synthetic unit-graphs. *Transactions of the American Geophysical Union*, 19(1), 447-454.

13. **Clark, C.O.** (1945). Storage and the unit hydrograph. *Transactions of the American Society of Civil Engineers*, 110, 1419-1446.

### FHWA

14. **FHWA** (2001). *Urban Drainage Design Manual*. Hydraulic Engineering Circular No. 22 (HEC-22), Third Edition. Federal Highway Administration, U.S. Department of Transportation. FHWA-NHI-01-021.

### Coeficiente λ

15. **Hawkins, R.H., Jiang, R., Woodward, D.E., Hjelmfelt, A.T., Van Mullem, J.A.** (2002). Runoff Curve Number Method: Examination of the Initial Abstraction Ratio. *Proceedings of the Second Federal Interagency Hydrologic Modeling Conference*, Las Vegas, NV.

---

*Códigos Internos y Referencias - HidroPluvial v2.0*
