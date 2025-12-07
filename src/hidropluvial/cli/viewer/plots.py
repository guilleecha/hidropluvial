"""
Funciones de gráficos para el visor interactivo.

Usa plotext para gráficos en terminal.
"""

import plotext as plt


def plot_combined(
    analysis,
    width: int = 70,
    height_hyeto: int = 8,
    height_hydro: int = 12,
) -> None:
    """
    Plotea hietograma e hidrograma combinados.

    Args:
        analysis: AnalysisRun con datos de tormenta e hidrograma
        width: Ancho total del grafico
        height_hyeto: Alto del hietograma
        height_hydro: Alto del hidrograma
    """
    hydro = analysis.hydrograph
    storm = analysis.storm

    plt.clear_figure()

    # Crear 2 filas, 1 columna
    plt.subplots(2, 1)

    # --- Hietograma (arriba) ---
    plt.subplot(1, 1)
    plt.plot_size(width, height_hyeto)

    if storm.time_min and storm.intensity_mmhr:
        # Calcular intervalo dt
        if len(storm.time_min) > 1:
            dt_min = storm.time_min[1] - storm.time_min[0]
        else:
            dt_min = 5.0

        # Calcular duracion total de la tormenta
        storm_duration_min = max(storm.time_min) + dt_min / 2 if storm.time_min else 60

        # Usar minutos si duracion < 2 horas, sino horas
        use_minutes = storm_duration_min < 120

        if use_minutes:
            time_values = list(storm.time_min)
            time_label = "min"
            tick_step = 10 if storm_duration_min <= 60 else 15
            max_time = max(time_values) + dt_min if time_values else 60
            x_ticks = list(range(0, int(max_time) + tick_step, tick_step))
        else:
            time_values = [t / 60 for t in storm.time_min]
            time_label = "h"
            max_time = max(time_values) + dt_min / 60 if time_values else 6
            x_ticks = list(range(0, int(max_time) + 2))

        # Barras con valores numericos
        plt.bar(time_values, storm.intensity_mmhr, color="cyan")

        plt.xticks(x_ticks, [str(t) for t in x_ticks])
        plt.title(f"Hietograma - P={storm.total_depth_mm:.1f}mm  imax={storm.peak_intensity_mmhr:.1f}mm/h")
        plt.ylabel("i (mm/h)")
        plt.xlabel(f"Tiempo ({time_label})")
    else:
        plt.title("Hietograma - Sin datos")

    plt.theme("clear")

    # --- Hidrograma (abajo) ---
    plt.subplot(2, 1)
    plt.plot_size(width, height_hydro)

    if hydro.time_hr and hydro.flow_m3s:
        plt.plot(list(hydro.time_hr), list(hydro.flow_m3s), marker="braille", color="blue")

        # Marcar pico
        peak_idx = list(hydro.flow_m3s).index(max(hydro.flow_m3s))
        peak_q = hydro.flow_m3s[peak_idx]
        peak_t = hydro.time_hr[peak_idx]
        plt.scatter([peak_t], [peak_q], marker="x", color="red")

        # Ticks limpios
        max_time = max(hydro.time_hr) if hydro.time_hr else 6
        x_ticks = list(range(0, int(max_time) + 2))
        plt.xticks(x_ticks, [str(t) for t in x_ticks])

        from hidropluvial.cli.formatters import format_flow
        plt.title(f"Hidrograma - Qp={format_flow(hydro.peak_flow_m3s)}m3/s  Tp={hydro.time_to_peak_min:.0f}min")
        plt.ylabel("Q (m3/s)")
        plt.xlabel("Tiempo (h)")
    else:
        plt.title("Hidrograma - Sin datos")

    plt.theme("clear")
    plt.show()


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
    plt.clear_figure()
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

    plt.theme("clear")
    plt.show()

    # Mostrar info adicional
    for line in info_lines:
        print(line)
