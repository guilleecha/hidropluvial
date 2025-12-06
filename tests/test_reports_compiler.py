"""
Tests para el módulo de compilación LaTeX.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from hidropluvial.reports.compiler import (
    LaTeXEngine,
    CompilationResult,
    compile_latex,
    find_latex_engine,
    check_latex_installation,
    _clean_aux_files,
    _extract_error_from_log,
)


class TestLaTeXEngine:
    """Tests para el enum LaTeXEngine."""

    def test_engines_values(self):
        """Test valores de los motores."""
        assert LaTeXEngine.PDFLATEX.value == "pdflatex"
        assert LaTeXEngine.XELATEX.value == "xelatex"
        assert LaTeXEngine.LUALATEX.value == "lualatex"


class TestCompilationResult:
    """Tests para CompilationResult."""

    def test_success_result(self):
        """Test resultado exitoso."""
        result = CompilationResult(
            success=True,
            pdf_path=Path("/tmp/test.pdf"),
            log_path=Path("/tmp/test.log"),
        )
        assert result.success is True
        assert result.pdf_path == Path("/tmp/test.pdf")
        assert result.warnings == []

    def test_failure_result(self):
        """Test resultado fallido."""
        result = CompilationResult(
            success=False,
            pdf_path=None,
            log_path=None,
            error_message="Error de compilación",
        )
        assert result.success is False
        assert result.error_message == "Error de compilación"

    def test_warnings_default(self):
        """Test que warnings por defecto es lista vacía."""
        result = CompilationResult(
            success=True,
            pdf_path=Path("/tmp/test.pdf"),
            log_path=None,
        )
        assert result.warnings == []


class TestFindLaTeXEngine:
    """Tests para find_latex_engine."""

    def test_finds_preferred_engine(self):
        """Test encuentra motor preferido si existe."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/pdflatex"
            result = find_latex_engine(LaTeXEngine.PDFLATEX)
            assert result == "pdflatex"

    def test_falls_back_to_alternative(self):
        """Test cae a alternativa si preferido no existe."""
        def mock_which(cmd):
            if cmd == "xelatex":
                return "/usr/bin/xelatex"
            return None

        with patch("shutil.which", side_effect=mock_which):
            result = find_latex_engine(LaTeXEngine.PDFLATEX)
            assert result == "xelatex"

    def test_returns_none_if_none_found(self):
        """Test retorna None si no hay motor."""
        with patch("shutil.which", return_value=None):
            result = find_latex_engine()
            assert result is None


class TestCheckLaTeXInstallation:
    """Tests para check_latex_installation."""

    def test_no_latex_installed(self):
        """Test cuando no hay LaTeX instalado."""
        with patch("shutil.which", return_value=None):
            info = check_latex_installation()
            assert info["installed"] is False
            assert info["engines"] == {}
            assert info["recommended"] is None

    def test_pdflatex_installed(self):
        """Test cuando pdflatex está instalado."""
        def mock_which(cmd):
            if cmd == "pdflatex":
                return "/usr/bin/pdflatex"
            return None

        with patch("shutil.which", side_effect=mock_which):
            info = check_latex_installation()
            assert info["installed"] is True
            assert "pdflatex" in info["engines"]
            assert info["recommended"] == "pdflatex"

    def test_multiple_engines_installed(self):
        """Test cuando hay múltiples motores."""
        def mock_which(cmd):
            paths = {
                "pdflatex": "/usr/bin/pdflatex",
                "xelatex": "/usr/bin/xelatex",
            }
            return paths.get(cmd)

        with patch("shutil.which", side_effect=mock_which):
            info = check_latex_installation()
            assert info["installed"] is True
            assert len(info["engines"]) == 2


class TestCompileLatex:
    """Tests para compile_latex."""

    def test_file_not_found(self):
        """Test archivo no encontrado."""
        result = compile_latex(Path("/nonexistent/file.tex"))
        assert result.success is False
        assert "no encontrado" in result.error_message.lower()

    def test_invalid_extension(self, tmp_path):
        """Test extensión inválida."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        result = compile_latex(txt_file)
        assert result.success is False
        assert ".tex" in result.error_message

    def test_no_latex_engine(self, tmp_path):
        """Test sin motor LaTeX instalado."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        with patch("shutil.which", return_value=None):
            result = compile_latex(tex_file)
            assert result.success is False
            assert "LaTeX" in result.error_message

    def test_successful_compilation(self, tmp_path):
        """Test compilación exitosa (mock)."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        # Crear PDF simulado
        pdf_file = tmp_path / "test.pdf"

        def mock_run(*args, **kwargs):
            # Simular creación del PDF
            pdf_file.write_bytes(b"%PDF-1.4")
            return MagicMock(returncode=0, stderr="")

        with patch("shutil.which", return_value="/usr/bin/pdflatex"):
            with patch("subprocess.run", side_effect=mock_run):
                result = compile_latex(tex_file)
                assert result.success is True
                assert result.pdf_path.name == "test.pdf"


class TestCleanAuxFiles:
    """Tests para _clean_aux_files."""

    def test_cleans_aux_files(self, tmp_path):
        """Test limpia archivos auxiliares."""
        # Crear archivos auxiliares
        basename = "test"
        for ext in [".aux", ".log", ".toc", ".out"]:
            (tmp_path / f"{basename}{ext}").write_text("content")

        # También crear el PDF que NO debe borrarse
        (tmp_path / f"{basename}.pdf").write_text("pdf")

        _clean_aux_files(tmp_path, basename)

        # Verificar que aux se borraron
        assert not (tmp_path / f"{basename}.aux").exists()
        assert not (tmp_path / f"{basename}.log").exists()
        assert not (tmp_path / f"{basename}.toc").exists()

        # PDF debe existir
        assert (tmp_path / f"{basename}.pdf").exists()


class TestExtractErrorFromLog:
    """Tests para _extract_error_from_log."""

    def test_no_log_file(self, tmp_path):
        """Test sin archivo de log."""
        result = _extract_error_from_log(tmp_path / "nonexistent.log")
        assert result is None

    def test_extracts_error(self, tmp_path):
        """Test extrae error del log."""
        log_file = tmp_path / "test.log"
        log_file.write_text("""
This is pdfTeX, Version 3.14
entering extended mode
! Undefined control sequence.
l.10 \\badcommand

?
        """)

        result = _extract_error_from_log(log_file)
        assert result is not None
        assert "Undefined control sequence" in result

    def test_no_error_in_log(self, tmp_path):
        """Test log sin errores."""
        log_file = tmp_path / "test.log"
        log_file.write_text("""
This is pdfTeX, Version 3.14
Output written on test.pdf (1 page, 1234 bytes).
        """)

        result = _extract_error_from_log(log_file)
        assert result is None
