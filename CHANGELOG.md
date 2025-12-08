# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Agregado
- Wizard interactivo para creación de proyectos y análisis
- Soporte para múltiples métodos de tiempo de concentración (Kirpich, California Culverts, Témez, SCS)
- Cálculo de escorrentía por método Racional (C) y SCS-CN
- Generación de hidrogramas unitarios (SCS, Snyder, Clark)
- Distribuciones temporales de tormentas (AES, Huff, SCS)
- Generación de reportes LaTeX con gráficos
- Visualizador interactivo de proyectos en terminal
- Exportación a Excel y JSON
- Base de datos SQLite para persistencia
- Soporte para múltiples cuencas por proyecto

### Cambiado
- Migración de almacenamiento JSON a SQLite
- Mejora en tablas de comparación de hidrogramas
- Solicitud proactiva de datos faltantes al calcular Tc

### Corregido
- Conteo correcto de análisis incluyendo métodos de escorrentía
- Selección de métodos de Tc cuando faltan datos de cuenca
- Opción "Volver" en visor de cuencas

## [0.1.0] - Próximamente

Primera versión pública.

### Características principales
- CLI completo con comandos y wizard interactivo
- Cálculos hidrológicos validados
- Generación de reportes profesionales en LaTeX
- Distribución vía PyPI, ejecutable Windows e instalador

[Unreleased]: https://github.com/your-username/hidropluvial/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/hidropluvial/releases/tag/v0.1.0
