"""
Utilidades de formateo para la CLI de HidroPluvial.
"""

import typer


class OutputFormatter:
    """Formateador de salida para la CLI."""

    @staticmethod
    def header(title: str, width: int = 60) -> None:
        """Imprime encabezado de sección."""
        typer.echo(f"\n{'='*width}")
        typer.echo(f"  {title}")
        typer.echo(f"{'='*width}")

    @staticmethod
    def subheader(title: str, width: int = 50) -> None:
        """Imprime subencabezado."""
        typer.echo(f"\n  {'-'*width}")
        typer.echo(f"  {title}")
        typer.echo(f"  {'-'*width}")

    @staticmethod
    def field(label: str, value: str, unit: str = "", indent: int = 2) -> None:
        """Imprime campo con etiqueta y valor."""
        spaces = " " * indent
        if unit:
            typer.echo(f"{spaces}{label}: {value} {unit}")
        else:
            typer.echo(f"{spaces}{label}: {value}")

    @staticmethod
    def field_aligned(label: str, value: float, unit: str = "",
                      label_width: int = 20, value_width: int = 10) -> None:
        """Imprime campo alineado."""
        if unit:
            typer.echo(f"  {label:<{label_width}} {value:>{value_width}.3f} {unit}")
        else:
            typer.echo(f"  {label:<{label_width}} {value:>{value_width}.3f}")

    @staticmethod
    def separator(width: int = 60) -> None:
        """Imprime línea separadora."""
        typer.echo(f"{'='*width}")

    @staticmethod
    def blank() -> None:
        """Imprime línea en blanco."""
        typer.echo("")

    @staticmethod
    def item(text: str, prefix: str = "+", indent: int = 4) -> None:
        """Imprime item de lista."""
        spaces = " " * indent
        typer.echo(f"{spaces}{prefix} {text}")

    @staticmethod
    def error(message: str) -> None:
        """Imprime mensaje de error."""
        typer.echo(f"Error: {message}", err=True)

    @staticmethod
    def warning(message: str) -> None:
        """Imprime mensaje de advertencia."""
        typer.echo(f"Advertencia: {message}", err=True)

    @staticmethod
    def success(message: str) -> None:
        """Imprime mensaje de éxito."""
        typer.echo(f"  {message}")

    @staticmethod
    def table_row(columns: list[str], widths: list[int]) -> None:
        """Imprime fila de tabla."""
        row = "  "
        for col, width in zip(columns, widths):
            row += f"{col:<{width}} "
        typer.echo(row)


# Instancia global para uso directo
fmt = OutputFormatter()
