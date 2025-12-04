### 2.2 Uruguay/DINAGUA IDF Method

Este método es el estándar utilizado en Uruguay para el cálculo de intensidades de lluvia de diseño. Está basado en el trabajo de Rodríguez Fontal (1980) y actualizaciones posteriores de DINAGUA/MTOP.

#### 2.2.1 Ecuación General

La intensidad de lluvia corregida se calcula como:

```
I(Tr,d,Ac) = P₃,₁₀ × CT(Tr) × CA(Ac,d) × CD(d)
```

Donde:
- `I` = intensidad de lluvia (mm/hr)
- `P₃,₁₀` = precipitación máxima de 3 horas para período de retorno de 10 años (mm)
- `CT(Tr)` = factor de corrección por período de retorno
- `CA(Ac,d)` = factor de corrección por área de cuenca
- `CD(d)` = factor de corrección por duración (implícito en las ecuaciones de intensidad)

#### 2.2.2 Factor CT - Corrección por Período de Retorno

```
CT(Tr) = 0.5786 - 0.4312 × log[ln(Tr / (Tr - 1))]
```

Donde:
- `Tr` = período de retorno (años), Tr ≥ 2

**Valores tabulados de CT:**

| Tr (años) | CT |
|-----------|------|
| 2 | 0.870 |
| 5 | 0.955 |
| 10 | 1.000 |
| 20 | 1.039 |
| 25 | 1.052 |
| 50 | 1.087 |
| 100 | 1.120 |

**Implementación Python:**
```python
import math

def calculate_CT(Tr: float) -> float:
    """
    Factor de corrección por período de retorno.
    
    Args:
        Tr: Período de retorno en años (Tr >= 2)
    
    Returns:
        Factor CT (adimensional)
    """
    if Tr < 2:
        raise ValueError("Período de retorno debe ser >= 2 años")
    
    return 0.5786 - 0.4312 * math.log10(math.log(Tr / (Tr - 1)))
```

#### 2.2.3 Factor CD - Corrección por Duración (Ecuaciones de Intensidad)

**Para duraciones d < 3 horas:**
```
I(d) = [P₃,₁₀ × CT(Tr)] × 0.6208 / (d + 0.0137)^0.5639
```

**Para duraciones d ≥ 3 horas:**
```
I(d) = [P₃,₁₀ × CT(Tr)] × 1.0287 / (d + 1.0293)^0.8083
```

Donde:
- `d` = duración de la tormenta (horas)
- `I` = intensidad (mm/hr)

**Implementación Python:**
```python
def calculate_intensity(P3_10: float, Tr: float, d: float) -> float:
    """
    Calcula intensidad de lluvia según método DINAGUA.
    
    Args:
        P3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        Tr: Período de retorno (años)
        d: Duración de la tormenta (horas)
    
    Returns:
        Intensidad de lluvia (mm/hr)
    """
    CT = calculate_CT(Tr)
    P_corr = P3_10 * CT
    
    if d < 3.0:
        I = P_corr * 0.6208 / ((d + 0.0137) ** 0.5639)
    else:
        I = P_corr * 1.0287 / ((d + 1.0293) ** 0.8083)
    
    return I
```

#### 2.2.4 Factor CA - Corrección por Área de Cuenca

Para cuencas con área significativa (Ac > 1 km²), se aplica una reducción por efecto de área:

```
CA(Ac,d) = 1.0 - (0.3549 × d^(-0.4272)) × (1.0 - e^(-0.005792 × Ac))
```

Donde:
- `Ac` = área de la cuenca (km²)
- `d` = duración de la tormenta (horas)
- `e` = base del logaritmo natural (2.71828...)

**Notas:**
- Para Ac ≤ 1 km², usar CA = 1.0 (sin reducción)
- Para Ac > 300 km², consultar estudios regionales específicos
- El factor CA siempre es ≤ 1.0

**Valores típicos de CA:**

| Área (km²) | d=1hr | d=3hr | d=6hr | d=12hr | d=24hr |
|------------|-------|-------|-------|--------|--------|
| 1 | 0.998 | 0.999 | 0.999 | 1.000 | 1.000 |
| 10 | 0.980 | 0.988 | 0.992 | 0.995 | 0.997 |
| 25 | 0.954 | 0.972 | 0.981 | 0.988 | 0.993 |
| 50 | 0.920 | 0.951 | 0.967 | 0.979 | 0.987 |
| 100 | 0.871 | 0.919 | 0.945 | 0.964 | 0.978 |
| 200 | 0.808 | 0.876 | 0.915 | 0.944 | 0.965 |

**Implementación Python:**
```python
import math

def calculate_CA(Ac: float, d: float) -> float:
    """
    Factor de corrección por área de cuenca.
    
    Args:
        Ac: Área de la cuenca (km²)
        d: Duración de la tormenta (horas)
    
    Returns:
        Factor CA (adimensional, <= 1.0)
    """
    if Ac <= 1.0:
        return 1.0
    
    if Ac > 300:
        import warnings
        warnings.warn("Área > 300 km²: verificar con estudios regionales")
    
    CA = 1.0 - (0.3549 * (d ** -0.4272)) * (1.0 - math.exp(-0.005792 * Ac))
    
    return min(CA, 1.0)  # Asegurar que CA <= 1.0
```

#### 2.2.5 Función Completa de Cálculo

```python
def calculate_intensity_idf(
    P3_10: float,
    Tr: float,
    d: float,
    Ac: float = None
) -> dict:
    """
    Calcula intensidad de lluvia usando método DINAGUA Uruguay.
    
    Args:
        P3_10: Precipitación máxima 3hr, Tr=10 años (mm)
        Tr: Período de retorno (años)
        d: Duración de la tormenta (horas)
        Ac: Área de cuenca (km²), opcional
    
    Returns:
        Diccionario con resultados y factores intermedios
    """
    # Validaciones
    if P3_10 < 50 or P3_10 > 120:
        import warnings
        warnings.warn(f"P3_10={P3_10}mm fuera del rango típico Uruguay (50-120mm)")
    
    if d <= 0:
        raise ValueError("Duración debe ser > 0")
    
    # Cálculo de factores
    CT = calculate_CT(Tr)
    CA = calculate_CA(Ac, d) if Ac else 1.0
    
    # Intensidad base (sin corrección por área)
    P_corr = P3_10 * CT
    
    if d < 3.0:
        I_base = P_corr * 0.6208 / ((d + 0.0137) ** 0.5639)
    else:
        I_base = P_corr * 1.0287 / ((d + 1.0293) ** 0.8083)
    
    # Intensidad final con corrección por área
    I_final = I_base * CA
    
    # Precipitación total
    P_total = I_final * d
    
    return {
        'I_mmh': round(I_final, 2),
        'P_mm': round(P_total, 2),
        'CT': round(CT, 4),
        'CA': round(CA, 4),
        'P3_10': P3_10,
        'Tr': Tr,
        'd_hours': d,
        'Ac_km2': Ac
    }
```

#### 2.2.6 Valores de P₃,₁₀ para Uruguay

Valores de referencia de precipitación máxima de 3 horas con período de retorno de 10 años (mm):

| Departamento/Ciudad | P₃,₁₀ (mm) | Fuente |
|---------------------|------------|--------|
| Montevideo | 75-78 | IM / Silveira et al. 2014 |
| Maldonado | 76 | DINAGUA |
| Canelones | 74-76 | DINAGUA |
| Colonia | 72-74 | DINAGUA |
| Paysandú | 78-80 | DINAGUA |
| Salto | 80-82 | DINAGUA |
| Rivera | 82-85 | DINAGUA |

**Nota sobre cambio climático:** Se recomienda mayorar el valor de P₃,₁₀ entre 5% y 10% para contemplar efectos del cambio climático en proyectos de infraestructura crítica.

**Ejemplo Maldonado:**
```
P₃,₁₀ base = 76 mm
P₃,₁₀ mayorado (≈9%) = 83 mm
```

#### 2.2.7 Ejemplo de Cálculo Completo

**Datos de entrada:**
- Ubicación: Maldonado
- P₃,₁₀ = 83 mm (mayorado por cambio climático)
- Tr = 100 años
- Duración = 6 horas
- Área de cuenca = 25 km²

**Cálculo paso a paso:**

1. **Factor CT:**
   ```
   CT(100) = 0.5786 - 0.4312 × log[ln(100/99)]
   CT(100) = 0.5786 - 0.4312 × log[0.01005]
   CT(100) = 0.5786 - 0.4312 × (-1.9978)
   CT(100) = 1.120
   ```

2. **Factor CA:**
   ```
   CA(25, 6) = 1.0 - (0.3549 × 6^(-0.4272)) × (1.0 - e^(-0.005792 × 25))
   CA(25, 6) = 1.0 - (0.3549 × 0.4467) × (1.0 - 0.8652)
   CA(25, 6) = 1.0 - (0.1585) × (0.1348)
   CA(25, 6) = 0.979
   ```

3. **Intensidad (d ≥ 3 horas):**
   ```
   I = [83 × 1.120] × 1.0287 / (6 + 1.0293)^0.8083 × 0.979
   I = 92.96 × 1.0287 / (7.0293)^0.8083 × 0.979
   I = 95.63 / 5.214 × 0.979
   I = 17.95 mm/hr
   ```

4. **Precipitación total:**
   ```
   P = 17.95 × 6 = 107.7 mm
   ```

**Resultado:**
```python
{
    'I_mmh': 17.95,
    'P_mm': 107.7,
    'CT': 1.120,
    'CA': 0.979,
    'P3_10': 83,
    'Tr': 100,
    'd_hours': 6,
    'Ac_km2': 25
}
```

#### 2.2.8 Rangos de Validez

| Parámetro | Rango Válido | Notas |
|-----------|--------------|-------|
| Tr | 2 - 500 años | Usar con precaución para Tr > 100 |
| d | 0.083 - 48 horas | 5 min a 2 días |
| Ac | 0 - 300 km² | Para áreas mayores, usar métodos regionales |
| P₃,₁₀ | 50 - 120 mm | Rango típico para Uruguay |

#### 2.2.9 Referencias

1. **Rodríguez Fontal, A. (1980).** Curvas Intensidad-Duración-Frecuencia para Uruguay. DINAGUA/MTOP.

2. **Silveira, L., Charbonnier, F., & Usera, G. (2014).** "Nuevas curvas intensidad-duración-frecuencia de precipitación para el departamento de Montevideo, Uruguay." *Ingeniería del Agua*, 18(1), 71-84.

3. **DINAGUA (2011).** Manual de Diseño de Sistemas de Drenaje de Aguas Pluviales Urbanas. Dirección Nacional de Aguas, Uruguay.

4. **Intendencia de Montevideo (2020).** Actualización de curvas IDF para el departamento de Montevideo.
