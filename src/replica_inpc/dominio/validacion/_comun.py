"""Lógica compartida por las tres funciones de validación interna.

`validacion/indices.py`, `variaciones.py` e `incidencias.py` reutilizan el
rollup global y los conteos del `.resumen`. La clasificación por fila NO se
comparte: cada función la resuelve con su propio bloque vectorizado, y el
ensamblado de las DataFrames de salida vive en cada una (los esquemas divergen).
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

# Estados que cuentan como comparación realizada contra INEGI.
_COMPARABLES = frozenset({"ok", "diferencia_detectada", "diferencia_por_parcial"})


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
