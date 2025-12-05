"""
Visor interactivo de hidrogramas con navegacion por teclado.

Permite navegar entre hidrogramas usando:
- Flechas izquierda/derecha: cambiar hidrograma
- q/ESC: salir
"""

import os
import sys
from typing import Callable, Optional

import plotext as plt


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


def interactive_hydrograph_viewer(
    analyses: list,
    session_name: str,
    width: int = 70,
    height: int = 16,
) -> None:
    """
    Visor interactivo de hidrogramas.

    Permite navegar entre hidrogramas con las flechas del teclado.

    Args:
        analyses: Lista de AnalysisRun
        session_name: Nombre de la sesion
        width: Ancho del grafico
        height: Alto del grafico
    """
    if not analyses:
        print("  No hay analisis disponibles.")
        return

    current_idx = 0
    n_analyses = len(analyses)

    while True:
        clear_screen()

        analysis = analyses[current_idx]
        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Construir titulo
        x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
        title = f"[{current_idx+1}/{n_analyses}] {tc.method} + {storm.type.upper()} Tr{storm.return_period}{x_str}"

        # Info adicional
        from hidropluvial.cli.formatters import format_flow, format_volume_hm3

        tp_str = f"{hydro.tp_unit_min:.1f}" if hydro.tp_unit_min else "-"
        tb_str = f"{hydro.tb_min:.1f}" if hydro.tb_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"

        info_lines = [
            f"\n  Sesion: {session_name}",
            f"  Hidrograma {current_idx + 1} de {n_analyses}",
            "",
            f"  Tc:   {tc.tc_min:.1f} min",
            f"  tp:   {tp_str} min",
            f"  X:    {x_str}",
            f"  tb:   {tb_str} min",
            f"  P:    {storm.total_depth_mm:.1f} mm",
            f"  Pe:   {hydro.runoff_mm:.1f} mm",
            f"  Qp:   {format_flow(hydro.peak_flow_m3s)} m3/s",
            f"  Tp:   {hydro.time_to_peak_min:.1f} min",
            f"  Vol:  {format_volume_hm3(hydro.volume_m3)} hm3",
            "",
            "  Controles:",
            "    <- / ->  Cambiar hidrograma",
            "    q / ESC  Salir",
        ]

        # Plotear
        if hydro.time_hr and hydro.flow_m3s:
            plot_hydrograph(
                list(hydro.time_hr),
                list(hydro.flow_m3s),
                title,
                info_lines,
                width,
                height,
            )
        else:
            print(f"\n  {title}")
            print("  (Sin datos de hidrograma)")
            for line in info_lines:
                print(line)

        # Esperar input
        key = get_key()

        if key == 'q' or key == 'esc':
            clear_screen()
            print(f"\n  Visor cerrado. Sesion: {session_name}\n")
            break
        elif key == 'left':
            current_idx = (current_idx - 1) % n_analyses
        elif key == 'right':
            current_idx = (current_idx + 1) % n_analyses
        elif key == 'up':
            # Ir al primero
            current_idx = 0
        elif key == 'down':
            # Ir al ultimo
            current_idx = n_analyses - 1
