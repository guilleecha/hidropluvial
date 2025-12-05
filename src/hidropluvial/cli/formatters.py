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


    @staticmethod
    def format_flow(flow_m3s: float) -> str:
        """
        Formatea caudal con 2 cifras significativas.

        Args:
            flow_m3s: Caudal en m³/s

        Returns:
            String formateado (ej: "0.15", "1.2", "12", "120")
        """
        if flow_m3s is None:
            return "-"
        if flow_m3s == 0:
            return "0"
        if flow_m3s >= 100:
            return f"{flow_m3s:.0f}"
        elif flow_m3s >= 10:
            return f"{flow_m3s:.1f}"
        elif flow_m3s >= 1:
            return f"{flow_m3s:.2f}"
        elif flow_m3s >= 0.1:
            return f"{flow_m3s:.2f}"
        else:
            return f"{flow_m3s:.2g}"

    @staticmethod
    def format_volume_hm3(volume_m3: float) -> str:
        """
        Formatea volumen en hm³ (1 hm³ = 1,000,000 m³).

        Args:
            volume_m3: Volumen en m³

        Returns:
            String formateado en hm³ (ej: "0.0012", "0.15", "1.2")
        """
        if volume_m3 is None:
            return "-"
        hm3 = volume_m3 / 1_000_000
        if hm3 >= 1:
            return f"{hm3:.2f}"
        elif hm3 >= 0.01:
            return f"{hm3:.4f}"
        else:
            return f"{hm3:.2g}"


# Instancia global para uso directo
fmt = OutputFormatter()


# Funciones de conveniencia para formateo
def format_flow(flow_m3s: float) -> str:
    """Formatea caudal con 2 cifras significativas."""
    return OutputFormatter.format_flow(flow_m3s)


def format_volume_hm3(volume_m3: float) -> str:
    """Formatea volumen en hm³."""
    return OutputFormatter.format_volume_hm3(volume_m3)
