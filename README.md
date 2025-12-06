# HidroPluvial

**Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-793%20passed-green.svg)]()

---

## Características

- **Curvas IDF** - Método DINAGUA Uruguay con factores CT y CA
- **Hietogramas** - Bloques alternantes (GZ), Chicago, SCS Tipo I/II/III, Huff, Bimodal
- **Tiempo de concentración** - Kirpich, Témez, Desbordes (DINAGUA)
- **Escorrentía** - SCS Curve Number (con AMC y λ configurable), Método Racional
- **Hidrogramas** - SCS triangular/curvilíneo, Triangular con factor X
- **Visor interactivo** - Hietograma + hidrograma combinados con navegación por teclado
- **Gestión de Proyectos y Cuencas** - Organización jerárquica para estudios complejos
- **Reportes LaTeX** - Memorias de cálculo con gráficos TikZ/PGFPlots
- **Exportación** - Excel, CSV, fichas técnicas PDF

---

## Instalación Rápida

```bash
# Clonar repositorio
git clone https://github.com/guilleecha/hidropluvial.git
cd hidropluvial

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Instalar
pip install -e .

# Verificar instalación
hp --help
```

> Para instalación completa (incluyendo LaTeX), ver [docs/INSTALACION.md](docs/INSTALACION.md)

---

## Inicio Rápido

### Wizard Interactivo (Recomendado)

```bash
hp wizard
```

El wizard guía paso a paso para:
1. Definir datos de la cuenca (área, pendiente, P₃,₁₀)
2. Calcular C y/o CN ponderados por cobertura
3. Seleccionar métodos de Tc (Kirpich, Desbordes, etc.)
4. Configurar parámetros avanzados (AMC, Lambda, t₀)
5. Ejecutar análisis (tormentas, Tr, factor X)
6. Exportar a Excel y/o generar reportes LaTeX

### Menú Principal del Wizard

```
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Analisis                |
|         Calculos hidrologicos para Uruguay                  |
+-------------------------------------------------------------+

? Que deseas hacer?
> 1. Nueva cuenca (analisis guiado)
  2. Crear nuevo proyecto
  3. Continuar proyecto/cuenca existente
  4. Gestionar proyectos y cuencas
  5. Ver comandos disponibles
  6. Salir
```

### Ejemplo de Flujo Completo

```bash
# 1. Iniciar wizard
hp wizard

# 2. Seleccionar "Nueva cuenca (analisis guiado)"
# 3. Ingresar datos:
#    - Nombre: Cuenca Las Piedras
#    - Área: 62 ha
#    - Pendiente: 3.41%
#    - P3,10: 78 mm
#    - Coeficiente C: 0.62
# 4. Seleccionar métodos Tc: Kirpich, Desbordes
# 5. Configurar análisis:
#    - Tormenta: GZ (6h pico adelantado)
#    - Tr: 2, 10, 25 años
#    - Factor X: 1.0, 1.25
# 6. Ver resultados y exportar
```

---

## Comandos CLI

### Consultas IDF

```bash
# Intensidad para Montevideo, 3 horas, Tr=25 años
hp idf uruguay 78 3 --tr 25

# Ver P3,10 por departamento
hp idf departamentos
```

### Gestión de Proyectos

```bash
# Crear proyecto
hp project create "Drenaje Barrio Norte" --desc "Estudio pluvial 2024"

# Listar proyectos
hp project list

# Ver detalles de un proyecto
hp project show <project_id>

# Agregar cuenca a proyecto
hp project basin-add <project_id> "Cuenca A" --area 50 --slope 2.5 --p310 83

# Listar cuencas de un proyecto
hp project basin-list <project_id>

# Ver detalles de una cuenca
hp project basin-show <project_id> <basin_id>
```

### Tiempo de Concentración

```bash
# Método Kirpich (longitud en m, pendiente decimal)
hp tc kirpich 800 0.0341

# Método Desbordes (área ha, pendiente %, C)
hp tc desbordes 62 3.41 0.62

# Método Témez (longitud km, pendiente decimal)
hp tc temez 0.8 0.0341
```

### Escorrentía

```bash
# SCS Curve Number
hp runoff cn 100 81 --amc II --lambda 0.2

# Ver tablas de CN
hp runoff cn-table --group B
```

### Exportación y Reportes

```bash
# Exportar cuenca a Excel (usa session para compatibilidad)
hp session export <id> --format xlsx

# Generar reporte LaTeX
hp session report <id> --output memoria --author "Ing. García"
```

> **Nota**: Los comandos `hp session` operan sobre cuencas individuales y son compatibles con el sistema de proyectos. El wizard es la forma recomendada de trabajar.

---

## Estructura de Datos

HidroPluvial organiza el trabajo en:

```
Proyecto (estudio)
├── Cuenca A
│   ├── Análisis Tr=10, X=1.0
│   ├── Análisis Tr=10, X=1.25
│   └── Análisis Tr=25, X=1.0
├── Cuenca B
│   └── ...
└── Metadatos (autor, ubicación, notas)
```

- **Proyecto**: Agrupa cuencas de un mismo estudio (ej: "Drenaje Pluvial Barrio X")
- **Cuenca (Basin)**: Área física con sus parámetros hidrológicos
- **Análisis**: Combinación específica de Tc, tormenta, Tr y método de escorrentía

---

## Parámetros Avanzados

El wizard permite configurar:

| Parámetro | Descripción | Valores |
|-----------|-------------|---------|
| **AMC** | Condición de humedad antecedente | I (seco), II (promedio), III (húmedo) |
| **Lambda (λ)** | Coeficiente abstracción inicial | 0.20 (estándar), 0.05 (urbano) |
| **t₀** | Tiempo entrada Desbordes | 3, 5, 10 min |
| **Factor X** | Forma del hidrograma triangular | 1.0 (racional) a 12.0 (rural) |

---

## Documentación

### Guías de Usuario

| Documento | Descripción |
|-----------|-------------|
| [INSTALACION.md](docs/INSTALACION.md) | Guía completa de instalación |
| [MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Manual práctico con ejemplos |
| [COEFICIENTES.md](docs/COEFICIENTES.md) | Tablas de coeficientes C y CN |

### Referencias Metodológicas

Documentación técnica con teoría, fórmulas y extractos de código:

| Documento | Contenido |
|-----------|-----------|
| [metodologias/idf.md](docs/metodologias/idf.md) | Curvas IDF: DINAGUA Uruguay, Sherman, Bernard |
| [metodologias/tc.md](docs/metodologias/tc.md) | Tiempo de concentración: Kirpich, Témez, Desbordes |
| [metodologias/storms.md](docs/metodologias/storms.md) | Tormentas de diseño: Bloques alternantes, Chicago, SCS, Huff |
| [metodologias/runoff.md](docs/metodologias/runoff.md) | Escorrentía: SCS Curve Number, Método Racional |
| [metodologias/hydrograph.md](docs/metodologias/hydrograph.md) | Hidrogramas: SCS triangular/curvilíneo, Snyder, Clark |

### Documentación Interna

| Documento | Descripción |
|-----------|-------------|
| [internal/SPEC.md](docs/internal/SPEC.md) | Especificación técnica del proyecto |
| [internal/DESARROLLO.md](docs/internal/DESARROLLO.md) | Estado del desarrollo |
| [internal/guia_graficos.md](docs/internal/guia_graficos.md) | Generación de gráficos TikZ |

---

## Valores P₃,₁₀ por Departamento (Uruguay)

| Departamento | P₃,₁₀ (mm) | Departamento | P₃,₁₀ (mm) |
|--------------|------------|--------------|------------|
| Montevideo | 78 | Canelones | 80 |
| Maldonado | 83 | Colonia | 78 |
| San José | 80 | Florida | 85 |
| Lavalleja | 85 | Rocha | 85 |
| Durazno | 88 | Flores | 85 |
| Río Negro | 88 | Soriano | 85 |
| Paysandú | 90 | Salto | 92 |
| Tacuarembó | 92 | Rivera | 95 |
| Artigas | 95 | Cerro Largo | 95 |
| Treinta y Tres | 90 | | |

---

## Tests

```bash
pytest tests/ -v
```

**Estado:** 793 tests pasando

---

## Licencia

MIT License - Ver [LICENSE](LICENSE)

---

## Referencias

- Rodríguez Fontal (1980) - Curvas IDF Uruguay
- DINAGUA/MTOP - Manual de Drenaje Pluvial Urbano
- SCS TR-55 - Urban Hydrology for Small Watersheds
- Chow, Maidment & Mays (1988) - Applied Hydrology
