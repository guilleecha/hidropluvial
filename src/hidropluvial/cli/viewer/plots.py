"""
Funciones de gráficos para el visor interactivo.

Usa plotext para gráficos en terminal.
"""

import plotext as plt

from hidropluvial.cli.theme import get_palette


def _round_ticks(max_val: float, num_ticks: int = 5) -> list[float]:
    """
    Genera ticks redondeados para un eje.

    Args:
        max_val: Valor máximo del eje
        num_ticks: Número aproximado de ticks deseados

    Returns:
        Lista de valores de ticks redondeados
    """
    if max_val <= 0:
        return [0]

    # Calcular intervalo "bonito"
    raw_interval = max_val / num_ticks
    magnitude = 10 ** int(f"{raw_interval:.0e}".split("e")[1])
    normalized = raw_interval / magnitude

    # Elegir intervalo redondeado
    if normalized <= 1:
        nice_interval = 1 * magnitude
    elif normalized <= 2:
        nice_interval = 2 * magnitude
    elif normalized <= 5:
        nice_interval = 5 * magnitude
    else:
        nice_interval = 10 * magnitude

    # Generar ticks
    ticks = []
    tick = 0
    while tick <= max_val * 1.1:  # Pequeño margen
        ticks.append(tick)
        tick += nice_interval

    return ticks


def build_combined_plot(
    analysis,
    width: int = 70,
    height_hyeto: int = 8,
    height_hydro: int = 12,
) -> str:
    """
    Construye gráfico combinado: hietograma + hidrograma en un solo gráfico.

    Formato con doble eje Y:
    - Eje Y izquierdo: Caudal Q (m³/s) - línea azul
    - Eje Y derecho: Intensidad i (mm/h) - barras cyan (invertido)

    Args:
        analysis: AnalysisRun con datos de tormenta e hidrograma
        width: Ancho total del grafico
        height_hyeto: No usado (se combina en un solo gráfico)
        height_hydro: Alto del gráfico combinado

    Returns:
        String con el gráfico renderizado
    """
    from hidropluvial.cli.formatters import format_flow

    hydro = analysis.hydrograph
    storm = analysis.storm

    # Altura total del gráfico
    total_height = height_hyeto + height_hydro

    # Obtener tema de plotext desde la paleta
    palette = get_palette()
    plot_theme = palette.plot_theme

    plt.clear_figure()
    plt.theme(plot_theme)
    plt.plot_size(width, total_height)

    # Valores para ticks redondeados
    max_flow = max(hydro.flow_m3s) if hydro.flow_m3s else 1
    max_intensity = storm.peak_intensity_mmhr if storm.intensity_mmhr else 1

    # --- Hietograma: barras en eje X superior, Y derecho (invertido, solo contorno) ---
    if storm.time_min and storm.intensity_mmhr:
        time_hr = [t / 60 for t in storm.time_min]
        plt.bar(
            time_hr,
            storm.intensity_mmhr,
            width=0.8,
            color="orange+",  # Naranja/amarillo para precipitación
            xside="upper",    # Eje X arriba
            yside="right",
            fill=False,       # Solo contorno, sin relleno
            marker="braille", # Líneas finas con caracteres braille
        )
        # Invertir eje Y derecho para que barras crezcan hacia abajo
        plt.yreverse(yside="right")

    # --- Hidrograma: línea en eje Y izquierdo ---
    if hydro.time_hr and hydro.flow_m3s:
        plt.plot(
            list(hydro.time_hr),
            list(hydro.flow_m3s),
            marker="braille",
            color="blue",
            yside="left",
        )

        # Marcar pico con X roja
        peak_idx = list(hydro.flow_m3s).index(max(hydro.flow_m3s))
        peak_q = hydro.flow_m3s[peak_idx]
        peak_t = hydro.time_hr[peak_idx]
        plt.scatter([peak_t], [peak_q], marker="x", color="red", yside="left")

    # Configurar ejes con ticks redondeados
    plt.xlabel("Tiempo (h)", xside="lower")
    plt.ylabel("Q m³/s", yside="left")
    plt.ylabel("i mm/h", yside="right")

    # Ocultar ticks del eje X superior (comparten escala de tiempo)
    plt.xticks([], xside="upper")

    # Ticks redondeados
    flow_ticks = _round_ticks(max_flow, 4)
    intensity_ticks = _round_ticks(max_intensity, 4)

    plt.yticks(flow_ticks, [f"{t:.2g}" for t in flow_ticks], yside="left")
    plt.yticks(intensity_ticks, [f"{t:.0f}" for t in intensity_ticks], yside="right")

    # Título con toda la info
    storm_type = storm.type.upper() if hasattr(storm, 'type') else "?"
    plt.title(f"{storm_type} Tr{storm.return_period}  P={storm.total_depth_mm:.1f}mm  Qp={format_flow(hydro.peak_flow_m3s)} m³/s  Tp={hydro.time_to_peak_min:.0f}min")

    # Construir gráfico
    plot_output = plt.build()

    # Agregar leyenda manual fuera del gráfico (abajo)
    legend = f"  ── Q m³/s (Qp={format_flow(hydro.peak_flow_m3s)})    ⡏⢹ i mm/h (imax={storm.peak_intensity_mmhr:.1f})"

    return f"{plot_output}\n{legend}"


def plot_combined(
    analysis,
    width: int = 70,
    height_hyeto: int = 8,
    height_hydro: int = 12,
) -> None:
    """
    Plotea hietograma e hidrograma combinados (imprime directamente).

    Args:
        analysis: AnalysisRun con datos de tormenta e hidrograma
        width: Ancho total del grafico
        height_hyeto: Alto del hietograma
        height_hydro: Alto del hidrograma
    """
    print(build_combined_plot(analysis, width, height_hyeto, height_hydro))


def plot_hydrograph(
    time_hr: list[float],
    flow_m3s: list[float],
    title: str,
    info_lines: list[str],
    width: int = 70,
    height: int = 18,
) -> None:
    """
    Plotea un hidrograma individual.

    Args:
        time_hr: Tiempo en horas
        flow_m3s: Caudal en m3/s
        title: Titulo del grafico
        info_lines: Lineas de informacion adicional
        width: Ancho del grafico
        height: Alto del grafico
    """
    palette = get_palette()

    plt.clear_figure()
    plt.theme(palette.plot_theme)
    plt.plot_size(width, height)

    plt.plot(time_hr, flow_m3s, marker="braille")

    plt.title(title)
    plt.xlabel("Tiempo (h)")
    plt.ylabel("Q (m3/s)")

    # Marcar pico
    if flow_m3s:
        peak_idx = flow_m3s.index(max(flow_m3s))
        peak_q = flow_m3s[peak_idx]
        peak_t = time_hr[peak_idx]
        plt.scatter([peak_t], [peak_q], marker="x", color="red")

    plt.show()

    # Mostrar info adicional
    for line in info_lines:
        print(line)
