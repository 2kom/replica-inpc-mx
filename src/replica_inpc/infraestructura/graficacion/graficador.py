"""Graficación de `ResultadoIndice` sobre plotnine.

Sin `Protocol` en `aplicacion/puertos/`: a diferencia de
`LectorCanasta`/`FuenteValidacion`, ningún componente de `dominio/` o
`aplicacion/` consume un graficador internamente — no hay abstracción que
enforzar (mismo pragmatismo de docs/diseño.md §D1).
"""

from __future__ import annotations

import pandas as pd
from plotnine import (
    aes,
    annotate,
    element_blank,
    element_text,
    geom_hline,
    geom_line,
    ggplot,
    labs,
    scale_color_manual,
    scale_linetype_identity,
    scale_x_datetime,
    scale_y_continuous,
    theme,
    theme_bw,
)

from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.infraestructura.graficacion._prepocesamiento import (
    _VALOR_BASE,
    _aplanar_resultado_indice,
    _breaks_y_etiqueta_y,
    _breaks_y_etiquetas_x,
    _colores_y_etiquetas,
    _ordenar_series_dibujo,
    _particionar_series,
    _primero_y_ultimo_para_anotar,
    _recortar_tramo,
    _titulo,
)


def _construir_grafica_linea(datos: pd.DataFrame, resultado: ResultadoIndice) -> ggplot:
    """Arma el `ggplot` completo a partir de `datos` ya aplanados (y opcionalmente particionados).

    `resultado` solo se usa para `periodo_referencia` (etiqueta del eje Y) —
    los datos a dibujar salen enteros de `datos`.
    """
    datos = datos.copy()
    datos["indice"] = _ordenar_series_dibujo(datos["indice"])
    titulo = _titulo(datos)

    series = list(pd.unique(datos["indice"]))
    breaks_x, etiquetas_x = _breaks_y_etiquetas_x(datos)
    breaks_y, etiqueta_y = _breaks_y_etiqueta_y(datos, resultado)
    colores, etiquetas_leyenda = _colores_y_etiquetas(series)

    grafica = ggplot(
        datos, aes(x="periodo_ts", y="indice_replicado", color="indice", linetype="linetype")
    )
    if breaks_y[0] <= _VALOR_BASE <= breaks_y[-1]:
        # Fuera de rango (ej. tramo recortado donde todo el índice quedó por
        # encima o por debajo de 100): la línea de base ya no aporta nada,
        # se omite en vez de dibujarla fuera del panel visible.
        grafica = grafica + geom_hline(
            yintercept=_VALOR_BASE, linetype="dashed", color="grey", size=0.3
        )
    grafica = grafica + geom_line(size=0.5) + scale_linetype_identity(guide=None)

    primero_ultimo = _primero_y_ultimo_para_anotar(datos, series)
    if primero_ultimo is not None:
        # Serie única (sin leyenda): hay espacio para el numerito, y el margen
        # más ancho existe justo para que ese texto no se corte contra el borde.
        expand_x, expand_y = (0.045, 0.045), (0.02, 0.02)
        primero, ultimo = primero_ultimo
        grafica = (
            grafica
            + annotate(
                "text",
                x=min(breaks_x),  # type: ignore[arg-type]
                y=primero["indice_replicado"],
                label=f"{primero['indice_replicado']:.2f}",
                ha="right",
                va="center",
                size=6,
                color=colores[primero["indice"]],
            )
            + annotate(
                "text",
                x=max(breaks_x),  # type: ignore[arg-type]
                y=ultimo["indice_replicado"],
                label=f"{ultimo['indice_replicado']:.2f}",
                ha="left",
                va="center",
                size=6,
                color=colores[ultimo["indice"]],
            )
        )
    else:
        # Varias series: sin numerito que proteger, margen mínimo.
        expand_x, expand_y = (0.01, 0.01), (0.01, 0.01)

    return (
        grafica
        + scale_x_datetime(breaks=breaks_x, labels=etiquetas_x, expand=expand_x)  # type: ignore[arg-type]
        + scale_y_continuous(breaks=breaks_y, expand=expand_y)  # type: ignore[arg-type]
        + scale_color_manual(values=colores, labels=etiquetas_leyenda)
        + labs(title=titulo, x="Periodo", y=etiqueta_y)
        + theme_bw()
        + theme(
            axis_title=element_text(size=8),
            axis_text_x=element_text(rotation=30, ha="right", size=6),
            axis_text_y=element_text(size=6),
            legend_position="bottom" if len(series) > 1 else "none",
            legend_box="horizontal",
            legend_title=element_blank(),
            legend_text=element_text(size=6),
            legend_key_size=8,
            legend_box_spacing=0.01,
            plot_margin=0.005,
            figure_size=(8, 4),
            dpi=300,
        )
    )


def _graficas_linea(
    resultado: ResultadoIndice,
    comparacion: ResultadoIndice | None = None,
    desde: PeriodoQuincenal | PeriodoMensual | None = None,
    hasta: PeriodoQuincenal | PeriodoMensual | None = None,
) -> list[ggplot]:
    """Arma uno o varios `ggplot` de `resultado` (+ `comparacion` si viene).

    `desde`/`hasta`, si vienen, recortan el tramo ANTES de particionar — el
    primer/último valor anotado (serie única) y las particiones (varias
    series) ya reflejan solo el tramo pedido, no el histórico completo.

    Más de una sola imagen cuando `resultado` trae más de
    `_MAX_SERIES_POR_IMAGEN` categorías distintas (ver `_particionar_series`)
    — `INPC`, si está presente, se repite completo en cada imagen.
    """
    datos = _aplanar_resultado_indice(resultado, comparacion)
    datos = _recortar_tramo(datos, desde, hasta)
    return [_construir_grafica_linea(parte, resultado) for parte in _particionar_series(datos)]


def graficar_indice(
    resultado: ResultadoIndice,
    comparacion: ResultadoIndice | None = None,
    desde: PeriodoQuincenal | PeriodoMensual | None = None,
    hasta: PeriodoQuincenal | PeriodoMensual | None = None,
) -> None:
    """Grafica un `ResultadoIndice`, en una o varias imágenes; no devuelve nada.

    Args:
        resultado: Resultado principal a graficar.
        comparacion: Un segundo `ResultadoIndice` opcional, para superponer
            en la misma gráfica (ej. INPC en negro + una clasificación).
        desde: Periodo inicial del tramo a graficar. `None` = desde el
            primer periodo disponible.
        hasta: Periodo final del tramo a graficar. `None` = hasta el
            último periodo disponible.
    """

    if isinstance(resultado, ResultadoIndice):
        for grafica in _graficas_linea(resultado, comparacion, desde, hasta):
            grafica.draw(show=True)
    else:
        print("Error, se esperaba un ResultadoIndice.")
