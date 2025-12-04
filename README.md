# HidroPluvial

Herramienta Python para cálculos hidrológicos con soporte para metodología DINAGUA Uruguay y generación de reportes LaTeX.

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/guilleecha/hidropluvial.git
cd hidropluvial

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar en modo desarrollo
pip install -e .
```

## Uso CLI

```bash
# Ver ayuda
python -m hidropluvial --help

# Calcular intensidad IDF Uruguay (Montevideo, Tr=25 años, 3 horas)
python -m hidropluvial idf uruguay 78 3 --tr 25

# Generar tabla IDF completa
python -m hidropluvial idf tabla-uy 78

# Ver valores P3,10 por departamento
python -m hidropluvial idf departamentos

# Generar hietograma DINAGUA
python -m hidropluvial storm uruguay 78 3 --tr 25 --dt 5
```

## Uso como Librería

```python
from hidropluvial.core.temporal import alternating_blocks_dinagua
from hidropluvial.reports import hyetograph_result_to_tikz

# Generar hietograma
hietograma = alternating_blocks_dinagua(p3_10=78, return_period_yr=25, duration_hr=6, dt_min=5)

# Exportar a LaTeX/TikZ
tikz = hyetograph_result_to_tikz(hietograma, caption='Hietograma Tr=25 años')
```

## Módulos

| Módulo | Descripción |
|--------|-------------|
| **core/idf** | Curvas IDF (DINAGUA Uruguay, Sherman, Bernard) |
| **core/temporal** | Distribuciones temporales (Bloques Alternantes, Chicago, SCS, Huff) |
| **core/tc** | Tiempo de concentración (Kirpich, NRCS, Témez, California) |
| **core/runoff** | Escorrentía (SCS-CN, Método Racional) |
| **core/hydrograph** | Hidrogramas unitarios (SCS, Snyder, Clark) |
| **reports/charts** | Generación de gráficos TikZ/PGFPlots para LaTeX |

## Documentación

- [Especificación técnica](docs/SPEC.md)
- [Guía de desarrollo](docs/DESARROLLO.md)
- [Guía de gráficos TikZ](docs/guia_graficos.md)

## Tests

```bash
pytest tests/ -v
```

## Licencia

MIT
