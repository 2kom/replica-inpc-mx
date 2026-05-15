"""Lógica compartida por las tres funciones de validación interna.

`validacion/indices.py`, `variaciones.py` e `incidencias.py` reutilizan la
clasificación por fila y el rollup global; el ensamblado de las DataFrames de
salida vive en cada función (los esquemas divergen).
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_Periodo = PeriodoQuincenal | PeriodoMensual

# Estados que cuentan como comparación realizada contra INEGI.
_COMPARABLES = frozenset({"ok", "diferencia_detectada", "diferencia_por_parcial"})


def clasificar(
    replicado: float,
    inegi_indice: dict[_Periodo, float | None] | None,
    periodo: _Periodo,
    estado_calculo: str,
    tolerancia: float,
    *,
    admite_sin_calculo: bool,
) -> tuple[str, float, float]:
    """Clasifica una fila `(periodo, indice)` contra INEGI.

    Devuelve `(estado_validacion, valor_inegi, error_absoluto)`. `valor_inegi`
    y `error_absoluto` quedan en `NaN` cuando no aplican.
    """
    if not inegi_indice or periodo not in inegi_indice:
        return "fuera_rango_inegi", float("nan"), float("nan")
    valor_inegi = inegi_indice[periodo]
    if valor_inegi is None:
        return "no_disponible", float("nan"), float("nan")
    valor_inegi = float(valor_inegi)
    if admite_sin_calculo and estado_calculo in ("sin_datos", "fallida"):
        # Faltante del lado replicado: se conserva el valor INEGI, sin error.
        return "sin_calculo", valor_inegi, float("nan")
    error = abs(float(replicado) - valor_inegi)
    if error <= tolerancia:
        return "ok", valor_inegi, error
    if estado_calculo == "parcial":
        return "diferencia_por_parcial", valor_inegi, error
    return "diferencia_detectada", valor_inegi, error


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
