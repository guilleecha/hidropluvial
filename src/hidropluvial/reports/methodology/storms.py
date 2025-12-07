"""
Textos metodológicos para Tormentas de Diseño.
"""

from typing import Optional


def get_storms_methodology_latex(
    storm_types_used: Optional[list[str]] = None,
) -> str:
    """
    Genera texto LaTeX explicativo sobre tormentas de diseño.

    Args:
        storm_types_used: Lista de tipos de tormenta utilizados (ab, gz, scs, huff).
                         Si es None, incluye los más comunes (AB, GZ).

    Returns:
        Contenido LaTeX con marco teórico y formulaciones.
    """
    content = r"""
\subsection{Marco Teórico: Tormentas de Diseño}

Una tormenta de diseño es una representación simplificada de un evento de
precipitación utilizada para el dimensionamiento de obras hidráulicas.
Define la distribución temporal de la lluvia para una duración y período
de retorno dados.

\textbf{Componentes de una tormenta de diseño:}
\begin{itemize}
    \item \textbf{Duración total}: Tiempo durante el cual ocurre la precipitación
    \item \textbf{Profundidad total}: Lámina de agua acumulada (mm)
    \item \textbf{Distribución temporal}: Cómo se distribuye la lluvia en el tiempo
    \item \textbf{Período de retorno}: Frecuencia estadística del evento
\end{itemize}

\textbf{Curvas IDF:}

Las curvas Intensidad-Duración-Frecuencia relacionan la intensidad de lluvia
con su duración para diferentes períodos de retorno:

\begin{equation}
i = f(D, T_r)
\label{eq:idf}
\end{equation}

En Uruguay, DINAGUA proporciona la fórmula regionalizada basada en $P_{3,10}$
(precipitación de 3 horas y 10 años de período de retorno).

"""

    # Determinar qué tipos incluir
    if storm_types_used is None:
        types_to_include = ["ab", "gz"]
    else:
        types_to_include = [t.lower() for t in storm_types_used]

    # Agregar secciones por tipo de tormenta
    if "ab" in types_to_include:
        content += _get_alternating_blocks_section()

    if "gz" in types_to_include:
        content += _get_gz_section()

    if any(t in types_to_include for t in ["scs", "scs1", "scs2", "scs3"]):
        content += _get_scs_storms_section()

    if "huff" in types_to_include:
        content += _get_huff_section()

    # Selección de duración
    content += _get_duration_selection_section()

    # Referencias
    content += _get_storms_references()

    return content


def _get_alternating_blocks_section() -> str:
    """Sección del método de Bloques Alternantes."""
    return r"""
\subsubsection{Método de Bloques Alternantes (AB)}

El método de bloques alternantes genera un hietograma sintético que maximiza
la intensidad de lluvia para cualquier duración dentro de la tormenta.

\textbf{Procedimiento:}
\begin{enumerate}
    \item Dividir la duración total en intervalos $\Delta t$
    \item Para cada duración acumulada, calcular la intensidad desde curvas IDF
    \item Calcular la profundidad acumulada: $P = i \times D$
    \item Obtener la profundidad incremental para cada intervalo
    \item Reordenar los bloques alternando a izquierda y derecha del pico
\end{enumerate}

\textbf{Posición del pico:}

El método permite configurar la posición del pico mediante un coeficiente $r$:
\begin{itemize}
    \item $r = 0.5$: Pico centrado (distribución simétrica)
    \item $r = 0.3$: Pico adelantado (más común en tormentas convectivas)
    \item $r = 0.7$: Pico retrasado
\end{itemize}

\textbf{Características:}
\begin{itemize}
    \item Produce la envolvente de máximas intensidades
    \item Resulta en diseños conservadores
    \item No representa una tormenta real típica
    \item Ampliamente utilizado por su simplicidad
\end{itemize}

\begin{figure}[H]
\centering
\begin{tikzpicture}[scale=0.6]
    % Ejes
    \draw[->] (0,0) -- (10,0) node[right] {$t$};
    \draw[->] (0,0) -- (0,5) node[above] {$i$};
    % Barras (bloques alternantes con pico central)
    \fill[blue!70] (1,0) rectangle (2,1.5);
    \fill[blue!70] (2,0) rectangle (3,2.5);
    \fill[blue!70] (3,0) rectangle (4,3.5);
    \fill[blue!70] (4,0) rectangle (5,4.5);  % Pico
    \fill[blue!70] (5,0) rectangle (6,3.0);
    \fill[blue!70] (6,0) rectangle (7,2.0);
    \fill[blue!70] (7,0) rectangle (8,1.2);
    % Etiquetas
    \node[below] at (4.5,-0.3) {Pico};
\end{tikzpicture}
\caption{Esquema de hietograma por bloques alternantes}
\end{figure}

"""


def _get_gz_section() -> str:
    """Sección del método GZ (Genta-Zanini, Uruguay)."""
    return r"""
\subsubsection{Método GZ (Uruguay)}

El método GZ es una variante del método de bloques alternantes desarrollada
para Uruguay, con el pico ubicado en el primer tercio de la tormenta.

\textbf{Características distintivas:}
\begin{itemize}
    \item Duración estándar de 6 horas
    \item Posición del pico: $r = 0.25$ (primer cuarto de la tormenta)
    \item Distribución más realista para tormentas uruguayas
    \item Recomendado por DINAGUA para diseño de drenaje urbano
\end{itemize}

\textbf{Factor X en tormentas GZ:}

Para tormentas GZ, se puede aplicar un factor morfológico X que modifica
la intensidad del pico:
\begin{equation}
i_{pico,mod} = i_{pico} \times X
\end{equation}

Valores típicos de X:
\begin{itemize}
    \item $X = 1.0$: Tormenta estándar
    \item $X = 1.2 - 1.5$: Tormentas más intensas (cuencas pequeñas)
    \item $X = 0.8 - 0.9$: Tormentas más suaves (cuencas grandes)
\end{itemize}

\textbf{Aplicación:}
\begin{itemize}
    \item Diseño de sistemas de drenaje pluvial urbano
    \item Estudios hidrológicos en Uruguay
    \item Duración típica: 6 horas
\end{itemize}

"""


def _get_scs_storms_section() -> str:
    """Sección de tormentas SCS."""
    return r"""
\subsubsection{Distribuciones Temporales SCS}

El Soil Conservation Service (NRCS) desarrolló cuatro distribuciones temporales
estándar para tormentas de 24 horas, basadas en análisis de lluvias en EE.UU.

\textbf{Tipos de distribución:}

\begin{table}[H]
\centering
\small
\begin{tabular}{clc}
\toprule
Tipo & Región característica & Posición del pico \\
\midrule
I & Costa del Pacífico, clima mediterráneo & 10 horas \\
IA & Costa del Pacífico, lluvias suaves & 8 horas \\
II & Interior continental, tormentas convectivas & 12 horas \\
III & Costa del Golfo, huracanes tropicales & 12 horas \\
\bottomrule
\end{tabular}
\caption{Distribuciones temporales SCS}
\end{table}

\textbf{Tipo II} (más común):
\begin{itemize}
    \item Pico muy pronunciado en el centro de la tormenta
    \item 50\% de la lluvia en las 2 horas centrales
    \item Representa tormentas convectivas intensas
    \item Ampliamente utilizado cuando no hay datos locales
\end{itemize}

\textbf{Aplicación:}
\begin{itemize}
    \item Estudios de cuencas rurales medianas y grandes
    \item Cuando se requiere distribución de 24 horas
    \item Modelación con HEC-HMS y similares
\end{itemize}

"""


def _get_huff_section() -> str:
    """Sección de distribuciones Huff."""
    return r"""
\subsubsection{Distribuciones de Huff}

Floyd Huff (1967) analizó tormentas en Illinois y las clasificó según el
cuartil en que ocurre la mayor intensidad.

\textbf{Clasificación:}
\begin{itemize}
    \item \textbf{Primer cuartil}: Pico en 0-25\% de la duración (más frecuente)
    \item \textbf{Segundo cuartil}: Pico en 25-50\% de la duración
    \item \textbf{Tercer cuartil}: Pico en 50-75\% de la duración
    \item \textbf{Cuarto cuartil}: Pico en 75-100\% de la duración
\end{itemize}

\textbf{Probabilidades de excedencia:}

Huff proporciona curvas para diferentes probabilidades (10\%, 50\%, 90\%),
permitiendo análisis de sensibilidad.

\textbf{Aplicación:}
\begin{itemize}
    \item Cuando se dispone de datos de tormentas locales
    \item Análisis probabilístico de distribución temporal
    \item Estudios detallados de drenaje urbano
\end{itemize}

"""


def _get_duration_selection_section() -> str:
    """Sección sobre selección de duración de tormenta."""
    return r"""
\subsubsection{Selección de la Duración de Tormenta}

La duración de la tormenta de diseño es un parámetro crítico que afecta
directamente los resultados del análisis hidrológico.

\textbf{Criterios de selección:}

\begin{enumerate}
    \item \textbf{Duración igual al tiempo de concentración} ($D = T_c$):
    \begin{itemize}
        \item Maximiza el caudal pico para cuencas pequeñas
        \item Criterio clásico del método racional
        \item Puede subestimar volúmenes en cuencas grandes
    \end{itemize}

    \item \textbf{Duración mayor que $T_c$} ($D > T_c$):
    \begin{itemize}
        \item Genera mayor volumen de escorrentía
        \item Importante para diseño de almacenamientos
        \item Típico: $D = 2 \times T_c$ o duraciones estándar (6h, 12h, 24h)
    \end{itemize}

    \item \textbf{Duraciones estándar}:
    \begin{itemize}
        \item 6 horas: Común en Uruguay (método GZ)
        \item 24 horas: Estándar internacional (SCS)
        \item Facilita comparación entre estudios
    \end{itemize}
\end{enumerate}

\textbf{Recomendaciones:}

\begin{table}[H]
\centering
\small
\begin{tabular}{lcc}
\toprule
Tipo de obra & Duración recomendada & Observación \\
\midrule
Alcantarillado menor & $D = T_c$ & Maximiza $Q_p$ \\
Colectores principales & $D = 2 \times T_c$ & Considera volumen \\
Lagunas de detención & $D \geq 6$ h & Volumen crítico \\
Estudios regionales & 24 h & Comparabilidad \\
\bottomrule
\end{tabular}
\caption{Duraciones recomendadas según tipo de obra}
\end{table}

"""


def _get_storms_references() -> str:
    """Genera sección de referencias bibliográficas."""
    return r"""
\subsubsection{Referencias Bibliográficas}

\begin{itemize}
    \item DINAGUA. ``Curvas Intensidad-Duración-Frecuencia para Uruguay''. MVOTMA.
    \item DINAGUA. ``Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas''.
    \item SCS (1986). ``Urban Hydrology for Small Watersheds''. TR-55, Chapter 5.
    \item Huff, F.A. (1967). ``Time Distribution of Rainfall in Heavy Storms''. Water Resources Research.
    \item Chow, V.T. (1988). ``Applied Hydrology''. McGraw-Hill, Chapter 14.
\end{itemize}

"""
