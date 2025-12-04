"""
Módulo de generación de gráficos TikZ/PGFPlots para LaTeX.

Genera código LaTeX para:
- Hidrogramas (comparativos y simples)
- Hietogramas (barras invertidas)

Estilo basado en ejemplos de referencia con:
- Ejes en formato hora (H:MM)
- Grid mayor punteado gris
- Leyendas posicionadas
"""

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class HydrographSeries:
    """Serie de datos para hidrograma."""
    time_min: Sequence[float]
    flow_m3s: Sequence[float]
    label: str
    color: str = "black"
    style: str = "solid"  # solid, dashed, dotted


@dataclass
class HyetographData:
    """Datos para hietograma."""
    time_min: Sequence[float]
    intensity_mmhr: Sequence[float]
    title: str = ""
    label: str = ""


def _minutes_to_hour_label(minutes: float) -> str:
    """Convierte minutos a formato H:MM."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}:{mins:02d}"


def _generate_hour_ticks(max_minutes: float, preferred_interval_hr: float = 1.0) -> tuple[list[float], list[str]]:
    """
    Genera ticks en horas completas.

    Args:
        max_minutes: Tiempo máximo en minutos
        preferred_interval_hr: Intervalo preferido en horas (1.0 por defecto)

    Returns:
        Tupla (posiciones en minutos, etiquetas en formato hora)
    """
    max_hours = max_minutes / 60

    # Determinar intervalo apropiado
    if max_hours <= 3:
        interval_hr = 0.5
    elif max_hours <= 6:
        interval_hr = 1.0
    elif max_hours <= 12:
        interval_hr = 2.0
    elif max_hours <= 24:
        interval_hr = 4.0
    else:
        interval_hr = 6.0

    # Usar intervalo preferido si es razonable
    if preferred_interval_hr and max_hours / preferred_interval_hr <= 12:
        interval_hr = preferred_interval_hr

    # Generar ticks
    ticks_hr = np.arange(0, max_hours + interval_hr, interval_hr)
    ticks_min = [t * 60 for t in ticks_hr if t * 60 <= max_minutes + 1]
    labels = [_minutes_to_hour_label(t) for t in ticks_min]

    return ticks_min, labels


def _format_coordinates(time_min: Sequence[float], values: Sequence[float], precision: int = 2) -> str:
    """Formatea coordenadas para TikZ."""
    coords = []
    for t, v in zip(time_min, values):
        coords.append(f"({t:.0f}, {v:.{precision}f})")

    # Agrupar en líneas de 5 coordenadas
    lines = []
    for i in range(0, len(coords), 5):
        chunk = coords[i:i+5]
        lines.append("\t\t\t\t" + " ".join(chunk))

    return "\n".join(lines)


def generate_hydrograph_tikz(
    series: list[HydrographSeries],
    caption: str = "",
    label: str = "",
    xlabel: str = "Tiempo",
    ylabel: str = r"Caudal (m$^3$/s)",
    width: str = r"\textwidth",
    height: str = "8cm",
    legend_pos: str = "north east",
    ymax: float | None = None,
) -> str:
    """
    Genera código TikZ para hidrograma.

    Args:
        series: Lista de series de datos
        caption: Título de la figura
        label: Etiqueta para referencias LaTeX
        xlabel: Etiqueta del eje X
        ylabel: Etiqueta del eje Y
        width: Ancho del gráfico
        height: Alto del gráfico
        legend_pos: Posición de la leyenda
        ymax: Valor máximo del eje Y (auto si None)

    Returns:
        Código LaTeX/TikZ completo
    """
    if not series:
        raise ValueError("Se requiere al menos una serie de datos")

    # Calcular límites
    all_times = []
    all_flows = []
    for s in series:
        all_times.extend(s.time_min)
        all_flows.extend(s.flow_m3s)

    xmax = max(all_times)
    if ymax is None:
        ymax = max(all_flows) * 1.1  # 10% de margen

    # Generar ticks de hora
    ticks_min, tick_labels = _generate_hour_ticks(xmax)
    xtick_str = ", ".join(f"{t:.0f}" for t in ticks_min)
    xticklabels_str = ", ".join(tick_labels)

    # Construir plots
    plots = []
    for s in series:
        coords = _format_coordinates(s.time_min, s.flow_m3s)
        plot = f"""		% {s.label}
		\\addplot [
		{s.color},
		thick,
		{s.style},
		] coordinates {{
{coords}
		}};
		\\addlegendentry{{{s.label}}}"""
        plots.append(plot)

    plots_str = "\n\t\t\n".join(plots)

    # Construir figura completa
    tex = f"""\\begin{{figure}}[H]
	\\centering
	\\begin{{tikzpicture}}
		\\begin{{axis}}[
			width={width},
			height={height},
			xlabel={{{xlabel}}},
			ylabel={{{ylabel}}},
			xmin=0,
			xmax={xmax:.0f},
			ymin=0,
			ymax={ymax:.0f},
			grid=major,
			grid style={{dashed, gray!30}},
			legend pos={legend_pos},
			xtick={{{xtick_str}}},
			xticklabels={{{xticklabels_str}}},
			]
{plots_str}

		\\end{{axis}}
	\\end{{tikzpicture}}
	\\caption{{{caption}}}
	\\label{{{label}}}
\\end{{figure}}
"""
    return tex


def generate_hydrograph_comparison_tikz(
    time_min_1: Sequence[float],
    flow_m3s_1: Sequence[float],
    time_min_2: Sequence[float],
    flow_m3s_2: Sequence[float],
    label_1: str = "Sin MCE",
    label_2: str = "Con MCE",
    caption: str = "Comparación de hidrogramas",
    label: str = "fig:hidrograma_comparacion",
    **kwargs,
) -> str:
    """
    Genera código TikZ para comparación de dos hidrogramas.

    Estilo por defecto:
    - Serie 1: rojo, discontinuo
    - Serie 2: negro, sólido

    Args:
        time_min_1: Tiempo de la primera serie (minutos)
        flow_m3s_1: Caudales de la primera serie (m³/s)
        time_min_2: Tiempo de la segunda serie (minutos)
        flow_m3s_2: Caudales de la segunda serie (m³/s)
        label_1: Etiqueta de la primera serie
        label_2: Etiqueta de la segunda serie
        caption: Título de la figura
        label: Etiqueta para referencias
        **kwargs: Argumentos adicionales para generate_hydrograph_tikz

    Returns:
        Código LaTeX/TikZ
    """
    series = [
        HydrographSeries(
            time_min=time_min_1,
            flow_m3s=flow_m3s_1,
            label=label_1,
            color="red",
            style="dashed",
        ),
        HydrographSeries(
            time_min=time_min_2,
            flow_m3s=flow_m3s_2,
            label=label_2,
            color="black",
            style="solid",
        ),
    ]

    return generate_hydrograph_tikz(series, caption=caption, label=label, **kwargs)


def generate_hyetograph_tikz(
    time_min: Sequence[float],
    intensity_mmhr: Sequence[float],
    caption: str = "",
    label: str = "",
    title: str = "",
    xlabel: str = "Tiempo",
    ylabel: str = "Precipitación (mm/h)",
    width: str = r"\textwidth",
    height: str = "8cm",
    bar_width: int | None = None,
    ymax: float | None = None,
) -> str:
    """
    Genera código TikZ para hietograma (barras invertidas).

    Args:
        time_min: Tiempos centrales de cada intervalo (minutos)
        intensity_mmhr: Intensidades (mm/h)
        caption: Título de la figura
        label: Etiqueta para referencias LaTeX
        title: Título dentro del gráfico
        xlabel: Etiqueta del eje X
        ylabel: Etiqueta del eje Y
        width: Ancho del gráfico
        height: Alto del gráfico
        bar_width: Ancho de las barras (auto si None)
        ymax: Valor máximo del eje Y (auto si None)

    Returns:
        Código LaTeX/TikZ completo
    """
    if len(time_min) < 2:
        raise ValueError("Se requieren al menos 2 puntos de datos")

    # Calcular intervalo dt
    dt = time_min[1] - time_min[0] if len(time_min) > 1 else 5

    # Calcular límites
    xmax = max(time_min) + dt / 2
    if ymax is None:
        ymax = max(intensity_mmhr) * 1.1

    # Ancho de barra automático
    if bar_width is None:
        bar_width = max(2, int(dt * 0.8))

    # Generar ticks de hora
    ticks_min, tick_labels = _generate_hour_ticks(xmax)
    xtick_str = ", ".join(f"{t:.0f}" for t in ticks_min)
    xticklabels_str = ", ".join(tick_labels)

    # Formatear coordenadas
    coords = _format_coordinates(time_min, intensity_mmhr)

    # Título opcional
    title_line = f"title={{{title}}},\n\t\t\t" if title else ""

    # Construir figura
    tex = f"""\\begin{{figure}}[H]
	\\centering
	\\begin{{tikzpicture}}
		\\begin{{axis}}[
			{title_line}width={width},
			height={height},
			xlabel={{{xlabel}}},
			ylabel={{{ylabel}}},
			y dir=reverse,
			ymin=0,
			ymax={ymax:.0f},
			xmin=0,
			xmax={xmax:.0f},
			ybar,
			bar width={bar_width},
			xtick={{{xtick_str}}},
			xticklabels={{{xticklabels_str}}},
			xticklabel style={{rotate=45, anchor=east}},
			grid=major,
			grid style={{dashed, gray!30}},
			]
			\\addplot [
			draw=black,
			fill=none
			]
			coordinates {{
{coords}
			}};
		\\end{{axis}}
	\\end{{tikzpicture}}
	\\caption{{{caption}}}
	\\label{{{label}}}
\\end{{figure}}
"""
    return tex


def generate_hyetograph_filled_tikz(
    time_min: Sequence[float],
    intensity_mmhr: Sequence[float],
    caption: str = "",
    label: str = "",
    title: str = "",
    fill_color: str = "blue!30",
    **kwargs,
) -> str:
    """
    Genera código TikZ para hietograma con barras rellenas.

    Args:
        time_min: Tiempos centrales (minutos)
        intensity_mmhr: Intensidades (mm/h)
        caption: Título de la figura
        label: Etiqueta para referencias
        title: Título dentro del gráfico
        fill_color: Color de relleno (default: blue!30)
        **kwargs: Argumentos adicionales

    Returns:
        Código LaTeX/TikZ
    """
    # Generar versión básica y modificar el fill
    tex = generate_hyetograph_tikz(
        time_min, intensity_mmhr, caption, label, title, **kwargs
    )

    # Reemplazar fill=none por fill=color
    tex = tex.replace("fill=none", f"fill={fill_color}")

    return tex


# ============================================================================
# Funciones de conveniencia para integración con modelos existentes
# ============================================================================

def hydrograph_result_to_tikz(
    result,  # HydrographResult
    caption: str = "",
    label: str = "",
    **kwargs,
) -> str:
    """
    Genera TikZ desde un HydrographResult.

    Args:
        result: Objeto HydrographResult del módulo core
        caption: Título de la figura
        label: Etiqueta LaTeX
        **kwargs: Argumentos adicionales

    Returns:
        Código LaTeX/TikZ
    """
    # Convertir tiempo de horas a minutos
    time_min = [t * 60 for t in result.time_hr]

    series = [
        HydrographSeries(
            time_min=time_min,
            flow_m3s=result.flow_m3s,
            label=f"{result.method.value}",
            color="black",
            style="solid",
        )
    ]

    return generate_hydrograph_tikz(series, caption=caption, label=label, **kwargs)


def hyetograph_result_to_tikz(
    result,  # HyetographResult
    caption: str = "",
    label: str = "",
    title: str = "",
    **kwargs,
) -> str:
    """
    Genera TikZ desde un HyetographResult.

    Args:
        result: Objeto HyetographResult del módulo core
        caption: Título de la figura
        label: Etiqueta LaTeX
        title: Título dentro del gráfico
        **kwargs: Argumentos adicionales

    Returns:
        Código LaTeX/TikZ
    """
    return generate_hyetograph_tikz(
        time_min=result.time_min,
        intensity_mmhr=result.intensity_mmhr,
        caption=caption,
        label=label,
        title=title,
        **kwargs,
    )
