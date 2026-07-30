"""Graficación de `ResultadoIndice` sobre plotnine.

Sin `Protocol` en `aplicacion/puertos/`: a diferencia de
`LectorCanasta`/`FuenteValidacion`, ningún componente de `dominio/` o
`aplicacion/` consume un graficador internamente — no hay abstracción que
enforzar (mismo pragmatismo de docs/diseño.md §D1).
"""

from __future__ import annotations

import pandas as pd
from mizani.breaks import breaks_extended
from plotnine import (
    aes,
    annotate,
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

_MAX_ETIQUETAS_EJE_X = 20
_N_ETIQUETAS_EJE_Y = 10
_VALOR_BASE = 100.0
_COLOR_INPC = "black"
# INPC nunca aparece acá — tiene su propio color fijo (_COLOR_INPC).
_PALETA_OTROS_TIPOS = ("#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02")


def _datos_indice(resultado: ResultadoIndice) -> pd.DataFrame:
    """Aplana `resultado.resultado.largo` y agrega `periodo_ts` (timestamp para el eje X)."""
    df = resultado.resultado.largo.reset_index()
    df["periodo_ts"] = pd.to_datetime(df["periodo"].map(lambda p: p.to_timestamp()))
    return df


def _breaks_y_etiquetas_x(datos: pd.DataFrame) -> tuple[list[pd.Timestamp], list[str]]:
    """Elige un subconjunto de periodos reales para las marcas del eje X.

    Usa `str(periodo)` (`"1Q Ene 2024"` o `"Ene 2024"`) de los periodos que
    ya están en los datos — no reconstruye un periodo a partir de una fecha
    arbitraria elegida por el algoritmo de breaks. El primer y último break
    son siempre el primer y último periodo real de los datos.
    """
    pares = datos[["periodo", "periodo_ts"]].drop_duplicates().sort_values("periodo_ts")
    paso = max(1, len(pares) // _MAX_ETIQUETAS_EJE_X)
    seleccion = pares.iloc[::paso]
    extremos = pares.iloc[[0, -1]]
    combinado = (
        pd.concat([seleccion, extremos])
        .drop_duplicates(subset="periodo_ts")
        .sort_values("periodo_ts")
    )
    return list(combinado["periodo_ts"]), [str(p) for p in combinado["periodo"]]


def _breaks_eje_y(datos: pd.DataFrame) -> list[float]:
    """Breaks automáticos + forzados: mínimo y máximo siempre son el primer y último break.

    Ningún break automático ni la base (100) puede quedar por fuera de
    `[mínimo, máximo]` ni desplazar a mínimo/máximo de los extremos de la lista.
    """
    minimo = float(datos["indice_replicado"].min())
    maximo = float(datos["indice_replicado"].max())
    extendidos = breaks_extended(n=_N_ETIQUETAS_EJE_Y)((minimo, maximo))
    intermedios = {b for b in extendidos.tolist() if minimo < b < maximo}
    if minimo < _VALOR_BASE < maximo:
        intermedios.add(_VALOR_BASE)
    return sorted({minimo, maximo, *intermedios})


def _colores_por_tipo(tipos: list[str]) -> dict[str, str]:
    """INPC siempre negro; el resto toma color de paleta en el orden en que aparece."""
    colores: dict[str, str] = {}
    i = 0
    for tipo in tipos:
        if tipo == "INPC":
            colores[tipo] = _COLOR_INPC
        else:
            colores[tipo] = _PALETA_OTROS_TIPOS[i % len(_PALETA_OTROS_TIPOS)]
            i += 1
    return colores


def _primero_y_ultimo(datos: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Primer y último punto (por fecha) de TODO el conjunto, no por `tipo`.

    Solo hay un margen izquierdo y uno derecho en el panel — con varias
    líneas (`comparacion`), se anota el primer/último dato real cronológico
    general, sea cual sea su `tipo`.
    """
    ordenado = datos.sort_values("periodo_ts")
    return ordenado.iloc[0], ordenado.iloc[-1]


def _etiqueta_eje_y(resultado: ResultadoIndice) -> str:
    """`"Indice"`, o `"Indice (periodo_referencia = 100)"` si el resultado fue rebasado."""
    if resultado.periodo_referencia is None:
        return "Indice"
    return f"Indice ({resultado.periodo_referencia} = 100)"


def _titulo(datos: pd.DataFrame) -> str:
    """Los `tipo` presentes unidos por `" + "` (ej. `"INPC"`, `"INPC + CCIF DIVISION"`)."""
    tipos = list(pd.unique(datos["tipo"]))
    return " + ".join(tipos)


def _construir_grafica(
    resultado: ResultadoIndice, comparacion: ResultadoIndice | None = None
) -> ggplot:
    """Arma el `ggplot` completo aplicando las reglas de diseño de `ResultadoIndice`."""
    datos = _datos_indice(resultado)
    if comparacion is not None:
        datos = pd.concat([datos, _datos_indice(comparacion)], ignore_index=True)

    tipos = list(pd.unique(datos["tipo"]))
    breaks_x, etiquetas_x = _breaks_y_etiquetas_x(datos)
    breaks_y = _breaks_eje_y(datos)
    colores = _colores_por_tipo(tipos)
    primero, ultimo = _primero_y_ultimo(datos)

    return (
        ggplot(datos, aes(x="periodo_ts", y="indice_replicado", color="tipo"))
        + geom_hline(yintercept=_VALOR_BASE, linetype="dashed", color="grey", size=0.3)
        + geom_line(size=0.5)
        + annotate(
            "text",
            x=min(breaks_x),  # type: ignore[arg-type]
            y=primero["indice_replicado"],
            label=f"{primero['indice_replicado']:.2f}",
            ha="right",
            va="center",
            size=6,
            color=colores[primero["tipo"]],
        )
        + annotate(
            "text",
            x=max(breaks_x),  # type: ignore[arg-type]
            y=ultimo["indice_replicado"],
            label=f"{ultimo['indice_replicado']:.2f}",
            ha="left",
            va="center",
            size=6,
            color=colores[ultimo["tipo"]],
        )
        + scale_x_datetime(breaks=breaks_x, labels=etiquetas_x, expand=(0.045, 0.045))  # type: ignore[arg-type]
        + scale_y_continuous(breaks=breaks_y, expand=(0.02, 0.02))  # type: ignore[arg-type]
        + scale_color_manual(values=colores)
        + labs(
            title=_titulo(datos),
            x="Periodo",
            y=_etiqueta_eje_y(resultado),
            color="Tipo",
        )
        + theme_bw()
        + theme(
            axis_text_x=element_text(rotation=45, ha="right", size=6),
            axis_text_y=element_text(size=7),
            legend_position="bottom" if len(tipos) > 1 else "none",
            legend_box="horizontal",
            legend_title=element_text(size=7),
            legend_text=element_text(size=7),
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
    _construir_grafica(resultado, comparacion).draw(show=True)
