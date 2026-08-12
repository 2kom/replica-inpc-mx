from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.api import insumos
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import VersionCanasta

# centinela sin __eq__ propio: solo `is` lo satisface, así que un wrapper que devuelva
# una copia igual en vez del objeto del lector no puede colarse
_CANASTA = object()


def _serie(desde: PeriodoQuincenal, hasta: PeriodoQuincenal) -> SerieNormalizada:
    """Serie de un solo genérico con dos columnas: los extremos del tramo a probar."""
    df = pd.DataFrame([[100.0, 110.0]], index=pd.Index(["arroz"], name="generico"))
    df.columns = pd.Index([desde, hasta])
    return SerieNormalizada(df)


# -- validación de versión --------------------------------------------------


@pytest.mark.parametrize("version", [2009, 2020, 0, 9999])
def test_cargar_canasta_version_invalida(version: int) -> None:
    with pytest.raises(InvarianteViolado):
        insumos.cargar_canasta("x.csv", version)  # type: ignore[arg-type]


@pytest.mark.parametrize("version", [2009, 2020, 0, 9999])
def test_cargar_serie_version_invalida(version: int) -> None:
    with pytest.raises(InvarianteViolado):
        insumos.cargar_serie("x.csv", version)  # type: ignore[arg-type]


# -- delegación a los lectores ----------------------------------------------


def test_cargar_canasta_delega_al_lector_con_path_y_version(mocker) -> None:
    mocker.patch.object(insumos, "_mostrar_resumen_carga_canasta")
    lector = mocker.patch.object(insumos, "LectorCanastaCsv")
    leer = lector.return_value.leer
    leer.return_value = _CANASTA

    resultado = insumos.cargar_canasta("data/c.csv", 2018)

    assert resultado is _CANASTA
    leer.assert_called_once_with(Path("data/c.csv"), 2018)


def test_cargar_serie_delega_al_lector_solo_con_path(mocker) -> None:
    lector = mocker.patch.object(insumos, "LectorSeriesCsv")
    leer = lector.return_value.leer
    leer.return_value = _serie(PeriodoQuincenal(2018, 1, 1), PeriodoQuincenal(2024, 7, 2))

    resultado = insumos.cargar_serie("data/s.csv", 2018)

    assert resultado is leer.return_value
    leer.assert_called_once_with(Path("data/s.csv"))


# -- resumen de canasta -----------------------------------------------------


def test_cargar_canasta_imprime_resumen_por_defecto(mocker) -> None:
    resumen = mocker.patch.object(insumos, "_mostrar_resumen_carga_canasta")
    mocker.patch.object(insumos, "LectorCanastaCsv").return_value.leer.return_value = _CANASTA

    assert insumos.cargar_canasta("data/c.csv", 2018) is _CANASTA

    resumen.assert_called_once_with(_CANASTA, 2018)


def test_cargar_canasta_resumen_false_no_imprime_pero_devuelve_lo_mismo(mocker) -> None:
    """Suprimir el resumen no puede alterar el retorno: es un efecto, no una rama."""
    resumen = mocker.patch.object(insumos, "_mostrar_resumen_carga_canasta")
    mocker.patch.object(insumos, "LectorCanastaCsv").return_value.leer.return_value = _CANASTA

    assert insumos.cargar_canasta("data/c.csv", 2018, resumen=False) is _CANASTA

    resumen.assert_not_called()


# -- cobertura serie / canasta ----------------------------------------------


@pytest.mark.parametrize(
    ("desde", "hasta", "version"),
    [
        # tramos representativos de las series del BIE contra su propia canasta
        (PeriodoQuincenal(2010, 1, 1), PeriodoQuincenal(2018, 7, 2), 2010),
        (PeriodoQuincenal(2018, 1, 1), PeriodoQuincenal(2024, 7, 2), 2018),
        (PeriodoQuincenal(2024, 1, 1), PeriodoQuincenal(2026, 3, 2), 2024),
        # frontera inferior inclusiva: la serie termina justo donde empieza la canasta
        (PeriodoQuincenal(2009, 1, 1), PeriodoQuincenal(2010, 12, 2), 2010),
        # frontera superior inclusiva: la serie empieza justo donde termina la canasta
        (PeriodoQuincenal(2013, 3, 2), PeriodoQuincenal(2018, 7, 2), 2010),
        # canasta abierta por la derecha (fin None)
        (PeriodoQuincenal(2030, 1, 1), PeriodoQuincenal(2030, 6, 2), 2024),
    ],
)
def test_cargar_serie_acepta_tramo_que_toca_la_canasta(
    mocker, desde: PeriodoQuincenal, hasta: PeriodoQuincenal, version: VersionCanasta
) -> None:
    serie = _serie(desde, hasta)
    mocker.patch.object(insumos, "LectorSeriesCsv").return_value.leer.return_value = serie

    assert insumos.cargar_serie("data/s.csv", version) is serie


@pytest.mark.parametrize(
    ("desde", "hasta", "version"),
    [
        # serie posterior al tramo declarado
        (PeriodoQuincenal(2024, 1, 1), PeriodoQuincenal(2026, 3, 2), 2010),
        (PeriodoQuincenal(2018, 1, 1), PeriodoQuincenal(2024, 7, 2), 2010),
        (PeriodoQuincenal(2024, 1, 1), PeriodoQuincenal(2026, 3, 2), 2013),
        # serie anterior al tramo declarado
        (PeriodoQuincenal(2000, 1, 1), PeriodoQuincenal(2009, 12, 2), 2010),
    ],
)
def test_cargar_serie_rechaza_tramo_que_no_toca_la_canasta(
    mocker, desde: PeriodoQuincenal, hasta: PeriodoQuincenal, version: VersionCanasta
) -> None:
    mocker.patch.object(insumos, "LectorSeriesCsv").return_value.leer.return_value = _serie(
        desde, hasta
    )

    with pytest.raises(InvarianteViolado, match="no toca el tramo de la canasta"):
        insumos.cargar_serie("data/s.csv", version)
