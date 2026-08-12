from __future__ import annotations

from pathlib import Path

import pytest

from replica_inpc.api import flujos
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.periodos import PeriodoQuincenal

_INSUMOS = [(2018, "canasta.csv", "serie.CSV")]

# -- firma pública: orden de los parámetros ------------------------------------


def test_orden_posicional_de_la_firma(mocker) -> None:
    # El orden es (insumos, tipo, periodicidad, referencia) desde 2026-08-11.
    # Sin este test, volver al orden anterior pasaba la suite entera: todas las
    # demás llamadas usan argumentos nombrados o defaults. El de integración que
    # también lo cubre lleva `requires_data` y el CI lo excluye.
    caso = mocker.patch.object(flujos, "CalcularHistoria")
    ejecutar = caso.return_value.ejecutar
    ejecutar.return_value = "resultado"

    salida = flujos.calcular_historia(_INSUMOS, "INPC", "mensual", "2Q Ago 2018")  # type: ignore[arg-type]

    assert salida == "resultado"
    ejecutar.assert_called_once_with(
        [(2018, Path("canasta.csv"), Path("serie.CSV"))],
        "INPC",
        "mensual",
        PeriodoQuincenal(2018, 8, 2),
    )


def test_defaults_de_la_firma(mocker) -> None:
    caso = mocker.patch.object(flujos, "CalcularHistoria")
    ejecutar = caso.return_value.ejecutar

    flujos.calcular_historia(_INSUMOS)  # type: ignore[arg-type]

    _, tipo, periodicidad, referencia = ejecutar.call_args[0]
    assert (tipo, periodicidad, referencia) == ("INPC", "mensual", PeriodoQuincenal(2018, 7, 2))


def test_tipo_se_normaliza_a_mayusculas(mocker) -> None:
    caso = mocker.patch.object(flujos, "CalcularHistoria")
    ejecutar = caso.return_value.ejecutar

    flujos.calcular_historia(_INSUMOS, "ccif division")  # type: ignore[arg-type]

    assert ejecutar.call_args[0][1] == "CCIF DIVISION"


# -- referencia ----------------------------------------------------------------


@pytest.mark.parametrize(
    "referencia",
    ["trimestre 3 de 2018", "Jul 2018"],
    ids=["no_interpretable", "mensual"],
)
def test_referencia_invalida_falla_sin_construir_el_caso_de_uso(referencia: str, mocker) -> None:
    # El rechazo ocurre antes de instanciar CalcularHistoria: no tiene sentido
    # armar lectores para una referencia que ya se sabe inservible.
    caso = mocker.patch.object(flujos, "CalcularHistoria")

    with pytest.raises(ErrorConfiguracion):
        flujos.calcular_historia(_INSUMOS, "INPC", "mensual", referencia)  # type: ignore[arg-type]

    caso.assert_not_called()
