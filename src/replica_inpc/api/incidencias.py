"""Cálculo y análisis de incidencias."""

from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.calculo.incidencias import (
    incidencia_acumulada_anual as _incidencia_acumulada_anual,
)
from replica_inpc.dominio.calculo.incidencias import (
    incidencia_desde as _incidencia_desde,
)
from replica_inpc.dominio.calculo.incidencias import (
    incidencia_periodica as _incidencia_periodica,
)
from replica_inpc.dominio.consulta import incidencias as _consulta
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import periodo_desde_str

# -- series --------------------------------------------------------------------


def incidencia_periodica(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    frecuencia: str,
) -> ResultadoIncidencia:
    """Incidencia de cada periodo contra N periodos anteriores."""
    return _incidencia_periodica(inpc, clasificacion, canastas, frecuencia)  # type: ignore[arg-type]


def incidencia_acumulada_anual(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
) -> ResultadoIncidencia:
    """Incidencia acumulada del año en curso por genérico."""
    return _incidencia_acumulada_anual(inpc, clasificacion, canastas)


def incidencia_desde(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    desde: str | None = None,
    hasta: str | None = None,
    incluir_parciales: bool = True,
) -> ResultadoIncidencia:
    """Incidencia total del rango `[desde, hasta]`; una fila por genérico."""
    return _incidencia_desde(
        inpc,
        clasificacion,
        canastas,
        periodo_desde_str(desde) if desde is not None else None,
        periodo_desde_str(hasta) if hasta is not None else None,
        incluir_parciales,
    )


# -- análisis ------------------------------------------------------------------


def incidencia_en(resultado: ResultadoIncidencia, periodo: str) -> pd.DataFrame:
    """Incidencia de todas las categorías en `periodo`; índice = `indice`."""
    return _consulta.incidencia_en(resultado, periodo_desde_str(periodo))


def incidencia_acumulada(
    resultado: ResultadoIncidencia,
    desde: str,
    hasta: str | None = None,
    *,
    indice: str,
) -> float:
    """Incidencia acumulada del rango para `indice`."""
    return _consulta.incidencia_acumulada(
        resultado,
        periodo_desde_str(desde),
        periodo_desde_str(hasta) if hasta is not None else None,
        indice=indice,
    )


def incidencia_promedio(
    resultado: ResultadoIncidencia,
    desde: str | None = None,
    hasta: str | None = None,
    *,
    indice: str,
) -> float:
    """Media aritmética de `incidencia_pp` en el rango para `indice`."""
    return _consulta.incidencia_promedio(
        resultado,
        periodo_desde_str(desde) if desde is not None else None,
        periodo_desde_str(hasta) if hasta is not None else None,
        indice=indice,
    )


def mayor_incidencia(
    resultado: ResultadoIncidencia,
    desde: str | None = None,
    hasta: str | None = None,
    indice: str | None = None,
) -> tuple[str, str, float]:
    """`(periodo, indice, incidencia_pp)` del máximo en el rango."""
    periodo, idx, valor = _consulta.mayor_incidencia(
        resultado,
        periodo_desde_str(desde) if desde is not None else None,
        periodo_desde_str(hasta) if hasta is not None else None,
        indice,
    )
    return str(periodo), idx, valor


def menor_incidencia(
    resultado: ResultadoIncidencia,
    desde: str | None = None,
    hasta: str | None = None,
    indice: str | None = None,
) -> tuple[str, str, float]:
    """`(periodo, indice, incidencia_pp)` del mínimo en el rango."""
    periodo, idx, valor = _consulta.menor_incidencia(
        resultado,
        periodo_desde_str(desde) if desde is not None else None,
        periodo_desde_str(hasta) if hasta is not None else None,
        indice,
    )
    return str(periodo), idx, valor
