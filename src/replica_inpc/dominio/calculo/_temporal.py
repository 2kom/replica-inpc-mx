"""Utilidades temporales compartidas por `variaciones.py` e `incidencias.py`.

Centraliza el alias de frecuencia, los mapas de lag y la aritmética de
periodos que en v1 estaba duplicada literalmente en ambos módulos.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import pandas as pd

from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

Frecuencia = Literal[
    "quincenal",
    "mensual",
    "bimestral",
    "trimestral",
    "cuatrimestral",
    "semestral",
    "anual",
]

# Lag en número de quincenas / meses según la frecuencia solicitada.
LAG_QUINCENAL: dict[str, int] = {
    "quincenal": 1,
    "mensual": 2,
    "bimestral": 4,
    "trimestral": 6,
    "cuatrimestral": 8,
    "semestral": 12,
    "anual": 24,
}

LAG_MENSUAL: dict[str, int] = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "cuatrimestral": 4,
    "semestral": 6,
    "anual": 12,
}


def restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    """Resta `n` quincenas a `periodo`, cruzando el cambio de año.

    Convierte a un ordinal de quincenas desde el año 0 para no tener que
    manejar el acarreo a mano. `n` no se valida: los únicos llamadores lo
    sacan de `LAG_QUINCENAL`, que solo tiene enteros positivos.
    """
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    return PeriodoQuincenal(ordinal // 24, (ordinal % 24) // 2 + 1, ordinal % 2 + 1)


def restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    """Resta `n` meses a `periodo`, cruzando el cambio de año.

    Mismo mecanismo ordinal que `restar_quincenas`, con 12 en vez de 24. No se
    unifican en una sola función: los tipos de entrada y de salida son
    distintos, y fundirlas obligaría a un `isinstance` que el llamador ya
    resolvió al elegir la tabla de lag.
    """
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    return PeriodoMensual(ordinal // 12, ordinal % 12 + 1)


def es_mensual(df: pd.DataFrame) -> bool:
    """`True` si el nivel `periodo` del índice contiene periodos mensuales.

    Mira solo la primera fila, así que asume lo que todos los llamadores le
    dan: un DataFrame no vacío, con nivel `periodo` y una única periodicidad.
    Un resultado con periodos mixtos reportaría la del primero sin avisar —
    no hay ruta que los produzca (`a_mensual` convierte el resultado entero y
    `empalmar` exige la misma periodicidad en todos los tramos), y sondear el
    índice completo en cada llamada costaría más de lo que protege.
    """
    return isinstance(df.index.get_level_values("periodo")[0], PeriodoMensual)


def resolver_extremo(
    exacto: PeriodoQuincenal | PeriodoMensual,
    validos: Sequence[PeriodoQuincenal | PeriodoMensual],
    *,
    incluir_parciales: bool,
    primero: bool,
) -> PeriodoQuincenal | PeriodoMensual | None:
    """Resuelve el periodo real de un extremo de rango para un índice/genérico.

    Devuelve `exacto` si tiene dato; si no y `incluir_parciales`, el periodo
    válido más temprano (`primero`) o más tardío; `None` si no es computable.

    Toma el mínimo y el máximo en vez del primer y último elemento: así el
    resultado no depende de que `validos` venga ordenado. Ambos llamadores hoy
    lo pasan ordenado, pero eso era un contrato implícito que nada verificaba y
    cuya violación no habría fallado — habría devuelto el extremo equivocado.

    `validos` es `Sequence` y no `list` porque la función solo la recorre: con
    `list` invariante, pasarle una `list[PeriodoQuincenal]` concreta no
    tipa contra la unión, aunque sea un uso perfectamente válido.
    """
    if exacto in validos:
        return exacto
    if not incluir_parciales or not validos:
        return None
    return min(validos) if primero else max(validos)  # type: ignore[type-var]
