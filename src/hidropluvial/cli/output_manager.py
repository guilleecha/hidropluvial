"""
Gestión centralizada de directorios y rutas de salida.

Estructura:
    output/
    ├── <uuid8>_<proyecto_nombre>/
    │   ├── <uuid8>_<cuenca_nombre>/
    │   │   ├── latex/
    │   │   │   ├── hidrogramas/
    │   │   │   ├── hietogramas/
    │   │   │   └── *.tex, *.pdf
    │   │   ├── excel/
    │   │   │   └── *.xlsx
    │   │   └── csv/
    │   │       └── *.csv
    │   └── reporte_proyecto/
    │       └── ...

Ejemplo:
    output/
    ├── a1b2c3d4_proyecto_drenaje_norte/
    │   ├── e5f6g7h8_cuenca_arroyo_las_piedras/
    │   │   ├── latex/
    │   │   └── excel/
    │   └── reporte_proyecto/
"""

from pathlib import Path
from typing import Optional

# Directorio base de salida
OUTPUT_BASE = Path("output")


def _sanitize_name(name: str) -> str:
    """
    Sanitiza un nombre para usarlo como nombre de directorio/archivo.

    - Convierte a minúsculas
    - Reemplaza espacios y caracteres especiales por guión bajo
    - Elimina caracteres no válidos para nombres de archivo
    """
    # Caracteres a reemplazar por guión bajo
    replace_chars = " /\\:*?\"<>|"

    result = name.lower()
    for char in replace_chars:
        result = result.replace(char, "_")

    # Eliminar guiones bajos múltiples
    while "__" in result:
        result = result.replace("__", "_")

    # Eliminar guiones bajos al inicio y final
    result = result.strip("_")

    return result


def _make_dir_name(uuid: str, name: str) -> str:
    """
    Crea nombre de directorio con formato: <uuid8>_<nombre_sanitizado>

    Args:
        uuid: UUID completo (se usan primeros 8 caracteres)
        name: Nombre descriptivo

    Returns:
        str: Nombre de directorio (ej: "a1b2c3d4_proyecto_norte")
    """
    uuid_short = uuid[:8] if uuid else "00000000"
    safe_name = _sanitize_name(name)
    return f"{uuid_short}_{safe_name}"


def get_project_output_dir(project_id: str, project_name: str) -> Path:
    """
    Obtiene el directorio de salida para un proyecto.

    Args:
        project_id: UUID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Path: output/<uuid8>_<proyecto_nombre>/
    """
    dir_name = _make_dir_name(project_id, project_name)
    output_dir = OUTPUT_BASE / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_basin_output_dir(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Path:
    """
    Obtiene el directorio de salida para una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto (opcional)
        project_name: Nombre del proyecto (opcional)

    Returns:
        Path: output/<uuid8>_<proyecto>/<uuid8>_<cuenca>/
    """
    if project_id and project_name:
        project_dir = get_project_output_dir(project_id, project_name)
    else:
        project_dir = OUTPUT_BASE / "sin_proyecto"
        project_dir.mkdir(parents=True, exist_ok=True)

    basin_dir_name = _make_dir_name(basin_id, basin_name)
    basin_dir = project_dir / basin_dir_name
    basin_dir.mkdir(parents=True, exist_ok=True)

    return basin_dir


def get_latex_output_dir(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Path:
    """
    Obtiene el directorio para reportes LaTeX de una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Path: output/<uuid8>_<proyecto>/<uuid8>_<cuenca>/latex/
    """
    basin_dir = get_basin_output_dir(basin_id, basin_name, project_id, project_name)
    latex_dir = basin_dir / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)
    return latex_dir


def get_excel_output_dir(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Path:
    """
    Obtiene el directorio para archivos Excel de una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Path: output/<uuid8>_<proyecto>/<uuid8>_<cuenca>/excel/
    """
    basin_dir = get_basin_output_dir(basin_id, basin_name, project_id, project_name)
    excel_dir = basin_dir / "excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    return excel_dir


def get_csv_output_dir(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Path:
    """
    Obtiene el directorio para archivos CSV de una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Path: output/<uuid8>_<proyecto>/<uuid8>_<cuenca>/csv/
    """
    basin_dir = get_basin_output_dir(basin_id, basin_name, project_id, project_name)
    csv_dir = basin_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    return csv_dir


def get_project_report_dir(project_id: str, project_name: str) -> Path:
    """
    Obtiene el directorio para reporte completo de proyecto.

    Args:
        project_id: UUID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Path: output/<uuid8>_<proyecto>/reporte_proyecto/
    """
    project_dir = get_project_output_dir(project_id, project_name)
    report_dir = project_dir / "reporte_proyecto"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def get_unique_filepath(base_path: Path, extension: str = "") -> Path:
    """
    Genera una ruta única agregando sufijo numérico si ya existe.

    Args:
        base_path: Ruta base (sin extensión si se proporciona extension)
        extension: Extensión del archivo (ej: ".xlsx")

    Returns:
        Path única que no existe

    Example:
        get_unique_filepath(Path("output/cuenca"), ".xlsx")
        -> Path("output/cuenca.xlsx") si no existe
        -> Path("output/cuenca_v2.xlsx") si ya existe
    """
    if extension and not extension.startswith("."):
        extension = "." + extension

    # Separar directorio y nombre base
    parent = base_path.parent
    stem = base_path.stem if base_path.suffix else base_path.name

    # Primer intento sin sufijo
    candidate = parent / f"{stem}{extension}"
    if not candidate.exists():
        return candidate

    # Agregar sufijo numérico
    version = 2
    while True:
        candidate = parent / f"{stem}_v{version}{extension}"
        if not candidate.exists():
            return candidate
        version += 1
        if version > 100:  # Límite de seguridad
            raise RuntimeError(f"Demasiadas versiones del archivo: {base_path}")


def get_latex_filepath(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    filename: Optional[str] = None,
) -> Path:
    """
    Obtiene la ruta para el archivo LaTeX principal de una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto
        project_name: Nombre del proyecto
        filename: Nombre del archivo (sin extensión), default: nombre de cuenca

    Returns:
        Path al archivo .tex
    """
    latex_dir = get_latex_output_dir(basin_id, basin_name, project_id, project_name)

    if filename is None:
        filename = _sanitize_name(basin_name)

    return latex_dir / f"{filename}.tex"


def get_excel_filepath(
    basin_id: str,
    basin_name: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    filename: Optional[str] = None,
    unique: bool = False,
) -> Path:
    """
    Obtiene la ruta para el archivo Excel de una cuenca.

    Args:
        basin_id: UUID de la cuenca
        basin_name: Nombre de la cuenca
        project_id: UUID del proyecto
        project_name: Nombre del proyecto
        filename: Nombre del archivo (sin extensión), default: nombre de cuenca
        unique: Si True, genera nombre único si ya existe

    Returns:
        Path al archivo .xlsx
    """
    excel_dir = get_excel_output_dir(basin_id, basin_name, project_id, project_name)

    if filename is None:
        filename = _sanitize_name(basin_name)

    base_path = excel_dir / filename

    if unique:
        return get_unique_filepath(base_path, ".xlsx")

    return excel_dir / f"{filename}.xlsx"
