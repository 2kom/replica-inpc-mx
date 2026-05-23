from __future__ import annotations

import pytest

from replica_inpc.api._periodos import parsear_periodo
from replica_inpc.dominio.errores import PeriodoNoInterpretable
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("ene 2015", PeriodoMensual(2015, 1)),
        ("DIC 2024", PeriodoMensual(2024, 12)),
        ("Jul 2018", PeriodoMensual(2018, 7)),
        ("2Q JUL 2018", PeriodoQuincenal(2018, 7, 2)),
        ("2q jul 2018", PeriodoQuincenal(2018, 7, 2)),
        ("1Q Ene 2015", PeriodoQuincenal(2015, 1, 1)),
    ],
)
def test_parsear_periodo_insensible_a_mayusculas(texto: str, esperado: object) -> None:
    assert parsear_periodo(texto) == esperado


def test_parsear_periodo_normaliza_espacios_extra() -> None:
    assert parsear_periodo("  2q   jul   2018 ") == PeriodoQuincenal(2018, 7, 2)


def test_parsear_periodo_texto_invalido_lanza_error() -> None:
    with pytest.raises(PeriodoNoInterpretable):
        parsear_periodo("trimestre 3 2020")
