"""
Tests para cli/formatters.py - Utilidades de formateo CLI.
"""

import pytest

from hidropluvial.cli.formatters import OutputFormatter, fmt


class TestOutputFormatter:
    """Tests para OutputFormatter."""

    def test_header(self, capsys):
        """Test impresión de header."""
        OutputFormatter.header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "=" in captured.out

    def test_header_custom_width(self, capsys):
        """Test header con ancho personalizado."""
        OutputFormatter.header("Title", width=40)
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines[0]) == 40  # Primera línea de =

    def test_subheader(self, capsys):
        """Test impresión de subheader."""
        OutputFormatter.subheader("Subheader")
        captured = capsys.readouterr()
        assert "Subheader" in captured.out
        assert "-" in captured.out

    def test_field_without_unit(self, capsys):
        """Test campo sin unidad."""
        OutputFormatter.field("Area", "100.5")
        captured = capsys.readouterr()
        assert "Area: 100.5" in captured.out

    def test_field_with_unit(self, capsys):
        """Test campo con unidad."""
        OutputFormatter.field("Area", "100.5", "ha")
        captured = capsys.readouterr()
        assert "Area: 100.5 ha" in captured.out

    def test_field_custom_indent(self, capsys):
        """Test campo con indentación personalizada."""
        OutputFormatter.field("Label", "Value", indent=4)
        captured = capsys.readouterr()
        assert "    Label: Value" in captured.out

    def test_field_aligned_with_unit(self, capsys):
        """Test campo alineado con unidad."""
        OutputFormatter.field_aligned("Flow", 123.456, "m³/s")
        captured = capsys.readouterr()
        assert "Flow" in captured.out
        assert "123.456" in captured.out
        assert "m³/s" in captured.out

    def test_field_aligned_without_unit(self, capsys):
        """Test campo alineado sin unidad."""
        OutputFormatter.field_aligned("Value", 99.999)
        captured = capsys.readouterr()
        assert "99.999" in captured.out

    def test_field_aligned_custom_widths(self, capsys):
        """Test campo alineado con anchos personalizados."""
        OutputFormatter.field_aligned("X", 1.5, label_width=10, value_width=8)
        captured = capsys.readouterr()
        # Verificar que hay espacios de alineación
        assert "X" in captured.out
        assert "1.500" in captured.out

    def test_separator(self, capsys):
        """Test separador."""
        OutputFormatter.separator()
        captured = capsys.readouterr()
        assert "=" * 60 in captured.out

    def test_separator_custom_width(self, capsys):
        """Test separador con ancho personalizado."""
        OutputFormatter.separator(width=30)
        captured = capsys.readouterr()
        assert "=" * 30 in captured.out

    def test_blank(self, capsys):
        """Test línea en blanco."""
        OutputFormatter.blank()
        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_item_default(self, capsys):
        """Test item con prefijo default."""
        OutputFormatter.item("Test item")
        captured = capsys.readouterr()
        assert "+ Test item" in captured.out

    def test_item_custom_prefix(self, capsys):
        """Test item con prefijo personalizado."""
        OutputFormatter.item("Test item", prefix="*")
        captured = capsys.readouterr()
        assert "* Test item" in captured.out

    def test_item_custom_indent(self, capsys):
        """Test item con indentación personalizada."""
        OutputFormatter.item("Text", indent=6)
        captured = capsys.readouterr()
        assert "      + Text" in captured.out

    def test_error(self, capsys):
        """Test mensaje de error."""
        OutputFormatter.error("Something failed")
        captured = capsys.readouterr()
        assert "Error: Something failed" in captured.err

    def test_warning(self, capsys):
        """Test mensaje de advertencia."""
        OutputFormatter.warning("Be careful")
        captured = capsys.readouterr()
        assert "Advertencia: Be careful" in captured.err

    def test_success(self, capsys):
        """Test mensaje de éxito."""
        OutputFormatter.success("All good!")
        captured = capsys.readouterr()
        assert "All good!" in captured.out

    def test_table_row(self, capsys):
        """Test fila de tabla."""
        columns = ["Col1", "Col2", "Col3"]
        widths = [10, 15, 10]
        OutputFormatter.table_row(columns, widths)
        captured = capsys.readouterr()
        assert "Col1" in captured.out
        assert "Col2" in captured.out
        assert "Col3" in captured.out


class TestFmtInstance:
    """Tests para instancia global fmt."""

    def test_fmt_is_output_formatter(self):
        """Test que fmt es instancia de OutputFormatter."""
        assert isinstance(fmt, OutputFormatter)

    def test_fmt_header(self, capsys):
        """Test fmt.header funciona."""
        fmt.header("Global fmt test")
        captured = capsys.readouterr()
        assert "Global fmt test" in captured.out

    def test_fmt_error(self, capsys):
        """Test fmt.error funciona."""
        fmt.error("Global error")
        captured = capsys.readouterr()
        assert "Error: Global error" in captured.err
