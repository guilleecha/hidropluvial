"""
Comando 'commands' - Lista todos los comandos disponibles.
"""

import typer

from hidropluvial.cli.formatters import fmt


def show_commands():
    """
    Muestra todos los comandos disponibles con ejemplos.
    """
    typer.echo("""
+-------------------------------------------------------------+
|              HIDROPLUVIAL - Comandos Disponibles            |
+-------------------------------------------------------------+

USO: hp <comando> [opciones]

SESIONES (flujo principal)
--------------------------------------------------------------
  session create <nombre>     Crear sesion de analisis
  session list                Listar sesiones guardadas
  session tc <id>             Calcular tiempo de concentracion
  session analyze <id>        Ejecutar analisis hidrologico
  session summary <id>        Ver tabla resumen
  session report <id>         Generar reporte LaTeX
  session batch <yaml>        Analisis batch desde archivo
  session delete <id>         Eliminar sesion

CURVAS IDF
--------------------------------------------------------------
  idf tabla-uy <estacion>     Tabla IDF para estacion Uruguay
  idf intensidad <est> <d>    Intensidad para duracion especifica

TORMENTAS DE DISENO
--------------------------------------------------------------
  storm blocks <p3_10> <dur>  Tormenta bloques alternantes
  storm gz <p3_10>            Tormenta metodologia GZ (6h)
  storm bimodal-uy <p3_10>    Tormenta bimodal Uruguay

TIEMPO DE CONCENTRACION
--------------------------------------------------------------
  tc kirpich <L> <S>          Metodo Kirpich (L en m, S en m/m)
  tc desbordes <A> <S> <C>    Metodo Desbordes (A en ha, S en %)

ESCORRENTIA
--------------------------------------------------------------
  runoff cn <P> <CN>          Escorrentia metodo SCS-CN

HIDROGRAMAS
--------------------------------------------------------------
  hydrograph scs              Hidrograma unitario SCS
  hydrograph gz               Hidrograma metodologia GZ

EXPORTACION
--------------------------------------------------------------
  export idf-csv <est>        Exportar tabla IDF a CSV
  report idf <est>            Generar reporte IDF en LaTeX

EJEMPLO RAPIDO
--------------------------------------------------------------
  # Crear sesion con datos de cuenca
  hp session create "Mi Cuenca" --area 50 --slope 2.5 --p3_10 80 --c 0.55

  # Calcular tiempo de concentracion
  hp session tc abc123 --methods "kirpich,desbordes"

  # Ejecutar analisis
  hp session analyze abc123 --tc desbordes --storm gz --tr 10

  # Generar reporte
  hp session report abc123 -o mi_reporte

MODO INTERACTIVO
--------------------------------------------------------------
  hp wizard                   Asistente guiado paso a paso

Usa 'hp <comando> --help' para ver opciones detalladas.
""")
