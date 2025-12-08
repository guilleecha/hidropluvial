# Assets

Este directorio contiene recursos gráficos para la aplicación.

## Archivos requeridos

### `icon.ico`
Icono de la aplicación en formato ICO para Windows.

**Especificaciones recomendadas:**
- Formato: ICO (multi-resolución)
- Tamaños incluidos: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- Profundidad de color: 32-bit (con transparencia)

**Herramientas para crear:**
- [IcoFX](https://icofx.ro/) (Windows)
- [GIMP](https://www.gimp.org/) con plugin ICO
- [ImageMagick](https://imagemagick.org/): `convert logo.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico`
- [favicon.io](https://favicon.io/) (online)

**Nota:** Si `icon.ico` no existe, el ejecutable se genera sin icono personalizado.
