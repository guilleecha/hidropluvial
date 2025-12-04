# HidroPluvial - Wizard Interactivo

**Guía del asistente de análisis hidrológicos**

---

## Introducción

El wizard es una interfaz interactiva guiada que permite realizar análisis hidrológicos completos sin necesidad de recordar comandos o sintaxis. Es ideal para:

- Usuarios nuevos aprendiendo la herramienta
- Análisis rápidos con múltiples combinaciones de parámetros
- Flujos de trabajo que requieren cálculo de C o CN ponderados

## Iniciar el Wizard

```bash
hp wizard
```

## Menú Principal

Al iniciar, se presenta el menú principal con las siguientes opciones:

```
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Analisis                |
|         Calculos hidrologicos para Uruguay                  |
+-------------------------------------------------------------+

? Que deseas hacer?
> 1. Nuevo analisis completo (guiado)
  2. Continuar sesion existente
  3. Consultar tabla IDF
  4. Ver comandos disponibles
  5. Salir
```

---

## 1. Nuevo Análisis Completo

El flujo de nuevo análisis guía al usuario a través de todos los pasos necesarios.

### Paso 1: Datos de la Cuenca

```
DATOS DE LA CUENCA
==================

? Nombre de la cuenca: Mi Cuenca Ejemplo
? Area de la cuenca (ha): 62
? Pendiente media (%): 3.41
? Longitud del cauce principal (m) [opcional]: 800
```

### Paso 2: Precipitación IDF

```
? Valor P3,10 para la zona (mm): 83

Consejo: Usa 'hp idf departamentos' para ver valores por departamento.
```

### Paso 3: Coeficientes de Escorrentía

El wizard ofrece tres opciones para ingresar los coeficientes:

```
? Como deseas ingresar los coeficientes de escorrentia?
> Solo C (Metodo Racional)
  Solo CN (Metodo SCS)
  Ambos (C y CN) - comparar metodologias
```

#### Opción: Solo C

```
? Como deseas obtener el coeficiente C?
> Ingresar valor directamente
  Calcular C ponderado por cobertura

? Coeficiente de escorrentia C (0.1-0.95): 0.62
```

#### Opción: Solo CN

```
? Como deseas obtener la Curva Numero CN?
> Ingresar valor directamente
  Calcular CN ponderado por cobertura

? Numero de curva CN (30-100): 81
```

#### Opción: Ambos (Comparación)

Esta opción permite calcular tanto C como CN para poder comparar análisis con diferentes metodologías:

```
COEFICIENTE C
? Como deseas obtener el coeficiente C?
> Calcular C ponderado por cobertura

? Selecciona la tabla de referencia:
> 1. Ven Te Chow (C segun periodo de retorno)
  2. FHWA HEC-22 (C base con factor de ajuste)
  3. Tabla regional Uruguay

[Se muestra la tabla seleccionada y se inicia el cálculo ponderado]

CURVA NUMERO CN
? Como deseas obtener la Curva Numero CN?
> Calcular CN ponderado por cobertura

[Se inicia el cálculo ponderado de CN]
```

### Paso 4: Cálculo de C Ponderado (si aplica)

```
  Tabla Ven Te Chow - C por Periodo de Retorno
  =====================================================================
  #   Categoria       Descripcion             Tr2    Tr5    Tr10   Tr25   Tr50   Tr100
  ---------------------------------------------------------------------
  1   Comercial       Centro comercial denso  0.75   0.80   0.85   0.88   0.90   0.95
  2   Comercial       Vecindario comercial    0.50   0.55   0.60   0.65   0.70   0.75
  ...

  Area total: 5.50 ha
  Asigna coberturas al area. Presiona Enter sin valor para terminar.

  Area restante: 5.500 ha (100.0%)
? Selecciona cobertura:
> 1. Comercial - Centro comercial denso (C=0.85 para Tr10)
  2. Comercial - Vecindario comercial (C=0.60 para Tr10)
  ...
  Asignar todo el area restante a una cobertura
  Terminar (area restante queda sin asignar)

? Area para 'Vecindario comercial' (ha, max 5.500): 2.0
  + 2.000 ha con C=0.60

  Area restante: 3.500 ha (63.6%)
? Selecciona cobertura:
> ...

============================================================
  RESUMEN DE COBERTURAS
============================================================
  Cobertura                           Area (ha)    C
  ----------------------------------------------------------
  Comercial: Vecindario comercial         2.000 (36.4%)   0.60
  Residencial: Multifamiliar adosado      2.500 (45.5%)   0.55
  Superficies: Pavimento asfaltico        1.000 (18.2%)   0.80
  ----------------------------------------------------------
  TOTAL                                   5.500 ha
============================================================
  COEFICIENTE C PONDERADO: 0.615
============================================================
```

### Paso 5: Cálculo de CN Ponderado (si aplica)

```
  Tabla SCS TR-55 - Areas Urbanas
  ==============================================================================
  #   Categoria    Descripcion             Cond.    A     B     C     D
  ------------------------------------------------------------------------------
  1   Residencial  Lotes 500 m2            N/A      77    85    90    92
  2   Residencial  Lotes 1000 m2           N/A      61    75    83    87
  ...

? Grupo hidrologico de suelo:
> A - Alta infiltracion (arena, grava)
  B - Moderada infiltracion (limo arenoso)
  C - Baja infiltracion (limo arcilloso)
  D - Muy baja infiltracion (arcilla)

  Area total: 5.50 ha
  Grupo hidrologico de suelo: B

[Proceso similar al C ponderado]

============================================================
  RESUMEN DE COBERTURAS (Grupo B)
============================================================
  Cobertura                               Area (ha)    CN
  ------------------------------------------------------------
  Comercial: Distritos comerciales          1.500 (27.3%)   92
  Residencial: Lotes 1000 m2                3.000 (54.5%)   75
  Espacios abiertos: Cesped >75% cubierto   1.000 (18.2%)   61
  ------------------------------------------------------------
  TOTAL                                     5.500 ha
============================================================
  CURVA NUMERO CN PONDERADA: 77.5
============================================================
```

### Paso 6: Tiempo de Concentración

```
CALCULO DE TIEMPO DE CONCENTRACION
==================================

? Selecciona metodos de Tc a calcular:
  [x] Kirpich
  [x] Desbordes (DINAGUA)
  [ ] Temez

RESULTADOS Tc
=============
  Kirpich:    12.3 min (0.21 hr)
  Desbordes:  22.6 min (0.38 hr)
```

### Paso 7: Configuración de Análisis

```
CONFIGURACION DE ANALISIS
=========================

? Tipo de tormenta:
> Bloques alternantes (gz - 6h pico adelantado)
  Bloques alternantes (blocks - duracion variable)
  Bimodal Uruguay (doble pico)
  Bloques 24 horas

? Periodos de retorno (separados por coma): 2,10,25

? Valores de X a analizar (separados por coma): 1.0,1.25
```

### Paso 8: Resumen y Confirmación

```
============================================================
  RESUMEN DE CONFIGURACION
============================================================
  Cuenca:     Mi Cuenca Ejemplo
  Area:       62.0 ha
  Pendiente:  3.41%
  P3,10:      83 mm
  C:          0.62
  CN:         81
============================================================
  METODOS Tc:
    - Kirpich:    12.3 min
    - Desbordes:  22.6 min
============================================================
  ANALISIS A EJECUTAR:
    - Tormenta: gz
    - Tr: 2, 10, 25
    - X: 1.0, 1.25
    - Total: 2 Tc x 3 Tr x 2 X = 12 analisis
============================================================

? Ejecutar analisis? (Y/n): Y

============================================================
  EJECUTANDO ANALISIS
============================================================

  [1/12] desbordes + gz Tr2 X1.0 ... OK (Qp = 6.748 m3/s)
  [2/12] desbordes + gz Tr2 X1.25 ... OK (Qp = 5.398 m3/s)
  ...
  [12/12] kirpich + gz Tr25 X1.25 ... OK (Qp = 12.356 m3/s)

  Sesion guardada: abc12345
============================================================
```

---

## 2. Menú Post-Ejecución

Después de ejecutar los análisis, se presenta un menú con opciones adicionales:

```
? Que deseas hacer?
> Ver resumen (tabla comparativa)
  Ver graficos en terminal
  Agregar mas analisis
  Filtrar resultados
  Generar reporte LaTeX
  Guardar y salir
```

### Ver Resumen

Muestra una tabla comparativa de todos los análisis:

```
====================================================================================================
  RESUMEN COMPARATIVO - Mi Cuenca Ejemplo (abc12345)
====================================================================================================
  #   Tc           |  Tc(min) | Tormenta   |   Tr |     X |   P(mm) |   Q(mm) |  Qp(m³/s) |  Tp(min)
  --------------------------------------------------------------------------------------------------
  0   desbordes    |     22.6 | gz         |    2 |  1.00 |    68.6 |    42.5 |     6.748 |     80.0
  1   desbordes    |     22.6 | gz         |    2 |  1.25 |    68.6 |    42.5 |     5.398 |     90.0
  2   desbordes    |     22.6 | gz         |   10 |  1.00 |   105.9 |    65.7 |    10.426 |     80.0
  ...
====================================================================================================

  Caudal maximo: 15.234 m³/s (kirpich + gz Tr25 X1.0)
  Caudal minimo: 5.398 m³/s (desbordes + gz Tr2 X1.25)
  Variacion: 182.3%
```

### Ver Gráficos en Terminal

```
? Selecciona tipo de visualizacion:
> Tabla con sparklines
  Comparar hidrogramas (superpuestos)
  Ver hidrograma individual
  Ver hietograma individual
```

#### Tabla con Sparklines

```
  Sesion: Mi Cuenca Ejemplo (abc12345)
  Cuenca: 62.0 ha, S=3.41%

  #   Tc        Storm   Tr     X    Qp(m³/s)  Tp(hr)  Hidrograma
  ----------------------------------------------------------------------------
  0   desbordes gz       2  1.00      6.748    1.33  ▁▂▄▇█▇▄▂▁
  1   desbordes gz       2  1.25      5.398    1.50  ▁▂▃▅▇█▇▅▃▂▁
  2   desbordes gz      10  1.00     10.426    1.33  ▁▂▄▇█▇▄▂▁
  ...
```

#### Comparar Hidrogramas

Superpone todos los hidrogramas usando plotext:

```
  Sesion: Mi Cuenca Ejemplo (abc12345)
  Comparando 12 hidrogramas

  ┌────────────────────────────────────────────────────────────────┐
  │                                                                │
  │  15 ┤                   ╭────╮                                 │
  │     │                  ╱      ╲      desbordes gz Tr25 X1.0    │
  │  12 ┤                 ╱        ╲                               │
  │     │                ╱          ╲    kirpich gz Tr10 X1.0      │
  │   9 ┤     ╭────╮    ╱            ╲                             │
  │     │    ╱      ╲  ╱              ╲                            │
  │   6 ┤   ╱        ╲╱                ╲───                        │
  │     │  ╱                              ───╲                     │
  │   3 ┤ ╱                                   ╲────                │
  │     │╱                                         ────────        │
  │   0 ┼──────────────────────────────────────────────────────    │
  │     0         1         2         3         4         5        │
  │                         Tiempo (hr)                            │
  └────────────────────────────────────────────────────────────────┘

  Q (m³/s) vs Tiempo (hr)
```

### Agregar Más Análisis

Permite agregar análisis adicionales a la sesión actual:

```
AGREGAR ANALISIS
================

? Tipo de tormenta:
> Bloques alternantes (gz - 6h pico adelantado)
  Bloques 24 horas
  Bimodal Uruguay

? Periodos de retorno adicionales: 50,100
? Valores de X adicionales: 1.67

  Agregando 4 analisis...
  [1/4] desbordes + gz Tr50 X1.67 ... OK
  ...
```

### Filtrar Resultados

Permite ver un subconjunto de los análisis:

```
FILTRAR RESULTADOS
==================

? Filtrar por metodo Tc (dejar vacio para todos): desbordes
? Filtrar por periodo de retorno (ej: 10 o 2,10,25):
? Filtrar por factor X (ej: 1.0 o 1.0,1.25): 1.0

  Mostrando 3 de 12 analisis [Filtros: Tc=desbordes, X=1.0]

  #   Tc        Storm   Tr     X    Qp(m³/s)  Tp(hr)
  --------------------------------------------------
  0   desbordes gz       2  1.00      6.748    1.33
  2   desbordes gz      10  1.00     10.426    1.33
  4   desbordes gz      25  1.00     12.894    1.33
```

### Generar Reporte LaTeX

```
GENERAR REPORTE
===============

? Nombre del archivo (sin extension): memoria_cuenca_norte
? Autor del reporte: Ing. Garcia

  Generando reporte...
  - Procesando 12 analisis
  - Creando tablas
  - Generando graficos TikZ
  - Compilando LaTeX

  Reporte generado: memoria_cuenca_norte.pdf
```

---

## 3. Continuar Sesión Existente

Permite retomar una sesión guardada:

```
SESIONES GUARDADAS
==================

  ID        Nombre              Area    Fecha       Analisis
  ----------------------------------------------------------------
  abc12345  Mi Cuenca Ejemplo   62 ha   2025-12-04  12
  def67890  Cuenca Sur          35 ha   2025-12-03   8
  ghi23456  Proyecto Centro    100 ha   2025-12-01  24

? Selecciona sesion: abc12345

[Se carga la sesión y se muestra el menú post-ejecución]
```

---

## 4. Consultar Tabla IDF

Acceso rápido a las tablas IDF de Uruguay:

```
CONSULTA IDF
============

? Que deseas consultar?
> Ver valores P3,10 por departamento
  Calcular intensidad para duracion especifica
  Generar tabla IDF completa

[Según la opción seleccionada]

VALORES P3,10 POR DEPARTAMENTO
==============================
  Departamento      P3,10 (mm)
  ------------------------------
  Artigas           95
  Canelones         80
  Cerro Largo       95
  Colonia           78
  ...
  Montevideo        78
  ...
```

---

## Características Especiales

### Validación en Tiempo Real

El wizard valida los datos a medida que se ingresan:

```
? Area de la cuenca (ha): -5
  ! El area debe ser un numero positivo

? Coeficiente C (0.1-0.95): 1.5
  ! C debe estar entre 0.1 y 0.95
```

### Análisis en Matriz

El wizard genera automáticamente todas las combinaciones de parámetros:

- Múltiples métodos de Tc
- Múltiples períodos de retorno
- Múltiples factores X

**Ejemplo:** 2 Tc × 3 Tr × 2 X = 12 análisis automáticos

### Navegación con Teclado

- Flechas arriba/abajo: Navegar opciones
- Enter: Seleccionar
- Espacio: Marcar/desmarcar en selección múltiple
- Ctrl+C: Cancelar

---

## Atajos y Consejos

1. **Valores por defecto**: Presiona Enter para aceptar el valor sugerido
2. **Múltiples valores**: Separa con comas (ej: `2,10,25`)
3. **Selección múltiple**: Usa espacio para marcar varios items
4. **Cancelar**: Ctrl+C en cualquier momento
5. **Ayuda IDF**: Consulta departamentos antes de ingresar P₃,₁₀

---

## Comparación CLI vs Wizard

| Aspecto | CLI Directo | Wizard |
|---------|-------------|--------|
| Velocidad | Más rápido para usuarios expertos | Más lento pero guiado |
| Curva de aprendizaje | Requiere conocer comandos | Intuitivo para principiantes |
| Automatización | Ideal para scripts | No automatizable |
| Cálculo ponderado | Comandos separados | Integrado en el flujo |
| Análisis batch | Desde YAML | No soportado |

---

*Documentación del Wizard - HidroPluvial v1.0*
