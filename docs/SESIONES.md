# HidroPluvial - Sistema de Sesiones

**Guía del sistema de gestión de análisis hidrológicos**

---

## Introducción

El sistema de sesiones permite:

- Definir una cuenca con sus características
- Ejecutar múltiples análisis con diferentes combinaciones de parámetros
- Comparar resultados (tablas, gráficos, filtros)
- Generar reportes automáticos
- Persistir datos para continuar posteriormente

---

## Conceptos Clave

### Sesión

Una sesión representa un proyecto de análisis hidrológico. Contiene:

- **Datos de la cuenca:** Área, pendiente, P₃,₁₀, coeficientes
- **Resultados de Tc:** Tiempos de concentración calculados
- **Análisis:** Conjunto de simulaciones ejecutadas
- **ID único:** Identificador de 8 caracteres (ej: `abc12345`)

### Análisis

Cada análisis dentro de una sesión incluye:

- **Parámetros:** Método Tc, tipo de tormenta, Tr, factor X
- **Tormenta generada:** Hietograma con tiempo e intensidad
- **Hidrograma resultante:** Caudal vs tiempo
- **Métricas:** Qp, Tp, volumen

---

## Comandos Principales

### Crear Sesión

```bash
hp session create <nombre> --area A --slope S --p3_10 P --c C [opciones]
```

**Parámetros obligatorios:**
- `nombre`: Nombre descriptivo de la cuenca
- `--area`: Área en hectáreas
- `--slope`: Pendiente media en %
- `--p3_10`: Precipitación P₃,₁₀ en mm
- `--c`: Coeficiente de escorrentía

**Parámetros opcionales:**
- `--cn`: Curva Número (para método SCS)
- `--length`: Longitud del cauce principal en metros

**Ejemplo:**
```bash
hp session create "Cuenca Norte" --area 62 --slope 3.41 --p3_10 83 --c 0.62 --cn 81 --length 800
```

**Salida:**
```
Sesion creada: abc12345
  Nombre: Cuenca Norte
  Area: 62.0 ha
  Pendiente: 3.41%
  P3,10: 83 mm
  C: 0.62
  CN: 81
  Longitud: 800 m
```

---

### Listar Sesiones

```bash
hp session list
```

**Salida:**
```
SESIONES GUARDADAS
==================
  ID        Nombre              Area    Fecha       Analisis
  ----------------------------------------------------------------
  abc12345  Cuenca Norte        62 ha   2025-12-04  12
  def67890  Cuenca Sur          35 ha   2025-12-03   8
  ghi23456  Proyecto Centro    100 ha   2025-12-01  24
```

---

### Ver Detalles de Sesión

```bash
hp session show <id>
```

**Ejemplo:**
```bash
hp session show abc12345
```

---

### Calcular Tiempo de Concentración

```bash
hp session tc <id> --methods "metodo1,metodo2,..."
```

**Métodos disponibles:**
- `kirpich`: Fórmula de Kirpich
- `desbordes`: Método de los Desbordes (DINAGUA)
- `temez`: Fórmula de Témez

**Ejemplo:**
```bash
hp session tc abc12345 --methods "kirpich,desbordes"
```

**Salida:**
```
TIEMPOS DE CONCENTRACION
========================
  Metodo      Tc (min)    Tc (hr)
  ---------------------------------
  kirpich        12.3      0.21
  desbordes      22.6      0.38

  Resultados guardados en sesion abc12345
```

---

### Ejecutar Análisis

```bash
hp session analyze <id> --tc METODO --storm TIPO --tr TR [--x X]
```

**Parámetros:**
- `--tc`: Método de Tc a usar (debe estar calculado)
- `--storm`: Tipo de tormenta (`gz`, `blocks`, `bimodal`, `blocks24`)
- `--tr`: Período de retorno en años
- `--x`: Factor de forma del hidrograma (opcional)

**Ejemplo:**
```bash
hp session analyze abc12345 --tc desbordes --storm gz --tr 10 --x 1.0
```

**Salida:**
```
ANALISIS EJECUTADO
==================
  ID: d36d2306
  Tc: desbordes (22.6 min)
  Tormenta: gz
  Tr: 10 anos
  X: 1.0

  Resultados:
    P total: 105.9 mm
    Q total: 65.7 mm
    Qp: 10.426 m3/s
    Tp: 80.0 min
```

**Ejecutar múltiples análisis:**
```bash
hp session analyze abc12345 --tc desbordes --storm gz --tr 2 --x 1.0
hp session analyze abc12345 --tc desbordes --storm gz --tr 10 --x 1.0
hp session analyze abc12345 --tc desbordes --storm gz --tr 25 --x 1.0
hp session analyze abc12345 --tc kirpich --storm gz --tr 10 --x 1.25
```

---

### Ver Resumen Comparativo

```bash
hp session summary <id>
```

**Salida:**
```
====================================================================================================
  RESUMEN COMPARATIVO - Cuenca Norte (abc12345)
====================================================================================================
  ID       | Tc           |  Tc(min) | Tormenta   |   Tr |     X |   P(mm) |   Q(mm) |  Qp(m³/s) |  Tp(min)
  --------------------------------------------------------------------------------------------------
  d36d2306 | desbordes    |     22.6 | gz         |    2 |  1.00 |    68.6 |    42.5 |     6.748 |     80.0
  7de6650b | desbordes    |     22.6 | gz         |   10 |  1.00 |   105.9 |    65.7 |    10.426 |     80.0
  bc416b51 | desbordes    |     22.6 | gz         |   25 |  1.00 |   127.3 |    79.0 |    12.534 |     80.0
  f2a8c912 | kirpich      |     12.3 | gz         |   10 |  1.25 |   105.9 |    65.7 |     8.341 |     70.0
====================================================================================================

  Caudal maximo: 12.534 m³/s (desbordes + gz Tr25)
  Caudal minimo: 6.748 m³/s (desbordes + gz Tr2)
  Variacion: 85.7%
```

---

### Visualización en Terminal (Preview)

El comando `preview` permite visualizar los resultados directamente en la terminal.

```bash
hp session preview <id> [opciones]
```

**Opciones:**
- `--idx N, -i N`: Ver análisis específico por índice
- `--compare, -c`: Comparar todos los hidrogramas
- `--hyeto, -y`: Mostrar hietograma en vez de hidrograma
- `--tr TR`: Filtrar por período de retorno
- `--x X`: Filtrar por factor X
- `--tc TC`: Filtrar por método Tc
- `--storm S`: Filtrar por tipo de tormenta
- `--width W, -w`: Ancho del gráfico (default: 70)
- `--height H, -h`: Alto del gráfico (default: 18)

#### Modo por Defecto: Tabla con Sparklines

```bash
hp session preview abc12345
```

**Salida:**
```
  Sesion: Cuenca Norte (abc12345)
  Cuenca: 62.0 ha, S=3.41%

  #   Tc        Storm   Tr     X    Qp(m³/s)  Tp(hr)  Hidrograma
  ----------------------------------------------------------------------
  0   desbordes gz       2  1.00      6.748    1.33  ▁▂▄▇█▇▄▂▁
  1   desbordes gz      10  1.00     10.426    1.33  ▁▂▄▇█▇▄▂▁
  2   desbordes gz      25  1.00     12.534    1.33  ▁▂▄▇█▇▄▂▁
  3   kirpich   gz      10  1.25      8.341    1.17  ▁▂▃▅▇█▇▅▃▂▁

  Comandos:
    hp session preview abc12345 -i 0         Ver hidrograma #0
    hp session preview abc12345 -i 0 --hyeto Ver hietograma #0
    hp session preview abc12345 --compare    Comparar todos
    hp session preview abc12345 --tr 10      Filtrar por Tr
```

#### Modo Comparación: Hidrogramas Superpuestos

```bash
hp session preview abc12345 --compare
```

Usa la librería `plotext` para mostrar gráficos ASCII:

```
  Sesion: Cuenca Norte (abc12345)
  Comparando 4 hidrogramas

  ┌────────────────────────────────────────────────────────────────┐
  │                                                                │
  │  12 ┤                 ╭──╮                                     │
  │     │                ╱    ╲    desbordes gz Tr25 X1.0          │
  │  10 ┤           ╭──╱       ╲                                   │
  │     │          ╱             ╲   desbordes gz Tr10 X1.0        │
  │   8 ┤    ╭───╱                 ╲──                             │
  │     │   ╱                         ╲   kirpich gz Tr10 X1.25    │
  │   6 ┤  ╱                           ╲──╮                        │
  │     │ ╱                                ╲                       │
  │   4 ┤╱                                  ╲──                    │
  │     │                                      ╲───                │
  │   2 ┤                                          ╲───────        │
  │     │                                                  ────    │
  │   0 ┼────────────────────────────────────────────────────────  │
  │     0         1         2         3         4         5        │
  │                         Tiempo (hr)                            │
  └────────────────────────────────────────────────────────────────┘
```

#### Modo Individual: Hidrograma Específico

```bash
hp session preview abc12345 -i 0
```

```
  desbordes + gz Tr2 X1.00
  Qp: 6.748 m³/s
  Tp: 1.33 h
  Vol: 2635.2 m³

  ┌────────────────────────────────────────────────────────────────┐
  │                                                                │
  │   7 ┤           ╭────╮                                         │
  │     │          ╱      ╲                                        │
  │   6 ┤         ╱        ╲                                       │
  │     │        ╱          ╲                                      │
  │   5 ┤       ╱            ╲                                     │
  │     │      ╱              ╲                                    │
  │   4 ┤     ╱                ╲                                   │
  │     │    ╱                  ╲                                  │
  │   3 ┤   ╱                    ╲                                 │
  │     │  ╱                      ╲──                              │
  │   2 ┤ ╱                          ╲──                           │
  │     │╱                              ╲────                      │
  │   1 ┤                                    ╲──────               │
  │     │                                           ╲──────────    │
  │   0 ┼────────────────────────────────────────────────────────  │
  └────────────────────────────────────────────────────────────────┘
```

#### Modo Hietograma

```bash
hp session preview abc12345 -i 0 --hyeto
```

```
  desbordes + gz Tr2 X1.00
  P total: 68.6 mm
  i max: 45.3 mm/h

  t(min)  i(mm/h)  Barras
  -----------------------------------------
    0-10     8.2   ████
   10-20    12.5   ██████
   20-30    18.7   █████████
   30-40    28.3   ██████████████
   40-50    45.3   ██████████████████████
   50-60    32.1   ████████████████
   60-70    21.4   ██████████
  ...

  ┌────────────────────────────────────────────────────────────────┐
  │  45 ┤                    ██                                    │
  │     │                   ████                                   │
  │  35 ┤                  ██████                                  │
  │     │                ████████                                  │
  │  25 ┤              ██████████                                  │
  │     │            ████████████                                  │
  │  15 ┤          ██████████████                                  │
  │     │        ████████████████                                  │
  │   5 ┤      ██████████████████                                  │
  │     │    ████████████████████                                  │
  │   0 ┼────────────────────────────────────────────────────────  │
  └────────────────────────────────────────────────────────────────┘
```

---

### Filtros

Los filtros permiten ver subconjuntos de análisis.

**Filtrar por período de retorno:**
```bash
hp session preview abc12345 --tr 10
hp session preview abc12345 --tr 2,10,25  # Múltiples valores
```

**Filtrar por factor X:**
```bash
hp session preview abc12345 --x 1.0
hp session preview abc12345 --x 1.0,1.25
```

**Filtrar por método Tc:**
```bash
hp session preview abc12345 --tc desbordes
hp session preview abc12345 --tc kirpich,temez
```

**Filtrar por tipo de tormenta:**
```bash
hp session preview abc12345 --storm gz
hp session preview abc12345 --storm gz,blocks
```

**Filtros combinados:**
```bash
hp session preview abc12345 --tc desbordes --tr 10 --x 1.0
```

**Salida con filtros:**
```
  Sesion: Cuenca Norte (abc12345) [Filtros: Tc=desbordes, Tr=10]
  Mostrando 1 de 4 analisis

  #   Tc        Storm   Tr     X    Qp(m³/s)  Tp(hr)
  --------------------------------------------------
  1   desbordes gz      10  1.00     10.426    1.33
```

---

### Análisis Batch desde YAML

Para proyectos complejos con muchas combinaciones:

```bash
hp session batch <archivo.yaml>
```

**Estructura del archivo YAML:**

```yaml
session:
  name: "Proyecto Drenaje Industrial"
  cuenca:
    nombre: "Cuenca A"
    area_ha: 62
    slope_pct: 3.41
    p3_10: 83
    c: 0.62
    cn: 81
    length_m: 800

tc_methods:
  - kirpich
  - desbordes

analyses:
  - storm: gz
    tr: [2, 10, 25]
    x: [1.0, 1.25]
  - storm: blocks
    tr: [10, 25]
```

**Ejecución:**
```
PROCESANDO ARCHIVO: proyecto.yaml
=================================

  Creando sesion: Proyecto Drenaje Industrial
  Sesion creada: xyz98765

  Calculando Tc...
    - kirpich: 12.3 min
    - desbordes: 22.6 min

  Ejecutando analisis...
    [1/16] desbordes + gz Tr2 X1.0 ... OK
    [2/16] desbordes + gz Tr2 X1.25 ... OK
    [3/16] desbordes + gz Tr10 X1.0 ... OK
    ...
    [16/16] kirpich + blocks Tr25 X1.0 ... OK

  Resumen: 16 analisis ejecutados
  ID sesion: xyz98765
```

---

### Generar Reporte LaTeX

```bash
hp session report <id> -o <archivo> --author "Autor" [--template DIR]
```

**Parámetros:**
- `-o, --output`: Nombre del archivo (sin extensión)
- `--author`: Autor del reporte
- `--template`: Directorio con plantillas personalizadas

**Ejemplo:**
```bash
hp session report abc12345 -o memoria_cuenca --author "Ing. García"
```

**Salida:**
```
GENERANDO REPORTE
=================
  Sesion: abc12345
  Analisis: 4

  - Generando tablas...
  - Generando graficos TikZ...
  - Compilando LaTeX...

  Archivos generados:
    memoria_cuenca.tex
    memoria_cuenca.pdf

  Directorio de graficos: memoria_cuenca_figures/
```

El reporte incluye:
- Datos de la cuenca
- Métodos y parámetros utilizados
- Tabla comparativa de resultados
- Fichas técnicas por análisis (tabla + hietograma + hidrograma)
- Gráficos TikZ/PGFPlots

---

### Eliminar Sesión

```bash
hp session delete <id> [--force]
```

**Ejemplo:**
```bash
hp session delete abc12345

? Eliminar sesion 'Cuenca Norte' (abc12345) con 4 analisis? (y/N): y
Sesion eliminada.
```

**Sin confirmación:**
```bash
hp session delete abc12345 --force
```

---

## Flujo de Trabajo Completo

```bash
# 1. Crear sesión
hp session create "Arroyo Norte" --area 50 --slope 2.5 --p3_10 80 --c 0.55

# 2. Calcular Tc con múltiples métodos
hp session tc a1b2c3d4 --methods "kirpich,desbordes,temez"

# 3. Ejecutar matriz de análisis
for tc in desbordes kirpich; do
  for tr in 2 10 25; do
    for x in 1.0 1.25; do
      hp session analyze a1b2c3d4 --tc $tc --storm gz --tr $tr --x $x
    done
  done
done

# 4. Ver resumen
hp session summary a1b2c3d4

# 5. Visualizar y filtrar
hp session preview a1b2c3d4 --compare
hp session preview a1b2c3d4 --tc desbordes --tr 10

# 6. Generar reporte
hp session report a1b2c3d4 -o memoria_arroyo_norte --author "Ing. Rodríguez"
```

---

## Almacenamiento

Las sesiones se almacenan en:
- **Windows:** `%APPDATA%\hidropluvial\sessions\`
- **Linux/Mac:** `~/.hidropluvial/sessions/`

Cada sesión es un archivo JSON que puede ser respaldado o compartido.

---

*Documentación del Sistema de Sesiones - HidroPluvial v1.0*
