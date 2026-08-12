"""Lógica compartida por las tres funciones de validación interna.

`validacion/indices.py`, `variaciones.py` e `incidencias.py` reutilizan el
rollup global, los conteos del `.resumen` y el alias `SeriesInegi` de su
entrada. La clasificación por fila NO se comparte: cada función la resuelve con
su propio bloque vectorizado, y el ensamblado de las DataFrames de salida vive
en cada una (los esquemas divergen).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import TypeAlias, TypeVar

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

Periodo: TypeAlias = PeriodoQuincenal | PeriodoMensual

PeriodoT = TypeVar("PeriodoT", bound=Periodo)

#: Series publicadas por INEGI, ya resueltas por quien hizo el I/O. Clave
#: exterior: nombre del índice; interior: el periodo consultado. Valor `None` =
#: INEGI tiene el periodo en rango pero sin dato; periodo ausente del mapa
#: interior = fuera del histórico publicado. Es `Mapping` y no `dict` porque los
#: comparadores solo leen: el esquema completo vive en el docstring del puerto
#: `FuenteValidacion`.
#:
#: Genérico en el periodo a propósito: la clave de `Mapping` es invariante, así
#: que un alias fijado a la unión rechazaría el `dict[str, dict[PeriodoMensual,
#: ...]]` que devuelve `obtener_incidencias`. Cada comparador se tipa como
#: `SeriesInegi[PeriodoT]` y mypy resuelve el parámetro por llamada.
SeriesInegi: TypeAlias = Mapping[str, Mapping[PeriodoT, float | None]]

# Estados que cuentan como comparación realizada contra INEGI.
_COMPARABLES = frozenset({"ok", "diferencia_detectada", "diferencia_por_parcial"})


def verificar_tolerancia(tolerancia: float, metodo: str) -> None:
    """Exige una tolerancia finita y no negativa.

    Sin esta guardia una tolerancia negativa o `NaN` no falla: hace que
    `error <= tolerancia` sea falso en toda fila, y dos series idénticas se
    reportan como `diferencia_detectada` con `error_absoluto = 0.0`. El valor
    llega desde `rep.tolerancia_indice`/`rep.tolerancia_derivados`, que son
    superficie pública y configurable, así que la comprobación vive acá —
    protege también a quien invoque el comparador directo.

    Raises:
        InvarianteViolado: Si `tolerancia` es negativa, `NaN` o infinita.
    """
    if math.isnan(tolerancia) or math.isinf(tolerancia) or tolerancia < 0:
        raise InvarianteViolado(
            f"{metodo}: la tolerancia debe ser un número finito >= 0; se recibió {tolerancia}."
        )


def rollup_global(estados: Iterable[str]) -> str:
    """Estado de validación global por prioridad descendente.

    `diferencia_detectada` > `diferencia_por_parcial` > `sin_calculo` >
    `no_disponible` (solo si no hay ninguna fila comparable) > `ok`.
    `fuera_rango_inegi` nunca afecta el estado global.
    """
    conjunto = set(estados)
    if "diferencia_detectada" in conjunto:
        return "diferencia_detectada"
    if "diferencia_por_parcial" in conjunto:
        return "diferencia_por_parcial"
    if "sin_calculo" in conjunto:
        return "sin_calculo"
    if not (conjunto & _COMPARABLES):
        return "no_disponible"
    return "ok"


def contar(estados: Iterable[str]) -> dict[str, int]:
    """Conteos de `estado_validacion` para el `.resumen`."""
    serie = pd.Series(list(estados), dtype="object")
    return {
        "n_comparables": int(serie.isin(_COMPARABLES).sum()),
        "n_fuera_rango_inegi": int((serie == "fuera_rango_inegi").sum()),
        "n_no_disponibles": int((serie == "no_disponible").sum()),
        "n_diferencia_por_parcial": int((serie == "diferencia_por_parcial").sum()),
        "n_sin_calculo": int((serie == "sin_calculo").sum()),
    }
