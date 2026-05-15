from __future__ import annotations

from pathlib import Path

import pytest

from replica_inpc.api import insumos
from replica_inpc.dominio.errores import InvarianteViolado


@pytest.mark.parametrize("version", [2009, 2020, 0, 9999])
def test_cargar_canasta_version_invalida(version: int) -> None:
    with pytest.raises(InvarianteViolado):
        insumos.cargar_canasta("x.csv", version)  # type: ignore[arg-type]


@pytest.mark.parametrize("version", [2009, 2020, 0, 9999])
def test_cargar_serie_version_invalida(version: int) -> None:
    with pytest.raises(InvarianteViolado):
        insumos.cargar_serie("x.csv", version)  # type: ignore[arg-type]


def test_cargar_canasta_delega_al_lector_con_path_y_version(mocker) -> None:
    lector = mocker.patch.object(insumos, "LectorCanastaCsv")
    leer = lector.return_value.leer
    leer.return_value = "canasta"

    resultado = insumos.cargar_canasta("data/c.csv", 2018)

    assert resultado == "canasta"
    leer.assert_called_once_with(Path("data/c.csv"), 2018)


def test_cargar_serie_delega_al_lector_solo_con_path(mocker) -> None:
    lector = mocker.patch.object(insumos, "LectorSeriesCsv")
    leer = lector.return_value.leer
    leer.return_value = "serie"

    resultado = insumos.cargar_serie("data/s.csv", 2018)

    assert resultado == "serie"
    leer.assert_called_once_with(Path("data/s.csv"))
