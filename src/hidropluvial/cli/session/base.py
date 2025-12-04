"""
Comandos básicos de sesión: create, list, show, tc, summary, delete.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.session import SessionManager

# Instancia global del gestor de sesiones
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtiene o crea el gestor de sesiones."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def session_create(
    name: Annotated[str, typer.Argument(help="Nombre de la sesión")],
    area_ha: Annotated[float, typer.Option("--area", "-a", help="Área en hectáreas")],
    slope_pct: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media en %")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    c: Annotated[Optional[float], typer.Option("--c", help="Coef. escorrentía (0-1)")] = None,
    cn: Annotated[Optional[int], typer.Option("--cn", help="Curve Number (30-100)")] = None,
    length_m: Annotated[Optional[float], typer.Option("--length", "-l", help="Longitud cauce en m")] = None,
    cuenca_nombre: Annotated[str, typer.Option("--cuenca", help="Nombre de la cuenca")] = "",
):
    """
    Crea una nueva sesión de análisis.

    Ejemplo:
        hidropluvial session create "Proyecto Norte" --area 62 --slope 3.41 --p3_10 83 --c 0.62 --cn 81
    """
    manager = get_session_manager()

    session = manager.create(
        name=name,
        area_ha=area_ha,
        slope_pct=slope_pct,
        p3_10=p3_10,
        c=c,
        cn=cn,
        length_m=length_m,
        cuenca_nombre=cuenca_nombre,
    )

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  SESION CREADA")
    typer.echo(f"{'='*55}")
    typer.echo(f"  ID:                {session.id}")
    typer.echo(f"  Nombre:            {session.name}")
    typer.echo(f"  Cuenca:            {session.cuenca.nombre}")
    typer.echo(f"  {'-'*40}")
    typer.echo(f"  Área:              {session.cuenca.area_ha:>10.2f} ha")
    typer.echo(f"  Pendiente:         {session.cuenca.slope_pct:>10.2f} %")
    typer.echo(f"  P3,10:             {session.cuenca.p3_10:>10.1f} mm")
    if session.cuenca.c:
        typer.echo(f"  Coef. C:           {session.cuenca.c:>10.2f}")
    if session.cuenca.cn:
        typer.echo(f"  CN:                {session.cuenca.cn:>10}")
    if session.cuenca.length_m:
        typer.echo(f"  Longitud cauce:    {session.cuenca.length_m:>10.0f} m")
    typer.echo(f"{'='*55}")
    typer.echo(f"\n  Usa 'session tc {session.id}' para calcular Tc")
    typer.echo(f"  Usa 'session analyze {session.id}' para análisis completo\n")


def session_list():
    """Lista todas las sesiones disponibles."""
    manager = get_session_manager()
    sessions = manager.list_sessions()

    if not sessions:
        typer.echo("\nNo hay sesiones guardadas.")
        typer.echo("Usa 'session create' para crear una nueva.\n")
        return

    typer.echo(f"\n{'='*75}")
    typer.echo(f"  SESIONES DISPONIBLES")
    typer.echo(f"{'='*75}")
    typer.echo(f"  {'ID':8} | {'Nombre':20} | {'Cuenca':15} | {'Análisis':>8} | {'Actualizado':19}")
    typer.echo(f"  {'-'*71}")

    for s in sessions:
        updated = s["updated_at"][:19].replace("T", " ")
        typer.echo(f"  {s['id']:8} | {s['name'][:20]:20} | {s['cuenca'][:15]:15} | {s['n_analyses']:>8} | {updated}")

    typer.echo(f"{'='*75}\n")


def session_show(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """Muestra detalles de una sesión."""
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  SESION: {session.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"  ID:                {session.id}")
    typer.echo(f"  Creada:            {session.created_at[:19].replace('T', ' ')}")
    typer.echo(f"  Actualizada:       {session.updated_at[:19].replace('T', ' ')}")

    typer.echo(f"\n  CUENCA: {session.cuenca.nombre}")
    typer.echo(f"  {'-'*45}")
    typer.echo(f"  Área:              {session.cuenca.area_ha:>12.2f} ha")
    typer.echo(f"  Pendiente:         {session.cuenca.slope_pct:>12.2f} %")
    typer.echo(f"  P3,10:             {session.cuenca.p3_10:>12.1f} mm")
    if session.cuenca.c:
        typer.echo(f"  Coef. C:           {session.cuenca.c:>12.2f}")
    if session.cuenca.cn:
        typer.echo(f"  CN:                {session.cuenca.cn:>12}")
    if session.cuenca.length_m:
        typer.echo(f"  Longitud cauce:    {session.cuenca.length_m:>12.0f} m")

    # Mostrar Tc calculados
    if session.tc_results:
        typer.echo(f"\n  TIEMPOS DE CONCENTRACION:")
        typer.echo(f"  {'-'*45}")
        for tc in session.tc_results:
            typer.echo(f"  {tc.method:15} Tc = {tc.tc_min:>8.1f} min ({tc.tc_hr:.2f} hr)")

    # Mostrar análisis
    if session.analyses:
        typer.echo(f"\n  ANALISIS REALIZADOS: {len(session.analyses)}")
        typer.echo(f"  {'-'*45}")
        for a in session.analyses:
            x_str = f"X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else ""
            typer.echo(f"  [{a.id}] {a.tc.method} + {a.storm.type} Tr{a.storm.return_period} {x_str}")
            typer.echo(f"          Qp = {a.hydrograph.peak_flow_m3s:.3f} m³/s, Tp = {a.hydrograph.time_to_peak_min:.1f} min")

    typer.echo(f"{'='*60}\n")


def session_tc(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    methods: Annotated[str, typer.Option("--methods", "-m", help="Métodos: kirpich,temez,desbordes")] = "desbordes",
):
    """
    Calcula tiempo de concentración con múltiples métodos.

    Ejemplo:
        hidropluvial session tc abc123 --methods "kirpich,desbordes"
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    from hidropluvial.core import desbordes, kirpich, temez

    method_list = [m.strip().lower() for m in methods.split(",")]

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  CALCULO DE TIEMPOS DE CONCENTRACION")
    typer.echo(f"  Sesión: {session.name} [{session.id}]")
    typer.echo(f"{'='*55}")

    for method in method_list:
        tc_hr = None
        params = {}

        if method == "kirpich":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            tc_hr = kirpich(session.cuenca.length_m, slope_mm)
            params = {"length_m": session.cuenca.length_m, "slope_mm": slope_mm}

        elif method == "temez":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            length_km = session.cuenca.length_m / 1000
            tc_hr = temez(length_km, slope_mm)
            params = {"length_km": length_km, "slope_mm": slope_mm}

        elif method == "desbordes":
            if not session.cuenca.c:
                typer.echo(f"  {method}: ERROR - Requiere coeficiente C", err=True)
                continue
            tc_hr = desbordes(
                session.cuenca.area_ha,
                session.cuenca.slope_pct,
                session.cuenca.c,
            )
            params = {
                "area_ha": session.cuenca.area_ha,
                "slope_pct": session.cuenca.slope_pct,
                "c": session.cuenca.c,
            }

        else:
            typer.echo(f"  {method}: ERROR - Método desconocido", err=True)
            continue

        if tc_hr:
            result = manager.add_tc_result(session, method, tc_hr, **params)
            typer.echo(f"  {method:15} Tc = {result.tc_min:>8.1f} min ({result.tc_hr:.2f} hr)")

    typer.echo(f"{'='*55}\n")


def session_summary(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """
    Muestra tabla comparativa de todos los análisis.

    Ejemplo:
        hidropluvial session summary abc123
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo(f"\nNo hay análisis en la sesión '{session.name}'.")
        typer.echo("Usa 'session analyze' para ejecutar análisis.\n")
        return

    rows = manager.get_summary_table(session)

    typer.echo(f"\n{'='*100}")
    typer.echo(f"  RESUMEN COMPARATIVO - {session.name}")
    typer.echo(f"{'='*100}")
    typer.echo(f"  {'ID':8} | {'Tc':12} | {'Tc(min)':>8} | {'Tormenta':10} | {'Tr':>4} | {'X':>5} | {'P(mm)':>7} | {'Q(mm)':>7} | {'Qp(m³/s)':>9} | {'Tp(min)':>8}")
    typer.echo(f"  {'-'*96}")

    for r in rows:
        x_str = f"{r['x']:.2f}" if r['x'] else "-"
        typer.echo(
            f"  {r['id']:8} | {r['tc_method']:12} | {r['tc_min']:>8.1f} | {r['storm']:10} | "
            f"{r['tr']:>4} | {x_str:>5} | {r['depth_mm']:>7.1f} | {r['runoff_mm']:>7.1f} | "
            f"{r['qpeak_m3s']:>9.3f} | {r['tp_min']:>8.1f}"
        )

    typer.echo(f"{'='*100}\n")

    # Mostrar máximos/mínimos
    if len(rows) > 1:
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])

        typer.echo(f"  Caudal máximo: {max_q['qpeak_m3s']:.3f} m³/s ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")
        typer.echo(f"  Caudal mínimo: {min_q['qpeak_m3s']:.3f} m³/s ({min_q['tc_method']} + {min_q['storm']} Tr{min_q['tr']})")
        typer.echo(f"  Variación: {(max_q['qpeak_m3s'] - min_q['qpeak_m3s']) / min_q['qpeak_m3s'] * 100:.1f}%\n")


def session_delete(
    session_id: Annotated[str, typer.Argument(help="ID de la sesión a eliminar")],
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
):
    """Elimina una sesión."""
    manager = get_session_manager()

    if not force:
        confirm = typer.confirm(f"¿Eliminar sesión '{session_id}'?")
        if not confirm:
            typer.echo("Cancelado.")
            raise typer.Exit(0)

    if manager.delete(session_id):
        typer.echo(f"Sesión '{session_id}' eliminada.")
    else:
        typer.echo(f"Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)
