"""
Compilación de documentos LaTeX a PDF.

Proporciona funciones para compilar archivos .tex a .pdf usando pdflatex
o alternativas como xelatex/lualatex.
"""

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class LaTeXEngine(str, Enum):
    """Motores de compilación LaTeX disponibles."""
    PDFLATEX = "pdflatex"
    XELATEX = "xelatex"
    LUALATEX = "lualatex"


@dataclass
class CompilationResult:
    """Resultado de la compilación LaTeX."""
    success: bool
    pdf_path: Optional[Path]
    log_path: Optional[Path]
    error_message: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def find_latex_engine(preferred: LaTeXEngine = LaTeXEngine.PDFLATEX) -> Optional[str]:
    """
    Busca un motor LaTeX disponible en el sistema.

    Args:
        preferred: Motor preferido a usar

    Returns:
        Nombre del ejecutable encontrado, o None si no hay ninguno
    """
    # Intentar el preferido primero
    if shutil.which(preferred.value):
        return preferred.value

    # Intentar alternativas
    for engine in LaTeXEngine:
        if engine != preferred and shutil.which(engine.value):
            return engine.value

    return None


def compile_latex(
    tex_file: Path,
    output_dir: Optional[Path] = None,
    engine: LaTeXEngine = LaTeXEngine.PDFLATEX,
    runs: int = 2,
    quiet: bool = True,
    clean_aux: bool = True,
) -> CompilationResult:
    """
    Compila un archivo LaTeX a PDF.

    Args:
        tex_file: Ruta al archivo .tex
        output_dir: Directorio de salida (default: mismo que tex_file)
        engine: Motor LaTeX a usar
        runs: Número de pasadas (2 para referencias cruzadas)
        quiet: Suprimir salida del compilador
        clean_aux: Limpiar archivos auxiliares después de compilar

    Returns:
        CompilationResult con el resultado de la compilación
    """
    tex_file = Path(tex_file).resolve()

    if not tex_file.exists():
        return CompilationResult(
            success=False,
            pdf_path=None,
            log_path=None,
            error_message=f"Archivo no encontrado: {tex_file}"
        )

    if not tex_file.suffix == ".tex":
        return CompilationResult(
            success=False,
            pdf_path=None,
            log_path=None,
            error_message=f"El archivo debe tener extensión .tex: {tex_file}"
        )

    # Determinar directorio de trabajo y salida
    work_dir = tex_file.parent
    if output_dir is None:
        output_dir = work_dir
    else:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    # Buscar motor LaTeX
    latex_cmd = find_latex_engine(engine)
    if latex_cmd is None:
        return CompilationResult(
            success=False,
            pdf_path=None,
            log_path=None,
            error_message=(
                "No se encontró ningún motor LaTeX instalado. "
                "Instale TeX Live, MiKTeX o MacTeX."
            )
        )

    # Construir comando
    cmd = [
        latex_cmd,
        "-interaction=nonstopmode",  # No detenerse en errores
        "-file-line-error",  # Formato de errores más legible
        f"-output-directory={output_dir}",
        str(tex_file.name),
    ]

    if quiet:
        cmd.insert(1, "-quiet")

    # Ejecutar compilación (múltiples pasadas para referencias)
    last_result = None
    for run in range(runs):
        try:
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutos máximo por pasada
            )
            last_result = result
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                pdf_path=None,
                log_path=None,
                error_message="Tiempo de compilación excedido (>120s)"
            )
        except FileNotFoundError:
            return CompilationResult(
                success=False,
                pdf_path=None,
                log_path=None,
                error_message=f"No se pudo ejecutar {latex_cmd}"
            )

    # Verificar resultado
    pdf_name = tex_file.stem + ".pdf"
    pdf_path = output_dir / pdf_name
    log_path = output_dir / (tex_file.stem + ".log")

    # Extraer warnings del log
    warnings = []
    if log_path.exists():
        try:
            log_content = log_path.read_text(encoding="utf-8", errors="ignore")
            for line in log_content.split("\n"):
                if "Warning" in line or "warning" in line:
                    warnings.append(line.strip())
        except Exception:
            pass

    if pdf_path.exists():
        # Limpiar archivos auxiliares si se solicita
        if clean_aux:
            _clean_aux_files(output_dir, tex_file.stem)

        return CompilationResult(
            success=True,
            pdf_path=pdf_path,
            log_path=log_path if log_path.exists() else None,
            warnings=warnings[:10],  # Limitar a 10 warnings
        )
    else:
        # Extraer mensaje de error del log
        error_msg = _extract_error_from_log(log_path)
        if not error_msg and last_result:
            error_msg = last_result.stderr[:500] if last_result.stderr else "Error desconocido"

        return CompilationResult(
            success=False,
            pdf_path=None,
            log_path=log_path if log_path.exists() else None,
            error_message=error_msg,
            warnings=warnings[:5],
        )


def _extract_error_from_log(log_path: Path) -> Optional[str]:
    """Extrae el primer error del archivo de log."""
    if not log_path.exists():
        return None

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        # Buscar líneas de error
        for i, line in enumerate(lines):
            if line.startswith("!"):
                # Encontrado error, extraer contexto
                error_lines = [line]
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip():
                        error_lines.append(lines[j])
                    if lines[j].startswith("l."):
                        break
                return "\n".join(error_lines)

        return None
    except Exception:
        return None


def _clean_aux_files(directory: Path, basename: str) -> None:
    """Elimina archivos auxiliares de LaTeX."""
    aux_extensions = [
        ".aux", ".log", ".out", ".toc", ".lof", ".lot",
        ".fls", ".fdb_latexmk", ".synctex.gz", ".nav",
        ".snm", ".vrb", ".bbl", ".blg", ".run.xml",
        "-blx.bib",
    ]

    for ext in aux_extensions:
        aux_file = directory / (basename + ext)
        if aux_file.exists():
            try:
                aux_file.unlink()
            except Exception:
                pass  # Ignorar errores al limpiar


def check_latex_installation() -> dict:
    """
    Verifica la instalación de LaTeX en el sistema.

    Returns:
        Diccionario con información de la instalación
    """
    info = {
        "installed": False,
        "engines": {},
        "recommended": None,
    }

    for engine in LaTeXEngine:
        path = shutil.which(engine.value)
        if path:
            info["engines"][engine.value] = path
            info["installed"] = True
            if info["recommended"] is None:
                info["recommended"] = engine.value

    return info
