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
    scale_x_datetime,
    scale_y_continuous,
    theme,
    theme_bw,
)

from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.infraestructura.graficacion._prepocesamiento import (
    _VALOR_BASE,
    _aplanar_resultado_indice,
    _breaks_y_etiqueta_y,
    _breaks_y_etiquetas_x,
    _colores_por_serie,
    _datos_para_anotar,
    _primero_y_ultimo,
    _titulo,
)


def _grafica_indice(resultado: ResultadoIndice) -> ggplot:
    """Arma el `ggplot` completo aplicando las reglas de diseño de `ResultadoIndice`."""
    datos = _aplanar_resultado_indice(resultado)
    titulo = _titulo(datos)

    series = list(pd.unique(datos["indice"]))
    breaks_x, etiquetas_x = _breaks_y_etiquetas_x(datos)
    breaks_y, etiqueta_y = _breaks_y_etiqueta_y(datos, resultado)
    colores = _colores_por_serie(series)

    grafica = (
        ggplot(datos, aes(x="periodo_ts", y="indice_replicado", color="indice"))
        + geom_hline(yintercept=_VALOR_BASE, linetype="dashed", color="grey", size=0.3)
        + geom_line(size=0.5)
    )

    datos_anotar = _datos_para_anotar(datos, series)
    if datos_anotar is not None:
        primero, ultimo = _primero_y_ultimo(datos_anotar)
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

    return (
        grafica
        + scale_x_datetime(breaks=breaks_x, labels=etiquetas_x, expand=(0.045, 0.045))  # type: ignore[arg-type]
        + scale_y_continuous(breaks=breaks_y, expand=(0.02, 0.02))  # type: ignore[arg-type]
        + scale_color_manual(values=colores)
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
            figure_size=(8, 4),
            dpi=300,
        )
    )


def graficar_indice(resultado: ResultadoIndice, comparacion: ResultadoIndice | None = None) -> None:
    """Grafica un `ResultadoIndice` y lo muestra de inmediato; no devuelve nada.

    Args:
        resultado: Resultado principal a graficar.
        comparacion: Un segundo `ResultadoIndice` opcional, para superponer
            en la misma gráfica (ej. INPC en negro + una clasificación).
    """

    if isinstance(resultado, ResultadoIndice):
        _grafica_indice(resultado).draw(show=True)
    else:
        print("Error, se esperaba un ResultadoIndice.")
