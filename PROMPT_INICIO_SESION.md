# Prompt de Inicio de Sesión - HidroPluvial

## Contexto del Proyecto

Estoy trabajando en **HidroPluvial**, una herramienta Python para cálculos hidrológicos orientada a Uruguay con soporte para metodología DINAGUA y generación de reportes LaTeX.

---

## Paso 1: Leer documentación esencial

Por favor, lee los siguientes archivos en orden:

1. `CLAUDE.md` - Instrucciones del proyecto y estado actual
2. `docs/DESARROLLO.md` - Documentación de desarrollo, estructura, configuración MCP
3. `docs/guia_graficos.md` - Guía de generación de gráficos TikZ (módulo recién implementado)

---

## Paso 2: Verificar servidores MCP

Verifica que los servidores MCP estén conectados:
- **github** - Para vincular con https://github.com/guilleecha/hidropluvial
- **context7** - Para memoria contextual

Si no están disponibles, revisar el archivo `.mcp.json` en la raíz del proyecto.

---

## Paso 3: Vincular con GitHub

El repositorio aún no está inicializado con git. Necesitamos:

1. Inicializar repositorio git local
2. Crear commit inicial con el estado actual
3. Vincular con el repositorio remoto: https://github.com/guilleecha/hidropluvial
4. Push inicial

**Archivos a excluir** (ya configurados en `.gitignore`):
- `.venv/`
- `.mcp.json` (contiene tokens)
- `__pycache__/`
- `.pytest_cache/`

---

## Paso 4: Tareas pendientes (Fase 3)

Después de vincular con GitHub, las siguientes tareas están pendientes:

### 3.1 Templates Jinja2 para reportes LaTeX
- [ ] Crear estructura `reports/templates/`
- [ ] Template para memoria de cálculo IDF
- [ ] Template para hietograma de diseño
- [ ] Template para hidrograma de crecida
- [ ] Template para reporte completo de cuenca

### 3.2 Mejoras CLI
- [ ] Comando `report` para generar reportes PDF
- [ ] Exportación a CSV/Excel
- [ ] Integrar generación de gráficos TikZ en CLI

### 3.3 Documentación API
- [ ] Configurar Sphinx o MkDocs
- [ ] Documentar funciones públicas
- [ ] Ejemplos en Jupyter notebooks

---

## Estado actual del proyecto

- **Tests:** 98 tests pasando ✅
- **Módulos core:** Todos completos (IDF, temporal, tc, runoff, hydrograph)
- **Gráficos TikZ:** Implementado (`reports/charts.py`)
- **CLI:** Funcional con comandos básicos

---

## Comandos útiles

```bash
# Activar entorno
.venv\Scripts\activate

# Ejecutar tests
pytest tests/ -v

# Probar CLI
python -m hidropluvial idf uruguay 78 3 --tr 25
```
