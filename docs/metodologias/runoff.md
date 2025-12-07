# Escorrentia Superficial

**Modulo:** `hidropluvial.core.runoff`

---

## 1. Introduccion

El modulo implementa dos metodos principales para calcular escorrentia superficial:
- **Metodo Racional**: Para caudales pico en cuencas pequenas
- **Metodo SCS Curve Number (CN)**: Para volumenes de escorrentia

---

## 2. Metodo SCS Curve Number (CN)

### 2.1 Contexto

Desarrollado por el Soil Conservation Service (ahora NRCS) de Estados Unidos. Es el metodo mas utilizado para estimar volumenes de escorrentia.

### 2.2 Formulas Principales

#### Retencion Potencial Maxima (S)
```
S = (25400 / CN) - 254  [mm]
```

Donde:
- `S`: Retencion potencial maxima (mm)
- `CN`: Numero de curva (30-100)

#### Abstraccion Inicial (Ia)
```
Ia = λ × S
```

Donde:
- `Ia`: Abstraccion inicial (mm)
- `λ`: Coeficiente (0.20 tradicional, 0.05 Hawkins 2002)
- `S`: Retencion potencial (mm)

#### Escorrentia Directa (Q)
```
Q = (P - Ia)² / (P - Ia + S)    para P > Ia
Q = 0                            para P ≤ Ia
```

Donde:
- `Q`: Escorrentia directa (mm)
- `P`: Precipitacion total (mm)
- `Ia`: Abstraccion inicial (mm)
- `S`: Retencion potencial (mm)

### 2.3 Implementacion

```python
# Archivo: src/hidropluvial/core/runoff.py (lineas 35-101)

def scs_potential_retention(cn: int | float) -> float:
    """
    Calcula retencion potencial maxima S.

    S = (25400 / CN) - 254  [mm]
    """
    if not 30 <= cn <= 100:
        raise ValueError("CN debe estar entre 30 y 100")

    return (25400 / cn) - 254


def scs_initial_abstraction(s_mm: float, lambda_coef: float = 0.2) -> float:
    """
    Calcula abstraccion inicial Ia.

    Ia = λ × S
    """
    return lambda_coef * s_mm


def scs_runoff(
    rainfall_mm: float | NDArray[np.floating],
    cn: int | float,
    lambda_coef: float = 0.2,
) -> float | NDArray[np.floating]:
    """
    Calcula escorrentia directa usando metodo SCS-CN.

    Q = (P - Ia)² / (P - Ia + S)  para P > Ia
    Q = 0  para P ≤ Ia
    """
    P = np.asarray(rainfall_mm)
    S = scs_potential_retention(cn)
    Ia = scs_initial_abstraction(S, lambda_coef)

    # Calcular escorrentia
    Q = np.where(
        P > Ia,
        ((P - Ia) ** 2) / (P - Ia + S),
        0.0
    )

    if np.isscalar(rainfall_mm):
        return float(Q)
    return Q
```

### 2.4 Ajuste por Condicion Antecedente de Humedad (AMC)

Las formulas para ajustar el CN segun la condicion de humedad del suelo:

#### AMC I (Seco)
```
CN_I = CN_II / (2.281 - 0.01281 × CN_II)
```

#### AMC III (Humedo)
```
CN_III = CN_II / (0.427 + 0.00573 × CN_II)
```

#### Implementacion

```python
# Archivo: src/hidropluvial/core/runoff.py (lineas 104-133)

def adjust_cn_for_amc(
    cn_ii: int | float,
    amc: AntecedentMoistureCondition,
) -> float:
    """
    Ajusta CN para condicion antecedente de humedad.

    CN_I = CN_II / (2.281 - 0.01281 × CN_II)   [AMC II → I (seco)]
    CN_III = CN_II / (0.427 + 0.00573 × CN_II) [AMC II → III (humedo)]
    """
    if not 30 <= cn_ii <= 100:
        raise ValueError("CN debe estar entre 30 y 100")

    if amc == AntecedentMoistureCondition.AVERAGE:
        return float(cn_ii)
    elif amc == AntecedentMoistureCondition.DRY:
        cn_i = cn_ii / (2.281 - 0.01281 * cn_ii)
        return max(30.0, min(100.0, cn_i))
    elif amc == AntecedentMoistureCondition.WET:
        cn_iii = cn_ii / (0.427 + 0.00573 * cn_ii)
        return max(30.0, min(100.0, cn_iii))
```

### 2.5 CN Compuesto

Para cuencas con multiples tipos de cobertura:

```
CN_compuesto = Σ(CNᵢ × Aᵢ) / Σ(Aᵢ)
```

```python
# Archivo: src/hidropluvial/core/runoff.py (lineas 136-160)

def composite_cn(
    areas: list[float],
    cns: list[int | float],
) -> float:
    """
    Calcula CN compuesto para cuenca con multiples coberturas.

    CN_compuesto = Σ(CNᵢ × Aᵢ) / Σ(Aᵢ)
    """
    total_area = sum(areas)
    weighted_sum = sum(a * cn for a, cn in zip(areas, cns))
    return weighted_sum / total_area
```

---

## 3. Metodo Racional

### 3.1 Contexto

Metodo clasico para estimar caudales pico en cuencas pequenas (< 80 ha). Asume que la intensidad de lluvia es uniforme sobre toda la cuenca.

### 3.2 Formula

```
Q = 0.00278 × C × i × A
```

Donde:
- `Q`: Caudal pico (m³/s)
- `C`: Coeficiente de escorrentia (0-1), ya ajustado por periodo de retorno
- `i`: Intensidad de lluvia (mm/hr)
- `A`: Area de la cuenca (hectareas)

### 3.3 Coeficiente C y Periodo de Retorno

El coeficiente C **ya incluye** el ajuste por periodo de retorno. Las tablas de
coeficientes (Ven Te Chow, DINAGUA, HEC-22) proporcionan valores diferentes segun
el Tr seleccionado.

Ejemplo (Tabla Ven Te Chow - Asfalto):

| Periodo de Retorno | C min | C max |
|--------------------|-------|-------|
| 2-10 anos | 0.73 | 0.77 |
| 25 anos | 0.80 | 0.84 |
| 50 anos | 0.82 | 0.87 |
| 100 anos | 0.85 | 0.90 |

Por lo tanto, **no se aplica** un factor Cf adicional en la formula.

### 3.4 Implementacion

```python
# Archivo: src/hidropluvial/core/runoff.py

def rational_peak_flow(
    c: float,
    intensity_mmhr: float,
    area_ha: float,
) -> float:
    """
    Calcula caudal pico usando metodo racional.

    Q = 0.00278 × C × i × A  [Q: m³/s, i: mm/hr, A: ha]

    El coeficiente C debe incluir el ajuste por periodo de retorno.
    Las tablas de C (ej: Ven Te Chow, DINAGUA) proporcionan valores
    diferentes segun el Tr.
    """
    if not 0 < c <= 1:
        raise ValueError("Coeficiente C debe estar entre 0 y 1")
    if intensity_mmhr <= 0:
        raise ValueError("Intensidad debe ser > 0")
    if area_ha <= 0:
        raise ValueError("Area debe ser > 0")

    # Q = 0.00278 × C × i × A
    Q = 0.00278 * c * intensity_mmhr * area_ha

    return Q
```

### 3.5 Coeficientes C Tipicos

Valores de coeficiente de escorrentia segun HEC-22:

| Uso de Suelo | C min | C max |
|--------------|-------|-------|
| Comercial centro | 0.70 | 0.95 |
| Comercial barrio | 0.50 | 0.70 |
| Residencial unifamiliar | 0.30 | 0.50 |
| Residencial multifamiliar | 0.40 | 0.60 |
| Apartamentos | 0.60 | 0.75 |
| Industrial liviano | 0.50 | 0.80 |
| Industrial pesado | 0.60 | 0.90 |
| Parques/cementerios | 0.10 | 0.25 |
| Asfalto | 0.70 | 0.95 |
| Concreto | 0.80 | 0.95 |
| Techos | 0.75 | 0.95 |
| Cesped arenoso plano | 0.05 | 0.10 |
| Cesped arcilloso plano | 0.13 | 0.17 |

### 3.6 C Compuesto

```python
# Archivo: src/hidropluvial/core/runoff.py (lineas 308-332)

def composite_c(
    areas: list[float],
    cs: list[float],
) -> float:
    """
    Calcula coeficiente C compuesto para cuenca con multiples coberturas.

    C_compuesto = Σ(Cᵢ × Aᵢ) / Σ(Aᵢ)
    """
    total_area = sum(areas)
    weighted_sum = sum(a * c for a, c in zip(areas, cs))
    return weighted_sum / total_area
```

---

## 4. Tasa Minima de Infiltracion (fc)

### 4.1 Contexto

Segun la metodologia HHA-FING UdelaR (2019), se debe verificar que la tasa de abstraccion
en cada intervalo de tiempo no sea menor que una tasa minima de infiltracion (fc) que
depende del grupo hidrologico del suelo.

Esta verificacion es importante para tormentas largas donde el metodo SCS-CN puro
podria subestimar la escorrentia al no considerar que el suelo tiene una capacidad
maxima de infiltracion cuando esta saturado.

### 4.2 Valores de fc por Grupo Hidrologico

| Grupo | fc (mm/h) | Descripcion |
|-------|-----------|-------------|
| A | 2.4 | Suelos con alta infiltracion (arena, grava) |
| B | 1.2 | Suelos con moderada infiltracion |
| C | 1.2 | Suelos con baja infiltracion |
| D | 1.2 | Suelos con muy baja infiltracion (arcilla) |

### 4.3 Verificacion

En cada intervalo de tiempo:
1. Se calcula la abstraccion incremental: `Fa_incr = P_incr - Q_incr`
2. Se calcula la tasa de abstraccion: `fa = Fa_incr / dt`
3. Si `fa < fc`, entonces se ajusta la escorrentia para que `fa = fc`

```python
# Archivo: src/hidropluvial/core/runoff.py

MINIMUM_INFILTRATION_RATE = {
    "A": 2.4,   # mm/h
    "B": 1.2,   # mm/h
    "C": 1.2,   # mm/h
    "D": 1.2,   # mm/h
}

def get_minimum_infiltration_rate(soil_group: str) -> float:
    """
    Obtiene la tasa minima de infiltracion para un grupo hidrologico.
    """
    return MINIMUM_INFILTRATION_RATE[soil_group.upper()]
```

---

## 5. Serie Temporal de Exceso de Lluvia

Para hidrogramas, se necesita calcular la precipitacion efectiva en cada intervalo:

```python
# Archivo: src/hidropluvial/core/runoff.py

def rainfall_excess_series(
    cumulative_rainfall_mm: NDArray[np.floating],
    cn: int | float,
    lambda_coef: float = 0.2,
    dt_min: float | None = None,
    soil_group: str | None = None,
) -> NDArray[np.floating]:
    """
    Calcula serie temporal de exceso de lluvia (precipitacion efectiva).

    Para cada paso de tiempo, calcula la escorrentia acumulada y luego
    obtiene el incremento. Si se especifica dt_min y soil_group, verifica
    que la tasa de abstraccion no sea menor que la tasa minima de infiltracion
    del suelo (metodologia HHA-FING UdelaR).

    Args:
        cumulative_rainfall_mm: Precipitacion acumulada (mm)
        cn: Numero de curva
        lambda_coef: Coeficiente λ
        dt_min: Intervalo de tiempo (minutos) - para verificacion fc
        soil_group: Grupo hidrologico (A, B, C, D) - para verificacion fc
    """
    # Escorrentia acumulada para cada valor de precipitacion acumulada
    cumulative_runoff = scs_runoff(cumulative_rainfall_mm, cn, lambda_coef)

    # Exceso incremental
    excess = np.zeros_like(cumulative_runoff)
    excess[0] = cumulative_runoff[0]
    excess[1:] = np.diff(cumulative_runoff)

    # Verificacion de tasa minima de infiltracion si se especifica
    if dt_min is not None and soil_group is not None:
        excess = _apply_minimum_infiltration_check(
            excess, cumulative_rainfall_mm, dt_min, soil_group
        )

    return excess
```

---

## 6. Ejemplos de Uso

### 6.1 Escorrentia SCS-CN

```python
from hidropluvial.core.runoff import calculate_scs_runoff
from hidropluvial.config import AntecedentMoistureCondition

# Precipitacion de 50 mm, CN=75
result = calculate_scs_runoff(
    rainfall_mm=50,
    cn=75,
    lambda_coef=0.2,
    amc=AntecedentMoistureCondition.AVERAGE,
)

print(f"Precipitacion: {result.rainfall_mm} mm")
print(f"Escorrentia: {result.runoff_mm:.2f} mm")
print(f"Abstraccion inicial: {result.initial_abstraction_mm:.2f} mm")
print(f"Retencion: {result.retention_mm:.2f} mm")
```

### 6.2 Caudal Pico (Metodo Racional)

```python
from hidropluvial.core.runoff import rational_peak_flow

# Cuenca de 10 ha, C=0.5, intensidad=60 mm/hr
Q = rational_peak_flow(
    c=0.5,
    intensity_mmhr=60,
    area_ha=10,
    return_period_yr=25,
)

print(f"Caudal pico: {Q:.3f} m³/s")
```

### 6.3 CN Compuesto

```python
from hidropluvial.core.runoff import composite_cn

# Cuenca con tres coberturas
areas = [5.0, 3.0, 2.0]  # hectareas
cns = [85, 70, 60]       # CN por cobertura

cn_total = composite_cn(areas, cns)
print(f"CN compuesto: {cn_total:.1f}")
```

---

### 6.4 Escorrentia con Verificacion fc

```python
from hidropluvial.core.runoff import rainfall_excess_series
import numpy as np

# Precipitacion acumulada de una tormenta (mm)
cumulative_rain = np.array([0, 5, 15, 35, 50, 60, 65, 68])

# Sin verificacion fc (SCS-CN puro)
excess_basic = rainfall_excess_series(cumulative_rain, cn=69, lambda_coef=0.2)

# Con verificacion fc (metodologia UdelaR)
excess_with_fc = rainfall_excess_series(
    cumulative_rain,
    cn=69,
    lambda_coef=0.2,
    dt_min=30,        # intervalo de 30 minutos
    soil_group="B",   # grupo hidrologico B -> fc=1.2 mm/h
)

print(f"Escorrentia total (sin fc): {sum(excess_basic):.2f} mm")
print(f"Escorrentia total (con fc): {sum(excess_with_fc):.2f} mm")
```

---

## 7. Tablas de CN

El modulo incluye tablas de CN segun TR-55 en `data/cn_tables.json`. Para obtener valores:

```python
from hidropluvial.core.runoff import get_cn_from_table
from hidropluvial.config import HydrologicSoilGroup

# Cesped en buen estado, suelo grupo B
cn = get_cn_from_table(
    cover_type="open_space_good",
    soil_group=HydrologicSoilGroup.B,
)
print(f"CN: {cn}")
```

---

## 8. Referencias

- NRCS. (1986). "Urban Hydrology for Small Watersheds". Technical Release 55 (TR-55).
- Chow, V.T., Maidment, D.R., Mays, L.W. (1988). "Applied Hydrology". McGraw-Hill.
- HEC-22. (2013). "Urban Drainage Design Manual". FHWA.
- Hawkins, R.H. et al. (2002). "Curve Number Hydrology: State of the Practice". ASCE.
- HHA-FING UdelaR. (2019). "Hidrologia e Hidraulica Aplicadas". Facultad de Ingenieria, Universidad de la Republica, Uruguay.

---

*Documentacion generada automaticamente desde el codigo fuente.*
