"""
Comandos CLI para calculo de escorrentia.
"""

from typing import Annotated, Optional

import typer
import questionary
from questionary import Style

from hidropluvial.config import AntecedentMoistureCondition
from hidropluvial.core import calculate_scs_runoff, rational_peak_flow
from hidropluvial.core.coefficients import (
    C_TABLES,
    CN_TABLES,
    ChowCEntry,
    FHWACEntry,
    weighted_c,
    weighted_cn,
)
from hidropluvial.cli.theme import (
    print_c_table_chow, print_c_table_fhwa, print_c_table_simple,
    print_cn_table, print_info,
)
from hidropluvial.session import WeightedCoefficient, CoverageItem

# Crear sub-aplicación
runoff_app = typer.Typer(help="Calculo de escorrentia")

# Estilo para questionary
RUNOFF_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('answer', 'fg:cyan'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:green'),
])


@runoff_app.command("cn")
def runoff_cn(
    rainfall: Annotated[float, typer.Argument(help="Precipitación total en mm")],
    cn: Annotated[int, typer.Argument(help="Número de curva (30-100)")],
    lambda_coef: Annotated[float, typer.Option("--lambda", "-l", help="Coeficiente λ")] = 0.2,
    amc: Annotated[str, typer.Option(help="AMC: I (seco), II (promedio), III (húmedo)")] = "II",
):
    """Calcula escorrentía usando método SCS-CN."""
    amc_map = {
        "I": AntecedentMoistureCondition.DRY,
        "II": AntecedentMoistureCondition.AVERAGE,
        "III": AntecedentMoistureCondition.WET,
    }

    if amc.upper() not in amc_map:
        typer.echo("Error: AMC debe ser I, II o III", err=True)
        raise typer.Exit(1)

    result = calculate_scs_runoff(rainfall, cn, lambda_coef, amc_map[amc.upper()])

    typer.echo(f"\n{'='*40}")
    typer.echo(f"Método SCS Curve Number")
    typer.echo(f"{'='*40}")
    typer.echo(f"Precipitación:     {result.rainfall_mm:>10.2f} mm")
    typer.echo(f"CN (AMC {amc}):        {result.cn_used:>10d}")
    typer.echo(f"Retención S:       {result.retention_mm:>10.2f} mm")
    typer.echo(f"Abstracción Ia:    {result.initial_abstraction_mm:>10.2f} mm")
    typer.echo(f"{'='*40}")
    typer.echo(f"Escorrentía Q:     {result.runoff_mm:>10.2f} mm")
    typer.echo(f"Coef. escorrentía: {result.runoff_mm/result.rainfall_mm:>10.2%}")


@runoff_app.command("rational")
def runoff_rational(
    c: Annotated[float, typer.Argument(help="Coeficiente de escorrentía (0-1), ya ajustado por Tr")],
    intensity: Annotated[float, typer.Argument(help="Intensidad en mm/hr")],
    area: Annotated[float, typer.Argument(help="Área en hectáreas")],
):
    """Calcula caudal pico usando método racional.

    El coeficiente C debe incluir el ajuste por período de retorno.
    Use tablas como Ven Te Chow o DINAGUA que proporcionan C según Tr.
    """
    q = rational_peak_flow(c, intensity, area)

    typer.echo(f"\nMétodo Racional")
    typer.echo(f"C = {c:.2f}")
    typer.echo(f"i = {intensity:.2f} mm/hr")
    typer.echo(f"A = {area:.2f} ha")
    typer.echo(f"Q = {q:.3f} m3/s")


@runoff_app.command("weighted-c")
def runoff_weighted_c(
    area_total: Annotated[Optional[float], typer.Option("--area", "-a", help="Area total de la cuenca (ha)")] = None,
    table: Annotated[str, typer.Option("--table", "-t", help="Tabla: fhwa, chow, uruguay")] = "chow",
):
    """
    Calcula coeficiente C ponderado por area de forma interactiva.

    Muestra la tabla de coeficientes seleccionada y permite asignar
    areas a diferentes coberturas. Calcula el C ponderado final.

    IMPORTANTE: Para la tabla Ven Te Chow, se selecciona C para Tr=2 anos.
    El valor se ajustara automaticamente segun el Tr de cada analisis.

    Tablas disponibles:
    - chow: Ven Te Chow (C base Tr2, se ajusta por Tr)
    - fhwa: FHWA HEC-22 (C base con factor de ajuste)
    - uruguay: Tabla regional simplificada

    Ejemplos:
        hp runoff weighted-c --area 5.5
        hp runoff weighted-c --table chow
        hp runoff weighted-c -a 10 -t fhwa
    """
    if table.lower() not in C_TABLES:
        typer.echo(f"Error: Tabla '{table}' no disponible. Opciones: {list(C_TABLES.keys())}")
        raise typer.Exit(1)

    table_name, table_data = C_TABLES[table.lower()]
    first_entry = table_data[0]
    is_chow = isinstance(first_entry, ChowCEntry)
    is_fhwa = isinstance(first_entry, FHWACEntry)

    # Para Ven Te Chow: siempre Tr=2 como base
    # Para FHWA: Tr base (<=10)
    tr = 2 if is_chow else 10

    if is_chow:
        print_info("Tabla Ven Te Chow: selección basada en Tr=2 años")
        print_info("El coeficiente se ajustará automáticamente según el Tr del análisis.")
        print_c_table_chow(table_data, table_name, selection_mode=True)
    elif is_fhwa:
        print_c_table_fhwa(table_data, table_name, tr=tr)
    else:
        print_c_table_simple(table_data, table_name)

    # Solicitar area total si no se proporciono
    if area_total is None:
        area_str = questionary.text(
            "Area total de la cuenca (ha):",
            validate=lambda x: _validate_positive(x),
            style=RUNOFF_STYLE,
        ).ask()
        if area_str is None:
            raise typer.Exit()
        area_total = float(area_str)

    typer.echo(f"\n  Area total: {area_total:.2f} ha")
    typer.echo("  Asigna coberturas al area. Presiona Enter sin valor para terminar.\n")

    areas = []
    coefficients = []
    descriptions = []
    table_indices = []  # Para recálculo por Tr
    area_remaining = area_total

    while area_remaining > 0.001:  # Tolerancia para errores de punto flotante
        typer.echo(f"  Area restante: {area_remaining:.3f} ha ({area_remaining/area_total*100:.1f}%)")

        # Construir choices segun tipo de tabla - Chow siempre usa Tr2
        choices = []
        for i, e in enumerate(table_data):
            if is_chow:
                c_val = e.c_tr2  # Siempre Tr2 para Ven Te Chow
                choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f} para Tr2)")
            elif is_fhwa:
                c_val = e.c_base
                choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")
            else:
                choices.append(f"{i+1}. {e.category} - {e.description} (C={e.c_recommended:.2f})")

        choices.append("Asignar todo el area restante a una cobertura")
        choices.append("Terminar (area restante queda sin asignar)")

        selection = questionary.select(
            "Selecciona cobertura:",
            choices=choices,
            style=RUNOFF_STYLE,
        ).ask()

        if selection is None or "Terminar" in selection:
            break

        if "Asignar todo" in selection:
            # Seleccionar cobertura para area restante
            cov_choices = []
            for i, e in enumerate(table_data):
                if is_chow:
                    c_val = e.c_tr2
                elif is_fhwa:
                    c_val = e.c_base
                else:
                    c_val = e.c_recommended
                cov_choices.append(f"{i+1}. {e.category} - {e.description} (C={c_val:.2f})")

            cov_selection = questionary.select(
                "Cobertura para area restante:",
                choices=cov_choices,
                style=RUNOFF_STYLE,
            ).ask()
            if cov_selection:
                idx = int(cov_selection.split(".")[0]) - 1
                entry = table_data[idx]
                if is_chow:
                    c_val = entry.c_tr2
                elif is_fhwa:
                    c_val = entry.c_base
                else:
                    c_val = entry.c_recommended
                areas.append(area_remaining)
                coefficients.append(c_val)
                descriptions.append(f"{entry.category}: {entry.description}")
                table_indices.append(idx)
                area_remaining = 0
            break

        # Obtener indice de cobertura
        idx = int(selection.split(".")[0]) - 1
        entry = table_data[idx]

        # Solicitar area
        area_str = questionary.text(
            f"Area para '{entry.description}' (ha, max {area_remaining:.3f}):",
            validate=lambda x, max_a=area_remaining: _validate_area(x, max_a),
            style=RUNOFF_STYLE,
        ).ask()

        if area_str is None or area_str.strip() == "":
            break

        area_val = float(area_str)
        if area_val > 0:
            # Obtener C segun tipo de entrada
            if is_chow:
                c_val = entry.c_tr2
                typer.echo(f"  C = {c_val:.2f} (tabla Ven Te Chow, Tr=2)")
            elif is_fhwa:
                c_val = entry.c_base
                typer.echo(f"  C = {c_val:.2f} (tabla FHWA, base)")
            else:
                # Preguntar si usar valor tipico o personalizado
                use_typical = questionary.confirm(
                    f"Usar C tipico = {entry.c_recommended:.2f}? (No para ingresar valor)",
                    default=True,
                    style=RUNOFF_STYLE,
                ).ask()

                if use_typical:
                    c_val = entry.c_recommended
                else:
                    c_str = questionary.text(
                        f"Ingresa C ({entry.c_min:.2f}-{entry.c_max:.2f}):",
                        default=f"{entry.c_recommended:.2f}",
                        validate=lambda x, e=entry: _validate_c_range(x, e.c_min, e.c_max),
                        style=RUNOFF_STYLE,
                    ).ask()
                    c_val = float(c_str)

            areas.append(area_val)
            coefficients.append(c_val)
            descriptions.append(f"{entry.category}: {entry.description}")
            table_indices.append(idx)
            area_remaining -= area_val

            typer.echo(f"  + {area_val:.3f} ha con C={c_val:.2f}")

    # Calcular resultado
    if not areas:
        typer.echo("\n  No se asignaron coberturas.")
        raise typer.Exit(1)

    c_weighted = weighted_c(areas, coefficients)

    # Mostrar resumen
    typer.echo("\n" + "=" * 60)
    typer.echo("  RESUMEN DE COBERTURAS")
    typer.echo("=" * 60)
    typer.echo(f"  {'Cobertura':<35} {'Area (ha)':<12} {'C':<8}")
    typer.echo("  " + "-" * 55)

    for desc, area, c in zip(descriptions, areas, coefficients):
        pct = area / area_total * 100
        typer.echo(f"  {desc:<35} {area:>8.3f} ({pct:>4.1f}%) {c:>6.2f}")

    if area_remaining > 0.001:
        pct = area_remaining / area_total * 100
        typer.echo(f"  {'(Sin asignar)':<35} {area_remaining:>8.3f} ({pct:>4.1f}%)")

    typer.echo("  " + "-" * 55)
    typer.echo(f"  {'TOTAL':<35} {sum(areas):>8.3f} ha")
    typer.echo("=" * 60)

    if is_chow:
        typer.echo(f"  COEFICIENTE C PONDERADO (Tr=2): {c_weighted:.3f}")
        typer.echo("")
        typer.echo("  Valores para otros periodos de retorno:")

        # Calcular valores exactos usando la tabla
        for tr_val in [5, 10, 25, 50, 100]:
            c_tr = 0.0
            for i, (area, idx) in enumerate(zip(areas, table_indices)):
                entry = table_data[idx]
                c_i = entry.get_c(tr_val)
                c_tr += area * c_i
            c_tr /= sum(areas)
            typer.echo(f"    Tr={tr_val:>3}: C = {c_tr:.3f}")
    else:
        typer.echo(f"  COEFICIENTE C PONDERADO: {c_weighted:.3f}")

    typer.echo("=" * 60)

    return c_weighted


@runoff_app.command("weighted-cn")
def runoff_weighted_cn(
    area_total: Annotated[Optional[float], typer.Option("--area", "-a", help="Area total de la cuenca (ha)")] = None,
    soil_group: Annotated[str, typer.Option("--soil", "-s", help="Grupo hidrologico: A, B, C, D")] = "B",
):
    """
    Calcula Curva Numero CN ponderada por area de forma interactiva.

    Permite mezclar coberturas de tablas urbanas y agricolas en la misma
    cuenca. En cada iteracion se puede elegir de que tabla agregar cobertura.

    Ejemplos:
        hp runoff weighted-cn --area 50
        hp runoff weighted-cn --soil C --area 100
    """
    if soil_group.upper() not in ['A', 'B', 'C', 'D']:
        typer.echo("Error: Grupo hidrologico debe ser A, B, C o D")
        raise typer.Exit(1)

    soil = soil_group.upper()

    # Solicitar area total si no se proporciono
    if area_total is None:
        area_str = questionary.text(
            "Area total de la cuenca (ha):",
            validate=lambda x: _validate_positive(x),
            style=RUNOFF_STYLE,
        ).ask()
        if area_str is None:
            raise typer.Exit()
        area_total = float(area_str)

    typer.echo(f"\n  Area total: {area_total:.2f} ha")
    typer.echo(f"  Grupo hidrologico de suelo: {soil}")
    typer.echo("  Puedes mezclar coberturas urbanas y agricolas.\n")

    areas = []
    cn_values = []
    descriptions = []
    area_remaining = area_total

    # Mantener track de la tabla actual para mostrarla
    current_table = None

    while area_remaining > 0.001:
        typer.echo(f"\n  Area restante: {area_remaining:.3f} ha ({area_remaining/area_total*100:.1f}%)")

        # Elegir tabla o accion
        table_choice = questionary.select(
            "Agregar cobertura de:",
            choices=[
                "Tabla Urbana (residencial, comercial, industrial)",
                "Tabla Agricola (cultivos, pasturas, bosque)",
                "Asignar todo el area restante",
                "Terminar",
            ],
            style=RUNOFF_STYLE,
        ).ask()

        if table_choice is None or "Terminar" in table_choice:
            break

        if "Asignar todo" in table_choice:
            # Elegir tabla para area restante
            final_table = questionary.select(
                "De que tabla?",
                choices=["Urbana", "Agricola"],
                style=RUNOFF_STYLE,
            ).ask()

            if final_table is None:
                break

            table_key = "urban" if "Urbana" in final_table else "agricultural"
            _, table_data = CN_TABLES[table_key]

            cov_choices = []
            for i, e in enumerate(table_data):
                cn = e.get_cn(soil)
                cond = f" ({e.condition})" if e.condition != "N/A" else ""
                cov_choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

            cov_selection = questionary.select(
                "Cobertura para area restante:",
                choices=cov_choices,
                style=RUNOFF_STYLE,
            ).ask()

            if cov_selection:
                idx = int(cov_selection.split(".")[0]) - 1
                entry = table_data[idx]
                cn = entry.get_cn(soil)
                areas.append(area_remaining)
                cn_values.append(cn)
                cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
                prefix = "[U]" if table_key == "urban" else "[A]"
                descriptions.append(f"{prefix} {entry.category}: {entry.description}{cond}")
                area_remaining = 0
            break

        # Determinar tabla seleccionada
        if "Urbana" in table_choice:
            table_key = "urban"
            table_name, table_data = CN_TABLES["urban"]
        else:
            table_key = "agricultural"
            table_name, table_data = CN_TABLES["agricultural"]

        # Mostrar tabla si cambio
        if current_table != table_key:
            print_cn_table(table_data, table_name)
            current_table = table_key

        # Seleccionar cobertura de la tabla elegida
        choices = []
        for i, e in enumerate(table_data):
            cn = e.get_cn(soil)
            cond = f" ({e.condition})" if e.condition != "N/A" else ""
            choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

        choices.append("Volver (elegir otra tabla)")

        selection = questionary.select(
            "Selecciona cobertura:",
            choices=choices,
            style=RUNOFF_STYLE,
        ).ask()

        if selection is None or "Volver" in selection:
            continue

        # Obtener indice
        idx = int(selection.split(".")[0]) - 1
        entry = table_data[idx]
        cn = entry.get_cn(soil)

        # Solicitar area
        area_str = questionary.text(
            f"Area para '{entry.description}' (ha, max {area_remaining:.3f}):",
            validate=lambda x, max_a=area_remaining: _validate_area(x, max_a),
            style=RUNOFF_STYLE,
        ).ask()

        if area_str is None or area_str.strip() == "":
            continue

        area_val = float(area_str)
        if area_val > 0:
            areas.append(area_val)
            cn_values.append(cn)
            cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
            prefix = "[U]" if table_key == "urban" else "[A]"
            descriptions.append(f"{prefix} {entry.category}: {entry.description}{cond}")
            area_remaining -= area_val

            typer.echo(f"  + {area_val:.3f} ha con CN={cn}")

    # Calcular resultado
    if not areas:
        typer.echo("\n  No se asignaron coberturas.")
        raise typer.Exit(1)

    cn_weighted_val = weighted_cn(areas, cn_values)

    # Mostrar resumen
    typer.echo("\n" + "=" * 70)
    typer.echo(f"  RESUMEN DE COBERTURAS (Grupo hidrologico {soil})")
    typer.echo("=" * 70)
    typer.echo(f"  {'Cobertura':<45} {'Area (ha)':<12} {'CN':<6}")
    typer.echo("  " + "-" * 65)

    for desc, area, cn in zip(descriptions, areas, cn_values):
        pct = area / area_total * 100
        typer.echo(f"  {desc:<45} {area:>8.3f} ({pct:>4.1f}%) {cn:>4}")

    if area_remaining > 0.001:
        pct = area_remaining / area_total * 100
        typer.echo(f"  {'(Sin asignar)':<45} {area_remaining:>8.3f} ({pct:>4.1f}%)")

    typer.echo("  " + "-" * 65)
    typer.echo(f"  {'TOTAL':<45} {sum(areas):>8.3f} ha")
    typer.echo("=" * 70)
    typer.echo(f"  CURVA NUMERO CN PONDERADA: {cn_weighted_val:.1f}")
    typer.echo("  [U] = Urbana, [A] = Agricola")
    typer.echo("=" * 70)

    return cn_weighted_val


def collect_weighted_cn_interactive(
    area_total: float,
    soil_group: str = "B",
    echo_fn=typer.echo,
) -> Optional[WeightedCoefficient]:
    """
    Recopila datos de CN ponderado de forma interactiva.

    Args:
        area_total: Área total de la cuenca en ha
        soil_group: Grupo hidrológico (A, B, C, D)
        echo_fn: Función para mostrar mensajes (default: typer.echo)

    Returns:
        WeightedCoefficient con los datos de ponderación, o None si se cancela
    """
    soil = soil_group.upper()
    if soil not in ['A', 'B', 'C', 'D']:
        echo_fn("Error: Grupo hidrológico debe ser A, B, C o D")
        return None

    echo_fn(f"\n  Área total: {area_total:.2f} ha")
    echo_fn(f"  Grupo hidrológico de suelo: {soil}")
    echo_fn("  Puedes mezclar coberturas urbanas y agrícolas.\n")

    areas = []
    cn_values = []
    descriptions = []
    area_remaining = area_total
    current_table = None

    while area_remaining > 0.001:
        echo_fn(f"\n  Área restante: {area_remaining:.3f} ha ({area_remaining/area_total*100:.1f}%)")

        table_choice = questionary.select(
            "Agregar cobertura de:",
            choices=[
                "Tabla Urbana (residencial, comercial, industrial)",
                "Tabla Agrícola (cultivos, pasturas, bosque)",
                "Asignar todo el área restante",
                "Terminar",
            ],
            style=RUNOFF_STYLE,
        ).ask()

        if table_choice is None or "Terminar" in table_choice:
            break

        if "Asignar todo" in table_choice:
            final_table = questionary.select(
                "¿De qué tabla?",
                choices=["Urbana", "Agrícola"],
                style=RUNOFF_STYLE,
            ).ask()

            if final_table is None:
                break

            table_key = "urban" if "Urbana" in final_table else "agricultural"
            _, table_data = CN_TABLES[table_key]

            cov_choices = []
            for i, e in enumerate(table_data):
                cn = e.get_cn(soil)
                cond = f" ({e.condition})" if e.condition != "N/A" else ""
                cov_choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

            cov_selection = questionary.select(
                "Cobertura para área restante:",
                choices=cov_choices,
                style=RUNOFF_STYLE,
            ).ask()

            if cov_selection:
                idx = int(cov_selection.split(".")[0]) - 1
                entry = table_data[idx]
                cn = entry.get_cn(soil)
                areas.append(area_remaining)
                cn_values.append(cn)
                cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
                prefix = "[U]" if table_key == "urban" else "[A]"
                descriptions.append(f"{prefix} {entry.category}: {entry.description}{cond}")
                area_remaining = 0
            break

        # Determinar tabla seleccionada
        if "Urbana" in table_choice:
            table_key = "urban"
            table_name, table_data = CN_TABLES["urban"]
        else:
            table_key = "agricultural"
            table_name, table_data = CN_TABLES["agricultural"]

        if current_table != table_key:
            print_cn_table(table_data, table_name)
            current_table = table_key

        choices = []
        for i, e in enumerate(table_data):
            cn = e.get_cn(soil)
            cond = f" ({e.condition})" if e.condition != "N/A" else ""
            choices.append(f"{i+1}. {e.category} - {e.description}{cond} (CN={cn})")

        choices.append("Volver (elegir otra tabla)")

        selection = questionary.select(
            "Selecciona cobertura:",
            choices=choices,
            style=RUNOFF_STYLE,
        ).ask()

        if selection is None or "Volver" in selection:
            continue

        idx = int(selection.split(".")[0]) - 1
        entry = table_data[idx]
        cn = entry.get_cn(soil)

        area_str = questionary.text(
            f"Área para '{entry.description}' (ha, max {area_remaining:.3f}):",
            validate=lambda x, max_a=area_remaining: _validate_area(x, max_a),
            style=RUNOFF_STYLE,
        ).ask()

        if area_str is None or area_str.strip() == "":
            continue

        area_val = float(area_str)
        if area_val > 0:
            areas.append(area_val)
            cn_values.append(cn)
            cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
            prefix = "[U]" if table_key == "urban" else "[A]"
            descriptions.append(f"{prefix} {entry.category}: {entry.description}{cond}")
            area_remaining -= area_val
            echo_fn(f"  + {area_val:.3f} ha con CN={cn}")

    if not areas:
        return None

    cn_weighted_val = weighted_cn(areas, cn_values)

    # Construir objeto WeightedCoefficient
    items = []
    for desc, area, cn in zip(descriptions, areas, cn_values):
        pct = (area / area_total) * 100
        items.append(CoverageItem(
            description=desc,
            area_ha=area,
            value=float(cn),
            percentage=pct,
        ))

    result = WeightedCoefficient(
        type="cn",
        table_used=f"NRCS (Grupo {soil})",
        weighted_value=cn_weighted_val,
        items=items,
    )

    # Mostrar resumen
    echo_fn("\n" + "=" * 70)
    echo_fn(f"  RESUMEN DE COBERTURAS (Grupo hidrológico {soil})")
    echo_fn("=" * 70)
    echo_fn(f"  {'Cobertura':<45} {'Área (ha)':<12} {'CN':<6}")
    echo_fn("  " + "-" * 65)

    for item in items:
        echo_fn(f"  {item.description:<45} {item.area_ha:>8.3f} ({item.percentage:>4.1f}%) {item.value:>4.0f}")

    if area_remaining > 0.001:
        pct = area_remaining / area_total * 100
        echo_fn(f"  {'(Sin asignar)':<45} {area_remaining:>8.3f} ({pct:>4.1f}%)")

    echo_fn("  " + "-" * 65)
    echo_fn(f"  {'TOTAL':<45} {sum(areas):>8.3f} ha")
    echo_fn("=" * 70)
    echo_fn(f"  CURVA NÚMERO CN PONDERADA: {cn_weighted_val:.1f}")
    echo_fn("=" * 70)

    return result


@runoff_app.command("show-tables")
def show_tables(
    table_type: Annotated[str, typer.Argument(help="Tipo: c o cn")] = "c",
):
    """
    Muestra las tablas de coeficientes disponibles.

    Ejemplos:
        hp runoff show-tables c
        hp runoff show-tables cn
    """
    if table_type.lower() == "c":
        typer.echo("\n  Tablas de Coeficiente C disponibles:")
        for key, (name, _) in C_TABLES.items():
            typer.echo(f"    {key}: {name}")
        typer.echo("\n  Usa: hp runoff weighted-c --table <nombre>")
    elif table_type.lower() == "cn":
        typer.echo("\n  Tablas de Curva Numero CN disponibles:")
        for key, (name, _) in CN_TABLES.items():
            typer.echo(f"    {key}: {name}")
        typer.echo("\n  Usa: hp runoff weighted-cn (permite mezclar tablas)")
    else:
        typer.echo("Error: Tipo debe ser 'c' o 'cn'")


def _validate_positive(value: str) -> bool | str:
    """Valida numero positivo."""
    try:
        v = float(value)
        if v <= 0:
            return "Debe ser un numero positivo"
        return True
    except ValueError:
        return "Debe ser un numero valido"


def _validate_area(value: str, max_area: float) -> bool | str:
    """Valida area dentro del rango."""
    if value.strip() == "":
        return True
    try:
        v = float(value)
        if v < 0:
            return "El area no puede ser negativa"
        if v > max_area:
            return f"El area no puede exceder {max_area:.3f} ha"
        return True
    except ValueError:
        return "Debe ser un numero valido"


def _validate_c_range(value: str, c_min: float, c_max: float) -> bool | str:
    """Valida C en rango."""
    try:
        v = float(value)
        if v < c_min or v > c_max:
            return f"C debe estar entre {c_min:.2f} y {c_max:.2f}"
        return True
    except ValueError:
        return "Debe ser un numero valido"
