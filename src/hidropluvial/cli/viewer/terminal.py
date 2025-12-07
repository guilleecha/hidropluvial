"""
Utilidades de terminal para el visor interactivo.

Funciones para limpiar pantalla y capturar teclas.
"""

import os
import sys


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
        - 'enter': tecla enter
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
        elif key == b'f' or key == b'F':
            return 'f'
        elif key == b'c' or key == b'C':
            return 'c'
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
            elif key == 'f' or key == 'F':
                return 'f'
            elif key == 'c' or key == 'C':
                return 'c'
            elif key == '\r' or key == '\n':
                return 'enter'

            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
