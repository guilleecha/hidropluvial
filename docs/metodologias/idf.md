# Curvas Intensidad-Duracion-Frecuencia (IDF)

**Modulo:** `hidropluvial.core.idf`

---

## 1. Introduccion

Las curvas IDF relacionan la intensidad de precipitacion con su duracion y frecuencia de ocurrencia (periodo de retorno). Son fundamentales para el diseno hidrologico de obras de drenaje urbano.

---

## 2. Metodo DINAGUA Uruguay (Principal)

### 2.1 Contexto

El metodo DINAGUA fue desarrollado por Rodriguez Fontal (1980) para Uruguay. Utiliza como valor base la precipitacion maxima para 3 horas y periodo de retorno de 10 anos (P₃,₁₀), obtenida del **mapa de isoyetas de Uruguay**.

### 2.2 Obtencion de P₃,₁₀

El valor de P₃,₁₀ debe obtenerse del **mapa de isoyetas de DINAGUA** para la ubicacion especifica del proyecto. Los valores tipicos en Uruguay varian entre 70-85 mm.

> **Nota:** El codigo incluye valores de referencia por departamento para facilitar estimaciones preliminares, pero para proyectos definitivos siempre debe usarse el mapa de isoyetas oficial.

### 2.3 Metodologia

La metodologia DINAGUA calcula primero la **precipitacion acumulada** P(d,Tr,A) y luego deriva la intensidad:

```
P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)

I = P / d
```

Donde:
- **P₃,₁₀**: Precipitacion maxima 3h, Tr=10 anos (del mapa de isoyetas)
- **Cd(d)**: Factor de correccion por duracion
- **Ct(Tr)**: Factor de correccion por periodo de retorno
- **CA(A,d)**: Factor de correccion por area de cuenca
- **I**: Intensidad derivada (mm/hr)
- **d**: Duracion (hr)

### 2.4 Formulas de los Factores

#### Factor de Correccion por Duracion (Cd)

El factor Cd esta normalizado para que Cd(3h) ≈ 1.0

Para d < 3 horas:
```
Cd(d) = 0.6208 / (d + 0.0137)^0.5639 × d / 3
```

Para d >= 3 horas:
```
Cd(d) = 1.0287 / (d + 1.0293)^0.8083 × d / 3
```

#### Factor de Correccion por Periodo de Retorno (Ct)

Normalizado para que Ct(10) ≈ 1.0

```
Ct(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]
```

Donde:
- `Tr`: Periodo de retorno en anos (>= 2)

#### Factor de Correccion por Area (CA)

Para cuencas pequeñas (A <= 1 km²), CA = 1.0 (sin reduccion).

```
CA(A, d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × A))
```

Donde:
- `A`: Area de la cuenca en km²
- `d`: Duracion de la tormenta en horas

### 2.5 Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py

def dinagua_cd(duration_hr: float) -> float:
    """
    Factor de correccion por duracion (Cd).
    Normalizado para que Cd(3) ≈ 1.0
    """
    if duration_hr <= 0:
        raise ValueError("Duracion debe ser > 0")

    d = duration_hr
    if d < 3.0:
        cd = 0.6208 / ((d + 0.0137) ** 0.5639) * d / 3.0
    else:
        cd = 1.0287 / ((d + 1.0293) ** 0.8083) * d / 3.0

    return cd


def dinagua_ct(return_period_yr: float) -> float:
    """
    Factor de correccion por periodo de retorno (Ct).
    Ct(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]
    """
    if return_period_yr < 2:
        raise ValueError("Periodo de retorno debe ser >= 2 anos")

    Tr = return_period_yr
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))


def dinagua_ca(area_km2: float, duration_hr: float) -> float:
    """
    Factor de correccion por area de cuenca (CA).
    CA(A,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × A))
    """
    if area_km2 <= 1.0:
        return 1.0

    d = max(duration_hr, 0.083)  # Minimo 5 minutos
    ca = 1.0 - (0.3549 * (d ** -0.4272)) * (1.0 - math.exp(-0.005792 * area_km2))

    return min(ca, 1.0)


def dinagua_precipitation(
    p3_10: float,
    return_period_yr: float,
    duration_hr: float,
    area_km2: float | None = None,
) -> UruguayIDFResult:
    """
    Calcula precipitacion acumulada usando metodo DINAGUA Uruguay.

    P(d,Tr,A) = P₃,₁₀ × Cd(d) × Ct(Tr) × CA(A,d)

    Luego la intensidad se deriva como: I = P / d
    """
    # Calcular factores de correccion
    cd = dinagua_cd(duration_hr)
    ct = dinagua_ct(return_period_yr)
    ca = dinagua_ca(area_km2, duration_hr) if area_km2 else 1.0

    # Precipitacion acumulada: P(d,Tr,A) = P₃,₁₀ × Cd × Ct × CA
    depth = p3_10 * cd * ct * ca

    # Intensidad derivada: I = P / d
    intensity = depth / duration_hr

    return UruguayIDFResult(
        depth_mm=round(depth, 2),
        intensity_mmhr=round(intensity, 2),
        cd=round(cd, 4),
        ct=round(ct, 4),
        ca=round(ca, 4),
        p3_10=p3_10,
        return_period_yr=return_period_yr,
        duration_hr=duration_hr,
        area_km2=area_km2,
    )
```

---

## 3. Metodos Internacionales

### 3.1 Ecuacion de Sherman (1931)

#### Formula
```
i = k × T^m / (t + c)^n
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
# Archivo: src/hidropluvial/core/idf.py

def sherman_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: ShermanCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuacion Sherman.
    i = k × T^m / (t + c)^n
    """
    t = np.asarray(duration_min)
    T = return_period_yr

    intensity = coeffs.k * (T ** coeffs.m) / ((t + coeffs.c) ** coeffs.n)
    return float(intensity) if np.isscalar(duration_min) else intensity
```

### 3.2 Ecuacion de Bernard (Power Law)

#### Formula
```
i = a × T^m / t^n
```

Valores tipicos: n: 0.5-0.9, m: 0.15-0.35

#### Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py

def bernard_intensity(
    duration_min: float | NDArray[np.floating],
    return_period_yr: float,
    coeffs: BernardCoefficients,
) -> float | NDArray[np.floating]:
    """
    Calcula intensidad usando ecuacion Bernard (Power Law).
    i = a × T^m / t^n
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
    a(T) = mu + sigma × y_T
    y_T = -ln(-ln(1 - 1/T))  [variable reducida Gumbel]
```

#### Implementacion

```python
# Archivo: src/hidropluvial/core/idf.py

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
from hidropluvial.core.idf import dinagua_precipitation

# P3,10 del mapa de isoyetas (ejemplo: Montevideo)
p3_10 = 78  # mm

# Calcular precipitacion e intensidad para Tr=25 anos, duracion 1 hora
result = dinagua_precipitation(
    p3_10=p3_10,
    return_period_yr=25,
    duration_hr=1.0,
    area_km2=50.0  # Opcional: correccion por area
)

print(f"Precipitacion: {result.depth_mm} mm")
print(f"Intensidad: {result.intensity_mmhr} mm/hr")
print(f"Factor Cd: {result.cd}")
print(f"Factor Ct: {result.ct}")
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
