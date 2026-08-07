"""Graficación de `ResultadoIndice`/`ResultadoVariacion` sobre plotnine.

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
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    scale_linetype_identity,
    scale_x_datetime,
    scale_y_continuous,
    theme,
    theme_bw,
)

from replica_inpc.dominio.calculo._temporal import es_mensual
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.infraestructura.graficacion._prepocesamiento import (
    _ETIQUETA_Y_VARIACION,
    _VALOR_BASE,
    _VALOR_BASE_VARIACION,
    _aplanar_resultado,
    _breaks_y,
    _breaks_y_etiquetas_x,
    _colores_y_etiquetas,
    _datos_para_puntos,
    _etiqueta_y_indice,
    _ordenar_series_dibujo,
    _particionar_series,
    _primero_y_ultimo_para_anotar,
    _recortar_tramo,
    _titulo,
)


def _construir_grafica_linea(
    datos: pd.DataFrame,
    resultado: ResultadoIndice | ResultadoVariacion,
    *,
    columna_valor: str = "indice_replicado",
    valor_base: float = _VALOR_BASE,
    etiqueta_y: str | None = None,
) -> ggplot:
    """Arma el `ggplot` completo a partir de `datos` ya aplanados (y opcionalmente particionados).

    `resultado` solo se usa para la etiqueta del eje Y cuando `etiqueta_y` no
    viene explícita (índices: `periodo_referencia` si fue rebasado) — los
    datos a dibujar salen enteros de `datos`. `columna_valor`, `valor_base` y
    `etiqueta_y` permiten reusar el mismo armado para variaciones
    (`variacion_pp`, base 0, `"Variación (pp)"`).
    """
    datos = datos.copy()
    datos["indice"] = _ordenar_series_dibujo(datos["indice"])
    titulo = _titulo(datos)

    series = list(pd.unique(datos["indice"]))
    breaks_x, etiquetas_x = _breaks_y_etiquetas_x(datos)
    breaks_y = _breaks_y(datos, columna_valor, valor_base)
    etiqueta_y_final = etiqueta_y if etiqueta_y is not None else _etiqueta_y_indice(resultado)
    colores, etiquetas_leyenda = _colores_y_etiquetas(series)

    grafica = ggplot(
        datos, aes(x="periodo_ts", y=columna_valor, color="indice", linetype="linetype")
    )
    if breaks_y[0] <= valor_base <= breaks_y[-1]:
        # Fuera de rango (ej. tramo recortado donde todo el valor quedó por
        # encima o por debajo de la base): la línea de base ya no aporta nada,
        # se omite en vez de dibujarla fuera del panel visible.
        grafica = grafica + geom_hline(
            yintercept=valor_base, linetype="dashed", color="grey", size=0.3
        )
    grafica = grafica + geom_line(size=0.5) + scale_linetype_identity(guide=None)
    # Los puntos no van siempre: en un tramo largo, uno por periodo satura la
    # línea. `_datos_para_puntos` decide qué filas los llevan — todas si el
    # tramo cabe en un año, o solo las series de una única observación (ej.
    # variacion_desde, o una categoría que aparece en un solo periodo), que
    # `geom_line` deja invisibles.
    datos_puntos = _datos_para_puntos(datos)
    if datos_puntos is not None:
        grafica = grafica + geom_point(data=datos_puntos, size=0.5)

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
                y=primero[columna_valor],
                label=f"{primero[columna_valor]:.2f}",
                ha="right",
                va="center",
                size=6,
                color=colores[primero["indice"]],
            )
            + annotate(
                "text",
                x=max(breaks_x),  # type: ignore[arg-type]
                y=ultimo[columna_valor],
                label=f"{ultimo[columna_valor]:.2f}",
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
        + labs(title=titulo, x="Periodo", y=etiqueta_y_final)
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


def _graficar_indice(
    resultado: ResultadoIndice,
    comparacion: ResultadoIndice | None,
    desde: PeriodoQuincenal | PeriodoMensual | None,
    hasta: PeriodoQuincenal | PeriodoMensual | None,
) -> None:
    """Arma y dibuja uno o varios `ggplot` de `resultado` (+ `comparacion` si viene).

    `desde`/`hasta`, si vienen, recortan el tramo ANTES de particionar — el
    primer/último valor anotado (serie única) y las particiones (varias
    series) ya reflejan solo el tramo pedido, no el histórico completo.

    Más de una sola imagen cuando `resultado` trae más de
    `_MAX_SERIES_POR_IMAGEN` categorías distintas (ver `_particionar_series`)
    — `INPC`, si está presente, se repite completo en cada imagen.
    """
    datos = _aplanar_resultado(resultado, comparacion)
    datos = _recortar_tramo(datos, desde, hasta)
    for parte in _particionar_series(datos):
        _construir_grafica_linea(parte, resultado).draw(show=True)


def _graficar_variacion(
    resultado: ResultadoVariacion,
    comparacion: ResultadoVariacion | None,
    desde: PeriodoQuincenal | PeriodoMensual | None,
    hasta: PeriodoQuincenal | PeriodoMensual | None,
) -> None:
    """Ídem `_graficar_indice` para un `ResultadoVariacion`: `variacion_pp` en el eje Y, base en 0."""
    datos = _aplanar_resultado(resultado, comparacion)
    datos = _recortar_tramo(datos, desde, hasta)
    for parte in _particionar_series(datos):
        _construir_grafica_linea(
            parte,
            resultado,
            columna_valor="variacion_pp",
            valor_base=_VALOR_BASE_VARIACION,
            etiqueta_y=_ETIQUETA_Y_VARIACION,
        ).draw(show=True)


def graficar(
    resultado: ResultadoIndice | ResultadoVariacion,
    comparacion: ResultadoIndice | ResultadoVariacion | None = None,
    desde: PeriodoQuincenal | PeriodoMensual | None = None,
    hasta: PeriodoQuincenal | PeriodoMensual | None = None,
) -> None:
    """Grafica un `ResultadoIndice` o `ResultadoVariacion`, en una o varias imágenes; no devuelve nada.

    Detecta el tipo de `resultado` y dispara el pipeline correspondiente —
    índice (base 100, eje Y "Indice") o variación (base 0, eje Y "Variación
    (pp)") — mismo punto de entrada para ambos, sin elegir función según el
    tipo del resultado.

    Args:
        resultado: Resultado principal a graficar — `ResultadoIndice` o
            `ResultadoVariacion`.
        comparacion: Un segundo resultado opcional, del MISMO tipo que
            `resultado` y con la MISMA periodicidad (quincenal o mensual —
            mezclarlas rompe la comparación de periodos aguas abajo, además
            de no tener sentido superponer dos resoluciones temporales
            distintas), para superponer en la misma gráfica (ej. INPC en
            negro + una clasificación). Si ambos son `ResultadoVariacion`,
            además deben compartir `clase_variacion` (ej. no se puede
            comparar una variación mensual contra una trimestral — los
            periodos representados no son comparables).
        desde: Periodo inicial del tramo a graficar. `None` = desde el
            primer periodo disponible.
        hasta: Periodo final del tramo a graficar. `None` = hasta el
            último periodo disponible.
    """
    if isinstance(resultado, ResultadoIndice):
        if comparacion is not None:
            if not isinstance(comparacion, ResultadoIndice):
                print("Error, comparacion debe ser del mismo tipo que resultado (ResultadoIndice).")
                return
            if es_mensual(resultado.resultado.largo) != es_mensual(comparacion.resultado.largo):
                print(
                    "Error, comparacion debe tener la misma periodicidad (quincenal/mensual) "
                    "que resultado."
                )
                return
        _graficar_indice(resultado, comparacion, desde, hasta)
    elif isinstance(resultado, ResultadoVariacion):
        if comparacion is not None:
            if not isinstance(comparacion, ResultadoVariacion):
                print(
                    "Error, comparacion debe ser del mismo tipo que resultado (ResultadoVariacion)."
                )
                return
            if es_mensual(resultado.resultado.largo) != es_mensual(comparacion.resultado.largo):
                print(
                    "Error, comparacion debe tener la misma periodicidad (quincenal/mensual) "
                    "que resultado."
                )
                return
            if comparacion.manifiesto.clase != resultado.manifiesto.clase:
                print(
                    "Error, comparacion debe tener la misma clase_variacion (frecuencia) que "
                    f"resultado ('{resultado.manifiesto.clase}' != '{comparacion.manifiesto.clase}')."
                )
                return
        _graficar_variacion(resultado, comparacion, desde, hasta)
    else:
        print("Error, se esperaba un ResultadoIndice o ResultadoVariacion.")
