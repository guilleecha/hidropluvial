# HidroPluvial - Metodologías Implementadas

**Índice de la documentación técnica de métodos hidrológicos**

---

## Documentación Detallada

La documentación completa de cada módulo se encuentra en la carpeta [`metodologias/`](metodologias/):

| Documento | Módulo | Descripción |
|-----------|--------|-------------|
| [idf.md](metodologias/idf.md) | `core.idf` | Curvas Intensidad-Duración-Frecuencia (DINAGUA, Sherman, Bernard) |
| [tc.md](metodologias/tc.md) | `core.tc` | Tiempo de Concentración (Kirpich, Témez, Desbordes, NRCS) |
| [storms.md](metodologias/storms.md) | `core.temporal` | Tormentas de Diseño (Bloques Alternantes, Chicago, SCS, Huff, Bimodal) |
| [runoff.md](metodologias/runoff.md) | `core.runoff` | Escorrentía (SCS Curve Number, Método Racional, verificación fc) |
| [hydrograph.md](metodologias/hydrograph.md) | `core.hydrograph` | Hidrogramas Unitarios (SCS triangular/curvilíneo, Snyder, Clark) |

Cada documento incluye:
- Contexto teórico y origen del método
- Fórmulas matemáticas con notación clara
- Extractos de código con referencias a líneas
- Ejemplos de uso funcionales
- Referencias bibliográficas

---

## Resumen de Métodos

### Curvas IDF
Cálculo de intensidades de precipitación para diferentes duraciones y períodos de retorno.
El método principal es **DINAGUA Uruguay**, basado en P₃,₁₀.

### Tormentas de Diseño
Distribución temporal de la precipitación:
- **Bloques Alternantes** - Método universal con pico configurable
- **GZ** - Variante uruguaya con pico adelantado (6 horas)
- **Bimodal** - Tormentas con doble pico (sistemas frontales)
- **SCS Tipo I-III** - Distribuciones de 24 horas del NRCS

### Tiempo de Concentración
- **Kirpich** - Cuencas rurales pequeñas
- **Témez** - Amplio uso en Latinoamérica
- **Desbordes (DINAGUA)** - Cuencas urbanas uruguayas
- **NRCS** - Método de velocidades por segmentos

### Escorrentía
- **SCS Curve Number** - Precipitación efectiva según tipo de suelo y uso
- **Método Racional** - Caudal pico para cuencas pequeñas
- **Verificación fc** - Tasa mínima de infiltración (HHA-FING UdelaR)

### Hidrogramas
- **SCS Triangular** - Hidrograma unitario simplificado
- **SCS Curvilíneo** - Forma más realista
- **Convolución** - Generación del hidrograma de crecida

---

## Referencias Principales

### Normativa Uruguay
- DINAGUA. "Curvas Intensidad-Duración-Frecuencia para Uruguay". MVOTMA.
- DINAGUA. "Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas".
- HHA-FING UdelaR. "Guía Metodológica: Hidrología e Hidráulica Aplicada" (2019).

### Literatura Técnica
- Chow, V.T., Maidment, D.R., Mays, L.W. (1988). "Applied Hydrology". McGraw-Hill.
- SCS (1986). "Urban Hydrology for Small Watersheds". TR-55.
- SCS (1972). "National Engineering Handbook, Section 4: Hydrology".

### Métodos Específicos
- Kirpich, Z.P. (1940). "Time of Concentration of Small Agricultural Watersheds".
- Témez, J.R. (1978). "Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales".
- Hawkins, R.H., et al. (2002). "Continuing Evolution of Rainfall-Runoff and the Curve Number Precedent".
- Huff, F.A. (1967). "Time Distribution of Rainfall in Heavy Storms".

---

*Para documentación detallada de cada método, consultar los archivos en [`metodologias/`](metodologias/)*
