"""Utilidades temporales compartidas por `variaciones.py` e `incidencias.py`.

Centraliza el alias de frecuencia, los mapas de lag y la aritmética de
periodos que en v1 estaba duplicada literalmente en ambos módulos.
"""

from __future__ import annotations

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
    """Resta `n` quincenas a `periodo`."""
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    return PeriodoQuincenal(ordinal // 24, (ordinal % 24) // 2 + 1, ordinal % 2 + 1)


def restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    """Resta `n` meses a `periodo`."""
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    return PeriodoMensual(ordinal // 12, ordinal % 12 + 1)


def es_mensual(df: pd.DataFrame) -> bool:
    """`True` si el nivel `periodo` del índice contiene periodos mensuales."""
    return isinstance(df.index.get_level_values("periodo")[0], PeriodoMensual)


def resolver_extremo(
    exacto: PeriodoQuincenal | PeriodoMensual,
    validos: list[PeriodoQuincenal | PeriodoMensual],
    incluir_parciales: bool,
    primero: bool,
) -> PeriodoQuincenal | PeriodoMensual | None:
    """Resuelve el periodo real de un extremo de rango para un índice/genérico.

    Devuelve `exacto` si tiene dato; si no y `incluir_parciales`, el primer
    (o último) periodo válido; `None` si no es computable.
    """
    if exacto in validos:
        return exacto
    if not incluir_parciales or not validos:
        return None
    return validos[0] if primero else validos[-1]
