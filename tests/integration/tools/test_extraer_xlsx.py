# Valida extraer_xlsx (canasta_inpc.extraer_xlsx) contra xlsx real de INEGI
# (data/tests/xlsx/, no versionado). @pytest.mark.requires_data, excluido de CI.

from pathlib import Path

import pytest
from canasta_inpc.config import columnas_xlsx
from canasta_inpc.extraer_xlsx import extraer_xlsx

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "tests" / "xlsx"

_VERSIONES = [2010, 2013, 2018, 2024]

# -- estructura --------------------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_xlsx_columnas_esperadas(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert list(df.columns) == columnas_xlsx(version)


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_xlsx_generico_sin_vacios_ni_duplicados(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert (df["generico"] != "").all()
    assert df["generico"].is_unique


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_xlsx_ponderador_suma_cien(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert df["ponderador"].sum() == pytest.approx(100, abs=0.01)


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_xlsx_canasta_basica_solo_x_o_vacio(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert set(df["canasta basica"].unique()) <= {"", "X"}


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_xlsx_inflacion_clasificada_en_todas_las_filas(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert (df["inflacion componente"] != "").all()
    assert (df["inflacion subcomponente"] != "").all()
    assert (df["inflacion agrupacion"] != "").all()


# -- CCIF (hoja separada: 2013, 2018, 2024) -----------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2013, 2018, 2024])
def test_extraer_xlsx_ccif_poblado_en_todas_las_filas(version: int) -> None:
    df = extraer_xlsx(DATA_DIR / f"{version}.xlsx", version)
    assert (df["CCIF division"] != "").all()


def test_extraer_xlsx_2010_sin_hoja_ccif() -> None:
    assert "CCIF division" not in columnas_xlsx(2010)


# -- canasta de consumo mínimo (solo 2024) ------------------------------


@pytest.mark.requires_data
def test_extraer_xlsx_2024_canasta_consumo_minimo_solo_x_o_vacio() -> None:
    df = extraer_xlsx(DATA_DIR / "2024.xlsx", 2024)
    assert set(df["canasta consumo minimo"].unique()) <= {"", "X"}
