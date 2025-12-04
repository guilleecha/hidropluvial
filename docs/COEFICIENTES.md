# HidroPluvial - Tablas de Coeficientes

**Guía de coeficientes de escorrentía C y Curva Número CN**

---

## Índice

1. [Coeficiente de Escorrentía C](#coeficiente-de-escorrentía-c)
2. [Curva Número CN](#curva-número-cn)
3. [Cálculo Ponderado](#cálculo-ponderado)
4. [Uso en CLI](#uso-en-cli)
5. [Referencias](#referencias)

---

## Coeficiente de Escorrentía C

El coeficiente C representa la fracción de la precipitación que se convierte en escorrentía superficial. Varía entre 0 (infiltración total) y 1 (escorrentía total).

### Tablas Disponibles

HidroPluvial incluye tres tablas de referencia:

| Tabla | Descripción | Característica |
|-------|-------------|----------------|
| `chow` | Ven Te Chow | C varía según período de retorno |
| `fhwa` | FHWA HEC-22 | C base con factor de ajuste por Tr |
| `uruguay` | Regional | Rangos típicos para Uruguay |

---

### Tabla Ven Te Chow

**Fuente:** Applied Hydrology, V.T. Chow et al. (1988), Tabla 5.5.2

Esta tabla proporciona valores de C para diferentes períodos de retorno, reconociendo que la respuesta hidrológica varía con la intensidad del evento.

| Categoría | Descripción | Tr2 | Tr5 | Tr10 | Tr25 | Tr50 | Tr100 |
|-----------|-------------|-----|-----|------|------|------|-------|
| **Comercial** | Centro comercial denso | 0.75 | 0.80 | 0.85 | 0.88 | 0.90 | 0.95 |
| **Comercial** | Vecindario comercial | 0.50 | 0.55 | 0.60 | 0.65 | 0.70 | 0.75 |
| **Residencial** | Unifamiliar | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 |
| **Residencial** | Multifamiliar separado | 0.35 | 0.40 | 0.45 | 0.50 | 0.55 | 0.60 |
| **Residencial** | Multifamiliar adosado | 0.45 | 0.50 | 0.55 | 0.60 | 0.65 | 0.70 |
| **Residencial** | Suburbano | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 |
| **Residencial** | Apartamentos | 0.50 | 0.55 | 0.60 | 0.65 | 0.70 | 0.75 |
| **Industrial** | Liviana | 0.50 | 0.55 | 0.60 | 0.65 | 0.70 | 0.80 |
| **Industrial** | Pesada | 0.60 | 0.65 | 0.70 | 0.75 | 0.80 | 0.85 |
| **Superficies** | Pavimento asfáltico | 0.70 | 0.75 | 0.80 | 0.85 | 0.90 | 0.95 |
| **Superficies** | Pavimento concreto | 0.75 | 0.80 | 0.85 | 0.90 | 0.92 | 0.95 |
| **Superficies** | Techos | 0.75 | 0.80 | 0.85 | 0.90 | 0.92 | 0.95 |
| **Superficies** | Adoquín con juntas | 0.50 | 0.55 | 0.60 | 0.65 | 0.70 | 0.75 |
| **Superficies** | Grava/Macadam | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 |
| **Césped arenoso** | Plano (<2%) | 0.05 | 0.08 | 0.10 | 0.13 | 0.15 | 0.18 |
| **Césped arenoso** | Medio (2-7%) | 0.10 | 0.13 | 0.16 | 0.19 | 0.22 | 0.25 |
| **Césped arenoso** | Fuerte (>7%) | 0.15 | 0.18 | 0.21 | 0.25 | 0.29 | 0.32 |
| **Césped arcilloso** | Plano (<2%) | 0.13 | 0.16 | 0.19 | 0.23 | 0.26 | 0.29 |
| **Césped arcilloso** | Medio (2-7%) | 0.18 | 0.21 | 0.25 | 0.29 | 0.34 | 0.37 |
| **Césped arcilloso** | Fuerte (>7%) | 0.25 | 0.29 | 0.34 | 0.40 | 0.44 | 0.50 |

**Uso:** Para períodos intermedios, el sistema interpola linealmente.

---

### Tabla FHWA HEC-22

**Fuente:** FHWA HEC-22 Urban Drainage Design Manual

Esta metodología usa un C base (para Tr ≤ 10 años) y aplica factores de ajuste para períodos mayores.

| Categoría | Descripción | C base |
|-----------|-------------|--------|
| **Comercial** | Centro comercial/negocios | 0.85 |
| **Comercial** | Vecindario comercial | 0.60 |
| **Industrial** | Industria liviana | 0.65 |
| **Industrial** | Industria pesada | 0.75 |
| **Residencial** | Unifamiliar (lotes >1000 m²) | 0.40 |
| **Residencial** | Unifamiliar (lotes 500-1000 m²) | 0.50 |
| **Residencial** | Unifamiliar (lotes <500 m²) | 0.60 |
| **Residencial** | Multifamiliar/Apartamentos | 0.70 |
| **Residencial** | Condominios/Townhouse | 0.60 |
| **Superficies** | Asfalto/Concreto | 0.85 |
| **Superficies** | Adoquín/Ladrillo | 0.78 |
| **Superficies** | Techos | 0.85 |
| **Superficies** | Grava/Ripio | 0.32 |
| **Césped arenoso** | Pendiente plana <2% | 0.08 |
| **Césped arenoso** | Pendiente media 2-7% | 0.12 |
| **Césped arenoso** | Pendiente alta >7% | 0.18 |
| **Césped arcilloso** | Pendiente plana <2% | 0.15 |
| **Césped arcilloso** | Pendiente media 2-7% | 0.20 |
| **Césped arcilloso** | Pendiente alta >7% | 0.28 |

**Factores de Ajuste por Período de Retorno:**

| Período de Retorno | Factor |
|--------------------|--------|
| Tr ≤ 10 años | 1.00 |
| Tr = 25 años | 1.10 |
| Tr = 50 años | 1.20 |
| Tr = 100 años | 1.25 |

**Nota:** El C ajustado nunca puede exceder 1.0

**Ejemplo:**
- C base = 0.85 (asfalto)
- Tr = 50 años → Factor = 1.20
- C ajustado = min(0.85 × 1.20, 1.0) = 1.0

---

### Tabla Regional Uruguay

Valores típicos adaptados a condiciones locales.

| Categoría | Descripción | C mín | C máx | C típico |
|-----------|-------------|-------|-------|----------|
| **Urbano** | Centro ciudad (muy denso) | 0.70 | 0.90 | 0.80 |
| **Urbano** | Comercial/Mixto | 0.60 | 0.80 | 0.70 |
| **Urbano** | Residencial alta densidad | 0.50 | 0.70 | 0.60 |
| **Urbano** | Residencial media densidad | 0.40 | 0.60 | 0.50 |
| **Urbano** | Residencial baja densidad | 0.30 | 0.50 | 0.40 |
| **Urbano** | Industrial | 0.60 | 0.85 | 0.72 |
| **Superficies** | Calles pavimentadas | 0.80 | 0.95 | 0.88 |
| **Superficies** | Veredas/Patios | 0.75 | 0.90 | 0.82 |
| **Superficies** | Techos | 0.80 | 0.95 | 0.88 |
| **Superficies** | Estacionamientos | 0.75 | 0.90 | 0.82 |
| **Superficies** | Tierra/Tosca compactada | 0.30 | 0.50 | 0.40 |
| **Áreas verdes** | Plazas/Parques | 0.10 | 0.25 | 0.18 |
| **Áreas verdes** | Jardines/Césped | 0.08 | 0.18 | 0.12 |
| **Áreas verdes** | Baldíos con vegetación | 0.15 | 0.35 | 0.25 |

---

## Curva Número CN

El método SCS-CN (Soil Conservation Service Curve Number) estima la escorrentía basándose en las características del suelo y la cobertura.

### Grupos Hidrológicos de Suelo

| Grupo | Descripción | Tasa de Infiltración |
|-------|-------------|----------------------|
| **A** | Alta infiltración | > 7.6 mm/hr |
| **B** | Moderada infiltración | 3.8 - 7.6 mm/hr |
| **C** | Baja infiltración | 1.3 - 3.8 mm/hr |
| **D** | Muy baja infiltración | < 1.3 mm/hr |

**Características:**
- **Grupo A:** Arena profunda, grava, suelos bien drenados
- **Grupo B:** Limo arenoso, suelos moderadamente profundos
- **Grupo C:** Limo arcilloso, suelos con capa impermeable
- **Grupo D:** Arcilla, nivel freático alto, suelos poco profundos

---

### Tabla SCS TR-55 - Áreas Urbanas

| Categoría | Descripción | Condición | A | B | C | D |
|-----------|-------------|-----------|---|---|---|---|
| **Residencial** | Lotes 500 m² (65% imp) | N/A | 77 | 85 | 90 | 92 |
| **Residencial** | Lotes 1000 m² (38% imp) | N/A | 61 | 75 | 83 | 87 |
| **Residencial** | Lotes 1500 m² (30% imp) | N/A | 57 | 72 | 81 | 86 |
| **Residencial** | Lotes 2000 m² (25% imp) | N/A | 54 | 70 | 80 | 85 |
| **Residencial** | Lotes 4000 m² (20% imp) | N/A | 51 | 68 | 79 | 84 |
| **Comercial** | Distritos comerciales (85% imp) | N/A | 89 | 92 | 94 | 95 |
| **Industrial** | Distritos industriales (72% imp) | N/A | 81 | 88 | 91 | 93 |
| **Superficies** | Pavimento impermeable | N/A | 98 | 98 | 98 | 98 |
| **Superficies** | Grava | N/A | 76 | 85 | 89 | 91 |
| **Superficies** | Tierra | N/A | 72 | 82 | 87 | 89 |
| **Espacios abiertos** | Césped >75% cubierto | Buena | 39 | 61 | 74 | 80 |
| **Espacios abiertos** | Césped 50-75% cubierto | Regular | 49 | 69 | 79 | 84 |
| **Espacios abiertos** | Césped <50% cubierto | Mala | 68 | 79 | 86 | 89 |

---

### Tabla SCS TR-55 - Áreas Agrícolas

| Categoría | Descripción | Condición | A | B | C | D |
|-----------|-------------|-----------|---|---|---|---|
| **Barbecho** | Suelo desnudo | N/A | 77 | 86 | 91 | 94 |
| **Cultivos** | Hileras rectas | Mala | 72 | 81 | 88 | 91 |
| **Cultivos** | Hileras rectas | Buena | 67 | 78 | 85 | 89 |
| **Cultivos** | Hileras en contorno | Mala | 70 | 79 | 84 | 88 |
| **Cultivos** | Hileras en contorno | Buena | 65 | 75 | 82 | 86 |
| **Cultivos** | Terrazas | Mala | 66 | 74 | 80 | 82 |
| **Cultivos** | Terrazas | Buena | 62 | 71 | 78 | 81 |
| **Pasturas** | Continua | Mala | 68 | 79 | 86 | 89 |
| **Pasturas** | Continua | Regular | 49 | 69 | 79 | 84 |
| **Pasturas** | Continua | Buena | 39 | 61 | 74 | 80 |
| **Pradera** | Natural | Buena | 30 | 58 | 71 | 78 |
| **Bosque** | Con mantillo | Mala | 45 | 66 | 77 | 83 |
| **Bosque** | Con mantillo | Regular | 36 | 60 | 73 | 79 |
| **Bosque** | Con mantillo | Buena | 30 | 55 | 70 | 77 |

---

## Cálculo Ponderado

### Fórmula de Ponderación por Área

Para cuencas con múltiples coberturas, el coeficiente ponderado se calcula:

**Coeficiente C ponderado:**
$$C_{ponderado} = \frac{\sum_{i=1}^{n} A_i \times C_i}{\sum_{i=1}^{n} A_i}$$

**Curva Número ponderada:**
$$CN_{ponderado} = \frac{\sum_{i=1}^{n} A_i \times CN_i}{\sum_{i=1}^{n} A_i}$$

Donde:
- $A_i$ = Área de la cobertura i
- $C_i$ o $CN_i$ = Coeficiente de la cobertura i
- $n$ = Número de coberturas

### Ejemplo de Cálculo

**Cuenca de 10 hectáreas:**

| Cobertura | Área (ha) | C |
|-----------|-----------|---|
| Residencial | 4.0 | 0.50 |
| Comercial | 2.5 | 0.70 |
| Parques | 2.0 | 0.15 |
| Calles | 1.5 | 0.88 |
| **Total** | **10.0** | |

**Cálculo:**
$$C = \frac{4.0 \times 0.50 + 2.5 \times 0.70 + 2.0 \times 0.15 + 1.5 \times 0.88}{10.0}$$
$$C = \frac{2.00 + 1.75 + 0.30 + 1.32}{10.0} = \frac{5.37}{10.0} = 0.537$$

---

## Uso en CLI

### Calcular C Ponderado

```bash
# Usando tabla Ven Te Chow para Tr=25
hp runoff weighted-c --table chow --tr 25 --area 10

# Usando tabla FHWA para Tr=50
hp runoff weighted-c --table fhwa --tr 50 --area 5.5

# Usando tabla regional Uruguay
hp runoff weighted-c --table uruguay --area 8
```

### Calcular CN Ponderado

```bash
# Áreas urbanas, suelo grupo B
hp runoff weighted-cn --table urban --soil B --area 50

# Áreas agrícolas, suelo grupo C
hp runoff weighted-cn --table agricultural --soil C --area 100
```

### Ver Tablas Disponibles

```bash
hp runoff show-tables c    # Tablas de coeficiente C
hp runoff show-tables cn   # Tablas de Curva Número
```

---

## Referencias

1. **Ven Te Chow, D.R. Maidment, L.W. Mays** (1988). *Applied Hydrology*. McGraw-Hill. Tabla 5.5.2.

2. **FHWA** (2024). *HEC-22: Urban Drainage Design Manual*, 4th Edition. Federal Highway Administration.

3. **NRCS** (1986). *TR-55: Urban Hydrology for Small Watersheds*. USDA Natural Resources Conservation Service.

4. **NRCS** (2020). *NEH Part 630: Hydrology*. Chapter 9: Hydrologic Soil-Cover Complexes.

5. **DINAGUA** (2011). *Manual de Drenaje Pluvial Urbano*. Ministerio de Transporte y Obras Públicas, Uruguay.

---

*Documentación de Coeficientes - HidroPluvial v1.0*
