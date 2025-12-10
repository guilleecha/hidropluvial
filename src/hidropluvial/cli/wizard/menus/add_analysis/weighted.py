"""
Calculadores de coeficientes ponderados para C y CN.

Proporciona funciones para calcular coeficientes de escorrentía
usando tablas de coberturas y ponderación por área.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hidropluvial.models import Basin


def get_c_popup_options(calculate_fn) -> list:
    """
    Retorna opciones para el popup de coeficiente C.

    Args:
        calculate_fn: Función que recibe table_key y calcula C ponderado
    """
    return [
        {"key": "d", "label": "Ingresar valor directo", "value": "__input__"},
        {"separator": True, "title": "Valores típicos"},
        {"key": "1", "label": "Urbano denso (C = 0.85)", "value": 0.85, "hint": "comercial, industrial"},
        {"key": "2", "label": "Residencial (C = 0.65)", "value": 0.65, "hint": "viviendas, media densidad"},
        {"key": "3", "label": "Mixto (C = 0.50)", "value": 0.50, "hint": "suburbano, baja densidad"},
        {"key": "4", "label": "Rural (C = 0.35)", "value": 0.35, "hint": "pasturas, cultivos"},
        {"separator": True, "title": "Ponderador (Tablas)"},
        {"key": "c", "label": "Ven Te Chow", "action": lambda: calculate_fn("chow"), "hint": "Applied Hydrology"},
        {"key": "f", "label": "FHWA HEC-22", "action": lambda: calculate_fn("fhwa"), "hint": "Federal Highway"},
    ]


def get_cn_popup_options(calculate_fn) -> list:
    """
    Retorna opciones para el popup de CN.

    Args:
        calculate_fn: Función que recibe table_key y calcula CN ponderado
    """
    return [
        {"key": "d", "label": "Ingresar valor directo", "value": "__input__"},
        {"separator": True, "title": "Valores típicos"},
        {"key": "1", "label": "Urbano (CN = 90)", "value": 90, "hint": "muy impermeable"},
        {"key": "2", "label": "Residencial (CN = 80)", "value": 80, "hint": "lotes medianos"},
        {"key": "3", "label": "Suburbano (CN = 70)", "value": 70, "hint": "baja densidad"},
        {"key": "4", "label": "Rural (CN = 60)", "value": 60, "hint": "agricultura, pastura"},
        {"separator": True, "title": "Ponderador (Tablas)"},
        {"key": "t", "label": "SCS TR-55 Unificada", "action": lambda: calculate_fn("unified"), "hint": "Urbana + Agrícola"},
        {"key": "u", "label": "SCS TR-55 Urbana", "action": lambda: calculate_fn("urban"), "hint": "Residencial, comercial"},
        {"key": "a", "label": "SCS TR-55 Agrícola", "action": lambda: calculate_fn("agricultural"), "hint": "Cultivos, pasturas"},
    ]


def calculate_weighted_c(basin: "Basin", table_key: str) -> Optional[float]:
    """
    Calcula C usando el ponderador por coberturas con una tabla específica.

    Args:
        basin: Cuenca para obtener área total
        table_key: Clave de tabla ("chow", "fhwa", "uruguay")

    Returns:
        Valor de C ponderado o None si se cancela
    """
    from hidropluvial.cli.viewer.terminal import clear_screen
    from hidropluvial.core.coefficients import (
        C_TABLES, ChowCEntry, FHWACEntry, weighted_c
    )
    from hidropluvial.cli.viewer.coverage_viewer import (
        interactive_coverage_viewer, CoverageRow
    )
    from hidropluvial.cli.theme import print_coverage_assignments_table

    clear_screen()

    table_name, table_data = C_TABLES[table_key]
    first_entry = table_data[0]
    is_chow = isinstance(first_entry, ChowCEntry)
    is_fhwa = isinstance(first_entry, FHWACEntry)

    def get_c_value(entry):
        if is_chow:
            return entry.c_tr2
        elif is_fhwa:
            return entry.c_base
        return entry.c_recommended

    # Construir filas para el visor
    rows = []
    for i, entry in enumerate(table_data):
        c_val = get_c_value(entry)
        row = CoverageRow(
            index=i,
            category=entry.category,
            description=entry.description,
            value=c_val,
            value_label="C",
        )
        # Incluir todos los valores por Tr para mostrar en la tabla
        if is_chow:
            row.c_tr2 = entry.c_tr2
            row.c_tr5 = entry.c_tr5
            row.c_tr10 = entry.c_tr10
            row.c_tr25 = entry.c_tr25
            row.c_tr50 = entry.c_tr50
            row.c_tr100 = entry.c_tr100
        elif is_fhwa:
            # FHWA: calcular valores por Tr usando factores de ajuste
            row.c_tr2 = entry.get_c(2)
            row.c_tr5 = entry.get_c(5)
            row.c_tr10 = entry.get_c(10)
            row.c_tr25 = entry.get_c(25)
            row.c_tr50 = entry.get_c(50)
            row.c_tr100 = entry.get_c(100)
        rows.append(row)

    # Mostrar visor interactivo
    coverage_data = interactive_coverage_viewer(
        rows=rows,
        total_area=basin.area_ha,
        value_label="C",
        table_name=f"Tabla {table_name}",
    )

    if not coverage_data:
        return None

    # Calcular C ponderado final
    areas = [d["area"] for d in coverage_data]
    coefficients = [d["c_val"] for d in coverage_data]
    c_weighted = weighted_c(areas, coefficients)

    # Mostrar resultado final
    print_coverage_assignments_table(
        coverage_data, basin.area_ha, "C", c_weighted,
        title="Resultado Final"
    )

    return c_weighted


def calculate_weighted_cn(basin: "Basin", table_key: str, menu=None) -> Optional[int]:
    """
    Calcula CN usando el ponderador por coberturas con una tabla específica.

    El tipo de suelo (A/B/C/D) se selecciona para cada cobertura individualmente,
    permitiendo cuencas con diferentes tipos de suelo en distintas zonas.

    Args:
        basin: Cuenca para obtener área total
        table_key: Clave de tabla ("unified", "urban", "agricultural")
        menu: Instancia del menú para mostrar mensajes (opcional)

    Returns:
        Valor de CN ponderado o None si se cancela
    """
    from hidropluvial.cli.viewer.terminal import clear_screen
    from hidropluvial.core.coefficients import CN_TABLES, weighted_cn
    from hidropluvial.cli.viewer.coverage_viewer import (
        interactive_coverage_viewer, CoverageRow
    )
    from hidropluvial.cli.theme import print_coverage_assignments_table

    clear_screen()

    if table_key not in CN_TABLES:
        if menu:
            menu.error(f"Tabla '{table_key}' no disponible")
        return None

    table_name, table_data = CN_TABLES[table_key]

    # Construir filas para el visor con todos los valores CN por grupo de suelo
    rows = []
    for i, entry in enumerate(table_data):
        cond = f" ({entry.condition})" if entry.condition != "N/A" else ""
        rows.append(CoverageRow(
            index=i,
            category=entry.category,
            description=f"{entry.description}{cond}",
            value=entry.get_cn("B"),  # Valor de referencia
            value_label="CN",
            cn_a=entry.cn_a,
            cn_b=entry.cn_b,
            cn_c=entry.cn_c,
            cn_d=entry.cn_d,
        ))

    # Callback para obtener CN según grupo de suelo seleccionado
    def get_cn_for_soil(option_index: int, soil_group: str) -> int:
        return table_data[option_index].get_cn(soil_group)

    # Mostrar visor interactivo con selección de suelo por cobertura
    coverage_data = interactive_coverage_viewer(
        rows=rows,
        total_area=basin.area_ha,
        value_label="CN",
        table_name=f"Tabla {table_name}",
        on_get_cn_for_soil=get_cn_for_soil,
    )

    if not coverage_data:
        return None

    # Calcular CN ponderado final
    areas = [d["area"] for d in coverage_data]
    cn_values = [d["c_val"] for d in coverage_data]
    cn_weighted = weighted_cn(areas, cn_values)

    # Mostrar resultado final
    print_coverage_assignments_table(
        coverage_data, basin.area_ha, "CN", cn_weighted,
        title="Resultado Final"
    )

    return int(round(cn_weighted))
