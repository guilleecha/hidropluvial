# HidroPluvial - Manual de Usuario

**Guía práctica con ejemplos paso a paso**

---

## Contenido

1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Conceptos: Proyectos y Cuencas](#conceptos-proyectos-y-cuencas)
4. [Ejemplo 1: Análisis Básico con Método Racional](#ejemplo-1-análisis-básico-con-método-racional)
5. [Ejemplo 2: Análisis con SCS-CN](#ejemplo-2-análisis-con-scs-cn)
6. [Ejemplo 3: Comparación de Metodologías](#ejemplo-3-comparación-de-metodologías)
7. [Ejemplo 4: Parámetros Avanzados](#ejemplo-4-parámetros-avanzados)
8. [Exportación y Reportes](#exportación-y-reportes)
9. [Organización de Salidas](#organización-de-salidas)
10. [Referencia Rápida](#referencia-rápida)

---

## Introducción

HidroPluvial es una herramienta de cálculo hidrológico para Uruguay que permite:

- Calcular curvas IDF según metodología DINAGUA
- Generar tormentas de diseño (bloques alternantes, bimodal, SCS)
- Calcular tiempo de concentración (Kirpich, Temez, Desbordes)
- Determinar escorrentía (Método Racional y SCS-CN)
- Generar hidrogramas de crecida
- Producir reportes técnicos en LaTeX/PDF

### Modos de Uso

1. **Wizard Interactivo** (`hp wizard`): Guía paso a paso, ideal para principiantes
2. **Línea de Comandos** (`hp <comando>`): Más flexible, ideal para usuarios avanzados
3. **Scripts**: Automatización con archivos YAML

---

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/usuario/hidropluvial.git
cd hidropluvial

# Crear entorno virtual e instalar
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/Mac

pip install -e .

# Verificar instalación
hp --help
```

---

## Conceptos: Proyectos y Cuencas

HidroPluvial organiza el trabajo en una estructura jerárquica:

### Proyecto
Un **Proyecto** representa un estudio o trabajo completo, por ejemplo:
- "Estudio de Drenaje Pluvial Barrio Norte"
- "Análisis Hidrológico Ruta 5 km 120-125"

Cada proyecto puede contener múltiples cuencas y tiene metadatos como autor, descripción y ubicación.

### Cuenca (Basin)
Una **Cuenca** es el área de análisis con sus propiedades físicas:
- Área (ha), Pendiente (%), P₃,₁₀ (mm)
- Coeficientes de escorrentía (C y/o CN)
- Resultados de Tc y análisis de crecidas

### Flujo de Trabajo

```
Opción 1: Nueva cuenca (analisis guiado)
  → Donde deseas crear la cuenca?
    > Crear nuevo proyecto
    > [Proyectos existentes...]
    > Cancelar
  → Configurar cuenca y ejecutar análisis

Opción 2: Crear nuevo proyecto (vacío)
  → Ingresar datos del proyecto
  → Agregar nueva cuenca / Importar cuenca / Volver

Opción 3: Continuar proyecto/cuenca existente
  → Seleccionar proyecto o cuenca y trabajar
```

### Parámetros de Resultados

| Símbolo | Descripción | Unidad |
|---------|-------------|--------|
| Tc | Tiempo de concentración | min |
| tp | Tiempo pico del hidrograma unitario | min |
| tb | Tiempo base del hidrograma unitario (2.67×tp) | min |
| Tp | Tiempo al pico del hidrograma resultante | min |
| Qp | Caudal pico | m³/s |
| Vol | Volumen de escorrentía | hm³ |

---

## Ejemplo 1: Análisis Básico con Método Racional

### Descripción del Problema

**Cuenca Las Piedras**:
- Área: 62 ha
- Pendiente media: 3.41%
- Longitud del cauce: 800 m
- Coeficiente C: 0.62
- Ubicación: Montevideo (P₃,₁₀ = 78 mm)

### Usando el Wizard

```bash
hp wizard
```

1. Seleccionar "Nueva cuenca (analisis guiado)"
2. Ingresar datos de la cuenca:
   - Nombre: Cuenca Las Piedras
   - Área: 62
   - Pendiente: 3.41
   - Longitud: 800
3. Ingresar P₃,₁₀: 78
4. Seleccionar "Solo C (Método Racional)"
5. Ingresar C: 0.62
6. Seleccionar métodos Tc: Kirpich, Desbordes
7. Configurar análisis:
   - Tormenta: gz (6h pico adelantado)
   - Tr: 2, 10, 25
   - X: 1.0, 1.25

### Usando Línea de Comandos

```bash
# Crear sesión
hp session new "Cuenca Las Piedras" \
    --area 62 --slope 3.41 --length 800 \
    --p3_10 78 --c 0.62

# Calcular Tc
hp session tc <session_id> --method kirpich --method desbordes

# Ejecutar análisis
hp session analyze <session_id> \
    --storm gz --tr 2 --tr 10 --tr 25 \
    --x 1.0 --x 1.25

# Ver resultados
hp session show <session_id>
```

### Resultados Esperados

| Método Tc | Tr | X | Tc | tp | tb | Qp | Vol |
|-----------|-----|------|-----|-----|-----|------|------|
| Kirpich | 2 | 1.00 | 12 | 21 | 56 | 7.9 | 0.021 |
| Kirpich | 10 | 1.00 | 12 | 21 | 56 | 12 | 0.033 |
| Kirpich | 25 | 1.00 | 12 | 21 | 56 | 15 | 0.041 |
| Desbordes | 2 | 1.00 | 23 | 29 | 77 | 6.8 | 0.021 |
| Desbordes | 10 | 1.00 | 23 | 29 | 77 | 10 | 0.033 |
| Desbordes | 25 | 1.00 | 23 | 29 | 77 | 13 | 0.041 |

*Tiempos en min, Qp en m³/s, Vol en hm³*

---

## Ejemplo 2: Análisis con SCS-CN

### Descripción del Problema

**Cuenca Urbana**:
- Área: 45 ha
- Pendiente: 2.5%
- CN ponderado: 81
- Ubicación: Canelones (P₃,₁₀ = 80 mm)

### Usando el Wizard

```bash
hp wizard
```

En el paso de coeficientes:
1. Seleccionar "Solo CN (Método SCS)"
2. Opción de ingresar valor o calcular ponderado
3. Si se calcula ponderado:
   - Seleccionar grupo hidrológico de suelo (A, B, C, D)
   - Asignar coberturas al área

### Parámetros Avanzados SCS-CN

El wizard preguntará si desea configurar parámetros avanzados:

**AMC (Condición de Humedad Antecedente)**:
- I (Seco): Reduce el CN, menos escorrentía
- II (Promedio): Condición estándar
- III (Húmedo): Aumenta el CN, más escorrentía

**Lambda (λ)**:
- 0.20 (estándar): Ia = 0.2 × S
- 0.05 (urbano): Menor abstracción inicial

```
? Configurar parametros avanzados? (S/n): S

? Condicion de humedad antecedente (AMC):
> I  - Seco (CN menor, poca lluvia previa)
  II - Promedio (condicion normal)
  III - Humedo (CN mayor, lluvia previa reciente)

? Coeficiente Lambda para abstraccion inicial:
> 0.20 (valor tradicional)
  0.05 (areas urbanas, NRCS actualizado)
  Otro valor
```

### Ejemplo de Ajuste por AMC

CN base = 81

| AMC | CN Ajustado | Escorrentía (mm) para P=100mm |
|-----|-------------|-------------------------------|
| I (Seco) | 63 | 34.2 |
| II (Promedio) | 81 | 59.3 |
| III (Húmedo) | 91 | 76.8 |

---

## Ejemplo 3: Comparación de Metodologías

### Descripción

Comparar resultados usando ambas metodologías (Racional y SCS-CN) para la misma cuenca.

### Configuración

```
? Como deseas ingresar los coeficientes?
> Ambos (C y CN) - comparar metodologias
```

El wizard solicitará:
1. Coeficiente C (o cálculo ponderado)
2. Curva Número CN (o cálculo ponderado)

### Análisis Generado

Para cada método de Tc, se generan análisis con:
- Escorrentía por método Racional (usando C)
- Escorrentía por método SCS-CN (usando CN)

### Tabla Comparativa

```
============================================================
  COMPARACION DE METODOLOGIAS - Tr=10, Tormenta GZ
============================================================

  Método       | Tc  | tp  | tb  | P(mm)| Pe(mm)| Qp    | Vol
  -------------+-----+-----+-----+------+-------+-------+------
  Kirpich + C  |  12 |  21 |  56 | 106  |  65.7 | 10    | 0.033
  Kirpich + CN |  12 |  21 |  56 | 106  |  58.4 |  9.3  | 0.030
  Desbordes + C|  23 |  29 |  77 | 106  |  65.7 |  8.9  | 0.033
  Desbordes+CN |  23 |  29 |  77 | 106  |  58.4 |  7.9  | 0.030

  Tiempos en min, Qp en m³/s, Vol en hm³
============================================================
```

---

## Ejemplo 4: Parámetros Avanzados

### t₀ para Método de Desbordes

El tiempo de entrada (t₀) en la fórmula de Desbordes:

```
Tc = t₀ + 0.76 × A^0.25 × C^(-0.2) × S^(-0.38)
```

Valores típicos:
- **3 min**: Cuencas pequeñas, muy urbanizadas
- **5 min**: Valor por defecto (DINAGUA)
- **10 min**: Cuencas rurales con mayor tiempo de entrada

```
? Tiempo de entrada t0 para Desbordes:
> 3 min (urbano denso)
  5 min (valor por defecto)
  10 min (rural/suburbano)
  Otro valor
```

### Configuración Completa de Parámetros

```
============================================================
  PARAMETROS AVANZADOS CONFIGURADOS
============================================================
  AMC:              II (Promedio)
  Lambda (λ):       0.20
  t₀ Desbordes:     5.0 min
============================================================
```

---

## Exportación y Reportes

### Exportar a Excel

Desde el wizard:
```
? Que deseas hacer?
> Exportar (Excel/LaTeX)

? Formato de exportacion:
> Excel (.xlsx) - Tabla con todos los datos
  Reporte LaTeX (.tex) - Documento tecnico
  Ambos formatos
```

### Contenido del Excel

1. **Hoja "Cuenca"**: Datos de la cuenca
2. **Hoja "Tiempo Concentración"**: Resultados Tc con parámetros
3. **Hoja "Resumen Análisis"**: Tabla completa con:
   - ID, Método Tc, Tc (min)
   - Tormenta, Tr, Duración
   - P total, i pico
   - Escorrentía, Q pico, t pico, Volumen
   - C (si aplica), CN ajustado, AMC, λ (si aplica)
   - Factor X, Nota
4. **Hoja "Por Periodo Retorno"**: Tabla pivote
5. **Hoja "Notas"**: Notas de sesión y análisis

### Generar Reporte LaTeX

```bash
hp session report <session_id> --output memoria_tecnica --author "Ing. García"
```

Genera:
- `memoria_tecnica.tex`: Documento principal
- `graficos/`: Gráficos TikZ
- `memoria_tecnica.pdf`: PDF compilado (si LaTeX está instalado)

---

## Organización de Salidas

### Estructura de Directorios

Las salidas se organizan automáticamente en la carpeta `outputs/`:

```
outputs/
├── cuenca_las_piedras_20251205/
│   ├── cuenca_las_piedras.xlsx
│   ├── memoria.tex
│   ├── memoria.pdf
│   └── graficos/
│       ├── hidrogramas/
│       │   ├── hidrograma_tr2.pgf
│       │   ├── hidrograma_tr10.pgf
│       │   └── hidrograma_tr25.pgf
│       └── hietogramas/
│           ├── hietograma_tr2.pgf
│           ├── hietograma_tr10.pgf
│           └── hietograma_tr25.pgf
├── proyecto_sur_20251204/
│   └── ...
└── ...
```

### Configurar Directorio de Salida

En el wizard se puede especificar el directorio de salida:

```
? Directorio de salida (Enter para 'outputs/'): ./resultados
```

### Almacenamiento de Datos

HidroPluvial guarda todos los proyectos y cuencas en una base de datos local:

```
~/.hidropluvial/
└── hidropluvial.db    # Base de datos SQLite
```

**Ubicación en Windows:** `C:\Users\<tu_usuario>\.hidropluvial\`

La base de datos se crea automáticamente la primera vez que se usa la aplicación.

**Backup de datos:**
```bash
# Copiar la base de datos para hacer backup
copy "%USERPROFILE%\.hidropluvial\hidropluvial.db" backup_hidropluvial.db
```

---

## Referencia Rápida

### Valores P₃,₁₀ por Departamento

| Departamento | P₃,₁₀ (mm) |
|--------------|------------|
| Montevideo | 78 |
| Canelones | 80 |
| Maldonado | 85 |
| Colonia | 78 |
| San José | 80 |
| Flores | 85 |
| Florida | 85 |
| Lavalleja | 90 |
| Rocha | 90 |
| Treinta y Tres | 95 |
| Cerro Largo | 95 |
| Rivera | 95 |
| Artigas | 95 |
| Salto | 90 |
| Paysandú | 85 |
| Río Negro | 85 |
| Soriano | 80 |
| Durazno | 85 |
| Tacuarembó | 90 |

### Fórmulas de Tc

**Kirpich** (cuencas rurales):
```
Tc = 0.0195 × L^0.77 × S^(-0.385)
```
- L: longitud del cauce (m)
- S: pendiente del cauce (m/m)

**Temez**:
```
Tc = 0.3 × (L / S^0.25)^0.76
```
- L: longitud del cauce (km)
- S: pendiente del cauce (m/m)

**Desbordes** (cuencas urbanas):
```
Tc = t₀ + 0.76 × A^0.25 × C^(-0.2) × S^(-0.38)
```
- t₀: tiempo de entrada (min)
- A: área (ha)
- C: coeficiente de escorrentía
- S: pendiente (%)

### Comandos Útiles

```bash
# Iniciar wizard
hp wizard

# Ver sesiones guardadas
hp session list

# Ver detalles de sesión
hp session show <id>

# Exportar sesión
hp session export <id> --format xlsx

# Generar reporte
hp session report <id> --output memoria

# Ver valores P3,10 por departamento
hp idf departamentos

# Calcular intensidad IDF
hp idf uruguay <p3_10> <duracion> --tr <tr>

# Ayuda de cualquier comando
hp <comando> --help
```

---

---

## Gestión de Proyectos

### Continuar Proyecto Existente

Desde el wizard, selecciona "Continuar proyecto/cuenca existente":

```
? Selecciona un proyecto o cuenca:
> [Proyecto] abc123 - Estudio Drenaje Norte (3 cuencas, 45 analisis)
  [Proyecto] def456 - Ruta 5 km 120 (1 cuenca, 12 analisis)
  [Cuenca] ghi789 - Cuenca Antigua (8 analisis)  <-- Session legacy
  ← Volver al menu principal
```

### Opciones de Proyecto

Una vez seleccionado un proyecto:

```
? Que deseas hacer?
> Ver cuencas del proyecto
  Seleccionar cuenca para trabajar
  Agregar nueva cuenca al proyecto
  Editar metadatos del proyecto
  Eliminar proyecto
  ← Volver (elegir otro proyecto)
  ← Salir al menu principal
```

### Opciones de Cuenca

Una vez seleccionada una cuenca:

```
? Que deseas hacer?
> Ver tabla resumen
  Ver graficos (hietograma + hidrograma)
  Comparar hidrogramas
  Agregar mas analisis
  Filtrar resultados
  Exportar (Excel/LaTeX)
  Editar cuenca...
```

### Visor Interactivo de Gráficos

El visor interactivo muestra **hietograma e hidrograma combinados** en la misma pantalla, permitiendo ver la relación causa-efecto entre la lluvia y el caudal.

```
? Que deseas hacer?
> Ver graficos (hietograma + hidrograma)
```

**Navegación:**
- `←` / `→`: Cambiar entre análisis
- `↑` / `↓`: Ir al primero / último
- `q` / `ESC`: Salir del visor

**Características:**
- Hietograma en la parte superior con barras de intensidad
- Hidrograma en la parte inferior con curva de caudal
- Marca del caudal pico con ×
- Unidad de tiempo adaptativa:
  - Minutos si la tormenta dura < 2 horas
  - Horas si la tormenta dura ≥ 2 horas

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │           Hietograma - P=106.2mm, imax=54.3mm/h                     │
  │  60 ┤                                                                │
  │  40 ┤   ████                                                         │
  │  20 ┤███████████████                                                 │
  │   0 └────────────────────────────────────────────────────────(min)   │
  ├─────────────────────────────────────────────────────────────────────┤
  │           Hidrograma - Qp=12 m3/s, Tp=35min                         │
  │  12 ┤              ×                                                 │
  │   8 ┤            ╱   ╲                                               │
  │   4 ┤          ╱       ╲                                             │
  │   0 └────────────────────────────────────────────────Tiempo (h)     │
  └─────────────────────────────────────────────────────────────────────┘
  [1/12] Kirpich + GZ Tr10

  Cuenca: Las Piedras
  Tc=23min  tp=29min  X=1.00  tb=77min
  P=106.2mm  Pe=65.7mm  Vol=0.041hm3

  [<-] Anterior  [->] Siguiente  [q] Salir
```

### Submenú Editar Cuenca

Las opciones de edición están agrupadas:

```
? Editar cuenca 'Las Piedras':
> Editar datos (area, pendiente, C, CN)
  Editar notas
  Eliminar cuenca
  ← Volver
```

---

*Manual de Usuario - HidroPluvial v1.1*
