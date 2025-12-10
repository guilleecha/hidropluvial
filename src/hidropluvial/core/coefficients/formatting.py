"""
Funciones de formato para tablas de coeficientes.

Genera representaciones ASCII de las tablas C y CN
para visualización en terminal.
"""

from .types import ChowCEntry, FHWACEntry, CNEntry


def format_c_table(table: list, title: str, tr: int = 10, selection_mode: bool = False) -> str:
    """
    Formatea tabla de coeficientes C en ASCII.

    Soporta diferentes tipos de tablas:
    - CoefficientEntry: muestra rango min-max
    - ChowCEntry: muestra C para cada Tr
    - FHWACEntry: muestra C base y ajustado para Tr dado

    Args:
        table: Lista de entradas de coeficientes
        title: Titulo de la tabla
        tr: Periodo de retorno para mostrar C ajustado (FHWA)
        selection_mode: Si True, indica que Tr2 es seleccionable (Ven Te Chow)
    """
    lines = []
    lines.append("")
    lines.append(f"  {title}")

    if not table:
        return "\n".join(lines)

    # Detectar tipo de tabla
    first = table[0]

    if isinstance(first, ChowCEntry):
        # Tabla Ven Te Chow con C por Tr
        if selection_mode:
            # Modo selección: Tr2 es seleccionable, otros son referencia
            lines.append("  " + "=" * 85)
            lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<22} {'*Tr2*':<6} {'(Tr5)':<6} {'(Tr10)':<7} {'(Tr25)':<7} {'(Tr50)':<7} {'(Tr100)':<7}")
            lines.append("  " + "-" * 85)

            current_category = ""
            for i, entry in enumerate(table):
                if entry.category != current_category:
                    if current_category:
                        lines.append("  " + "-" * 85)
                    current_category = entry.category

                lines.append(
                    f"  {i+1:<3} {entry.category:<15} {entry.description:<22} "
                    f"{entry.c_tr2:<6.2f} ({entry.c_tr5:.2f}) ({entry.c_tr10:.2f})  "
                    f"({entry.c_tr25:.2f})  ({entry.c_tr50:.2f})  ({entry.c_tr100:.2f})"
                )

            lines.append("  " + "=" * 85)
            lines.append("")
            lines.append("  NOTA: Selecciona el coeficiente C para Tr=2 anos (columna *Tr2*).")
            lines.append("        El valor se ajustara automaticamente segun el Tr del analisis.")
            lines.append("        Los valores entre parentesis son de referencia.")
        else:
            # Modo consulta: mostrar todos los valores
            lines.append("  " + "=" * 85)
            lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<22} {'Tr2':<6} {'Tr5':<6} {'Tr10':<6} {'Tr25':<6} {'Tr50':<6} {'Tr100':<6}")
            lines.append("  " + "-" * 85)

            current_category = ""
            for i, entry in enumerate(table):
                if entry.category != current_category:
                    if current_category:
                        lines.append("  " + "-" * 85)
                    current_category = entry.category

                lines.append(
                    f"  {i+1:<3} {entry.category:<15} {entry.description:<22} "
                    f"{entry.c_tr2:<6.2f} {entry.c_tr5:<6.2f} {entry.c_tr10:<6.2f} "
                    f"{entry.c_tr25:<6.2f} {entry.c_tr50:<6.2f} {entry.c_tr100:<6.2f}"
                )

            lines.append("  " + "=" * 85)
            lines.append("")
            lines.append("  Nota: Para ponderacion, se usa C(Tr2) y se ajusta segun Tr del analisis.")

    elif isinstance(first, FHWACEntry):
        # Tabla FHWA con C base y factor
        lines.append("  " + "=" * 70)
        tr_header = f"C (Tr={tr})"
        lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<28} {'C base':<8} {tr_header:<10}")
        lines.append("  " + "-" * 70)

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category:
                if current_category:
                    lines.append("  " + "-" * 70)
                current_category = entry.category

            c_adj = entry.get_c(tr)
            lines.append(
                f"  {i+1:<3} {entry.category:<15} {entry.description:<28} "
                f"{entry.c_base:<8.2f} {c_adj:<10.2f}"
            )

        lines.append("  " + "=" * 70)
        lines.append("")
        lines.append("  Factores de ajuste FHWA por Tr:")
        lines.append("    Tr <= 10: 1.00 | Tr=25: 1.10 | Tr=50: 1.20 | Tr=100: 1.25")

    else:
        # Tabla simple con rango
        lines.append("  " + "=" * 70)
        lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<28} {'C min':<7} {'C max':<7} {'C tip':<7}")
        lines.append("  " + "-" * 70)

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category:
                if current_category:
                    lines.append("  " + "-" * 70)
                current_category = entry.category

            lines.append(
                f"  {i+1:<3} {entry.category:<15} {entry.description:<28} "
                f"{entry.c_min:<7.2f} {entry.c_max:<7.2f} {entry.c_recommended:<7.2f}"
            )

        lines.append("  " + "=" * 70)

    return "\n".join(lines)


def format_cn_table(table: list[CNEntry], title: str) -> str:
    """Formatea tabla de CN en ASCII."""
    lines = []
    lines.append("")
    lines.append(f"  {title}")
    lines.append("  " + "=" * 78)
    lines.append(f"  {'#':<3} {'Categoria':<12} {'Descripcion':<20} {'Cond.':<8} {'A':<5} {'B':<5} {'C':<5} {'D':<5}")
    lines.append("  " + "-" * 78)

    current_category = ""
    for i, entry in enumerate(table):
        if entry.category != current_category:
            if current_category:
                lines.append("  " + "-" * 78)
            current_category = entry.category

        lines.append(
            f"  {i+1:<3} {entry.category:<12} {entry.description:<20} {entry.condition:<8} "
            f"{entry.cn_a:<5} {entry.cn_b:<5} {entry.cn_c:<5} {entry.cn_d:<5}"
        )

    lines.append("  " + "=" * 78)
    lines.append("")
    lines.append("  Grupos hidrologicos de suelo:")
    lines.append("    A: Alta infiltracion (arena, grava)")
    lines.append("    B: Moderada infiltracion (limo arenoso)")
    lines.append("    C: Baja infiltracion (limo arcilloso)")
    lines.append("    D: Muy baja infiltracion (arcilla)")
    return "\n".join(lines)
