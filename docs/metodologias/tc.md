# Tiempo de Concentracion (Tc)

**Modulo:** `hidropluvial.core.tc`

---

## 1. Introduccion

El tiempo de concentracion (Tc) es el tiempo que tarda el agua en llegar desde el punto mas alejado de la cuenca hasta el punto de salida. Es un parametro fundamental para el calculo de caudales maximos.

---

## 2. Metodo de Kirpich (1940)

### 2.1 Contexto

Desarrollado por Kirpich para pequenas cuencas agricolas en Tennessee, USA. Es uno de los metodos mas utilizados por su simplicidad.

### 2.2 Formula

```
tc = 0.0195 × L^0.77 × S^(-0.385)
```

Donde:
- `tc`: Tiempo de concentracion (minutos)
- `L`: Longitud del cauce principal (metros)
- `S`: Pendiente media del cauce (m/m)

### 2.3 Factores de Ajuste por Superficie

| Superficie | Factor |
|------------|--------|
| Natural | 1.0 |
| Con pasto (grassy) | 2.0 |
| Concreto/asfalto | 0.4 |
| Canal de concreto | 0.2 |

### 2.4 Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 43-84)

def kirpich(
    length_m: float,
    slope: float,
    surface_type: str = "natural",
) -> float:
    """
    Calcula Tc usando formula Kirpich (1940).

    tc = 0.0195 × L^0.77 × S^(-0.385)  [tc: min, L: m, S: m/m]
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")

    # Factores de ajuste
    adjustment_factors = {
        "natural": 1.0,
        "grassy": 2.0,
        "concrete": 0.4,
        "concrete_channel": 0.2,
    }

    factor = adjustment_factors.get(surface_type, 1.0)

    # Formula Kirpich (resultado en minutos)
    tc_min = 0.0195 * (length_m ** 0.77) * (slope ** -0.385)
    tc_min *= factor

    return tc_min / 60.0  # Convertir a horas
```

---

## 3. Metodo Temez

### 3.1 Contexto

Formula desarrollada para cuencas en Espana y ampliamente usada en Latinoamerica. Valido para cuencas de 1 a 3000 km².

### 3.2 Formula

```
tc = 0.3 × (L / S^0.25)^0.76
```

Donde:
- `tc`: Tiempo de concentracion (horas)
- `L`: Longitud del cauce principal (km)
- `S`: Pendiente media (m/m)

### 3.3 Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 227-248)

def temez(length_km: float, slope: float) -> float:
    """
    Calcula Tc usando formula Temez (Espana/Latinoamerica).

    tc = 0.3 × (L / S^0.25)^0.76  [tc: hr, L: km, S: m/m]

    Valido para cuencas de 1-3000 km².
    """
    if length_km <= 0:
        raise ValueError("Longitud debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")

    tc_hr = 0.3 * ((length_km / (slope ** 0.25)) ** 0.76)
    return tc_hr
```

---

## 4. Metodo de los Desbordes (DINAGUA Uruguay)

### 4.1 Contexto

Metodo recomendado por DINAGUA para cuencas urbanas en Uruguay. Especialmente util para drenaje pluvial urbano.

### 4.2 Formula

```
Tc = T0 + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)
```

Donde:
- `Tc`: Tiempo de concentracion (minutos)
- `T0`: Tiempo de entrada inicial (tipicamente 5 min)
- `A`: Area de la cuenca (hectareas)
- `P`: Pendiente media de la cuenca (%)
- `C`: Coeficiente de escorrentia (0-1)

### 4.3 Valores Tipicos

- `T0`: 5 minutos para areas residenciales
- `C`: 0.3-0.5 para zonas residenciales, 0.7-0.9 para zonas comerciales/industriales

### 4.4 Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 304-338)

def desbordes(
    area_ha: float,
    slope_pct: float,
    c: float,
    t0_min: float = 5.0,
) -> float:
    """
    Calcula Tc usando Metodo de los Desbordes (DINAGUA Uruguay).

    Tc = T0 + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)  [Tc: min]

    Recomendado en el "Manual de Diseno para Sistemas de Drenaje de
    Aguas Pluviales Urbanas" de DINAGUA.
    """
    if area_ha <= 0:
        raise ValueError("Area debe ser > 0")
    if slope_pct <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")
    if t0_min < 0:
        raise ValueError("Tiempo de entrada T0 debe ser >= 0")

    tc_min = t0_min + 6.625 * (area_ha ** 0.3) * (slope_pct ** -0.39) * (c ** -0.45)
    return tc_min / 60.0  # Convertir a horas
```

---

## 5. Metodo NRCS (TR-55)

### 5.1 Contexto

El metodo NRCS (antes SCS) divide el trayecto del agua en tres tipos de flujo:
1. Flujo laminar (sheet flow)
2. Flujo concentrado superficial (shallow flow)
3. Flujo en canal

### 5.2 Flujo Laminar (Sheet Flow)

#### Formula
```
Tt = 0.007 × (n × L)^0.8 / (P2^0.5 × S^0.4)
```

Donde:
- `Tt`: Tiempo de viaje (horas)
- `n`: Coeficiente de rugosidad
- `L`: Longitud del flujo (ft) - maximo ~100m
- `P2`: Precipitacion de 2 anos, 24 horas (pulgadas)
- `S`: Pendiente (m/m)

#### Coeficientes de Manning para Flujo Laminar

| Superficie | n |
|------------|---|
| Lisa (smooth) | 0.011 |
| Barbecho (fallow) | 0.05 |
| Pasto corto | 0.15 |
| Pasto denso | 0.24 |
| Bosque ligero | 0.40 |
| Bosque denso | 0.80 |

#### Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 87-124)

def nrcs_sheet_flow(
    length_m: float,
    n: float,
    slope: float,
    p2_mm: float,
) -> float:
    """
    Calcula tiempo de viaje para flujo laminar (sheet flow).

    Tt = 0.091 × (n × L)^0.8 / (P2^0.5 × S^0.4)  [Tt: hr, L: m, P2: mm]
    """
    if length_m <= 0 or length_m > 100:
        raise ValueError("Longitud de flujo laminar debe ser 0-100 m")

    # Convertir P2 de mm a pulgadas para la formula original
    p2_in = p2_mm / 25.4
    # Convertir longitud de m a ft
    length_ft = length_m * 3.28084

    # Formula TR-55 (resultado en horas)
    tt_hr = 0.007 * ((n * length_ft) ** 0.8) / ((p2_in ** 0.5) * (slope ** 0.4))

    return tt_hr
```

### 5.3 Flujo Concentrado Superficial (Shallow Flow)

#### Formula
```
V = k × S^0.5
Tt = L / (V × 3600)
```

Donde:
- `V`: Velocidad (m/s)
- `k`: Coeficiente segun superficie
- `S`: Pendiente (m/m)
- `L`: Longitud (m)
- `Tt`: Tiempo de viaje (horas)

#### Coeficientes k por Superficie

| Superficie | k (m/s) |
|------------|---------|
| Pavimentada | 6.196 |
| Sin pavimentar | 4.918 |
| Con pasto | 4.572 |
| Pasto corto | 2.134 |

#### Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 127-155)

SHALLOW_FLOW_K = {
    "paved": 6.196,      # k = 20.3 ft/s convertido a m/s
    "unpaved": 4.918,    # k = 16.1 ft/s
    "grassed": 4.572,    # k = 15.0 ft/s
    "short_grass": 2.134,  # k = 7.0 ft/s
}

def nrcs_shallow_flow(
    length_m: float,
    slope: float,
    surface: str = "unpaved",
) -> float:
    """
    Calcula tiempo de viaje para flujo concentrado superficial.

    V = k × S^0.5  [V: m/s, S: m/m]
    Tt = L / (V × 3600)  [Tt: hr]
    """
    k = SHALLOW_FLOW_K.get(surface, SHALLOW_FLOW_K["unpaved"])
    velocity = k * (slope ** 0.5)  # m/s

    tt_hr = length_m / (velocity * 3600)
    return tt_hr
```

### 5.4 Flujo en Canal

#### Formula (Manning)
```
V = (1/n) × R^(2/3) × S^(1/2)
Tt = L / (V × 3600)
```

Donde:
- `V`: Velocidad (m/s)
- `n`: Coeficiente de Manning
- `R`: Radio hidraulico (m)
- `S`: Pendiente (m/m)

#### Implementacion

```python
# Archivo: src/hidropluvial/core/tc.py (lineas 158-191)

def nrcs_channel_flow(
    length_m: float,
    n: float,
    slope: float,
    hydraulic_radius_m: float,
) -> float:
    """
    Calcula tiempo de viaje para flujo en canal usando Manning.

    V = (1/n) × R^(2/3) × S^(1/2)  [V: m/s, R: m, S: m/m]
    Tt = L / (V × 3600)  [Tt: hr]
    """
    velocity = (1 / n) * (hydraulic_radius_m ** (2/3)) * (slope ** 0.5)
    tt_hr = length_m / (velocity * 3600)

    return tt_hr
```

---

## 6. Otros Metodos

### 6.1 California Culverts Practice

```
tc = 60 × (11.9 × L³ / H)^0.385
```

Donde:
- `tc`: Tiempo de concentracion (minutos)
- `L`: Longitud del cauce (millas)
- `H`: Diferencia de elevacion (pies)

### 6.2 Formula FAA

```
tc = 1.8 × (1.1 - C) × L^0.5 / S^0.333
```

Donde:
- `tc`: Tiempo de concentracion (minutos)
- `C`: Coeficiente de escorrentia
- `L`: Longitud (pies)
- `S`: Pendiente (%)

### 6.3 Onda Cinematica (Kinematic Wave)

```
tc = 6.99 × (n × L)^0.6 / (i^0.4 × S^0.3)
```

Donde:
- `tc`: Tiempo de concentracion (minutos)
- `n`: Coeficiente de Manning
- `L`: Longitud (m)
- `i`: Intensidad de lluvia (mm/hr)
- `S`: Pendiente (m/m)

---

## 7. Ejemplos de Uso

### 7.1 Kirpich

```python
from hidropluvial.core.tc import kirpich

# Cuenca natural, L=1000m, S=2%
tc = kirpich(length_m=1000, slope=0.02, surface_type="natural")
print(f"Tc = {tc:.2f} horas ({tc*60:.1f} minutos)")
```

### 7.2 Temez

```python
from hidropluvial.core.tc import temez

# Cuenca de 2.5 km de longitud, S=2.23%
tc = temez(length_km=2.5, slope=0.0223)
print(f"Tc = {tc:.2f} horas")
```

### 7.3 Desbordes (DINAGUA)

```python
from hidropluvial.core.tc import desbordes

# Cuenca urbana: 10 ha, pendiente 2%, C=0.5
tc = desbordes(area_ha=10, slope_pct=2.0, c=0.5, t0_min=5.0)
print(f"Tc = {tc:.2f} horas ({tc*60:.1f} minutos)")
```

### 7.4 Funcion General

```python
from hidropluvial.core.tc import calculate_tc

# Usando Kirpich
tc = calculate_tc(method="kirpich", length_m=1000, slope=0.02)

# Usando Temez
tc = calculate_tc(method="temez", length_km=2.5, slope=0.02)

# Usando Desbordes
tc = calculate_tc(method="desbordes", area_ha=10, slope_pct=2.0, c=0.5)
```

---

## 8. Seleccion del Metodo

| Metodo | Aplicacion | Tamano de Cuenca |
|--------|------------|------------------|
| Kirpich | Cuencas rurales, canales naturales | < 80 ha |
| Temez | Cuencas naturales espanolas/latinoamericanas | 1-3000 km² |
| Desbordes | Cuencas urbanas Uruguay (DINAGUA) | < 500 ha |
| NRCS | Cuencas mixtas con segmentos diferenciados | Variable |
| FAA | Cuencas urbanas pequenas | < 40 ha |
| California | Cuencas de montana | Variable |

---

## 9. Referencias

- Kirpich, Z.P. (1940). "Time of concentration of small agricultural watersheds". Civil Engineering, Vol. 10, No. 6.
- NRCS. (1986). "Urban Hydrology for Small Watersheds". Technical Release 55 (TR-55).
- Temez, J.R. (1978). "Calculo hidrometeorologico de caudales maximos en pequenas cuencas naturales". MOPU, Espana.
- DINAGUA. "Manual de Diseno para Sistemas de Drenaje de Aguas Pluviales Urbanas". MVOTMA, Uruguay.

---

*Documentacion generada automaticamente desde el codigo fuente.*
