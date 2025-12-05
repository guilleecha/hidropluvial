"""
Visualizacion rapida de hidrogramas e hietogramas en terminal.

Incluye:
- Sparklines para vistas compactas en tablas
- Graficos ASCII detallados con plotext
"""

from typing import Sequence

import plotext as plt


# Caracteres para sparklines (8 niveles)
SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def sparkline(values: Sequence[float], width: int = 20) -> str:
    """
    Genera un sparkline compacto para una serie de valores.

    Args:
        values: Serie de valores numericos
        width: Ancho maximo en caracteres

    Returns:
        String con sparkline usando caracteres Unicode

    Example:
        >>> sparkline([0, 1, 4, 9, 4, 1, 0])
        '▁▂▄█▄▂▁'
    """
    if not values or len(values) == 0:
        return ""

    # Resamplear si es necesario
    if len(values) > width:
        step = len(values) / width
        resampled = []
        for i in range(width):
            idx = int(i * step)
            resampled.append(values[idx])
        values = resampled

    # Normalizar valores
    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        # Todos los valores iguales
        return SPARK_CHARS[4] * len(values)

    # Mapear a caracteres
    result = []
    for v in values:
        normalized = (v - min_val) / (max_val - min_val)
        idx = int(normalized * (len(SPARK_CHARS) - 1))
        result.append(SPARK_CHARS[idx])

    return "".join(result)


def sparkline_with_peak(
    values: Sequence[float],
    width: int = 20,
    peak_value: float | None = None,
    peak_unit: str = ""
) -> str:
    """
    Sparkline con valor pico anotado.

    Example:
        >>> sparkline_with_peak([0,1,4,9,4,1,0], peak_value=9.0, peak_unit="m3/s")
        '▁▂▄█▄▂▁ (Qp=9.0 m3/s)'
    """
    spark = sparkline(values, width)

    if peak_value is not None:
        return f"{spark} (Qp={peak_value:.2f} {peak_unit})"

    return spark


def plot_hydrograph_terminal(
    time_hr: Sequence[float],
    flow_m3s: Sequence[float],
    title: str = "Hidrograma",
    width: int = 60,
    height: int = 15,
) -> None:
    """
    Grafica un hidrograma en la terminal usando plotext.

    Args:
        time_hr: Tiempo en horas
        flow_m3s: Caudal en m3/s
        title: Titulo del grafico
        width: Ancho en caracteres
        height: Alto en caracteres
    """
    plt.clear_figure()
    plt.plot_size(width, height)

    plt.plot(list(time_hr), list(flow_m3s), marker="braille")

    plt.title(title)
    plt.xlabel("Tiempo (h)")
    plt.ylabel("Q (m3/s)")

    # Marcar pico
    peak_idx = flow_m3s.index(max(flow_m3s)) if isinstance(flow_m3s, list) else list(flow_m3s).index(max(flow_m3s))
    peak_q = flow_m3s[peak_idx]
    peak_t = time_hr[peak_idx]

    plt.scatter([peak_t], [peak_q], marker="x", color="red")

    plt.theme("clear")
    plt.show()


def plot_hyetograph_terminal(
    time_min: Sequence[float],
    intensity_mmhr: Sequence[float],
    title: str = "Hietograma",
    width: int = 60,
    height: int = 12,
) -> None:
    """
    Grafica un hietograma en la terminal usando barras.

    Args:
        time_min: Tiempo en minutos
        intensity_mmhr: Intensidad en mm/h
        title: Titulo del grafico
        width: Ancho en caracteres
        height: Alto en caracteres
    """
    plt.clear_figure()
    plt.plot_size(width, height)

    # Usar barras para hietograma
    plt.bar(list(time_min), list(intensity_mmhr))

    plt.title(title)
    plt.xlabel("Tiempo (min)")
    plt.ylabel("i (mm/h)")

    plt.theme("clear")
    plt.show()


def plot_hydrograph_comparison_terminal(
    analyses: list[dict],
    width: int = 70,
    height: int = 18,
    show_legend: bool = True,
) -> None:
    """
    Grafica multiples hidrogramas superpuestos para comparacion.

    Args:
        analyses: Lista de diccionarios con 'time_hr', 'flow_m3s', 'label'
        width: Ancho en caracteres
        height: Alto en caracteres
        show_legend: Si mostrar leyenda debajo del grafico
    """
    plt.clear_figure()
    plt.plot_size(width, height)

    # Colores y simbolos para leyenda
    colors = ["blue", "red", "green", "yellow", "cyan", "magenta"]
    symbols = ["─", "═", "~", "-", "┄", "╌"]  # Símbolos para la leyenda

    legend_items = []

    for i, analysis in enumerate(analyses):
        color = colors[i % len(colors)]
        label = analysis.get("label", f"Serie {i+1}")

        plt.plot(
            list(analysis["time_hr"]),
            list(analysis["flow_m3s"]),
            label=label,
            color=color,
            marker="braille"
        )

        # Guardar para leyenda manual
        legend_items.append((symbols[i % len(symbols)], color, label))

    plt.title("Comparacion de Hidrogramas")
    plt.xlabel("Tiempo (h)")
    plt.ylabel("Q (m3/s)")

    plt.theme("clear")
    plt.show()

    # Mostrar leyenda manual debajo del grafico
    if show_legend and legend_items:
        _print_legend(legend_items)


def _print_legend(items: list[tuple[str, str, str]]) -> None:
    """
    Imprime leyenda para el grafico de comparacion.

    Args:
        items: Lista de (simbolo, color, etiqueta)
    """
    # Mapeo de colores a códigos ANSI
    color_codes = {
        "blue": "\033[34m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "cyan": "\033[36m",
        "magenta": "\033[35m",
    }
    reset = "\033[0m"

    print("\n  Leyenda:")
    print("  " + "-" * 60)

    for symbol, color, label in items:
        color_code = color_codes.get(color, "")
        # Usar línea coloreada como indicador
        line_indicator = f"{color_code}{'━' * 3}{reset}"
        print(f"  {line_indicator}  {label}")

    print("")


def print_hyetograph_bars(
    time_min: Sequence[float],
    intensity_mmhr: Sequence[float],
    dt_min: float = 5.0,
    max_bar_width: int = 40,
) -> None:
    """
    Imprime hietograma como barras horizontales ASCII.

    Args:
        time_min: Tiempo en minutos
        intensity_mmhr: Intensidad en mm/h
        dt_min: Intervalo de tiempo
        max_bar_width: Ancho maximo de las barras
    """
    if not intensity_mmhr:
        return

    max_i = max(intensity_mmhr)
    if max_i == 0:
        return

    print("\nHietograma:")
    print("-" * (max_bar_width + 25))

    for t, i in zip(time_min, intensity_mmhr):
        bar_len = int((i / max_i) * max_bar_width)
        bar = "█" * bar_len

        # Marcar pico
        peak_marker = " <- pico" if i == max_i else ""

        print(f"{t:5.0f}-{t+dt_min:5.0f} min | {bar:<{max_bar_width}} {i:6.1f} mm/h{peak_marker}")

    print("-" * (max_bar_width + 25))


def print_summary_table_with_sparklines(rows: list[dict], show_sparkline: bool = True) -> None:
    """
    Imprime tabla resumen con sparklines integrados.

    Args:
        rows: Lista de diccionarios con datos de analisis
        show_sparkline: Si mostrar sparklines
    """
    if not rows:
        print("  No hay analisis.")
        return

    # Encabezado
    if show_sparkline:
        header = f"{'Tc':12} {'Tormenta':10} {'Tr':>4} {'X':>5} {'Qp (m3/s)':>10} {'Tp (h)':>7} {'Hidrograma':22}"
    else:
        header = f"{'Tc':12} {'Tormenta':10} {'Tr':>4} {'X':>5} {'Qp (m3/s)':>10} {'Tp (h)':>7}"

    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for row in rows:
        tc = row.get('tc_method', '')[:12]
        storm = row.get('storm', '')[:10]
        tr = row.get('tr', 0)
        x = row.get('x', 1.0) or 1.0
        qp = row.get('qpeak_m3s', 0)
        tp = row.get('tp_hr', 0)

        if show_sparkline and 'hydrograph_flow' in row:
            spark = sparkline(row['hydrograph_flow'], width=20)
            print(f"{tc:12} {storm:10} {tr:>4} {x:>5.2f} {qp:>10.3f} {tp:>7.2f} {spark}")
        else:
            print(f"{tc:12} {storm:10} {tr:>4} {x:>5.2f} {qp:>10.3f} {tp:>7.2f}")

    print("=" * len(header) + "\n")
