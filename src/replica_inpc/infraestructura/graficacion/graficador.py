"""Graficación de `ResultadoIndice`/`ResultadoVariacion`/`ResultadoIncidencia` sobre plotnine.

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
    geom_col,
    geom_hline,
    geom_line,
    geom_point,
    ggplot,
    guide_legend,
    guides,
    labs,
    scale_color_manual,
    scale_fill_manual,
    scale_linetype_identity,
    scale_x_datetime,
    scale_y_continuous,
    theme,
    theme_bw,
)

from replica_inpc.dominio.calculo._temporal import es_mensual
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.infraestructura.graficacion._prepocesamiento import (
    _COLOR_INPC,
    _COLUMNA_INCIDENCIA,
    _COLUMNA_VARIACION,
    _ETIQUETA_Y_INCIDENCIA,
    _ETIQUETA_Y_VARIACION,
    _MAX_COLUMNAS_LEYENDA,
    _RESTOS,
    _VALOR_BASE,
    _VALOR_BASE_INCIDENCIA,
    _VALOR_BASE_VARIACION,
    _ancho_barra,
    _aplanar_resultado,
    _breaks_desde_extremos,
    _breaks_y,
    _breaks_y_etiquetas_x,
    _colores_y_etiquetas,
    _datos_para_puntos,
    _etiqueta_y_indice,
    _extremos_apilado,
    _ordenar_series_dibujo,
    _particionar_apilado,
    _particionar_series,
    _pie_apilado,
    _primero_y_ultimo_para_anotar,
    _recortar_tramo,
    _titulo,
)

# Pies de imagen, en gris tenue para que no compitan con el contenido.
_GRIS_PIE = "#666666"


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


def _construir_grafica_barras(
    datos: pd.DataFrame,
    linea: pd.DataFrame | None = None,
    *,
    orden: list[str] | None = None,
    pie_izquierda: str | None = None,
    pie_derecha: str | None = None,
) -> ggplot:
    """Arma el `ggplot` de barras apiladas por periodo, con una línea de referencia opcional.

    `datos` trae una fila por `(periodo, indice)` con `incidencia_pp`; cada
    categoría es un segmento de la barra de su periodo. `linea`, si viene, es
    otro DataFrame ya aplanado (`variacion_pp`) que se superpone como línea
    negra — típicamente la variación del INPC de la que las incidencias son
    descomposición.

    No reusa `_construir_grafica_linea` porque casi nada coincide: el eje Y se
    calcula sobre el apilado y no sobre la columna (`_extremos_apilado`), las
    barras necesitan ancho explícito en días, y hay dos escalas de leyenda
    (relleno para las categorías, color para la línea) en vez de una.

    La línea marca el NETO del periodo, que solo coincide con el techo de la
    barra cuando todas las categorías son positivas — con una negativa, el
    neto queda por debajo del tope dibujado.

    Los dos pies dicen el alcance de la imagen sin ensuciar el título, que se
    mantiene igual en todas las imágenes de la misma serie. Usan los dos textos
    de figura que ofrece plotnine: `caption` (anclado abajo a la derecha) y
    `tag`, al que se le fija posición abajo a la izquierda — agregarlos a mano
    sobre la figura no es opción, porque `draw(show=False)` la cierra al salir
    y ya no se puede mostrar.

    El orden de la leyenda no es el del apilado: los agregados de resto se
    apilan en el extremo (primeros en el orden categórico) pero se listan al
    final, después de las categorías reales.
    """
    datos = datos.copy()
    datos["indice"] = _ordenar_series_dibujo(datos["indice"], orden)
    series = list(pd.unique(datos["indice"]))
    colores, etiquetas_leyenda = _colores_y_etiquetas(series)
    orden_leyenda = [s for s in series if s not in set(_RESTOS)]
    orden_leyenda += [s for s in _RESTOS if s in set(series)]

    piso, techo = _extremos_apilado(datos, _COLUMNA_INCIDENCIA, linea, _COLUMNA_VARIACION)
    breaks_y = _breaks_desde_extremos(piso, techo, _VALOR_BASE_INCIDENCIA)
    breaks_x, etiquetas_x = _breaks_y_etiquetas_x(datos)

    grafica = (
        ggplot()
        + geom_hline(yintercept=_VALOR_BASE_INCIDENCIA, color="grey", size=0.3)
        + geom_col(
            mapping=aes(x="periodo_ts", y=_COLUMNA_INCIDENCIA, fill="indice"),
            data=datos,
            width=_ancho_barra(datos),
        )
        + scale_fill_manual(values=colores, labels=etiquetas_leyenda, breaks=orden_leyenda)
    )
    if linea is not None:
        series_linea = list(pd.unique(linea["indice"]))
        grafica = (
            grafica
            + geom_line(
                mapping=aes(x="periodo_ts", y=_COLUMNA_VARIACION, color="indice"),
                data=linea,
                size=0.3,
            )
            + scale_color_manual(values={s: _COLOR_INPC for s in series_linea})
        )

    return (
        grafica
        + scale_x_datetime(breaks=breaks_x, labels=etiquetas_x, expand=(0.01, 0.01))  # type: ignore[arg-type]
        + scale_y_continuous(breaks=breaks_y, expand=(0.01, 0.01))  # type: ignore[arg-type]
        + labs(
            title=_titulo(datos),
            x="Periodo",
            y=_ETIQUETA_Y_INCIDENCIA,
            caption=pie_derecha,
            tag=pie_izquierda,
        )
        + guides(fill=guide_legend(ncol=_MAX_COLUMNAS_LEYENDA))
        + theme_bw()
        + theme(
            axis_title=element_text(size=8),
            axis_text_x=element_text(rotation=30, ha="right", size=6),
            axis_text_y=element_text(size=6),
            plot_caption=element_text(size=6, ha="right", color=_GRIS_PIE),
            plot_tag=element_text(size=6, ha="left", color=_GRIS_PIE),
            plot_tag_position="bottomleft",
            plot_tag_location="plot",
            legend_position="bottom",
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


def _graficar_incidencia(
    resultado: ResultadoIncidencia,
    comparacion: ResultadoVariacion | None,
    desde: PeriodoQuincenal | PeriodoMensual | None,
    hasta: PeriodoQuincenal | PeriodoMensual | None,
) -> None:
    """Arma y dibuja las barras apiladas de `resultado`, con `comparacion` como línea si viene.

    Se generan tantas imágenes como hagan falta para detallar las categorías
    que cubren `_COBERTURA_OBJETIVO` de la magnitud total; en cada una, lo que
    esa imagen no detalla va agregado en dos grises, así la barra sigue valiendo
    el total del periodo y la línea cierra en todas (ver `_particionar_apilado`).

    El tramo se recorta ANTES de repartir: qué categorías merecen detalle
    depende de lo que se va a mirar, no del histórico completo.
    """
    datos = _recortar_tramo(_aplanar_resultado(resultado), desde, hasta)
    linea = None
    if comparacion is not None:
        linea = _recortar_tramo(_aplanar_resultado(comparacion), desde, hasta)

    categorias_totales = len(pd.unique(datos["indice"]))
    partes = _particionar_apilado(datos, _COLUMNA_INCIDENCIA)
    for i, parte in enumerate(partes, start=1):
        cobertura, numeracion = _pie_apilado(parte, i, len(partes), categorias_totales)
        _construir_grafica_barras(
            parte, linea, pie_izquierda=cobertura, pie_derecha=numeracion
        ).draw(show=True)


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
    resultado: ResultadoIndice | ResultadoVariacion | ResultadoIncidencia,
    comparacion: ResultadoIndice | ResultadoVariacion | None = None,
    desde: PeriodoQuincenal | PeriodoMensual | None = None,
    hasta: PeriodoQuincenal | PeriodoMensual | None = None,
) -> None:
    """Grafica un `ResultadoIndice`, `ResultadoVariacion` o `ResultadoIncidencia`; no devuelve nada.

    Detecta el tipo de `resultado` y dispara el pipeline correspondiente —
    línea para índice (base 100, eje Y "Indice") y variación (base 0, eje Y
    "Variación (pp)"), barras apiladas para incidencia (base 0, eje Y
    "Incidencia (pp)") — mismo punto de entrada para los tres, sin elegir
    función según el tipo del resultado.

    Args:
        resultado: Resultado principal a graficar — `ResultadoIndice`,
            `ResultadoVariacion` o `ResultadoIncidencia`.
        comparacion: Un segundo resultado opcional, con la MISMA periodicidad
            que `resultado` (quincenal o mensual — mezclarlas rompe la
            comparación de periodos aguas abajo, además de no tener sentido
            superponer dos resoluciones temporales distintas). Para índices y
            variaciones debe ser del MISMO tipo que `resultado` y se superpone
            como línea punteada (ej. INPC en negro + una clasificación); si
            ambos son `ResultadoVariacion`, además deben compartir
            `clase_variacion`. Para una incidencia es el único caso donde el
            tipo NO coincide: se espera un `ResultadoVariacion` — la variación
            del INPC de la que esas incidencias son descomposición — que se
            dibuja como línea negra sobre las barras, y debe compartir la
            clase con la incidencia.
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
    elif isinstance(resultado, ResultadoIncidencia):
        if comparacion is not None:
            # Único caso donde comparacion NO es del mismo tipo que resultado: las
            # barras son la descomposición y la línea es el agregado del que salen,
            # así que superponer dos incidencias no diría nada.
            if not isinstance(comparacion, ResultadoVariacion):
                print(
                    "Error, comparacion de una incidencia debe ser un ResultadoVariacion "
                    "(la variación del INPC que las incidencias descomponen)."
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
                    "Error, comparacion debe tener la misma clase (frecuencia) que resultado "
                    f"('{resultado.manifiesto.clase}' != '{comparacion.manifiesto.clase}')."
                )
                return
        _graficar_incidencia(resultado, comparacion, desde, hasta)
    else:
        print("Error, se esperaba un ResultadoIndice, ResultadoVariacion o ResultadoIncidencia.")
