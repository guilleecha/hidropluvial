"""
Visor interactivo de fichas de analisis con navegacion por teclado.

Permite navegar entre analisis usando:
- Flechas izquierda/derecha: cambiar analisis secuencialmente
- Flechas arriba/abajo: moverse en la lista lateral
- Enter: seleccionar analisis de la lista
- q/ESC: salir
"""

import os
import sys
from typing import Optional

import plotext as plt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette


def clear_screen() -> None:
    """Limpia la pantalla de la terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_key() -> str:
    """
    Captura una tecla del usuario.

    Returns:
        String representando la tecla presionada:
        - 'left': flecha izquierda
        - 'right': flecha derecha
        - 'up': flecha arriba
        - 'down': flecha abajo
        - 'q': tecla q
        - 'esc': tecla escape
        - otro caracter
    """
    if os.name == 'nt':
        # Windows
        import msvcrt
        key = msvcrt.getch()

        if key == b'\xe0':  # Tecla especial (flechas)
            key2 = msvcrt.getch()
            if key2 == b'K':
                return 'left'
            elif key2 == b'M':
                return 'right'
            elif key2 == b'H':
                return 'up'
            elif key2 == b'P':
                return 'down'
        elif key == b'\x1b':  # ESC
            return 'esc'
        elif key == b'q' or key == b'Q':
            return 'q'
        elif key == b'\r':  # Enter
            return 'enter'

        return key.decode('utf-8', errors='ignore')
    else:
        # Unix/Linux/Mac
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)

            if key == '\x1b':  # Secuencia de escape
                key2 = sys.stdin.read(1)
                if key2 == '[':
                    key3 = sys.stdin.read(1)
                    if key3 == 'D':
                        return 'left'
                    elif key3 == 'C':
                        return 'right'
                    elif key3 == 'A':
                        return 'up'
                    elif key3 == 'B':
                        return 'down'
                return 'esc'
            elif key == 'q' or key == 'Q':
                return 'q'
            elif key == '\r' or key == '\n':
                return 'enter'

            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _format_analysis_label(analysis, index: int, max_len: int = 35) -> str:
    """Formatea etiqueta corta de un analisis."""
    hydro = analysis.hydrograph
    storm = analysis.storm
    tc = analysis.tc

    x_str = f"X{hydro.x_factor:.1f}" if hydro.x_factor else ""
    label = f"{tc.method[:8]} {storm.type[:3]}Tr{storm.return_period}"
    if x_str:
        label += f" {x_str}"
    label += f" Qp={hydro.peak_flow_m3s:.1f}"

    if len(label) > max_len:
        label = label[:max_len-2] + ".."
    return label


def _build_analysis_list(analyses: list, current_idx: int, max_visible: int = 12) -> Table:
    """Construye la tabla con lista de analisis, destacando el actual."""
    p = get_palette()

    table = Table(
        show_header=True,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("#", style=p.muted, width=3)
    table.add_column("Analisis", width=38)
    table.add_column("Qp", justify="right", width=7)

    n = len(analyses)

    # Calcular ventana visible centrada en current_idx
    half = max_visible // 2
    start = max(0, current_idx - half)
    end = min(n, start + max_visible)
    if end - start < max_visible:
        start = max(0, end - max_visible)

    # Indicador de scroll arriba
    if start > 0:
        table.add_row("", Text("...", style=p.muted), "")

    for i in range(start, end):
        a = analyses[i]
        hydro = a.hydrograph
        storm = a.storm
        tc = a.tc

        x_str = f" X{hydro.x_factor:.1f}" if hydro.x_factor else ""
        label = f"{tc.method[:8]} {storm.type[:3]}Tr{storm.return_period}{x_str}"
        qp_str = f"{hydro.peak_flow_m3s:.2f}"

        # Estilo: destacado si es el actual, gris si no
        if i == current_idx:
            idx_text = Text(f">{i+1}", style=f"bold {p.accent}")
            label_text = Text(label, style=f"bold {p.accent}")
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            idx_text = Text(f" {i+1}", style=p.muted)
            label_text = Text(label, style=p.muted)
            qp_text = Text(qp_str, style=p.muted)

        table.add_row(idx_text, label_text, qp_text)

    # Indicador de scroll abajo
    if end < n:
        table.add_row("", Text("...", style=p.muted), "")

    return table


def _build_info_panel(analysis, session_name: str, current_idx: int, n_total: int) -> Panel:
    """Construye panel con informacion del analisis."""
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3
    p = get_palette()

    hydro = analysis.hydrograph
    storm = analysis.storm
    tc = analysis.tc

    # Titulo del panel
    x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
    title = Text()
    title.append(f" FICHA DE ANALISIS ", style=f"bold {p.primary}")
    title.append(f"[{current_idx+1}/{n_total}]", style=p.muted)

    # Contenido: tabla compacta con datos
    info_table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    info_table.add_column("Label", style=p.label, width=10)
    info_table.add_column("Value", style=f"bold {p.number}", width=14)
    info_table.add_column("Label2", style=p.label, width=10)
    info_table.add_column("Value2", style=f"bold {p.number}", width=14)

    # Fila 1: Cuenca y Tormenta
    info_table.add_row(
        "Cuenca:", Text(session_name[:14], style=p.secondary),
        "Tormenta:", Text(f"{storm.type.upper()} Tr{storm.return_period}", style=p.secondary),
    )

    # Fila 2: Tc (metodo) y tp
    tp_str = f"{hydro.tp_unit_min:.0f} min" if hydro.tp_unit_min else "-"
    tc_text = Text()
    tc_text.append(f"{tc.tc_min:.1f} min ", style=f"bold {p.number}")
    tc_text.append(f"({tc.method[:6]})", style=p.muted)
    info_table.add_row(
        "Tc:", tc_text,
        "tp (HU):", Text(tp_str, style=f"bold {p.number}"),
    )

    # Fila 3: Factor X y tb
    x_val = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
    tb_str = f"{hydro.tb_min:.0f} min" if hydro.tb_min else "-"
    info_table.add_row(
        "Factor X:", Text(x_val, style=f"bold {p.number}"),
        "tb:", Text(tb_str, style=f"bold {p.number}"),
    )

    # Fila 4: P y Pe
    info_table.add_row(
        "P total:", Text(f"{storm.total_depth_mm:.1f} mm", style=f"bold {p.number}"),
        "Pe:", Text(f"{hydro.runoff_mm:.1f} mm", style=f"bold {p.number}"),
    )

    # Fila 5: i_max y coeficiente
    param_str = "-"
    if tc.parameters:
        if "c" in tc.parameters:
            param_str = f"C={tc.parameters['c']:.2f}"
        elif "cn_adjusted" in tc.parameters:
            param_str = f"CN={tc.parameters['cn_adjusted']}"

    info_table.add_row(
        "i max:", Text(f"{storm.peak_intensity_mmhr:.1f} mm/h", style=f"bold {p.number}"),
        "Coef.:", Text(param_str, style=f"bold {p.number}"),
    )

    # Separador
    info_table.add_row("", "", "", "")

    # Fila 6: Resultados principales (destacados)
    qp_text = Text()
    qp_text.append(f"{format_flow(hydro.peak_flow_m3s)} ", style=f"bold {p.accent}")
    qp_text.append("m3/s", style=p.unit)

    tp_peak_text = Text()
    tp_peak_text.append(f"{hydro.time_to_peak_min:.0f} ", style=f"bold {p.accent}")
    tp_peak_text.append("min", style=p.unit)

    info_table.add_row(
        "Qp:", qp_text,
        "Tp:", tp_peak_text,
    )

    # Fila 7: Volumen
    vol_text = Text()
    vol_text.append(f"{format_volume_hm3(hydro.volume_m3)} ", style=f"bold {p.accent}")
    vol_text.append("hm3", style=p.unit)

    info_table.add_row(
        "Volumen:", vol_text,
        "", "",
    )

    return Panel(
        info_table,
        title=title,
        title_align="left",
        border_style=p.primary,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def plot_combined_styled(
    analysis,
    width: int = 70,
    height_hyeto: int = 10,
    height_hydro: int = 14,
) -> None:
    """
    Plotea hietograma e hidrograma combinados con barras separadas.

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


def interactive_hydrograph_viewer(
    analyses: list,
    session_name: str,
    width: int = 75,
    height: int = 16,
) -> None:
    """
    Visor interactivo de fichas de analisis.

    Permite navegar entre analisis con las flechas del teclado.
    Muestra hietograma e hidrograma combinados con panel de informacion.

    Navegacion:
    - Flechas izquierda/derecha: cambiar analisis secuencialmente
    - Flechas arriba/abajo: moverse en la lista lateral
    - Enter: ir al analisis seleccionado en la lista
    - q/ESC: salir

    Args:
        analyses: Lista de AnalysisRun
        session_name: Nombre de la sesion
        width: Ancho del grafico
        height: Alto del grafico (no usado, se usan alturas fijas)
    """
    if not analyses:
        print("  No hay analisis disponibles.")
        return

    console = Console()
    p = get_palette()

    current_idx = 0
    n_analyses = len(analyses)

    while True:
        clear_screen()

        analysis = analyses[current_idx]

        # Panel de informacion
        info_panel = _build_info_panel(analysis, session_name, current_idx, n_analyses)
        console.print(info_panel)
        console.print()

        # Graficos
        plot_combined_styled(
            analysis,
            width=width,
            height_hyeto=10,
            height_hydro=14,
        )

        # Lista de analisis (si hay mas de uno)
        if n_analyses > 1:
            console.print()
            list_table = _build_analysis_list(analyses, current_idx)
            list_panel = Panel(
                list_table,
                title=Text(" Lista de Analisis ", style=f"bold {p.secondary}"),
                title_align="left",
                border_style=p.border,
                box=box.ROUNDED,
                padding=(0, 1),
            )
            console.print(list_panel)

        # Instrucciones de navegacion
        console.print()
        nav_text = Text()
        nav_text.append("  [", style=p.muted)
        nav_text.append("<-", style=f"bold {p.primary}")
        nav_text.append("] Anterior  [", style=p.muted)
        nav_text.append("->", style=f"bold {p.primary}")
        nav_text.append("] Siguiente  [", style=p.muted)
        nav_text.append("q", style=f"bold {p.primary}")
        nav_text.append("] Salir", style=p.muted)
        console.print(nav_text)

        # Esperar input
        key = get_key()

        if key == 'q' or key == 'esc':
            clear_screen()
            console.print(f"\n  Visor cerrado. Cuenca: {session_name}\n")
            break
        elif key == 'left':
            current_idx = (current_idx - 1) % n_analyses
        elif key == 'right':
            current_idx = (current_idx + 1) % n_analyses


# Mantener funcion legacy para compatibilidad
def plot_combined(
    analysis,
    title: str,
    width: int = 85,
    height_hyeto: int = 12,
    height_hydro: int = 18,
) -> None:
    """
    Plotea hietograma e hidrograma combinados (version legacy).
    Redirige a la nueva funcion con barras separadas.
    """
    plot_combined_styled(analysis, width, height_hyeto, height_hydro)
    print(f"\n  {title}")


def plot_hydrograph(
    time_hr: list[float],
    flow_m3s: list[float],
    title: str,
    info_lines: list[str],
    width: int = 70,
    height: int = 18,
) -> None:
    """
    Plotea un hidrograma individual (version legacy).

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
