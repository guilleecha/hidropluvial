# HidroPluvial - Manual de Usuario

**Herramienta de Cálculos Hidrológicos para Uruguay**

---

## Contenido

1. [Introducción](#introducción)
2. [El Wizard Interactivo](#el-wizard-interactivo)
3. [Ficha de Análisis](#ficha-de-análisis)
4. [Métodos de Escorrentía](#métodos-de-escorrentía)
5. [Tiempo de Concentración](#tiempo-de-concentración)
6. [Tipos de Tormenta](#tipos-de-tormenta)
7. [Hidrogramas de Crecida](#hidrogramas-de-crecida)
8. [Visor de Resultados](#visor-de-resultados)
9. [Exportación y Reportes](#exportación-y-reportes)
10. [Referencia Rápida](#referencia-rápida)

---

## Introducción

HidroPluvial es una herramienta de cálculo hidrológico desarrollada para Uruguay que permite:

- Calcular curvas IDF según metodología DINAGUA (Rodríguez Fontal, 1980)
- Generar tormentas de diseño (GZ, SCS, Chicago, Bloques Alternantes, Bimodal)
- Calcular tiempo de concentración (Kirpich, Temez, Desbordes, NRCS)
- Determinar escorrentía (Método Racional y SCS-CN)
- Generar hidrogramas de crecida con factor X (Porto, 1995)
- Producir reportes técnicos en LaTeX/PDF

### Flujo de Trabajo

```
┌─────────────────────────────────────────────────────────────┐
│                    WIZARD INTERACTIVO                        │
├─────────────────────────────────────────────────────────────┤
│  1. Crear/Seleccionar Proyecto                              │
│  2. Crear/Seleccionar Cuenca                                │
│  3. Configurar Análisis:                                    │
│     • Método escorrentía (C o CN)                           │
│     • Métodos Tc                                            │
│     • Tipos de tormenta                                     │
│     • Períodos de retorno                                   │
│  4. Ejecutar y visualizar resultados                        │
│  5. Exportar (Excel/LaTeX)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## El Wizard Interactivo

### Iniciar el Wizard

```bash
hp wizard
```

### Menú Principal

```
╔══════════════════════════════════════════════════╗
║                                                  ║
║    ╦ ╦╦╔╦╗╦═╗╔═╗╔═╗╦  ╦ ╦╦  ╦╦╔═╗╦               ║
║    ╠═╣║ ║║╠╦╝║ ║╠═╝║  ║ ║╚╗╔╝║╠═╣║               ║
║    ╩ ╩╩═╩╝╩╚═╚═╝╩  ╩═╝╚═╝ ╚╝ ╩╩ ╩╩═╝             ║
║                                                  ║
║       ≋≋≋  Cálculos Hidrológicos  ≋≋≋            ║
║                   Uruguay                        ║
╚══════════════════════════════════════════════════╝

┌─ Menú Principal ─────────────────────────────────┐
│                                                  │
│  [e] Entrar     Gestionar proyectos y cuencas    │
│  ─────────────────────────────────────────────── │
│  [c] Configuración   Ajustes de la herramienta   │
│  [q] Salir                                       │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Navegación

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Navegar opciones |
| `Enter` | Seleccionar |
| `b` | Volver atrás |
| `Esc` / `q` | Salir |
| Letras | Acceso directo (ej: `e` para Entrar) |

### Conceptos: Proyectos y Cuencas

**Proyecto**: Agrupa múltiples cuencas de un estudio
- "Estudio de Drenaje Pluvial Barrio Norte"
- "Análisis Hidrológico Ruta 5 km 120-125"

**Cuenca (Basin)**: Área de análisis con propiedades físicas
- Área (ha), Pendiente (%), Longitud cauce (m)
- Coeficientes C y/o CN
- Análisis de crecidas asociados

---

## Ficha de Análisis

El formulario interactivo permite configurar todos los parámetros del análisis:

```
┌─ Agregar Análisis - Cuenca Las Piedras ──────────┐
│                                                  │
│  Método de Escorrentía        [✓] C  [✓] CN     │
│  Coeficiente C                0.62              │
│  Número de Curva CN           81                │
│  ─────────────────────────────────────────────── │
│  Métodos de Tc                                   │
│     [✓] Desbordes (urbano)    C=0.62            │
│     [✓] Kirpich (rural)       L=800m            │
│     [ ] Temez                 L=800m            │
│     [ ] NRCS                  Configurar →      │
│  ─────────────────────────────────────────────── │
│  Tipos de tormenta                               │
│     [✓] GZ (6 horas)          DINAGUA Uruguay   │
│     [ ] SCS Type II           NRCS estándar     │
│     [ ] Chicago               Pico sintético    │
│     [ ] Bimodal               Doble pico        │
│  ─────────────────────────────────────────────── │
│  Períodos de retorno                             │
│     [ ] 2 años  [✓] 10 años  [✓] 25 años        │
│  Factor X (hidrograma)                           │
│     [✓] 1.00    [ ] 1.25     [ ] 1.67           │
│                                                  │
│  [Enter] Ejecutar   [b] Volver   [q] Cancelar   │
└──────────────────────────────────────────────────┘
```

### Campos del Formulario

| Campo | Descripción | Referencia |
|-------|-------------|------------|
| Método Escorrentía | C (Racional) o CN (SCS-CN) | Chow, 1988 |
| Coeficiente C | 0.10 - 0.95 | FHWA HEC-22, Chow |
| Curva Número CN | 30 - 98 | SCS TR-55 |
| Métodos Tc | Kirpich, Temez, Desbordes, NRCS | Ver sección Tc |
| Tormentas | GZ, SCS, Chicago, Bloques, Bimodal | Ver sección Tormentas |
| Tr | 2, 5, 10, 25, 50, 100 años | IDF DINAGUA |
| Factor X | Forma del hidrograma (1.0-12.0) | Porto, 1995 |

---

## Métodos de Escorrentía

### Método Racional (Coeficiente C)

El coeficiente de escorrentía C representa la fracción de la precipitación que se convierte en escorrentía superficial.

**Fórmula del caudal pico:**
```
Qp = C × i × A / 360
```
Donde: Qp (m³/s), C (adimensional), i (mm/h), A (ha)

**Tablas de valores típicos:**

| Fuente | Descripción | Código |
|--------|-------------|--------|
| FHWA HEC-22 | Federal Highway Administration | `tables_c.py:14-39` |
| Ven Te Chow | Applied Hydrology, Table 5.5.2 | `tables_c.py:44-69` |

**Tabla FHWA HEC-22 (valores base Tr=2-10 años):**

| Categoría | Descripción | C |
|-----------|-------------|---|
| Comercial | Centro comercial/negocios | 0.85 |
| Comercial | Vecindario comercial | 0.60 |
| Industrial | Industria liviana | 0.65 |
| Industrial | Industria pesada | 0.75 |
| Residencial | Unifamiliar (>1000 m²) | 0.40 |
| Residencial | Unifamiliar (500-1000 m²) | 0.50 |
| Residencial | Unifamiliar (<500 m²) | 0.60 |
| Residencial | Multifamiliar/Apartamentos | 0.70 |
| Superficies | Asfalto/Concreto | 0.85 |
| Superficies | Techos | 0.85 |
| Superficies | Grava/Ripio | 0.32 |
| Césped arenoso | Pendiente plana <2% | 0.08 |
| Césped arenoso | Pendiente media 2-7% | 0.12 |
| Césped arcilloso | Pendiente plana <2% | 0.15 |
| Césped arcilloso | Pendiente media 2-7% | 0.20 |

**Referencia:** FHWA (2001). Urban Drainage Design Manual. HEC-22.

### Método SCS-CN (Curva Número)

El Número de Curva representa las características de infiltración del suelo según su cobertura y grupo hidrológico.

**Fórmulas fundamentales:**
```
S = (25400 / CN) - 254          Retención potencial (mm)
Ia = λ × S                       Abstracción inicial (λ=0.20 o 0.05)
Q = (P - Ia)² / (P - Ia + S)    Escorrentía (mm), si P > Ia
```

**Código fuente:** `core/runoff/scs.py:38-104`

**Grupos Hidrológicos de Suelo:**

| Grupo | Descripción | Infiltración |
|-------|-------------|--------------|
| A | Arena, grava | Alta (>7.6 mm/h) |
| B | Limo arenoso | Moderada (3.8-7.6 mm/h) |
| C | Limo arcilloso | Baja (1.3-3.8 mm/h) |
| D | Arcilla | Muy baja (<1.3 mm/h) |

**Tabla CN (SCS TR-55):**

| Cobertura | Condición | A | B | C | D |
|-----------|-----------|---|---|---|---|
| Residencial 500 m² (65% imp) | - | 77 | 85 | 90 | 92 |
| Residencial 1000 m² (38% imp) | - | 61 | 75 | 83 | 87 |
| Comercial (85% imp) | - | 89 | 92 | 94 | 95 |
| Industrial (72% imp) | - | 81 | 88 | 91 | 93 |
| Pavimento impermeable | - | 98 | 98 | 98 | 98 |
| Césped >75% cubierto | Buena | 39 | 61 | 74 | 80 |
| Césped 50-75% cubierto | Regular | 49 | 69 | 79 | 84 |
| Pasturas continua | Buena | 39 | 61 | 74 | 80 |
| Bosque con mantillo | Buena | 30 | 55 | 70 | 77 |

**Código fuente:** `core/coefficients/tables_cn.py:11-45`

**Ajuste por Condición de Humedad Antecedente (AMC):**

```
CN_I = CN_II / (2.281 - 0.01281 × CN_II)    AMC I (seco)
CN_III = CN_II / (0.427 + 0.00573 × CN_II)  AMC III (húmedo)
```

| AMC | Descripción | Lluvia 5 días previos |
|-----|-------------|----------------------|
| I | Seco | < 35 mm (crecimiento) |
| II | Promedio | 35-53 mm |
| III | Húmedo | > 53 mm |

**Código fuente:** `core/runoff/scs.py:107-120`

**Referencia:** USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55.

---

## Tiempo de Concentración

El tiempo de concentración (Tc) es el tiempo que tarda el agua en viajar desde el punto más alejado de la cuenca hasta la salida.

### Método Kirpich (1940)

Desarrollado para cuencas agrícolas pequeñas en Tennessee.

**Fórmula:**
```
Tc = 0.0195 × L^0.77 × S^(-0.385)
```
Donde: Tc (min), L (m), S (m/m)

**Factores de ajuste por superficie:**

| Superficie | Factor |
|------------|--------|
| Natural | 1.0 |
| Canales con pasto | 2.0 |
| Concreto/asfalto | 0.4 |
| Canales de concreto | 0.2 |

**Código fuente:** `core/tc/kirpich.py:8-49`

**Referencia:** Kirpich, Z.P. (1940). Time of concentration of small agricultural watersheds. Civil Engineering, 10(6), 362.

### Método Témez

Utilizado ampliamente en España y Latinoamérica.

**Fórmula:**
```
Tc = 0.3 × (L / S^0.25)^0.76
```
Donde: Tc (hr), L (km), S (m/m)

**Válido para:** Cuencas de 1-3000 km²

**Código fuente:** `core/tc/empirical.py:12-33`

**Referencia:** Témez, J.R. (1978). Cálculo hidrometeorológico de caudales máximos en pequeñas cuencas naturales. MOPU, España.

### Método Desbordes (DINAGUA Uruguay)

Recomendado para cuencas urbanas en Uruguay.

**Fórmula:**
```
Tc = T0 + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45)
```
Donde: Tc (min), T0 (min), A (ha), P (%), C (adimensional)

**Valores típicos de T0:**

| Tipo de cuenca | T0 (min) |
|----------------|----------|
| Urbano denso | 3 |
| Por defecto | 5 |
| Rural/suburbano | 10 |

**Código fuente:** `core/tc/empirical.py:89-123`

**Referencia:** DINAGUA (2011). Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas. Uruguay.

### Método NRCS (TR-55)

Método de velocidades que divide el recorrido en segmentos con diferentes tipos de flujo.

**Tipos de flujo:**

| Tipo | Descripción | Fórmula |
|------|-------------|---------|
| Sheet flow | Flujo laminar (<100m) | Tt = 0.007 × (nL)^0.8 / (P2^0.5 × S^0.4) |
| Shallow concentrated | Flujo superficial | V = k × S^0.5 |
| Channel flow | Flujo en canal | V = (1/n) × R^(2/3) × S^(1/2) |

**Código fuente:** `core/tc/nrcs.py`

**Referencia:** USDA-NRCS (1986). Urban Hydrology for Small Watersheds. TR-55.

---

## Tipos de Tormenta

### GZ - Tormenta DINAGUA Uruguay

Distribución temporal de 6 horas con pico adelantado, basada en la metodología DINAGUA.

**Características:**
- Duración: 6 horas
- Pico: aproximadamente al 25% de la duración
- Método: Bloques alternantes con IDF DINAGUA

**Código fuente:** `core/temporal/blocks.py` (función `alternating_blocks_dinagua`)

**Referencia:** Rodríguez Fontal (1980). Estudio de Isoyetas Uruguay. DINAGUA.

### SCS Type II

Distribución temporal de 24 horas del NRCS, aplicable a la mayor parte de Estados Unidos.

**Características:**
- Duración: 24 horas
- Pico: al 50% de la duración (hora 12)
- Acumulación: basada en datos empíricos NRCS

**Código fuente:** `core/temporal/scs.py:15-80`

**Referencia:** USDA-SCS (1986). Urban Hydrology for Small Watersheds. TR-55.

### Chicago

Método de tormenta sintética basado en la curva IDF.

**Características:**
- Duración: variable
- Pico: configurable (coeficiente de avance r)
- Intensidad: derivada directamente de IDF

**Fórmula de intensidad:**
```
i(t) = a × [(1-b) × t^(-b) + c]     para t ≤ tb (rama ascendente)
i(t) = a × [(1-b) × t^(-b) + c]     para t > tb (rama descendente)
```

**Código fuente:** `core/temporal/chicago.py`

**Referencia:** Keifer, C.J. & Chu, H.H. (1957). Synthetic Storm Pattern for Drainage Design. ASCE Journal of the Hydraulics Division.

### Bloques Alternantes

Método clásico que ordena los bloques de lluvia de mayor a menor, alternando a cada lado del pico.

**Características:**
- Duración: 2×Tc o 24 horas
- Pico: central
- Método: redistribución de IDF acumulada

**Código fuente:** `core/temporal/blocks.py`

**Referencia:** Chow, V.T. et al. (1988). Applied Hydrology. McGraw-Hill.

### Bimodal (Doble Pico)

Tormenta con dos picos de intensidad, útil para eventos frontales o convectivos complejos.

**Parámetros configurables:**

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| Duración | Duración total | 6 horas |
| Pico 1 | Posición primer pico | 0.25 (25%) |
| Pico 2 | Posición segundo pico | 0.75 (75%) |
| Vol. Split | Fracción volumen pico 1 | 0.50 |
| Ancho pico | Fracción de duración | 0.15 |

**Código fuente:** `core/temporal/bimodal.py:18-99`

**Aplicaciones:**
- Cuencas urbanas con impermeabilidad mixta
- Regiones costeras tropicales
- Tormentas frontales de larga duración

---

## Hidrogramas de Crecida

### Hidrograma Unitario Triangular con Factor X

El factor X (Porto, 1995) permite ajustar la forma del hidrograma unitario según las características de la cuenca.

**Parámetros del hidrograma:**
```
tp = 0.6 × Tc                    Tiempo al pico (hr)
tb = tp × (1 + X)                Tiempo base (hr)
Qp = 0.208 × A × Pe / tp         Caudal pico (m³/s)
```
Donde: A (km²), Pe (mm), tp (hr)

**Valores típicos de X:**

| X | Descripción | Tipo de cuenca |
|---|-------------|----------------|
| 1.00 | Racional/urbano | Cuenca urbana densa |
| 1.25 | Urbano con pendiente | Urbana con pendiente |
| 1.67 | NRCS estándar | Mixta |
| 2.25 | Mixto rural/urbano | Periurbana |
| 3.33 | Rural sinuoso | Rural con cauces sinuosos |
| 5.50 | Rural pendiente baja | Rural con baja pendiente |
| 12.0 | Rural muy baja pendiente | Llanuras |

**Código fuente:** `core/hydrograph/triangular_x.py`

**Referencia:** Porto, R. et al. (1995). Drenagem Urbana. En: Tucci, C.E.M. Hidrologia: Ciência e Aplicação. ABRH.

### Otros Hidrogramas Disponibles

| Método | Descripción | Código |
|--------|-------------|--------|
| SCS Triangular | Estándar NRCS | `hydrograph/scs.py` |
| SCS Curvilinear | Adimensional NRCS | `hydrograph/scs.py` |
| Snyder | Sintético (1938) | `hydrograph/snyder.py` |
| Clark | Tiempo-área (1945) | `hydrograph/clark.py` |

---

## Visor de Resultados

### Tabla Resumen

```
┌─ Resultados - Cuenca Las Piedras ────────────────────────────────────────┐
│                                                                          │
│  # │ Tc      │ Tormenta │ Tr  │ X    │ Tc  │ tp  │ Qp    │ Vol    │ Esc │
│ ───┼─────────┼──────────┼─────┼──────┼─────┼─────┼───────┼────────┼─────│
│  1 │ Kirpich │ GZ       │  10 │ 1.00 │  12 │  21 │ 12.3  │ 0.033  │ C   │
│  2 │ Kirpich │ GZ       │  25 │ 1.00 │  12 │  21 │ 15.1  │ 0.041  │ C   │
│  3 │ Desbord │ GZ       │  10 │ 1.00 │  23 │  29 │ 10.2  │ 0.033  │ C   │
│  4 │ Desbord │ GZ       │  25 │ 1.00 │  23 │  29 │ 12.8  │ 0.041  │ C   │
│ ───┴─────────┴──────────┴─────┴──────┴─────┴─────┴───────┴────────┴─────│
│  Tiempos en min | Qp en m³/s | Vol en hm³                               │
│                                                                          │
│  [↑↓] Navegar  [Enter] Ver gráfico  [f] Filtrar  [e] Exportar           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Visor de Gráficos

El visor interactivo muestra hietograma e hidrograma combinados:

```
┌─────────────────────────────────────────────────────────────────────────┐
│           Hietograma - P=106.2mm, imax=54.3mm/h                         │
│  60 ┤                                                                   │
│  40 ┤   ████                                                            │
│  20 ┤███████████████                                                    │
│   0 └────────────────────────────────────────────────────────(min)      │
├─────────────────────────────────────────────────────────────────────────┤
│           Hidrograma - Qp=12 m³/s, Tp=35min                             │
│  12 ┤              ×                                                    │
│   8 ┤            ╱   ╲                                                  │
│   4 ┤          ╱       ╲                                                │
│   0 └────────────────────────────────────────────────────(min)          │
└─────────────────────────────────────────────────────────────────────────┘
  [1/12] Kirpich + GZ Tr10

  Cuenca: Las Piedras
  Tc=23min  tp=29min  X=1.00  tb=77min
  P=106.2mm  Pe=65.7mm  Vol=0.041hm³

  [←] Anterior  [→] Siguiente  [q] Salir
```

**Navegación:**
- `←` `→`: Cambiar entre análisis
- `↑` `↓`: Ir al primero / último
- `c`: Comparar hidrogramas
- `q` / `Esc`: Salir

---

## Exportación y Reportes

### Exportar a Excel

```
? Formato de exportación:
> Excel (.xlsx) - Tabla con todos los datos
```

**Contenido del Excel:**

| Hoja | Contenido |
|------|-----------|
| Cuenca | Datos geométricos y coeficientes |
| Tiempo Concentración | Tc por método con parámetros |
| Resumen Análisis | Tabla completa de resultados |
| Por Período Retorno | Tabla pivote |
| Notas | Observaciones del proyecto |

### Generar Reporte LaTeX

```bash
hp session report <id> --output memoria --author "Ing. García"
```

**Estructura generada:**
```
outputs/
└── cuenca_las_piedras_20251211/
    ├── memoria.tex
    ├── memoria.pdf
    └── graficos/
        ├── hidrogramas/
        │   ├── hidrograma_tr10.pgf
        │   └── hidrograma_tr25.pgf
        └── hietogramas/
            ├── hietograma_tr10.pgf
            └── hietograma_tr25.pgf
```

---

## Referencia Rápida

### Valores P₃,₁₀ por Departamento (DINAGUA)

| Departamento | P₃,₁₀ (mm) | Departamento | P₃,₁₀ (mm) |
|--------------|------------|--------------|------------|
| Montevideo | 78 | Lavalleja | 90 |
| Canelones | 80 | Rocha | 90 |
| Maldonado | 85 | Treinta y Tres | 95 |
| Colonia | 78 | Cerro Largo | 95 |
| San José | 80 | Rivera | 95 |
| Flores | 85 | Artigas | 95 |
| Florida | 85 | Salto | 90 |
| Soriano | 80 | Paysandú | 85 |
| Durazno | 85 | Río Negro | 85 |
| Tacuarembó | 90 | | |

**Código fuente:** `core/idf/dinagua.py`

### Comandos CLI

```bash
# Iniciar wizard
hp wizard

# Gestión de proyectos
hp project list
hp project show <id>
hp project delete <id>

# Cálculos directos
hp idf departamentos                    # Ver P3,10 por departamento
hp idf uruguay <p3_10> <dur> --tr <tr>  # Calcular intensidad IDF
hp tc kirpich --length 800 --slope 0.03 # Calcular Tc Kirpich

# Ayuda
hp --help
hp <comando> --help
```

### Símbolos y Unidades

| Símbolo | Descripción | Unidad |
|---------|-------------|--------|
| P₃,₁₀ | Precipitación 3h, Tr=10 años | mm |
| Tc | Tiempo de concentración | min |
| tp | Tiempo al pico | min |
| tb | Tiempo base | min |
| Qp | Caudal pico | m³/s |
| Vol | Volumen de escorrentía | hm³ |
| C | Coeficiente de escorrentía | - |
| CN | Número de Curva | - |
| Tr | Período de retorno | años |
| X | Factor de forma del hidrograma | - |

---

## Referencias Bibliográficas

1. **Chow, V.T., Maidment, D.R., Mays, L.W.** (1988). Applied Hydrology. McGraw-Hill.

2. **DINAGUA** (2011). Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas. Uruguay.

3. **FHWA** (2001). Urban Drainage Design Manual. Hydraulic Engineering Circular No. 22 (HEC-22). Federal Highway Administration.

4. **Keifer, C.J. & Chu, H.H.** (1957). Synthetic Storm Pattern for Drainage Design. ASCE Journal of the Hydraulics Division, 83(HY4).

5. **Kirpich, Z.P.** (1940). Time of concentration of small agricultural watersheds. Civil Engineering, 10(6), 362.

6. **Porto, R., Zahed Filho, K., Tucci, C., Bidone, F.** (1995). Drenagem Urbana. En: Tucci, C.E.M. (Ed.), Hidrologia: Ciência e Aplicação. ABRH/EDUSP.

7. **Rodríguez Fontal** (1980). Estudio de Precipitaciones Máximas en Uruguay. DINAGUA.

8. **Témez, J.R.** (1978). Cálculo hidrometeorológico de caudales máximos en pequeñas cuencas naturales. MOPU, España.

9. **USDA-SCS** (1986). Urban Hydrology for Small Watersheds. Technical Release 55 (TR-55). Soil Conservation Service.

---

*Manual de Usuario - HidroPluvial v2.0*
