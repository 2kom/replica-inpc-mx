"""Consulta de variaciones sobre un `ResultadoVariacion`.

Funciones thin sin estado ni IO; operan sobre la columna `variacion_pp`.
Devuelven escalares, pares o `DataFrame` — nunca un `ResultadoX`.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.consulta import _comun
from replica_inpc.dominio.consulta._comun import Periodo
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoQuincenal

_COL = "variacion_pp"


def inflacion_en(resultado: ResultadoVariacion, periodo: Periodo) -> pd.DataFrame:
    """Variación de todas las categorías en `periodo`; índice = `indice`."""
    return _comun.valor_en(resultado.df, _COL, periodo)


def inflacion_acumulada(
    resultado: ResultadoVariacion,
    desde: Periodo,
    hasta: Periodo | None = None,
    *,
    indice: str,
) -> float:
    """Suma de `variacion_pp` en `[desde, hasta]` para `indice`."""
    return _comun.acumulada(resultado.df, _COL, desde, hasta, indice)


def inflacion_promedio(
    resultado: ResultadoVariacion,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    *,
    indice: str,
    metodo: Literal["tcac", "simple"] = "tcac",
) -> float:
    """Inflación promedio del rango para `indice`.

    `metodo="simple"` → media aritmética de `variacion_pp`.
    `metodo="tcac"` → tasa de crecimiento anual compuesta.
    """
    if metodo == "simple":
        return _comun.promedio_simple(resultado.df, _COL, desde, hasta, indice)
    if metodo == "tcac":
        return _tcac(resultado.df, desde, hasta, indice)
    raise InvarianteViolado(f"metodo '{metodo}' inválido; usa 'tcac' o 'simple'.")


def _tcac(
    df: pd.DataFrame, desde: Periodo | None, hasta: Periodo | None, indice: str
) -> float:
    """Tasa de crecimiento anual compuesta sobre las variaciones del rango.

    `factor = Π(1 + v/100)`; se anualiza suponiendo que cada fila representa
    `1/ppy` de año (`ppy = 24` quincenal, `12` mensual).
    """
    serie = _comun.serie_en_rango(df, _COL, desde, hasta, indice)
    factor = float((1.0 + serie / 100.0).prod())
    ppy = 24 if isinstance(serie.index[0], PeriodoQuincenal) else 12
    return (factor ** (ppy / len(serie)) - 1.0) * 100.0


def inflacion_maxima(
    resultado: ResultadoVariacion,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    indice: str | None = None,
) -> tuple[Periodo, str, float]:
    """`(periodo, indice, variacion_pp)` del máximo en el rango."""
    return _comun.extremo(resultado.df, _COL, desde, hasta, indice, mayor=True)


def inflacion_minima(
    resultado: ResultadoVariacion,
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    indice: str | None = None,
) -> tuple[Periodo, str, float]:
    """`(periodo, indice, variacion_pp)` del mínimo en el rango."""
    return _comun.extremo(resultado.df, _COL, desde, hasta, indice, mayor=False)
