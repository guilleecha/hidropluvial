"""
Textos metodológicos para Hidrogramas Unitarios.
"""

from typing import Optional


def get_hydrograph_methodology_latex(
    methods_used: Optional[list[str]] = None,
) -> str:
    """
    Genera texto LaTeX explicativo sobre hidrogramas unitarios.

    Args:
        methods_used: Lista de métodos utilizados (scs, snyder, clark).
                     Si es None, incluye solo SCS (el más común).

    Returns:
        Contenido LaTeX con marco teórico y formulaciones.
    """
    content = r"""
\subsection{Marco Teórico: Hidrograma Unitario}

El hidrograma unitario (HU) es la respuesta de una cuenca a una precipitación
efectiva unitaria (1 mm o 1 cm) de duración específica, uniformemente distribuida
sobre la cuenca.

\textbf{Principios fundamentales:}
\begin{enumerate}
    \item \textbf{Linealidad}: Las ordenadas del hidrograma son proporcionales
          a la precipitación efectiva.
    \item \textbf{Superposición}: Los hidrogramas de lluvias sucesivas pueden
          sumarse (convolución).
    \item \textbf{Invarianza temporal}: La respuesta de la cuenca es constante
          en el tiempo.
\end{enumerate}

\textbf{Proceso de convolución:}

El hidrograma de crecida se obtiene mediante la convolución de la precipitación
efectiva con el hidrograma unitario:

\begin{equation}
Q_n = \sum_{m=1}^{n} P_m \times U_{n-m+1}
\label{eq:convolucion}
\end{equation}

Donde:
\begin{itemize}
    \item $Q_n$ = Ordenada del hidrograma de crecida en el tiempo $n$
    \item $P_m$ = Precipitación efectiva en el intervalo $m$
    \item $U_k$ = Ordenada del hidrograma unitario
\end{itemize}

"""

    # Determinar qué métodos incluir
    if methods_used is None:
        methods_to_include = ["scs"]
    else:
        methods_to_include = [m.lower() for m in methods_used]

    # Siempre incluir SCS ya que es el método principal
    content += _get_scs_section()

    if "snyder" in methods_to_include:
        content += _get_snyder_section()

    if "clark" in methods_to_include:
        content += _get_clark_section()

    # Factor X para HU modificado
    content += _get_factor_x_section()

    # Referencias
    content += _get_hydrograph_references()

    return content


def _get_scs_section() -> str:
    """Sección del hidrograma unitario SCS."""
    return r"""
\subsubsection{Hidrograma Unitario SCS}

El método SCS proporciona un hidrograma unitario sintético adimensional basado
en el análisis de numerosas cuencas en Estados Unidos.

\textbf{Parámetros temporales:}

\begin{itemize}
    \item \textbf{Duración unitaria} ($D$): Intervalo de tiempo de la precipitación
          efectiva unitaria. Se recomienda $D \leq 0.2 \times T_c$.

    \item \textbf{Tiempo de retardo} ($t_{lag}$):
    \begin{equation}
    t_{lag} = 0.6 \times T_c
    \end{equation}

    \item \textbf{Tiempo al pico} ($t_p$):
    \begin{equation}
    t_p = \frac{D}{2} + t_{lag} = \frac{D}{2} + 0.6 \times T_c
    \label{eq:tp}
    \end{equation}

    \item \textbf{Tiempo base} ($t_b$): Para el HU triangular:
    \begin{equation}
    t_b = 2.67 \times t_p
    \end{equation}
\end{itemize}

\textbf{Caudal pico unitario:}

Para 1 mm de precipitación efectiva:
\begin{equation}
q_p = \frac{0.208 \times A}{t_p}
\label{eq:qp_unit}
\end{equation}

Donde:
\begin{itemize}
    \item $q_p$ = Caudal pico unitario (m$^3$/s por mm de $P_e$)
    \item $A$ = Área de la cuenca (km$^2$)
    \item $t_p$ = Tiempo al pico (horas)
\end{itemize}

\textbf{Hidrograma Unitario Triangular:}

El HU triangular es una simplificación que facilita los cálculos manuales:

\begin{figure}[H]
\centering
\begin{tikzpicture}[scale=0.8]
    % Ejes
    \draw[->] (0,0) -- (8,0) node[right] {$t$};
    \draw[->] (0,0) -- (0,4) node[above] {$Q$};
    % Triángulo
    \draw[thick,blue] (0,0) -- (2,3.5) -- (7,0) -- cycle;
    % Etiquetas
    \draw[dashed] (2,0) -- (2,3.5);
    \node[below] at (2,0) {$t_p$};
    \node[below] at (7,0) {$t_b$};
    \node[left] at (0,3.5) {$q_p$};
    % Área
    \node at (3,1.2) {Área = 1 mm};
\end{tikzpicture}
\caption{Hidrograma unitario triangular SCS}
\end{figure}

\textbf{Hidrograma Unitario Curvilíneo:}

El SCS también define un HU curvilíneo adimensional más realista, expresado como
fracciones de $t/t_p$ y $Q/Q_p$. Este hidrograma tiene:
\begin{itemize}
    \item Rama ascendente más suave
    \item Pico redondeado
    \item Rama descendente con cola más larga
    \item Tiempo base efectivo $\approx 5 \times t_p$
\end{itemize}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas rurales y urbanas
    \item Tamaños desde pequeñas subcuencas hasta cuencas medianas
    \item Requiere estimación confiable de $T_c$
\end{itemize}

"""


def _get_snyder_section() -> str:
    """Sección del hidrograma unitario Snyder."""
    return r"""
\subsubsection{Hidrograma Unitario de Snyder}

Desarrollado por Snyder (1938) para cuencas de los Montes Apalaches.
Utiliza coeficientes regionales que deben calibrarse.

\textbf{Tiempo de retardo:}
\begin{equation}
t_{lag} = C_t \times (L \times L_c)^{0.3}
\end{equation}

Donde:
\begin{itemize}
    \item $C_t$ = Coeficiente regional (1.8-2.2 típico)
    \item $L$ = Longitud del cauce principal (km)
    \item $L_c$ = Distancia al centroide de la cuenca (km)
\end{itemize}

\textbf{Caudal pico unitario:}
\begin{equation}
q_p = \frac{2.75 \times C_p \times A}{t_{lag}}
\end{equation}

Donde $C_p$ es un coeficiente de pico (0.4-0.8).

"""


def _get_clark_section() -> str:
    """Sección del hidrograma unitario Clark."""
    return r"""
\subsubsection{Hidrograma Unitario de Clark}

El método de Clark considera explícitamente el efecto de traslación y
almacenamiento en la cuenca mediante:

\begin{enumerate}
    \item \textbf{Histograma tiempo-área}: Representa la distribución temporal
          del área que contribuye al caudal.
    \item \textbf{Embalse lineal}: Modela el efecto de almacenamiento con un
          coeficiente $R$ (constante de almacenamiento).
\end{enumerate}

\textbf{Ecuación de continuidad con almacenamiento:}
\begin{equation}
\frac{dS}{dt} = I - O \quad ; \quad S = R \times O
\end{equation}

El tiempo de concentración ($T_c$) y la constante de almacenamiento ($R$)
son los parámetros principales del método.

"""


def _get_factor_x_section() -> str:
    """Sección sobre el factor morfológico X."""
    return r"""
\subsubsection{Factor Morfológico X}

El factor X permite ajustar la forma del hidrograma unitario para representar
diferentes características morfológicas de la cuenca.

\textbf{Definición:}

El factor X modifica la relación entre el tiempo al pico y el tiempo base:
\begin{equation}
t_b = (1 + X) \times t_p
\label{eq:factor_x}
\end{equation}

\textbf{Interpretación física:}
\begin{itemize}
    \item $X = 1.67$ (valor SCS estándar): Hidrograma triangular típico
    \item $X < 1.67$: Hidrograma más puntiagudo, respuesta rápida
    \item $X > 1.67$: Hidrograma más achatado, respuesta lenta
\end{itemize}

\textbf{Efecto sobre el caudal pico:}

Al modificar X, el caudal pico unitario se ajusta para mantener el volumen:
\begin{equation}
q_p = \frac{0.208 \times A}{t_p} \times \frac{2}{1 + X}
\end{equation}

Un valor menor de X produce:
\begin{itemize}
    \item Mayor caudal pico
    \item Menor tiempo base
    \item Hidrograma más concentrado
\end{itemize}

\textbf{Valores típicos según morfología:}

\begin{table}[H]
\centering
\small
\begin{tabular}{lcc}
\toprule
Tipo de cuenca & X típico & Característica \\
\midrule
Alargada, montañosa & 1.2 - 1.5 & Respuesta rápida \\
Forma media & 1.67 & Estándar SCS \\
Redondeada, plana & 2.0 - 2.5 & Respuesta lenta \\
Con almacenamiento & 2.5 - 3.0 & Muy atenuada \\
\bottomrule
\end{tabular}
\caption{Valores típicos del factor X según morfología}
\label{tab:factor_x}
\end{table}

"""


def _get_hydrograph_references() -> str:
    """Genera sección de referencias bibliográficas."""
    return r"""
\subsubsection{Referencias Bibliográficas}

\begin{itemize}
    \item SCS (1972). ``National Engineering Handbook, Section 4: Hydrology''. USDA.
    \item NRCS (1986). ``Urban Hydrology for Small Watersheds''. Technical Release 55.
    \item Chow, V.T., Maidment, D.R., Mays, L.W. (1988). ``Applied Hydrology''. McGraw-Hill.
    \item Snyder, F.F. (1938). ``Synthetic Unit Graphs''. Trans. AGU, Vol. 19.
    \item Clark, C.O. (1945). ``Storage and the Unit Hydrograph''. Trans. ASCE, Vol. 110.
\end{itemize}

"""
