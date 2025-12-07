# HidroPluvial

**Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-826%20passed-green.svg)]()

---

## Características

- **Curvas IDF** - Método DINAGUA Uruguay con factores CT y CA
- **Hietogramas** - Bloques alternantes (GZ), Chicago, SCS Tipo I/II/III, Huff, Bimodal
- **Tiempo de concentración** - Kirpich, Témez, Desbordes (DINAGUA)
- **Escorrentía** - SCS Curve Number (con AMC y λ configurable), Método Racional
- **Hidrogramas** - SCS triangular/curvilíneo, Triangular con factor X
- **Visor interactivo** - Hietograma + hidrograma combinados con navegación por teclado
- **Gestión de Proyectos** - Organización jerárquica Proyecto → Cuencas → Análisis
- **Reportes LaTeX** - Memorias de cálculo con gráficos TikZ/PGFPlots
- **Exportación** - Excel, CSV, fichas técnicas PDF

---

## Instalación Rápida

```bash
git clone https://github.com/guilleecha/hidropluvial.git
cd hidropluvial
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
hp --help
```

> Ver [docs/INSTALACION.md](docs/INSTALACION.md) para guía completa incluyendo LaTeX.

---

## Uso

### Wizard Interactivo

La forma principal de usar HidroPluvial es a través del wizard:

```bash
hp wizard
```

```
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Análisis                |
|         Cálculos hidrológicos para Uruguay                  |
+-------------------------------------------------------------+

? Qué deseas hacer?
> 1. Nueva cuenca (análisis guiado)
  2. Crear nuevo proyecto
  3. Continuar proyecto/cuenca existente
  4. Gestionar proyectos y cuencas
  5. Ver comandos disponibles
  6. Salir
```

### Flujo de Trabajo Típico

1. **Iniciar wizard** → `hp wizard`
2. **Seleccionar "Nueva cuenca"** → Ingresa datos de la cuenca
3. **Configurar coeficientes** → C ponderado y/o CN por cobertura
4. **Seleccionar métodos Tc** → Kirpich, Desbordes, Témez
5. **Definir análisis** → Tipo de tormenta, períodos de retorno, factor X
6. **Ver resultados** → Tabla resumen, gráficos interactivos
7. **Exportar** → Excel y/o reporte LaTeX

### Ejemplo: Cuenca Urbana

```
Datos de entrada:
  - Área: 62 ha
  - Pendiente: 3.41%
  - P₃,₁₀: 78 mm (Montevideo)
  - Coeficiente C: 0.62

Configuración:
  - Métodos Tc: Kirpich, Desbordes
  - Tormenta: GZ (6h pico adelantado)
  - Períodos de retorno: 2, 10, 25 años
  - Factor X: 1.0, 1.25

Resultados:
  - Tc: 12-23 min según método
  - Qp: 7-15 m³/s según Tr
  - Volumen: 0.02-0.04 hm³
```

### Visor de Gráficos

El visor interactivo muestra hietograma e hidrograma combinados:

```
┌─────────────────────────────────────────────────────────────┐
│           Hietograma - P=106mm, imax=54mm/h                 │
│  60 ┤   ████                                                │
│  20 ┤███████████████                                        │
├─────────────────────────────────────────────────────────────┤
│           Hidrograma - Qp=12 m³/s, Tp=35min                 │
│  12 ┤          ×                                            │
│   4 ┤        ╱   ╲                                          │
└─────────────────────────────────────────────────────────────┘
[1/12] Kirpich + GZ Tr10

[←] Anterior  [→] Siguiente  [q] Salir
```

---

## Estructura de Proyectos

HidroPluvial organiza el trabajo jerárquicamente:

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

Los datos se almacenan en `~/.hidropluvial/hidropluvial.db` (SQLite).

---

## Parámetros Configurables

| Parámetro | Descripción | Valores |
|-----------|-------------|---------|
| **AMC** | Condición de humedad antecedente | I (seco), II (promedio), III (húmedo) |
| **Lambda (λ)** | Coeficiente abstracción inicial | 0.20 (estándar), 0.05 (urbano) |
| **t₀** | Tiempo entrada Desbordes | 3, 5, 10 min |
| **Factor X** | Forma del hidrograma | 1.0 (racional) a 12.0 (rural) |

---

## Valores P₃,₁₀ por Departamento

| Departamento | P₃,₁₀ (mm) | Departamento | P₃,₁₀ (mm) |
|--------------|------------|--------------|------------|
| Montevideo | 78 | Canelones | 80 |
| Maldonado | 83 | Colonia | 78 |
| San José | 80 | Florida | 85 |
| Lavalleja | 85 | Rocha | 85 |
| Durazno | 88 | Flores | 85 |
| Paysandú | 90 | Salto | 92 |
| Tacuarembó | 92 | Rivera | 95 |
| Artigas | 95 | Cerro Largo | 95 |

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Manual práctico con ejemplos paso a paso |
| [INSTALACION.md](docs/INSTALACION.md) | Guía completa de instalación |
| [COEFICIENTES.md](docs/COEFICIENTES.md) | Tablas de coeficientes C y CN |
| [METODOLOGIAS.md](docs/METODOLOGIAS.md) | Fundamentos teóricos |

### Documentación Técnica

| Documento | Contenido |
|-----------|-----------|
| [metodologias/idf.md](docs/metodologias/idf.md) | Curvas IDF DINAGUA |
| [metodologias/tc.md](docs/metodologias/tc.md) | Tiempo de concentración |
| [metodologias/storms.md](docs/metodologias/storms.md) | Tormentas de diseño |
| [metodologias/runoff.md](docs/metodologias/runoff.md) | Escorrentía SCS-CN |
| [metodologias/hydrograph.md](docs/metodologias/hydrograph.md) | Hidrogramas |

---

## Comandos CLI

Para usuarios avanzados, también están disponibles comandos directos:

```bash
# Consultas IDF
hp idf departamentos              # Ver P₃,₁₀ por departamento
hp idf uruguay 78 3 --tr 25       # Calcular intensidad

# Tiempo de concentración
hp tc kirpich 800 0.0341          # Kirpich (L en m, S decimal)
hp tc desbordes 62 3.41 0.62      # Desbordes (A ha, S%, C)

# Escorrentía
hp runoff cn 100 81               # Escorrentía SCS-CN
hp runoff cn-table --group B      # Ver tabla CN

# Gestión de proyectos
hp project list                   # Listar proyectos
hp project show <id>              # Ver proyecto
hp project basin-add <id> "Nombre" --area 50 --slope 2.5 --p310 80
hp project basin-list <id>        # Ver cuencas
hp project basin-show <pid> <bid> # Ver cuenca específica
```

> **Nota**: El wizard (`hp wizard`) es la forma recomendada de trabajar.

---

## Tests

```bash
pytest tests/ -v
```

Estado: **826 tests pasando**

---

## Licencia

MIT License - Ver [LICENSE](LICENSE)

---

## Referencias

- Rodríguez Fontal (1980) - Curvas IDF Uruguay
- DINAGUA/MTOP - Manual de Drenaje Pluvial Urbano
- SCS TR-55 - Urban Hydrology for Small Watersheds
- Chow, Maidment & Mays (1988) - Applied Hydrology
