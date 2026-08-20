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
    """Incidencia de cada periodo contra N periodos anteriores según `frecuencia`.

    Args:
        inpc: resultado de índice INPC global.
        clasificacion: resultado de clasificación (componentes o
            subcomponentes); debe compartir `periodo_referencia` con `inpc`.
        canastas: canastas por versión, con `VersionCanasta` como clave.
        frecuencia: `"quincenal"` (1Q), `"mensual"` (1M), `"bimestral"` (2M),
            `"trimestral"` (3M), `"cuatrimestral"` (4M), `"semestral"` (6M) o
            `"anual"` (12M).

    Raises:
        InvarianteViolado: `inpc.periodo_referencia != clasificacion.periodo_referencia`,
            `frecuencia` fuera del conjunto válido, o `frecuencia="quincenal"`
            con un resultado mensual.
    """
    return _incidencia_periodica(inpc, clasificacion, canastas, frecuencia)  # type: ignore[arg-type]


def incidencia_acumulada_anual(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
) -> ResultadoIncidencia:
    """Incidencia acumulada del año en curso por genérico.

    Propiedad no obvia: la suma de todos los genéricos da la variación anual
    acumulada del INPC — sirve para verificar la aditividad del resultado.

    Raises:
        InvarianteViolado: `inpc.periodo_referencia != clasificacion.periodo_referencia`.
    """
    return _incidencia_acumulada_anual(inpc, clasificacion, canastas)


def incidencia_desde(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    desde: str | None = None,
    hasta: str | None = None,
    incluir_parciales: bool = True,
) -> ResultadoIncidencia:
    """Incidencia total del rango `[desde, hasta]`; una fila por genérico.

    A diferencia de `variacion_desde`, `desde` también es opcional.

    Args:
        desde: `None` = primer periodo disponible.
        hasta: `None` = último disponible.
        incluir_parciales: si `False`, excluye genéricos con
            `estado_calculo = parcial`. Default `True`.

    Raises:
        InvarianteViolado: `inpc.periodo_referencia != clasificacion.periodo_referencia`,
            `desde`/`hasta` fuera de rango o ausente en el resultado, o `desde`
            posterior a `hasta`.
        PeriodoNoInterpretable: `desde`/`hasta` con formato inválido.
    """
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
    """Incidencia de todas las categorías en `periodo`; índice = `indice`.

    Raises:
        PeriodoNoInterpretable: `periodo` con formato inválido.
        InvarianteViolado: `periodo` fuera de rango o ausente en `resultado`.
    """
    return _consulta.incidencia_en(resultado, periodo_desde_str(periodo))


def incidencia_acumulada(
    resultado: ResultadoIncidencia,
    desde: str,
    hasta: str | None = None,
    *,
    indice: str,
) -> float:
    """Incidencia acumulada del rango para `indice`.

    Solo tiene sentido con `incidencia_periodica` como fuente — con
    `incidencia_desde` o `incidencia_acumulada_anual` los valores ya son
    totales y sumarlos sería incorrecto.

    Args:
        indice: debe existir en `resultado`. Keyword-only.

    Raises:
        PeriodoNoInterpretable: `desde`/`hasta` con formato inválido.
        InvarianteViolado: `desde`/`hasta` fuera de rango o ausente en
            `resultado`, `desde` posterior a `hasta`, o `indice` inexistente.
    """
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
    """Media aritmética de `incidencia_pp` en el rango para `indice`.

    Sin parámetro `metodo` — siempre promedio simple, a diferencia de
    `inflacion_promedio` (que además admite TCAC).

    Raises:
        PeriodoNoInterpretable: `desde`/`hasta` con formato inválido.
        InvarianteViolado: `desde`/`hasta` fuera de rango o ausente en
            `resultado`, o `indice` inexistente.
    """
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
    """`(periodo, indice, incidencia_pp)` del máximo en el rango.

    `periodo` se devuelve como `str`. `indice=None` busca el máximo global
    entre todos los índices y periodos, en vez de uno específico.

    Raises:
        PeriodoNoInterpretable: `desde`/`hasta` con formato inválido.
        InvarianteViolado: `desde`/`hasta` fuera de rango o ausente en
            `resultado`, o `indice` inexistente.
    """
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
    """`(periodo, indice, incidencia_pp)` del mínimo en el rango.

    Mismo contrato que `mayor_incidencia`, en la dirección opuesta.
    """
    periodo, idx, valor = _consulta.menor_incidencia(
        resultado,
        periodo_desde_str(desde) if desde is not None else None,
        periodo_desde_str(hasta) if hasta is not None else None,
        indice,
    )
    return str(periodo), idx, valor
