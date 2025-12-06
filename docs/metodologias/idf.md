# Curvas Intensidad-Duracion-Frecuencia (IDF)

**Modulo:** `hidropluvial.core.idf`

---

## 1. Introduccion

Las curvas IDF relacionan la intensidad de precipitacion con su duracion y frecuencia de ocurrencia (periodo de retorno). Son fundamentales para el diseno hidrologico de obras de drenaje urbano.

---

## 2. Metodo DINAGUA Uruguay (Principal)

### 2.1 Contexto

El metodo DINAGUA fue desarrollado por Rodriguez Fontal (1980) para Uruguay. Utiliza como valor base la precipitacion maxima para 3 horas y periodo de retorno de 10 anos (P3,10), disponible por departamento.

### 2.2 Valores P3,10 por Departamento

| Departamento | P3,10 (mm) |
|--------------|------------|
| Montevideo | 78 |
| Canelones | 75 |
| Maldonado | 76 |
| Rivera | 84 |
| Artigas | 83 |
| Tacuarembo | 82 |
| Cerro Largo | 82 |
| Salto | 81 |
| Treinta y Tres | 80 |
| Paysandu | 79 |
| Durazno | 78 |
| Lavalleja | 78 |
| Rocha | 77 |
| Florida | 76 |
| Rio Negro | 76 |
| Flores | 75 |
| Canelones | 75 |
| San Jose | 74 |
| Soriano | 74 |
| Colonia | 73 |

### 2.3 Formulas

#### Factor de Correccion por Periodo de Retorno (CT)

```
CT(Tr) = 0.5786 - 0.4312 * log[ln(Tr / (Tr - 1))]
```

Donde:
- `Tr`: Periodo de retorno en anos (>= 2)

#### Factor de Correccion por Area (CA)

```
CA(Ac, d) = 1.0 - (0.3549 * d^(-0.4272)) * (1.0 - e^(-0.005792 * Ac))
```

Donde:
- `Ac`: Area de la cuenca en km2
- `d`: Duracion de la tormenta en horas

**Nota:** Para Ac <= 1 km2, CA = 1.0

#### Intensidad de Precipitacion

Para duracion d < 3 horas:
```
I(d) = [P3,10 * CT(Tr)] * 0.6208 / (d + 0.0137)^0.5639
```

Para duracion d >= 3 horas:
```
I(d) = [P3,10 * CT(Tr)] * 1.0287 / (d + 1.0293)^0.8083
```

Intensidad final con correccion por area:
```
I_final = I(d) * CA(Ac, d)
```

### 2.4 Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py (lineas 66-176)

def dinagua_ct(return_period_yr: float) -> float:
    """
    Factor de correccion por periodo de retorno (CT).

    CT(Tr) = 0.5786 - 0.4312 * log[ln(Tr / (Tr - 1))]
    """
    if return_period_yr < 2:
        raise ValueError("Periodo de retorno debe ser >= 2 anos")

    Tr = return_period_yr
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))


def dinagua_ca(area_km2: float, duration_hr: float) -> float:
    """
    Factor de correccion por area de cuenca (CA).

    CA(Ac,d) = 1.0 - (0.3549 * d^(-0.4272)) * (1.0 - e^(-0.005792 * Ac))
    """
    if area_km2 <= 1.0:
        return 1.0

    d = max(duration_hr, 0.083)  # Minimo 5 minutos
    ca = 1.0 - (0.3549 * (d ** -0.4272)) * (1.0 - math.exp(-0.005792 * area_km2))

    return min(ca, 1.0)


def dinagua_intensity(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> UruguayIDFResult:
    """
    Calcula intensidad de lluvia usando metodo DINAGUA Uruguay.
    """
    ct = dinagua_ct(return_period_yr)
    ca = dinagua_ca(area_km2, duration_hr) if area_km2 else 1.0

    p_corr = p3_10 * ct

    d = duration_hr
    if d < 3.0:
        intensity = p_corr * 0.6208 / ((d + 0.0137) ** 0.5639)
    else:
        intensity = p_corr * 1.0287 / ((d + 1.0293) ** 0.8083)

    intensity *= ca
    depth = intensity * duration_hr

    return UruguayIDFResult(
        intensity_mmhr=round(intensity, 2),
        depth_mm=round(depth, 2),
        ct=round(ct, 4),
        ca=round(ca, 4),
        # ...
    )
```

---

## 3. Metodos Internacionales

### 3.1 Ecuacion de Sherman (1931)

#### Formula
```
i = k * T^m / (t + c)^n
```

Donde:
- `i`: Intensidad (mm/hr)
- `t`: Duracion (minutos)
- `T`: Periodo de retorno (anos)
- `k, m, c, n`: Coeficientes regionales

#### Rangos Tipicos
- `c`: 0-30 min
- `n`: 0.5-1.0
- `m`: 0.1-0.5

#### Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py (lineas 294-316)

def sherman_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: ShermanCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuacion Sherman.

    i = k * T^m / (t + c)^n
    """
    t = np.asarray(duration_min)
    T = return_period_yr

    intensity = coeffs.k * (T ** coeffs.m) / ((t + coeffs.c) ** coeffs.n)
    return float(intensity) if np.isscalar(duration_min) else intensity
```

### 3.2 Ecuacion de Bernard (Power Law)

#### Formula
```
i = a * T^m / t^n
```

Valores tipicos: n: 0.5-0.9, m: 0.15-0.35

#### Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py (lineas 319-344)

def bernard_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: BernardCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuacion Bernard (Power Law).

    i = a * T^m / t^n
    """
    t = np.asarray(duration_min)
    T = return_period_yr

    t = np.maximum(t, 0.1)  # Evitar division por cero

    intensity = coeffs.a * (T ** coeffs.m) / (t ** coeffs.n)
    return float(intensity) if np.isscalar(duration_min) else intensity
```

### 3.3 Metodo Koutsoyiannis (1998)

Formulacion teoricamente rigurosa basada en distribucion Gumbel.

#### Formula
```
I(T,d) = a(T) / (d + theta)^eta

donde:
    a(T) = mu + sigma * y_T
    y_T = -ln(-ln(1 - 1/T))  [variable reducida Gumbel]
```

#### Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py (lineas 347-383)

def koutsoyiannis_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: KoutsoyiannisCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando metodo Koutsoyiannis (1998).
    """
    d = np.asarray(duration_min)
    T = return_period_yr

    if T <= 1:
        raise ValueError("Periodo de retorno debe ser > 1 ano")

    # Variable reducida Gumbel
    y_T = -np.log(-np.log(1 - 1 / T))
    a_T = coeffs.mu + coeffs.sigma * y_T

    intensity = a_T / ((d + coeffs.theta) ** coeffs.eta)
    return float(intensity) if np.isscalar(duration_min) else intensity
```

---

## 4. Ejemplo de Uso

```python
from hidropluvial.core.idf import dinagua_intensity, get_p3_10

# Obtener P3,10 para Montevideo
p3_10 = get_p3_10("montevideo")  # 78 mm

# Calcular intensidad para Tr=25 anos, duracion 1 hora
result = dinagua_intensity(
    p3_10=p3_10,
    return_period_yr=25,
    duration_hr=1.0,
    area_km2=50.0  # Opcional: correccion por area
)

print(f"Intensidad: {result.intensity_mmhr} mm/hr")
print(f"Precipitacion: {result.depth_mm} mm")
print(f"Factor CT: {result.ct}")
print(f"Factor CA: {result.ca}")
```

---

## 5. Referencias

- DINAGUA. "Curvas Intensidad-Duracion-Frecuencia para Uruguay". Ministerio de Vivienda, Ordenamiento Territorial y Medio Ambiente.
- Rodriguez Fontal (1980). Metodo para curvas IDF en Uruguay.
- Sherman, C.W. (1931). "Frequency and intensity of excessive rainfalls at Boston, Massachusetts". Transactions ASCE.
- Koutsoyiannis, D. et al. (1998). "A mathematical framework for studying rainfall intensity-duration-frequency relationships". Journal of Hydrology.

---

*Documentacion generada automaticamente desde el codigo fuente.*
