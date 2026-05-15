"""Cálculo y análisis de variaciones (inflación)."""

from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.api._periodos import parsear_periodo
from replica_inpc.dominio.calculo.variaciones import (
    variacion_acumulada_anual as _variacion_acumulada_anual,
)
from replica_inpc.dominio.calculo.variaciones import (
    variacion_desde as _variacion_desde,
)
from replica_inpc.dominio.calculo.variaciones import (
    variacion_periodica as _variacion_periodica,
)
from replica_inpc.dominio.consulta import variaciones as _consulta
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion

# -- series --------------------------------------------------------------------


def variacion_periodica(resultado: ResultadoIndice, frecuencia: str) -> ResultadoVariacion:
    """Variación de cada periodo contra N periodos anteriores según `frecuencia`."""
    return _variacion_periodica(resultado, frecuencia)  # type: ignore[arg-type]


def variacion_acumulada_anual(resultado: ResultadoIndice) -> ResultadoVariacion:
    """Variación acumulada del año en curso (ene→periodo vs dic año anterior)."""
    return _variacion_acumulada_anual(resultado)


def variacion_desde(
    resultado: ResultadoIndice,
    desde: str,
    hasta: str | None = None,
    incluir_parciales: bool = True,
) -> ResultadoVariacion:
    """Variación total del rango `[desde, hasta]`; una fila por índice."""
    return _variacion_desde(
        resultado,
        parsear_periodo(desde),
        parsear_periodo(hasta) if hasta is not None else None,
        incluir_parciales,
    )


# -- análisis ------------------------------------------------------------------


def inflacion_en(resultado: ResultadoVariacion, periodo: str) -> pd.DataFrame:
    """Variación de todas las categorías en `periodo`; índice = `indice`."""
    return _consulta.inflacion_en(resultado, parsear_periodo(periodo))


def inflacion_acumulada(
    resultado: ResultadoVariacion,
    desde: str,
    hasta: str | None = None,
    *,
    indice: str,
) -> float:
    """Variación total del rango para `indice`."""
    return _consulta.inflacion_acumulada(
        resultado,
        parsear_periodo(desde),
        parsear_periodo(hasta) if hasta is not None else None,
        indice=indice,
    )


def inflacion_promedio(
    resultado: ResultadoVariacion,
    desde: str | None = None,
    hasta: str | None = None,
    *,
    indice: str,
    metodo: Literal["tcac", "simple"] = "tcac",
) -> float:
    """Inflación promedio del rango para `indice` (TCAC o media simple)."""
    return _consulta.inflacion_promedio(
        resultado,
        parsear_periodo(desde) if desde is not None else None,
        parsear_periodo(hasta) if hasta is not None else None,
        indice=indice,
        metodo=metodo,
    )


def inflacion_maxima(
    resultado: ResultadoVariacion,
    desde: str | None = None,
    hasta: str | None = None,
    indice: str | None = None,
) -> tuple[str, str, float]:
    """`(periodo, indice, variacion_pp)` del máximo en el rango."""
    periodo, idx, valor = _consulta.inflacion_maxima(
        resultado,
        parsear_periodo(desde) if desde is not None else None,
        parsear_periodo(hasta) if hasta is not None else None,
        indice,
    )
    return str(periodo), idx, valor


def inflacion_minima(
    resultado: ResultadoVariacion,
    desde: str | None = None,
    hasta: str | None = None,
    indice: str | None = None,
) -> tuple[str, str, float]:
    """`(periodo, indice, variacion_pp)` del mínimo en el rango."""
    periodo, idx, valor = _consulta.inflacion_minima(
        resultado,
        parsear_periodo(desde) if desde is not None else None,
        parsear_periodo(hasta) if hasta is not None else None,
        indice,
    )
    return str(periodo), idx, valor
