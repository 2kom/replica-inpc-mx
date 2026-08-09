from __future__ import annotations

import pytest

from replica_inpc.dominio.validacion._comun import contar, rollup_global

# -- rollup_global -------------------------------------------------------------

# Prioridad declarada: diferencia_detectada > diferencia_por_parcial >
# sin_calculo > no_disponible (solo sin ninguna fila comparable) > ok.
# Cada caso MEZCLA estados a propósito: la función resuelve precedencia, y un
# estado aislado no prueba que gane sobre los de menor prioridad.


@pytest.mark.parametrize(
    "estados, esperado",
    [
        # diferencia_detectada gana incluso rodeada de todos los demás.
        (
            [
                "ok",
                "diferencia_por_parcial",
                "sin_calculo",
                "no_disponible",
                "fuera_rango_inegi",
                "diferencia_detectada",
            ],
            "diferencia_detectada",
        ),
        # sin diferencia_detectada, gana diferencia_por_parcial.
        (
            ["ok", "sin_calculo", "no_disponible", "fuera_rango_inegi", "diferencia_por_parcial"],
            "diferencia_por_parcial",
        ),
        # sin las dos diferencias, gana sin_calculo.
        (["ok", "no_disponible", "fuera_rango_inegi", "sin_calculo"], "sin_calculo"),
        # no_disponible solo gana cuando NO hay ninguna fila comparable.
        (["no_disponible", "fuera_rango_inegi"], "no_disponible"),
        # el mismo conjunto más un 'ok' (comparable) cae a ok — es la condición
        # que distingue este caso del anterior.
        (["no_disponible", "fuera_rango_inegi", "ok"], "ok"),
        # fuera_rango_inegi nunca afecta el global.
        (["ok", "fuera_rango_inegi"], "ok"),
        # sin comparables ni no_disponible el resultado sigue siendo
        # no_disponible: la rama mira la ausencia de comparables, no la
        # presencia de no_disponible.
        (["fuera_rango_inegi"], "no_disponible"),
    ],
)
def test_rollup_global_resuelve_precedencia(estados: list[str], esperado: str) -> None:
    assert rollup_global(estados) == esperado


def test_rollup_global_sin_estados_es_no_disponible() -> None:
    # Reporte vacío: no hay ninguna fila comparable.
    assert rollup_global([]) == "no_disponible"


# -- contar --------------------------------------------------------------------


def test_contar_cuenta_cada_estado_por_separado() -> None:
    estados = [
        "ok",
        "diferencia_detectada",
        "diferencia_por_parcial",
        "diferencia_por_parcial",
        "no_disponible",
        "sin_calculo",
        "fuera_rango_inegi",
    ]

    conteos = contar(estados)

    # n_comparables agrupa ok + diferencia_detectada + diferencia_por_parcial (x2).
    assert conteos["n_comparables"] == 4
    assert conteos["n_diferencia_por_parcial"] == 2
    assert conteos["n_no_disponibles"] == 1
    assert conteos["n_sin_calculo"] == 1
    assert conteos["n_fuera_rango_inegi"] == 1


def test_contar_sin_estados_devuelve_ceros() -> None:
    assert contar([]) == {
        "n_comparables": 0,
        "n_fuera_rango_inegi": 0,
        "n_no_disponibles": 0,
        "n_diferencia_por_parcial": 0,
        "n_sin_calculo": 0,
    }
