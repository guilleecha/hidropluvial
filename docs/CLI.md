# HidroPluvial - Documentación del CLI

**Guía completa de comandos de línea de comandos**

---

## Índice

1. [Instalación y Uso Básico](#instalación-y-uso-básico)
2. [Comandos Principales](#comandos-principales)
3. [Curvas IDF](#curvas-idf)
4. [Tormentas de Diseño](#tormentas-de-diseño)
5. [Tiempo de Concentración](#tiempo-de-concentración)
6. [Escorrentía](#escorrentía)
7. [Hidrogramas](#hidrogramas)
8. [Sistema de Sesiones](#sistema-de-sesiones)
9. [Reportes y Exportación](#reportes-y-exportación)
10. [Wizard Interactivo](#wizard-interactivo)

---

## Instalación y Uso Básico

### Ejecutar el CLI

```bash
# Forma completa
python -m hidropluvial <comando>

# Usando el alias (después de pip install -e .)
hp <comando>

# Ver ayuda general
hp --help

# Ver comandos disponibles
hp commands
```

### Estructura de Comandos

```
hp
├── idf          # Curvas Intensidad-Duración-Frecuencia
├── storm        # Tormentas de diseño
├── tc           # Tiempo de concentración
├── runoff       # Escorrentía
├── hydrograph   # Hidrogramas
├── session      # Sistema de sesiones
├── report       # Generación de reportes LaTeX
├── export       # Exportación de datos
├── wizard       # Asistente interactivo
└── commands     # Lista de comandos con ejemplos
```

---

## Curvas IDF

### `idf uruguay` - Método DINAGUA

Calcula intensidad usando las curvas IDF de Uruguay (DINAGUA).

```bash
hp idf uruguay <P3_10> <duracion> [--tr TR] [--area AREA]
```

**Parámetros:**
- `P3_10`: Precipitación de 3 horas y 10 años de retorno (mm)
- `duracion`: Duración de la tormenta (horas)
- `--tr`: Período de retorno (años). Default: 10
- `--area`: Área de la cuenca en km² para factor CA

**Ejemplo:**
```bash
# Montevideo, 3 horas, Tr=25 años
hp idf uruguay 78 3 --tr 25

# Con corrección por área de cuenca
hp idf uruguay 78 3 --tr 25 --area 50
```

**Salida:**
```
==================================================
  METODO DINAGUA URUGUAY
==================================================
  P3,10 base:              78.0 mm
  Periodo retorno:           25 años
  Duracion:                3.00 hr
==================================================
  Factor CT:             1.1781
  Factor CA:             1.0000
==================================================
  INTENSIDAD:            30.63 mm/hr
  PRECIPITACION:         91.90 mm
==================================================
```

### `idf tabla-uy` - Tabla IDF Completa

Genera una tabla IDF para todos los períodos de retorno y duraciones.

```bash
hp idf tabla-uy <P3_10> [-o ARCHIVO]
```

**Ejemplo:**
```bash
hp idf tabla-uy 78 -o tabla_montevideo.json
```

### `idf departamentos` - Valores P₃,₁₀

Muestra los valores de P₃,₁₀ por departamento de Uruguay.

```bash
hp idf departamentos
```

---

## Tormentas de Diseño

### `storm uruguay` - Bloques Alternantes DINAGUA

Genera un hietograma usando el método de bloques alternantes con IDF Uruguay.

```bash
hp storm uruguay <P3_10> <duracion> [--tr TR] [--dt DT]
```

**Parámetros:**
- `P3_10`: Precipitación base (mm)
- `duracion`: Duración total (horas)
- `--tr`: Período de retorno (años). Default: 10
- `--dt`: Intervalo de discretización (minutos). Default: 5

**Ejemplo:**
```bash
hp storm uruguay 78 3 --tr 25 --dt 5
```

### `storm gz` - Tormenta GZ (6 horas)

Genera una tormenta de 6 horas con pico adelantado (metodología DINAGUA).

```bash
hp storm gz <P3_10> [--tr TR] [--dt DT]
```

**Ejemplo:**
```bash
hp storm gz 83 --tr 10
```

### `storm bimodal-uy` - Tormenta Bimodal

Genera una tormenta de doble pico típica de Uruguay.

```bash
hp storm bimodal-uy <P3_10> [--tr TR] [--peak1 POS1] [--peak2 POS2]
```

**Ejemplo:**
```bash
hp storm bimodal-uy 83 --tr 10 --peak1 0.25 --peak2 0.75
```

### `storm blocks24` - Bloques 24 Horas

Genera una tormenta de 24 horas con pico centrado.

```bash
hp storm blocks24 <P3_10> [--tr TR]
```

---

## Tiempo de Concentración

### `tc kirpich` - Fórmula de Kirpich

```bash
hp tc kirpich <longitud_m> <pendiente>
```

**Parámetros:**
- `longitud_m`: Longitud del cauce principal (metros)
- `pendiente`: Pendiente media (m/m)

**Ejemplo:**
```bash
hp tc kirpich 2000 0.02
```

**Salida:**
```
==================================================
  TIEMPO DE CONCENTRACION - KIRPICH
==================================================
  Longitud:              2000.0 m
  Pendiente:              0.020 m/m
==================================================
  Tc:                    19.23 min (0.32 hr)
==================================================
```

### `tc temez` - Fórmula de Témez

```bash
hp tc temez <longitud_km> <pendiente>
```

### `tc desbordes` - Método de los Desbordes

Método recomendado por DINAGUA para áreas urbanas.

```bash
hp tc desbordes <area_ha> <pendiente_pct> <coef_c>
```

**Parámetros:**
- `area_ha`: Área de la cuenca (hectáreas)
- `pendiente_pct`: Pendiente media (%)
- `coef_c`: Coeficiente de escorrentía

**Ejemplo:**
```bash
hp tc desbordes 62 3.41 0.62
```

---

## Escorrentía

### `runoff cn` - Método SCS Curve Number

```bash
hp runoff cn <precipitacion> <CN> [--lambda LAMBDA] [--amc AMC]
```

**Parámetros:**
- `precipitacion`: Precipitación total (mm)
- `CN`: Número de curva (30-100)
- `--lambda`: Coeficiente de abstracción inicial. Default: 0.2
- `--amc`: Condición de humedad antecedente: I (seco), II (promedio), III (húmedo)

**Ejemplo:**
```bash
# Condición promedio
hp runoff cn 100 75

# Condición húmeda
hp runoff cn 100 75 --amc III
```

### `runoff rational` - Método Racional

```bash
hp runoff rational <C> <intensidad> <area_ha> [--tr TR]
```

**Ejemplo:**
```bash
hp runoff rational 0.6 50 10 --tr 25
```

### `runoff weighted-c` - C Ponderado Interactivo

Calcula un coeficiente C ponderado por área de forma interactiva.

```bash
hp runoff weighted-c [--area AREA] [--table TABLA] [--tr TR]
```

**Tablas disponibles:**
- `chow`: Ven Te Chow (C varía según Tr)
- `fhwa`: FHWA HEC-22 (C base con factor de ajuste)
- `uruguay`: Tabla regional simplificada

**Ejemplo:**
```bash
# Usando tabla de Ven Te Chow para Tr=25
hp runoff weighted-c --table chow --tr 25 --area 5.5

# Usando tabla FHWA
hp runoff weighted-c -t fhwa --tr 50 -a 10
```

### `runoff weighted-cn` - CN Ponderado Interactivo

Calcula una Curva Número ponderada por área de forma interactiva.

```bash
hp runoff weighted-cn [--area AREA] [--table TABLA] [--soil GRUPO]
```

**Tablas disponibles:**
- `urban`: Áreas urbanas (TR-55)
- `agricultural`: Áreas agrícolas

**Grupos hidrológicos:** A, B, C, D

**Ejemplo:**
```bash
hp runoff weighted-cn --table urban --soil B --area 50
```

### `runoff show-tables` - Ver Tablas de Coeficientes

```bash
hp runoff show-tables c    # Ver tablas de C
hp runoff show-tables cn   # Ver tablas de CN
```

---

## Hidrogramas

### `hydrograph scs` - Hidrograma SCS Completo

Genera un hidrograma usando el método SCS (triangular o curvilíneo).

```bash
hp hydrograph scs --area AREA --length L --slope S --p3_10 P --cn CN --tr TR
```

**Ejemplo:**
```bash
hp hydrograph scs --area 1 --length 1000 --slope 0.02 --p3_10 83 --cn 81 --tr 25
```

### `hydrograph gz` - Hidrograma GZ (Uruguay)

Genera un hidrograma usando la metodología GZ de drenaje urbano.

```bash
hp hydrograph gz --area AREA --slope S --c C --p3_10 P --tr TR --x X
```

**Parámetros:**
- `--area`: Área de la cuenca (hectáreas)
- `--slope`: Pendiente media (%)
- `--c`: Coeficiente de escorrentía
- `--p3_10`: Precipitación P₃,₁₀ (mm)
- `--tr`: Período de retorno (años)
- `--x`: Factor de forma del hidrograma

**Valores de X recomendados:**

| Factor X | Uso típico |
|----------|------------|
| 1.00 | Áreas urbanas internas |
| 1.25 | Áreas urbanas (gran pendiente) |
| 1.67 | Método SCS/NRCS estándar |
| 2.25 | Uso mixto rural/urbano |

**Ejemplo:**
```bash
hp hydrograph gz --area 62 --slope 3.41 --c 0.62 --p3_10 83 --tr 2 --x 1.0
```

---

## Sistema de Sesiones

El sistema de sesiones permite gestionar análisis hidrológicos completos con múltiples combinaciones de parámetros.

### `session create` - Crear Sesión

```bash
hp session create <nombre> --area A --slope S --p3_10 P --c C [--cn CN] [--length L]
```

**Ejemplo:**
```bash
hp session create "Cuenca Norte" --area 62 --slope 3.41 --p3_10 83 --c 0.62 --length 800
```

### `session list` - Listar Sesiones

```bash
hp session list
```

### `session show` - Ver Sesión

```bash
hp session show <id>
```

### `session tc` - Calcular Tc

Calcula el tiempo de concentración con múltiples métodos.

```bash
hp session tc <id> --methods "kirpich,desbordes"
```

### `session analyze` - Ejecutar Análisis

```bash
hp session analyze <id> --tc METODO --storm TIPO --tr TR [--x X]
```

**Ejemplo:**
```bash
hp session analyze abc123 --tc desbordes --storm gz --tr 10 --x 1.0
```

### `session summary` - Ver Resumen

Muestra una tabla comparativa de todos los análisis.

```bash
hp session summary <id>
```

### `session preview` - Visualización Terminal

Muestra gráficos ASCII/plotext de hidrogramas y hietogramas.

```bash
hp session preview <id> [--idx N] [--compare] [--hyeto] [--tr TR] [--x X] [--tc TC] [--storm TIPO]
```

**Opciones:**
- `--idx N`: Ver análisis específico por índice
- `--compare`: Superponer todos los hidrogramas
- `--hyeto`: Mostrar hietograma en vez de hidrograma
- `--tr, --x, --tc, --storm`: Filtros para análisis

**Ejemplos:**
```bash
# Tabla con sparklines
hp session preview abc123

# Comparar todos los hidrogramas
hp session preview abc123 --compare

# Ver hidrograma #0
hp session preview abc123 -i 0

# Ver hietograma #0
hp session preview abc123 -i 0 --hyeto

# Filtrar por Tr=10
hp session preview abc123 --tr 10

# Filtro combinado
hp session preview abc123 --tc desbordes --tr 10
```

### `session batch` - Análisis por Lotes

Ejecuta múltiples análisis desde un archivo YAML.

```bash
hp session batch <archivo.yaml>
```

**Formato del archivo YAML:**
```yaml
session:
  name: "Proyecto Drenaje Sur"
  cuenca:
    nombre: "Arroyo Las Piedras"
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

### `session report` - Generar Reporte

Genera un reporte LaTeX con todos los análisis.

```bash
hp session report <id> -o nombre_archivo --author "Ing. García" [--template DIR]
```

### `session delete` - Eliminar Sesión

```bash
hp session delete <id> [--force]
```

---

## Reportes y Exportación

### `report idf` - Reporte IDF

```bash
hp report idf <P3_10> -o archivo.tex --author "Autor"
```

### `report storm` - Reporte de Tormenta

```bash
hp report storm <P3_10> <duracion> --tr TR -o archivo.tex
```

### `export idf-csv` - Exportar IDF a CSV

```bash
hp export idf-csv <P3_10> -o tabla.csv
```

### `export storm-csv` - Exportar Hietograma a CSV

```bash
hp export storm-csv <P3_10> <duracion> --tr TR -o hietograma.csv
```

### `export storm-tikz` - Exportar Figura TikZ

```bash
hp export storm-tikz <P3_10> <duracion> --tr TR -o figura.tex
```

---

## Wizard Interactivo

El wizard proporciona una interfaz guiada paso a paso para realizar análisis completos.

```bash
hp wizard
```

### Flujo del Wizard

1. **Definir Cuenca**: Nombre, área, pendiente, P₃,₁₀
2. **Calcular C y/o CN**:
   - Ingresar directamente
   - Calcular C ponderado (Ven Te Chow, FHWA, Uruguay)
   - Calcular CN ponderado (Urbano, Agrícola)
3. **Calcular Tc**: Selección de métodos (Kirpich, Desbordes, Témez)
4. **Configurar Análisis**: Tipo de tormenta, períodos de retorno, factores X
5. **Ejecutar Análisis**: Genera hidrogramas para todas las combinaciones
6. **Menú Post-Ejecución**:
   - Ver resumen (tabla comparativa)
   - Ver gráficos en terminal
   - Agregar más análisis
   - Filtrar resultados
   - Generar reporte LaTeX
   - Guardar y salir

### Características del Wizard

- Validación de datos en tiempo real
- Cálculo automático de C y CN ponderados
- Análisis en matriz (múltiples Tr × múltiples X × múltiples Tc)
- Visualización de hidrogramas con sparklines
- Comparación de hidrogramas superpuestos
- Filtrado de resultados por criterios

---

## Flujo de Trabajo Típico

### Opción 1: CLI Directo

```bash
# 1. Crear sesión
hp session create "Mi Cuenca" --area 50 --slope 2.5 --p3_10 80 --c 0.55

# 2. Calcular Tc
hp session tc abc123 --methods "kirpich,desbordes"

# 3. Ejecutar análisis
hp session analyze abc123 --tc desbordes --storm gz --tr 2 --x 1.0
hp session analyze abc123 --tc desbordes --storm gz --tr 10 --x 1.0
hp session analyze abc123 --tc desbordes --storm gz --tr 25 --x 1.25

# 4. Ver resumen
hp session summary abc123

# 5. Ver gráficos
hp session preview abc123 --compare

# 6. Generar reporte
hp session report abc123 -o memoria_calculo --author "Ing. García"
```

### Opción 2: Wizard Interactivo

```bash
hp wizard
# Seguir las instrucciones paso a paso
```

### Opción 3: Batch desde YAML

```bash
# Crear archivo de configuración y ejecutar
hp session batch mi_proyecto.yaml
hp session report <id_generado> -o reporte --author "Ing. García"
```

---

## Valores de Referencia

### P₃,₁₀ por Departamento (Uruguay)

| Departamento | P₃,₁₀ (mm) | Departamento | P₃,₁₀ (mm) |
|--------------|------------|--------------|------------|
| Artigas | 95 | Maldonado | 83 |
| Canelones | 80 | Montevideo | 78 |
| Cerro Largo | 95 | Paysandú | 90 |
| Colonia | 78 | Río Negro | 88 |
| Durazno | 88 | Rivera | 95 |
| Flores | 85 | Rocha | 85 |
| Florida | 85 | Salto | 92 |
| Lavalleja | 85 | San José | 80 |
| | | Soriano | 85 |
| | | Tacuarembó | 92 |
| | | Treinta y Tres | 90 |

### Valores Típicos de CN

| Cobertura | Grupo B | Grupo C |
|-----------|---------|---------|
| Zonas comerciales | 92 | 94 |
| Residencial 1/4 acre | 75 | 83 |
| Parques, jardines | 61 | 74 |
| Calles pavimentadas | 98 | 98 |
| Pastura (buena) | 61 | 74 |

### Valores Típicos de C

| Cobertura | C (Tr=10) |
|-----------|-----------|
| Centro comercial | 0.80-0.90 |
| Residencial denso | 0.60-0.75 |
| Residencial suburbano | 0.35-0.50 |
| Parques, jardines | 0.15-0.25 |
| Asfalto | 0.80-0.95 |

---

## Solución de Problemas

### Error: "Sesión no encontrada"

Las sesiones se identifican por los primeros 8 caracteres del ID. Verificar con:
```bash
hp session list
```

### Error: "Área restante por asignar"

En el cálculo de C/CN ponderado, asegurar que la suma de áreas asignadas sea igual al área total.

### Gráficos no se muestran

Verificar que `plotext` esté instalado:
```bash
pip install plotext
```

### Reporte LaTeX no compila

Verificar que las dependencias LaTeX estén instaladas:
- pdflatex
- Paquetes: tikz, pgfplots, booktabs, siunitx

---

*Documentación generada para HidroPluvial v1.0*
