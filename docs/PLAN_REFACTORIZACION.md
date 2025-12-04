# Plan de Refactorización - HidroPluvial

## Objetivo
Refactorizar el código para que ningún archivo supere 500 líneas, priorizando el uso de clases y siguiendo mejores prácticas de Python.

## Estado Actual

### Fase 1: CLI ✅ COMPLETADA

| Archivo Original | Líneas | Estado |
|-----------------|--------|--------|
| `cli.py` | 2,371 | ✅ Refactorizado |

#### Estructura Resultante

```
src/hidropluvial/cli/
├── __init__.py          (66 líneas)   ✅
├── formatters.py        (84 líneas)   ✅
├── idf.py               (181 líneas)  ✅
├── storm.py             (284 líneas)  ✅
├── tc.py                (60 líneas)   ✅
├── runoff.py            (521 líneas)  ⚠️ (creció por weighted-cn)
├── hydrograph.py        (265 líneas)  ✅
├── report.py            (203 líneas)  ✅
├── export.py            (93 líneas)   ✅
├── session/
│   ├── __init__.py      (39 líneas)   ✅
│   ├── base.py          (430 líneas)  ✅
│   ├── analyze.py       (168 líneas)  ✅
│   ├── batch.py         (232 líneas)  ✅
│   ├── preview.py       (165 líneas)  ✅
│   └── report.py        (485 líneas)  ✅
└── wizard/
    ├── __init__.py      (8 líneas)    ✅
    ├── main.py          (63 líneas)   ✅
    ├── menus.py         (700 líneas)  ⚠️ Considerar dividir
    └── runner.py        (320 líneas)  ✅
```

**Resultado**: Tests: 142/142 pasando. Archivos grandes a revisar: runoff.py (521), menus.py (~700).

---

### Pendientes: Fases 2-4

| Archivo | Líneas | Estado |
|---------|--------|--------|
| `core/temporal.py` | 769 | Pendiente |
| `core/hydrograph.py` | 682 | Pendiente |
| `core/idf.py` | 589 | Pendiente |
| `core/tc.py` | 483 | OK |
| `reports/charts.py` | 440 | OK |
| `reports/generator.py` | 405 | OK |
| `core/runoff.py` | 382 | OK |
| `session.py` | 326 | OK |
| `config.py` | 235 | OK |

---

## Fase 2: Refactorizar Core Modules (Pendiente)

### 2.1 IDF (589 → ~200 líneas por archivo)

```
core/idf/
├── __init__.py              # Re-exporta funciones principales
├── dinagua.py               # Métodos Uruguay/DINAGUA (~200 líneas)
├── methods.py               # Métodos internacionales (~250 líneas)
└── models.py                # Dataclasses (~50 líneas)
```

### 2.2 Temporal (769 → ~130 líneas por archivo)

```
core/temporal/
├── __init__.py
├── base.py                  # Utilidades compartidas (~80 líneas)
├── alternating_blocks.py    # Bloques alternantes (~120 líneas)
├── chicago.py               # Tormenta Chicago (~100 líneas)
├── scs.py                   # Distribución SCS (~100 líneas)
├── bimodal.py               # Tormentas bimodales (~150 líneas)
└── gz.py                    # Metodología GZ (~150 líneas)
```

### 2.3 Hydrograph (682 → ~130 líneas por archivo)

```
core/hydrograph/
├── __init__.py
├── parameters.py            # Parámetros Tc, Tp, Tb (~80 líneas)
├── scs.py                   # HU triangular y curvilíneo SCS (~150 líneas)
├── synthetic.py             # Snyder, Clark, Gamma (~180 líneas)
├── triangular_x.py          # HU triangular con factor X (~100 líneas)
└── convolution.py           # Convolución (~80 líneas)
```

---

## Fase 3: Refactorizar Reports (Pendiente)

```
reports/charts/
├── __init__.py
├── models.py                # HydrographSeries, HyetographData (~30 líneas)
├── formatters.py            # Funciones de formato tiempo/coords (~100 líneas)
├── hydrograph.py            # Generación TikZ hidrogramas (~150 líneas)
└── hyetograph.py            # Generación TikZ hietogramas (~120 líneas)
```

---

## Fase 4: Introducir Clases de Dominio (Pendiente)

### 4.1 Clase HydrographPipeline

Encapsula el flujo completo de cálculo hidrológico.

**Ubicación:** `session/pipeline.py`

### 4.2 Clase ReportBuilder

Construye reportes LaTeX de forma modular.

**Ubicación:** `reports/builder.py`

---

## Métricas de Éxito

| Métrica | Antes | Fase 1 | Meta Final |
|---------|-------|--------|------------|
| Archivo más grande | 2,371 líneas | 485 líneas | <500 líneas ✅ |
| Promedio por archivo | 627 líneas | ~170 líneas | <200 líneas |
| Archivos con clases | 2 | 3 | 8+ |

---

## Notas

1. **Fase 1 completada**: CLI refactorizada con éxito
2. **Tests**: Todos los 98 tests pasan sin modificación
3. **Compatibilidad**: Comandos CLI funcionan igual que antes
4. **Fichas técnicas**: Implementadas en reportes de sesión
