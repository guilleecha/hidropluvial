"""
Validadores centralizados para entradas CLI.

Proporciona funciones de validación con mensajes de error consistentes.
"""

from typing import Optional
import typer

from hidropluvial.cli.theme import print_error, print_warning


# =============================================================================
# VALIDADORES DE RANGO
# =============================================================================

def validate_cn(value: int, exit_on_error: bool = True) -> bool:
    """
    Valida que el Curve Number esté en rango válido (30-100).

    Args:
        value: Valor de CN a validar
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if not 30 <= value <= 100:
        print_error(f"CN debe estar entre 30 y 100 (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_c_coefficient(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que el coeficiente de escorrentía C esté en rango válido (0-1).

    Args:
        value: Valor de C a validar
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if not 0 < value <= 1:
        print_error(f"Coeficiente C debe estar entre 0 y 1 (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_slope(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que la pendiente sea positiva y razonable.

    Args:
        value: Pendiente en m/m o %
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"La pendiente debe ser positiva (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    if value > 1:
        # Probablemente en porcentaje, advertir pero no fallar
        print_warning(f"Pendiente={value} parece estar en %. Asegúrese de usar m/m si corresponde.")
    return True


def validate_area(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que el área sea positiva.

    Args:
        value: Área en ha o km²
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"El área debe ser positiva (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_length(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que la longitud sea positiva.

    Args:
        value: Longitud en m o km
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"La longitud debe ser positiva (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_p310(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que P3,10 esté en rango realista para Uruguay (30-150 mm).

    Args:
        value: P3,10 en mm
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"P3,10 debe ser positivo (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    if not 30 <= value <= 150:
        print_warning(f"P3,10={value} mm está fuera del rango típico para Uruguay (30-150 mm)")
    return True


def validate_return_period(value: int, exit_on_error: bool = True) -> bool:
    """
    Valida que el período de retorno sea válido.

    Args:
        value: Período de retorno en años
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    valid_periods = [2, 5, 10, 25, 50, 100]
    if value not in valid_periods:
        print_error(f"Período de retorno debe ser uno de {valid_periods} (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_duration(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que la duración sea positiva y razonable.

    Args:
        value: Duración en horas
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"La duración debe ser positiva (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    if value > 72:
        print_warning(f"Duración={value} hr es muy larga. Tormentas típicas son < 24 hr.")
    return True


def validate_amc(value: str, exit_on_error: bool = True) -> bool:
    """
    Valida que la condición de humedad antecedente sea válida.

    Args:
        value: AMC como string ("I", "II", "III")
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    valid_amc = ["I", "II", "III", "1", "2", "3"]
    if value.upper() not in valid_amc:
        print_error(f"AMC debe ser I, II o III (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_x_factor(value: float, exit_on_error: bool = True) -> bool:
    """
    Valida que el factor X esté en rango típico (0.5-3.0).

    Args:
        value: Factor X del hidrograma
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    if value <= 0:
        print_error(f"Factor X debe ser positivo (recibido: {value})")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    if not 0.5 <= value <= 3.0:
        print_warning(f"Factor X={value} está fuera del rango típico (0.5-3.0)")
    return True


# =============================================================================
# VALIDADORES DE TIPO
# =============================================================================

def validate_storm_type(value: str, exit_on_error: bool = True) -> bool:
    """
    Valida que el tipo de tormenta sea válido.

    Args:
        value: Tipo de tormenta
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    valid_types = ["gz", "ab", "scs_i", "scs_ia", "scs_ii", "scs_iii", "huff1", "huff2", "huff3", "huff4", "bimodal"]
    if value.lower() not in valid_types:
        print_error(f"Tipo de tormenta inválido: {value}")
        typer.echo(f"  Tipos válidos: {', '.join(valid_types)}")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True


def validate_tc_method(value: str, exit_on_error: bool = True) -> bool:
    """
    Valida que el método de Tc sea válido.

    Args:
        value: Nombre del método
        exit_on_error: Si True, termina el programa con error

    Returns:
        True si es válido, False si no
    """
    valid_methods = ["kirpich", "temez", "desbordes", "nrcs", "california", "giandotti"]
    if value.lower() not in valid_methods:
        print_error(f"Método de Tc inválido: {value}")
        typer.echo(f"  Métodos válidos: {', '.join(valid_methods)}")
        if exit_on_error:
            raise typer.Exit(1)
        return False
    return True
