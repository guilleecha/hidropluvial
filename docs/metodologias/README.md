# Documentacion de Metodologias

Esta carpeta contiene la documentacion tecnica de los metodos implementados en HidroPluvial.

Cada archivo incluye:
- **Contexto teorico** - Origen y aplicacion del metodo
- **Formulas** - Ecuaciones matematicas con notacion clara
- **Extractos de codigo** - Implementacion real con referencias a lineas
- **Ejemplos de uso** - Codigo funcional para replicar
- **Referencias** - Fuentes bibliograficas

---

## Contenido

| Archivo | Modulo | Metodos |
|---------|--------|---------|
| [idf.md](idf.md) | `core.idf` | DINAGUA Uruguay, Sherman, Bernard, Koutsoyiannis |
| [tc.md](tc.md) | `core.tc` | Kirpich, Temez, Desbordes, NRCS, FAA, Kinematic |
| [runoff.md](runoff.md) | `core.runoff` | SCS Curve Number, Metodo Racional |
| [hydrograph.md](hydrograph.md) | `core.hydrograph` | SCS triangular/curvilinear, Snyder, Clark, Gamma |

---

## Proposito

Esta documentacion sirve para:

1. **Verificacion** - Comparar implementacion con formulas teoricas
2. **Auditoria** - Revisar calculos en proyectos profesionales
3. **Aprendizaje** - Entender los fundamentos de cada metodo
4. **Extension** - Agregar nuevos metodos siguiendo el patron

---

## Estructura de cada documento

```markdown
# Nombre del Modulo

**Modulo:** `hidropluvial.core.xxx`

## 1. Introduccion
## 2. Metodo A
   ### 2.1 Contexto
   ### 2.2 Formula
   ### 2.3 Implementacion (con extracto de codigo)
## 3. Metodo B
   ...
## N. Ejemplos de Uso
## N+1. Referencias
```

---

*Documentacion generada para HidroPluvial v1.x*
