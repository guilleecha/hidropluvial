# HidroPluvial - Guía de Instalación

**Instalación completa desde cero en Windows**

---

## Contenido

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación de Python](#instalación-de-python)
3. [Instalación de Git](#instalación-de-git)
4. [Instalación de LaTeX](#instalación-de-latex)
5. [Instalación de HidroPluvial](#instalación-de-hidropluvial)
6. [Verificación de la Instalación](#verificación-de-la-instalación)
7. [Uso Diario](#uso-diario)
8. [Solución de Problemas](#solución-de-problemas)

---

## Requisitos del Sistema

### Mínimos
- **Sistema Operativo**: Windows 10/11 (64-bit)
- **RAM**: 4 GB
- **Espacio en disco**: 5 GB (incluye Python + LaTeX)
- **Conexión a Internet**: Para descarga e instalación

### Software Necesario

| Software | Versión | Uso | Obligatorio |
|----------|---------|-----|-------------|
| Python | 3.11+ | Ejecutar la aplicación | Sí |
| Git | Cualquiera | Clonar el repositorio | Sí |
| MiKTeX/TeX Live | 2023+ | Compilar reportes PDF | Opcional |

---

## Instalación de Python

### Paso 1: Descargar Python

1. Ir a [python.org/downloads](https://www.python.org/downloads/)
2. Descargar **Python 3.11** o superior (botón amarillo "Download Python 3.x.x")
3. Guardar el instalador

### Paso 2: Instalar Python

1. Ejecutar el instalador descargado
2. **IMPORTANTE**: Marcar la casilla **"Add Python to PATH"** en la primera pantalla
3. Clic en **"Install Now"**
4. Esperar a que termine la instalación
5. Clic en **"Close"**

### Paso 3: Verificar instalación

Abrir PowerShell o CMD y ejecutar:

```powershell
python --version
```

Debería mostrar algo como: `Python 3.11.x`

También verificar pip:
```powershell
pip --version
```

---

## Instalación de Git

### Paso 1: Descargar Git

1. Ir a [git-scm.com/download/win](https://git-scm.com/download/win)
2. La descarga debería iniciar automáticamente
3. Si no, clic en "Click here to download manually"

### Paso 2: Instalar Git

1. Ejecutar el instalador
2. Aceptar la licencia
3. En las opciones, dejar los valores por defecto
4. **Recomendado**: En "Choosing the default editor", seleccionar "Use Visual Studio Code" o "Use Notepad++"
5. Continuar con valores por defecto hasta el final
6. Clic en **"Install"**

### Paso 3: Verificar instalación

Abrir una **nueva** ventana de PowerShell:

```powershell
git --version
```

Debería mostrar: `git version 2.x.x`

---

## Instalación de LaTeX

LaTeX es necesario para generar los reportes PDF. Puedes elegir entre **MiKTeX** (más liviano) o **TeX Live** (más completo).

### Opción A: MiKTeX (Recomendado para principiantes)

#### Paso 1: Descargar MiKTeX

1. Ir a [miktex.org/download](https://miktex.org/download)
2. Clic en "Download" para Windows
3. Guardar el instalador (~200 MB)

#### Paso 2: Instalar MiKTeX

1. Ejecutar el instalador
2. Aceptar la licencia
3. Seleccionar **"Install missing packages on-the-fly: Yes"**
4. Elegir carpeta de instalación (dejar por defecto)
5. Clic en **"Start"**
6. La instalación puede demorar 5-10 minutos

#### Paso 3: Actualizar paquetes

1. Abrir **MiKTeX Console** desde el menú Inicio
2. Ir a **"Updates"**
3. Clic en **"Check for updates"**
4. Si hay actualizaciones, clic en **"Update now"**

### Opción B: TeX Live (Instalación completa)

#### Paso 1: Descargar TeX Live

1. Ir a [tug.org/texlive/acquire-netinstall.html](https://tug.org/texlive/acquire-netinstall.html)
2. Descargar `install-tl-windows.exe`

#### Paso 2: Instalar TeX Live

1. Ejecutar el instalador
2. Seleccionar "Custom installation" si deseas elegir componentes
3. Para instalación completa: ~7 GB, puede demorar 1-2 horas
4. Para instalación básica: seleccionar solo "Basic scheme"

### Verificar instalación de LaTeX

```powershell
pdflatex --version
```

Debería mostrar información de versión de pdfTeX.

---

## Instalación de HidroPluvial

### Paso 1: Clonar el repositorio

Abrir PowerShell y navegar a donde deseas instalar:

```powershell
# Crear carpeta para proyectos (opcional)
mkdir C:\proyectos
cd C:\proyectos

# Clonar repositorio
git clone https://github.com/ghaynes/hidropluvial.git

# Entrar a la carpeta
cd hidropluvial
```

### Paso 2: Crear entorno virtual

```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate
```

Verás que el prompt cambia a `(.venv) PS C:\...`

### Paso 3: Instalar dependencias

```powershell
# Actualizar pip
python -m pip install --upgrade pip

# Instalar HidroPluvial en modo desarrollo
pip install -e .
```

### Paso 4: Verificar instalación

```powershell
# Verificar que el comando hp funciona
hp --help
```

Deberías ver la ayuda de HidroPluvial.

---

## Verificación de la Instalación

### Test 1: Comando básico

```powershell
hp --help
```

Debería listar todos los comandos disponibles.

### Test 2: Consulta IDF

```powershell
hp idf departamentos
```

Debería mostrar la tabla de valores P₃,₁₀ por departamento.

### Test 3: Cálculo simple

```powershell
hp idf uruguay 78 3 --tr 25
```

Debería mostrar resultados de intensidad y precipitación.

### Test 4: Wizard interactivo

```powershell
hp wizard
```

Debería abrir el asistente interactivo con el menú principal:

```
╔══════════════════════════════════════════════════╗
║                                                  ║
║    ╦ ╦╦╔╦╗╦═╗╔═╗╔═╗╦  ╦ ╦╦  ╦╦╔═╗╦               ║
║    ╠═╣║ ║║╠╦╝║ ║╠═╝║  ║ ║╚╗╔╝║╠═╣║               ║
║    ╩ ╩╩═╩╝╩╚═╚═╝╩  ╩═╝╚═╝ ╚╝ ╩╩ ╩╩═╝             ║
║                                                  ║
║       ≋≋≋  Cálculos Hidrológicos  ≋≋≋            ║
║                   Uruguay                        ║
╚══════════════════════════════════════════════════╝
```

### Test 5: Generación de PDF (requiere LaTeX)

Después de crear un análisis en el wizard, exportar a LaTeX para verificar que se genera el PDF correctamente.

---

## Uso Diario

### Iniciar HidroPluvial

Cada vez que quieras usar HidroPluvial:

```powershell
# Navegar a la carpeta
cd C:\proyectos\hidropluvial

# Activar entorno virtual
.venv\Scripts\activate

# Iniciar wizard
hp wizard
```

### Crear acceso directo (opcional)

Puedes crear un archivo `.bat` para acceso rápido:

1. Crear archivo `hidropluvial.bat` en el Escritorio
2. Contenido:
```batch
@echo off
cd /d C:\proyectos\hidropluvial
call .venv\Scripts\activate
hp wizard
pause
```

3. Doble clic para ejecutar

### Almacenamiento de Datos

HidroPluvial guarda todos los proyectos y cuencas en una base de datos local:

```
%USERPROFILE%\.hidropluvial\
└── hidropluvial.db    # Base de datos SQLite
```

**Ubicación típica:** `C:\Users\<tu_usuario>\.hidropluvial\`

La base de datos se crea automáticamente la primera vez que se usa la aplicación.

**Backup de datos:**
```powershell
# Copiar la base de datos para hacer backup
copy "%USERPROFILE%\.hidropluvial\hidropluvial.db" backup_hidropluvial.db
```

---

## Solución de Problemas

### Error: "python no se reconoce como comando"

**Causa**: Python no está en el PATH

**Solución**:
1. Desinstalar Python
2. Reinstalar marcando "Add Python to PATH"

O agregar manualmente:
1. Buscar "Variables de entorno" en Windows
2. En "Path" agregar: `C:\Users\TuUsuario\AppData\Local\Programs\Python\Python311\`

### Error: "pip no se reconoce"

**Solución**:
```powershell
python -m pip install --upgrade pip
```

### Error al activar entorno virtual

**Causa**: Política de ejecución de scripts

**Solución**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "pdflatex no se reconoce"

**Causa**: LaTeX no está instalado o no está en PATH

**Solución**:
1. Verificar que MiKTeX está instalado
2. Reiniciar PowerShell/CMD
3. Si persiste, agregar MiKTeX al PATH:
   - Ubicación típica: `C:\Program Files\MiKTeX\miktex\bin\x64\`

### Error: "Package ... not found" al compilar LaTeX

**Causa**: Faltan paquetes LaTeX

**Solución MiKTeX**:
1. Abrir MiKTeX Console
2. Ir a "Packages"
3. Buscar el paquete faltante
4. Clic derecho → Install

O configurar instalación automática:
- Settings → "Install missing packages on-the-fly: Yes"

### Error de encoding/caracteres especiales

**Causa**: Problemas con UTF-8 en Windows

**Solución**:
```powershell
# Configurar UTF-8 en PowerShell
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
```

### La interfaz no muestra bien los caracteres

**Causa**: Terminal sin soporte Unicode

**Solución**:
1. Usar Windows Terminal (disponible en Microsoft Store)
2. O configurar la fuente en CMD/PowerShell:
   - Clic derecho en barra de título → Propiedades → Fuente → "Consolas" o "Lucida Console"

### Reportar otros problemas

Si encuentras otros errores:

1. Abrir issue en GitHub: https://github.com/ghaynes/hidropluvial/issues
2. Incluir:
   - Versión de Windows
   - Versión de Python (`python --version`)
   - Mensaje de error completo
   - Pasos para reproducir

---

## Desinstalación

### Desinstalar HidroPluvial

```powershell
# Eliminar carpeta del proyecto
Remove-Item -Recurse -Force C:\proyectos\hidropluvial

# Eliminar datos de usuario (opcional)
Remove-Item -Recurse -Force "$env:USERPROFILE\.hidropluvial"
```

### Desinstalar componentes (opcional)

- **Python**: Panel de Control → Programas → Desinstalar
- **MiKTeX**: Panel de Control → Programas → Desinstalar
- **Git**: Panel de Control → Programas → Desinstalar

---

*Guía de Instalación - HidroPluvial v2.0*
