"""Consulta de incidencias sobre un `ResultadoIncidencia`.

Funciones thin sin estado ni IO; operan sobre la columna `incidencia_pp`.
Devuelven escalares, pares o `DataFrame` — nunca un `ResultadoX`.
"""

from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.consulta import _comun
from replica_inpc.dominio.consulta._comun import Periodo
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia

_COL = "incidencia_pp"


def incidencia_en(resultado: ResultadoIncidencia, periodo: Periodo) -> pd.DataFrame:
    """Incidencia de todas las categorías en `periodo`; índice = `indice`."""
    return _comun.valor_en(resultado.df, _COL, periodo)


def incidencia_acumulada(
    resultado: ResultadoIncidencia,
    desde: Periodo,
    hasta: Periodo | None = None,
    *,
    indice: str,
) -> float:
    """Suma de `incidencia_pp` en `[desde, hasta]` para `indice`."""
    return _comun.acumulada(resultado.df, _COL, desde, hasta, indice)


def incidencia_promedio(
    resultado: ResultadoIncidencia,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    *,
    indice: str,
) -> float:
    """Media aritmética de `incidencia_pp` en `[desde, hasta]` para `indice`."""
    return _comun.promedio_simple(resultado.df, _COL, desde, hasta, indice)


def mayor_incidencia(
    resultado: ResultadoIncidencia,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    indice: str | None = None,
) -> tuple[Periodo, str, float]:
    """`(periodo, indice, incidencia_pp)` del máximo en el rango."""
    return _comun.extremo(resultado.df, _COL, desde, hasta, indice, mayor=True)


def menor_incidencia(
    resultado: ResultadoIncidencia,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    indice: str | None = None,
) -> tuple[Periodo, str, float]:
    """`(periodo, indice, incidencia_pp)` del mínimo en el rango."""
    return _comun.extremo(resultado.df, _COL, desde, hasta, indice, mayor=False)
