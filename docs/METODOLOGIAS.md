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

### Curvas IDF (Intensidad-Duración-Frecuencia)

Cálculo de intensidades de precipitación para diferentes duraciones y períodos de retorno.
El método principal es **DINAGUA Uruguay**, basado en P₃,₁₀ (Rodríguez Fontal, 1980).

**Fórmulas verificadas:**
- Factor CT(Tr) = 0.5786 - 0.4312 × log[ln(Tr/(Tr-1))]
- Intensidad (d<3h): I = P₃,₁₀ × CT × 0.6208 / (d+0.0137)^0.5639

### Tormentas de Diseño

Distribución temporal de la precipitación:
- **Bloques Alternantes** - Método universal con pico configurable
- **GZ** - Variante uruguaya con pico adelantado (6 horas, DINAGUA)
- **Bimodal** - Tormentas con doble pico (sistemas frontales Uruguay)
- **SCS Tipo I-III** - Distribuciones de 24 horas del NRCS (TR-55)

### Tiempo de Concentración

**Fórmulas verificadas contra bibliografía:**

| Método | Fórmula | Referencia |
|--------|---------|------------|
| **Kirpich** | tc = 0.0195 × L^0.77 × S^(-0.385) | Kirpich (1940), Civil Engineering Vol.10 |
| **Témez** | tc = 0.3 × (L / S^0.25)^0.76 | Témez (1978), MOPU España |
| **Desbordes** | Tc = t₀ + 6.625 × A^0.3 × P^(-0.39) × C^(-0.45) | DINAGUA Uruguay |
| **NRCS** | Suma de segmentos (sheet + shallow + channel) | TR-55 (1986), Capítulo 3 |

Donde:
- L: Longitud del cauce (m para Kirpich, km para Témez)
- S: Pendiente (m/m)
- A: Área (ha)
- C: Coeficiente de escorrentía
- t₀: Tiempo de entrada (típicamente 5 min)

### Escorrentía

**SCS Curve Number (CN)** - Verificado contra TR-55 y ASCE:

```
S = (25400/CN) - 254  [mm]
Ia = λ × S
Q = (P - Ia)² / (P - Ia + S)  para P > Ia
```

Donde:
- λ = 0.20 (tradicional) o 0.05 (Hawkins et al., 2002)
- CN: Número de curva (30-100)

**Método Racional:**
```
Q = 0.00278 × C × i × A  [Q: m³/s, i: mm/h, A: ha]
```

### Hidrogramas Unitarios

**Hidrograma Triangular SCS** - Verificado contra TR-55 y HEC-HMS:

```
tp = D/2 + 0.6×Tc        (tiempo al pico)
Tb = 2.67 × tp           (tiempo base)
Qp = 2.08 × A × Q / tp   (caudal pico en m³/s, A en km²)
```

El factor 2.08 es la conversión del factor 484 de unidades imperiales (cfs, mi², in) a métricas (m³/s, km², mm).

---

## Referencias Bibliográficas

### Normativa Uruguay

1. **DINAGUA**. "Curvas Intensidad-Duración-Frecuencia para Uruguay". Ministerio de Vivienda, Ordenamiento Territorial y Medio Ambiente.

2. **DINAGUA**. "Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas". MVOTMA.

3. **HHA-FING UdelaR** (2019). "Guía Metodológica: Hidrología e Hidráulica Aplicada". Facultad de Ingeniería, Universidad de la República, Uruguay.

4. **Rodríguez Fontal, E.** (1980). "Método para curvas IDF en Uruguay". DINAGUA.

### Documentación Técnica NRCS/SCS

5. **NRCS** (1986). "Urban Hydrology for Small Watersheds". Technical Release 55 (TR-55). USDA.
   - Capítulo 3: Time of Concentration and Travel Time
   - Capítulo 4: Graphical Peak Discharge Method
   - Capítulo 5: Tabular Hydrograph Method

6. **NRCS** (2004). "National Engineering Handbook, Part 630: Hydrology". USDA.
   - Capítulo 9: Hydrologic Soil-Cover Complexes
   - Capítulo 10: Estimation of Direct Runoff from Storm Rainfall
   - Capítulo 16: Hydrographs

### Literatura Técnica Internacional

7. **Chow, V.T., Maidment, D.R., Mays, L.W.** (1988). "Applied Hydrology". McGraw-Hill.
   - Tabla 5.5.2: Coeficientes C de escorrentía

8. **FHWA** (2024). "Urban Drainage Design Manual". HEC-22, 4th Edition. Federal Highway Administration.

### Métodos de Tiempo de Concentración

9. **Kirpich, Z.P.** (1940). "Time of Concentration of Small Agricultural Watersheds". Civil Engineering, Vol. 10, No. 6, p. 362.

10. **Témez, J.R.** (1978). "Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales". MOPU, Dirección General de Carreteras, España.

### Escorrentía y Curva Número

11. **Hawkins, R.H., Ward, T.J., Woodward, D.E., Van Mullem, J.A.** (2002). "Curve Number Hydrology: State of the Practice". ASCE.

12. **Mockus, V.** (1949). "Estimation of Total Surface Runoff for Individual Storms". Exhibit A of Appendix B, Interim Survey Report, Grand (Neosho) River Watershed.

### Hidrogramas

13. **Snyder, F.F.** (1938). "Synthetic Unit-Graphs". Transactions of the American Geophysical Union, Vol. 19, pp. 447-454.

14. **Clark, C.O.** (1945). "Storage and the Unit Hydrograph". Transactions ASCE, Vol. 110, pp. 1419-1446.

### Tormentas de Diseño

15. **Huff, F.A.** (1967). "Time Distribution of Rainfall in Heavy Storms". Water Resources Research, Vol. 3, No. 4.

---

## Verificación de Fórmulas

Todas las fórmulas implementadas han sido verificadas contra las fuentes bibliográficas originales:

| Método | Estado | Verificado contra |
|--------|--------|-------------------|
| Kirpich | ✓ Verificado | Paper original (1940) |
| Témez | ✓ Verificado | MOPU España (1978) |
| NRCS TR-55 | ✓ Verificado | Documentación TR-55 |
| SCS-CN | ✓ Verificado | TR-55 y ASCE (2002) |
| Hidrograma SCS | ✓ Verificado | TR-55 y HEC-HMS |
| Snyder | ✓ Verificado | Paper original (1938) |
| DINAGUA IDF | ✓ Verificado | Documentación DINAGUA |

---

*Para documentación detallada de cada método, consultar los archivos en [`metodologias/`](metodologias/)*
