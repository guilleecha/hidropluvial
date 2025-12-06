# Hidrogramas Unitarios Sinteticos

**Modulo:** `hidropluvial.core.hydrograph`

---

## 1. Introduccion

El modulo implementa varios metodos para generar hidrogramas unitarios sinteticos:
- SCS Triangular
- SCS Curvilinear (Adimensional)
- Triangular con Factor X (GZ/Porto)
- Snyder (1938)
- Clark
- Ecuacion Gamma

---

## 2. Parametros Temporales SCS

### 2.1 Tiempo de Retardo (Lag Time)

```
tlag = 0.6 × Tc
```

Donde:
- `tlag`: Tiempo de retardo (horas)
- `Tc`: Tiempo de concentracion (horas)

### 2.2 Tiempo al Pico

```
Tp = ΔD/2 + tlag = ΔD/2 + 0.6 × Tc
```

Donde:
- `Tp`: Tiempo al pico (horas)
- `ΔD`: Duracion del intervalo de exceso de lluvia (horas)

### 2.3 Tiempo Base

```
Tb = 2.67 × Tp
```

### 2.4 Intervalo Recomendado

```
ΔD ≤ 0.25 × Tp
```

Recomendacion practica: `ΔD = 0.133 × Tc`

### 2.5 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 34-93)

def scs_lag_time(tc_hr: float) -> float:
    """
    Calcula tiempo de retardo SCS.
    tlag = 0.6 × Tc
    """
    return 0.6 * tc_hr


def scs_time_to_peak(tc_hr: float, dt_hr: float) -> float:
    """
    Calcula tiempo al pico SCS.
    Tp = ΔD/2 + tlag = ΔD/2 + 0.6×Tc
    """
    tlag = scs_lag_time(tc_hr)
    return dt_hr / 2 + tlag


def scs_time_base(tp_hr: float) -> float:
    """
    Calcula tiempo base del hidrograma triangular SCS.
    Tb = 2.67 × Tp
    """
    return 2.67 * tp_hr


def recommended_dt(tc_hr: float) -> float:
    """
    Calcula intervalo de tiempo recomendado.
    ΔD ≤ 0.25 × Tp (recomendado: ΔD = 0.133 × Tc)
    """
    return 0.133 * tc_hr
```

---

## 3. Hidrograma Triangular SCS

### 3.1 Formula del Caudal Pico

```
qp = 2.08 × A × Q / Tp
```

Donde:
- `qp`: Caudal pico (m³/s)
- `A`: Area de la cuenca (km²)
- `Q`: Escorrentia directa (mm)
- `Tp`: Tiempo al pico (horas)

### 3.2 Forma del Hidrograma

El hidrograma tiene forma triangular con:
- Rama ascendente: lineal de 0 a Tp
- Rama descendente: lineal de Tp a Tb
- Tiempo de recesion: `Tr = 1.67 × Tp`

### 3.3 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 100-167)

def scs_triangular_peak(
    area_km2: float,
    runoff_mm: float,
    tp_hr: float,
) -> float:
    """
    Calcula caudal pico del hidrograma triangular SCS.

    qp = 2.08 × A × Q / Tp  [qp: m³/s, A: km², Q: mm, Tp: hr]
    """
    if area_km2 <= 0:
        raise ValueError("Area debe ser > 0")
    if runoff_mm < 0:
        raise ValueError("Escorrentia no puede ser negativa")
    if tp_hr <= 0:
        raise ValueError("Tiempo al pico debe ser > 0")

    return 2.08 * area_km2 * runoff_mm / tp_hr


def scs_triangular_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario triangular SCS (1 mm de escorrentia).
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)
    tb = scs_time_base(tp)
    tr = 1.67 * tp  # tiempo de recesion

    # Caudal pico para 1 mm de escorrentia
    qp = scs_triangular_peak(area_km2, 1.0, tp)

    # Generar tiempos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Generar ordenadas del triangulo
    flow = np.zeros_like(time)
    for i, t in enumerate(time):
        if t <= tp:
            # Rama ascendente
            flow[i] = qp * t / tp
        else:
            # Rama descendente
            flow[i] = qp * (tb - t) / tr

    flow = np.maximum(flow, 0)
    return time, flow
```

---

## 4. Hidrograma Triangular con Factor X

### 4.1 Contexto

Metodo adaptado de Porto, permite ajustar la forma del hidrograma mediante un factor morfologico X.

### 4.2 Formulas

```
Tp = 0.5 × Du + 0.6 × Tc
qp = 0.278 × A / Tp × 2 / (1 + X)
Tb = (1 + X) × Tp
```

Donde:
- `Tp`: Tiempo al pico (horas)
- `Du`: Duracion del intervalo (horas)
- `qp`: Caudal pico (m³/s por mm)
- `A`: Area (km²)
- `X`: Factor morfologico
- `Tb`: Tiempo base (horas)

### 4.3 Valores Tipicos de X

| Factor X | Aplicacion |
|----------|------------|
| 1.00 | Metodo racional / areas urbanas internas |
| 1.25 | Areas urbanas (gran pendiente) |
| 1.67 | Metodo NRCS (SCS estandar) |
| 2.25 | Uso mixto (rural/urbano) |
| 3.33 | Area rural sinuosa |
| 5.50 | Area rural (pendiente baja) |

### 4.4 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 174-246)

def triangular_uh_x(
    area_ha: float,
    tc_hr: float,
    dt_hr: float,
    x_factor: float = 1.0,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario triangular con factor X ajustable.

    Formulas (adaptadas de Porto):
        Tp = 0.5 × Du + 0.6 × Tc
        qp = 0.278 × A / Tp × 2 / (1 + X)   [A: ha, Tp: hr, qp: m³/s]
        Tb = (1 + X) × Tp
    """
    # Tiempo al pico
    tp = 0.5 * dt_hr + 0.6 * tc_hr

    # Caudal pico para 1 mm de escorrentia
    area_km2 = area_ha / 100
    qp = 0.278 * area_km2 / tp * 2 / (1 + x_factor)

    # Tiempo base
    tb = (1 + x_factor) * tp

    # Tiempo de recesion
    tr = tb - tp  # = X × Tp

    # Generar tiempos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Generar ordenadas del triangulo
    flow = np.zeros_like(time)
    for i, t in enumerate(time):
        if t <= tp:
            flow[i] = qp * t / tp if tp > 0 else 0
        else:
            flow[i] = qp * (tb - t) / tr if tr > 0 else 0

    return time, flow
```

---

## 5. Hidrograma Curvilinear SCS

### 5.1 Contexto

El hidrograma adimensional SCS se basa en un analisis de muchos hidrogramas observados. Se define como la relacion entre q/qp y t/Tp.

### 5.2 Formula

El caudal pico se calcula con el Peak Rate Factor (PRF):

```
qp = (PRF/484) × 2.08 × A × Q / Tp
```

Para PRF=484 (estandar), es equivalente al triangular.

### 5.3 Ecuacion Gamma

Una aproximacion analitica del hidrograma curvilinear:

```
q/qp = (t/Tp)^m × e^(m × (1 - t/Tp))
```

Donde `m = 3.7` para PRF=484.

### 5.4 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 253-333)

def scs_curvilinear_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    prf: int = 484,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario curvilinear SCS (1 mm de escorrentia).
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)

    # Caudal pico para 1 mm usando PRF
    qp = (prf / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    # Cargar hidrograma adimensional
    uh_data = _load_uh_data()
    t_tp_std = np.array(uh_data["scs_curvilinear"]["t_Tp"])
    q_qp_std = np.array(uh_data["scs_curvilinear"]["q_qp"])

    # Escalar a valores reales
    tb = t_tp_std[-1] * tp
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Interpolar ordenadas
    t_tp = time / tp
    flow = qp * np.interp(t_tp, t_tp_std, q_qp_std, right=0)

    return time, flow


def gamma_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    m: float = 3.7,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario usando ecuacion Gamma.

    q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp)
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)
    prf_approx = 130 * m + 3
    qp = (prf_approx / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    tb = 5 * tp
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    t_tp = time / tp
    t_tp = np.maximum(t_tp, 1e-10)

    q_qp = (t_tp ** m) * np.exp(m * (1 - t_tp))
    flow = qp * q_qp

    return time, flow
```

---

## 6. Hidrograma de Snyder (1938)

### 6.1 Contexto

Desarrollado por Snyder para cuencas en los Apalaches (USA). Requiere calibracion regional de los coeficientes Ct y Cp.

### 6.2 Formulas

#### Tiempo de Retardo
```
tp = Ct × (L × Lc)^0.3
```

Donde:
- `tp`: Tiempo de retardo (horas)
- `L`: Longitud del cauce (millas)
- `Lc`: Distancia al centroide (millas)
- `Ct`: Coeficiente regional (1.8-2.2 tipico)

#### Caudal Pico
```
Qp = 640 × Cp × A / tp
```

Donde:
- `Qp`: Caudal pico (cfs para 1 pulgada)
- `A`: Area (mi²)
- `Cp`: Coeficiente de pico (0.4-0.8 tipico)

#### Anchos del Hidrograma
```
W50 = 770 × (Qp/A)^(-1.08)  [horas]
W75 = 440 × (Qp/A)^(-1.08)  [horas]
```

### 6.3 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 340-470)

def snyder_lag_time(
    length_km: float,
    lc_km: float,
    ct: float = 2.0,
) -> float:
    """
    Calcula tiempo de retardo Snyder.
    tp = Ct × (L × Lc)^0.3  [tp: hr, L/Lc: km]
    """
    length_mi = length_km * 0.621371
    lc_mi = lc_km * 0.621371
    return ct * ((length_mi * lc_mi) ** 0.3)


def snyder_peak(
    area_km2: float,
    tp_hr: float,
    cp: float = 0.6,
) -> float:
    """
    Calcula caudal pico Snyder para 1 pulgada de escorrentia.
    Qp = 640 × Cp × A / tp  [Qp: cfs, A: mi²]
    """
    area_mi2 = area_km2 * 0.386102
    qp_cfs = 640 * cp * area_mi2 / tp_hr
    qp_m3s = qp_cfs * 0.0283168
    return qp_m3s


def snyder_widths(qp_m3s: float, area_km2: float) -> tuple[float, float]:
    """
    Calcula anchos del hidrograma Snyder al 50% y 75% del pico.
    W50 = 770 × (Qp/A)^(-1.08)  [hr]
    W75 = 440 × (Qp/A)^(-1.08)  [hr]
    """
    qp_cfs = qp_m3s / 0.0283168
    area_mi2 = area_km2 * 0.386102
    qp_a = qp_cfs / area_mi2
    w50 = 770 * (qp_a ** -1.08)
    w75 = 440 * (qp_a ** -1.08)
    return w50, w75
```

---

## 7. Hidrograma de Clark

### 7.1 Contexto

El metodo de Clark utiliza una curva tiempo-area y un reservorio lineal para transformar la precipitacion en escorrentia.

### 7.2 Curva Tiempo-Area

Relacion por defecto (forma de diamante):

```
A(t) = 1.414 × (t/Tc)^1.5         para t/Tc ≤ 0.5
A(t) = 1 - 1.414 × (1 - t/Tc)^1.5 para t/Tc > 0.5
```

### 7.3 Routing del Reservorio Lineal

```
c1 = dt / (2R + dt)
c2 = c1
c0 = (2R - dt) / (2R + dt)

O(t) = c1 × I(t) + c2 × I(t-1) + c0 × O(t-1)
```

Donde:
- `R`: Coeficiente de almacenamiento (horas)
- `I`: Entrada al reservorio
- `O`: Salida del reservorio

### 7.4 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 477-547)

def clark_time_area(
    t_tc: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Calcula relacion tiempo-area por defecto (forma de diamante).
    """
    a_at = np.zeros_like(t_tc)
    mask_rise = t_tc <= 0.5
    a_at[mask_rise] = 1.414 * (t_tc[mask_rise] ** 1.5)
    a_at[~mask_rise] = 1 - 1.414 * ((1 - t_tc[~mask_rise]) ** 1.5)
    return np.clip(a_at, 0, 1)


def clark_uh(
    area_km2: float,
    tc_hr: float,
    r_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario Clark (1 mm de escorrentia).
    """
    # Coeficientes de routing lineal
    c1 = dt_hr / (2 * r_hr + dt_hr)
    c2 = c1
    c0 = (2 * r_hr - dt_hr) / (2 * r_hr + dt_hr)

    # Tiempo base (aproximado)
    tb = tc_hr + 5 * r_hr
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Calcular entrada desde curva tiempo-area
    t_tc = time / tc_hr
    area_cum = clark_time_area(np.minimum(t_tc, 1.0))

    # Area incremental
    area_incr = np.zeros(n_points)
    area_incr[1:] = np.diff(area_cum)
    area_incr[0] = area_cum[0]

    # Inflow al reservorio
    inflow = area_incr * area_km2 * 1000 / (dt_hr * 3600)

    # Routing
    outflow = np.zeros(n_points)
    for i in range(1, n_points):
        outflow[i] = c1 * inflow[i] + c2 * inflow[i-1] + c0 * outflow[i-1]

    return time, outflow
```

---

## 8. Convolucion

### 8.1 Concepto

La convolucion combina el exceso de lluvia con el hidrograma unitario para obtener el hidrograma resultante:

```
Qn = Σ(m=1 to M) [Pm × U(n-m+1)]
```

### 8.2 Implementacion

```python
# Archivo: src/hidropluvial/core/hydrograph.py (lineas 554-570)

def convolve_uh(
    rainfall_excess: NDArray[np.floating],
    unit_hydrograph: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Convolucion discreta de exceso de lluvia con hidrograma unitario.

    Qn = Σ(m=1 to M) [Pm × U(n-m+1)]
    """
    return np.convolve(rainfall_excess, unit_hydrograph, mode='full')
```

---

## 9. Ejemplos de Uso

### 9.1 Hidrograma Triangular SCS

```python
from hidropluvial.core.hydrograph import scs_triangular_uh, scs_time_to_peak

# Cuenca de 5 km², Tc=1 hora, dt=10 min
area_km2 = 5.0
tc_hr = 1.0
dt_hr = 10/60  # 10 minutos

time, flow = scs_triangular_uh(area_km2, tc_hr, dt_hr)

# Tiempo al pico
tp = scs_time_to_peak(tc_hr, dt_hr)
print(f"Tiempo al pico: {tp:.2f} horas")
print(f"Caudal pico unitario: {max(flow):.2f} m³/s por mm")
```

### 9.2 Hidrograma con Factor X

```python
from hidropluvial.core.hydrograph import triangular_uh_x

# Cuenca urbana de 50 ha, Tc=0.5 horas
area_ha = 50.0
tc_hr = 0.5
dt_hr = 5/60  # 5 minutos
x_factor = 1.25  # Area urbana

time, flow = triangular_uh_x(area_ha, tc_hr, dt_hr, x_factor)
print(f"Caudal pico: {max(flow):.2f} m³/s por mm")
```

### 9.3 Hidrograma Completo con Convolucion

```python
from hidropluvial.core.hydrograph import generate_hydrograph
from hidropluvial.config import HydrographMethod
import numpy as np

# Exceso de lluvia (mm por intervalo)
rainfall_excess = np.array([0.5, 2.0, 5.0, 3.0, 1.0, 0.5])

result = generate_hydrograph(
    rainfall_excess_mm=rainfall_excess,
    method=HydrographMethod.SCS_TRIANGULAR,
    area_km2=10.0,
    tc_hr=2.0,
    dt_hr=0.25,  # 15 minutos
)

print(f"Caudal pico: {result.peak_flow_m3s:.2f} m³/s")
print(f"Tiempo al pico: {result.time_to_peak_hr:.2f} horas")
print(f"Volumen: {result.volume_m3/1e6:.4f} hm³")
```

---

## 10. Seleccion del Metodo

| Metodo | Aplicacion | Datos Requeridos |
|--------|------------|------------------|
| SCS Triangular | General, rapido | Tc, Area |
| SCS Curvilinear | General, mas preciso | Tc, Area, PRF |
| Triangular X | Cuencas urbanas Uruguay | Tc, Area, X |
| Snyder | Cuencas grandes | L, Lc, Ct, Cp |
| Clark | Cuencas con reservorio | Tc, R |
| Gamma | Alternativa analitica | Tc, Area, m |

---

## 11. Referencias

- NRCS. (1986). "Urban Hydrology for Small Watersheds". TR-55.
- Snyder, F.F. (1938). "Synthetic Unit-Graphs". Trans. AGU.
- Clark, C.O. (1945). "Storage and the Unit Hydrograph". Trans. ASCE.
- Chow, V.T., Maidment, D.R., Mays, L.W. (1988). "Applied Hydrology".

---

*Documentacion generada automaticamente desde el codigo fuente.*
