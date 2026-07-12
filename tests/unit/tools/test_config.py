# Valida LayoutXlsx y LAYOUTS_XLSX (canasta_inpc.config) — constantes/estructura, sin I/O.

import dataclasses

import pytest
from canasta_inpc.config import (
    COLUMNAS_FIJAS,
    FUENTES,
    LAYOUTS_XLSX,
    PRECISION_DECIMALES,
    columnas_pdf,
    columnas_xlsx,
)

_VERSIONES = [2010, 2013, 2018, 2024]

# -- FUENTES -----------------------------------------------------------


@pytest.mark.parametrize("version", _VERSIONES)
def test_fuentes_columnas_completas_y_en_orden(version: int) -> None:
    assert list(FUENTES[version].keys()) == COLUMNAS_FIJAS


@pytest.mark.parametrize("version", _VERSIONES)
def test_fuentes_valores_validos(version: int) -> None:
    assert set(FUENTES[version].values()) <= {"xlsx", "pdf", "sync", None}


@pytest.mark.parametrize("version", _VERSIONES)
def test_columnas_xlsx_y_pdf_sin_overlap(version: int) -> None:
    assert set(columnas_xlsx(version)) & set(columnas_pdf(version)) == set()


def test_columnas_xlsx_2010() -> None:
    assert columnas_xlsx(2010) == [
        "generico",
        "ponderador",
        "COG",
        "inflacion componente",
        "inflacion subcomponente",
        "inflacion agrupacion",
        "canasta basica",
    ]


def test_columnas_xlsx_2024_incluye_encadenamiento_y_consumo_minimo() -> None:
    cols = columnas_xlsx(2024)
    assert "encadenamiento" in cols
    assert "canasta consumo minimo" in cols


def test_columnas_xlsx_2018_sin_encadenamiento() -> None:
    assert "encadenamiento" not in columnas_xlsx(2018)


# -- LAYOUTS_XLSX --------------------------------------------------------


def test_layouts_xlsx_cubre_las_4_versiones() -> None:
    assert set(LAYOUTS_XLSX.keys()) == set(_VERSIONES)


def test_layout_2010_sin_hoja_ccif() -> None:
    assert LAYOUTS_XLSX[2010].hoja_ccif is None


@pytest.mark.parametrize("version", [2013, 2018, 2024])
def test_layout_con_hoja_ccif(version: int) -> None:
    assert LAYOUTS_XLSX[version].hoja_ccif is not None


@pytest.mark.parametrize("version", _VERSIONES)
def test_layout_columnas_sin_colision(version: int) -> None:
    layout = LAYOUTS_XLSX[version]

    posiciones = [layout.col_ponderador, layout.col_canasta_basica]
    if layout.col_concepto_agg == layout.col_concepto_gen:
        posiciones.append(layout.col_concepto_agg)
    else:
        posiciones += [layout.col_concepto_agg, layout.col_concepto_gen]
    if layout.col_encadenamiento:
        posiciones.append(layout.col_encadenamiento)
    if layout.col_canasta_consumo_minimo:
        posiciones.append(layout.col_canasta_consumo_minimo)
    posiciones += list(layout.agrupaciones.keys())

    assert len(posiciones) == len(set(posiciones))


def test_layoutxlsx_es_inmutable() -> None:
    layout = LAYOUTS_XLSX[2010]
    with pytest.raises(dataclasses.FrozenInstanceError):
        layout.col_ponderador = 99  # type: ignore[misc]


# -- PRECISION_DECIMALES --------------------------------------------------


def test_precision_decimales_cubre_las_4_versiones() -> None:
    assert set(PRECISION_DECIMALES.keys()) == set(_VERSIONES)
