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
        elif key == b'e' or key == b'E':
            return 'e'
        elif key == b'd' or key == b'D':
            return 'd'
        elif key == b's' or key == b'S':
            return 's'
        elif key == b'y' or key == b'Y':
            return 'y'
        elif key == b'n' or key == b'N':
            return 'n'
        elif key == b'i' or key == b'I':
            return 'i'
        elif key == b'a' or key == b'A':
            return 'a'
        elif key == b'b' or key == b'B':
            return 'b'
        elif key == b'x' or key == b'X':
            return 'x'
        elif key == b' ':  # Espacio
            return 'space'
        elif key == b'\r':  # Enter
            return 'enter'
        elif key == b'\x08':  # Backspace
            return 'backspace'
        elif key == b'\t':  # Tab
            return 'tab'

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
            elif key == 'e' or key == 'E':
                return 'e'
            elif key == 'd' or key == 'D':
                return 'd'
            elif key == 's' or key == 'S':
                return 's'
            elif key == 'y' or key == 'Y':
                return 'y'
            elif key == 'n' or key == 'N':
                return 'n'
            elif key == 'i' or key == 'I':
                return 'i'
            elif key == 'a' or key == 'A':
                return 'a'
            elif key == 'b' or key == 'B':
                return 'b'
            elif key == 'x' or key == 'X':
                return 'x'
            elif key == ' ':  # Espacio
                return 'space'
            elif key == '\r' or key == '\n':
                return 'enter'
            elif key == '\x7f' or key == '\x08':  # Backspace (Unix/Mac)
                return 'backspace'
            elif key == '\t':  # Tab
                return 'tab'

            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
