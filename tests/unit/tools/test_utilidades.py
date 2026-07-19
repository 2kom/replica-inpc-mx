from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from canasta_inpc.esquema import COLUMNAS_BASE
from canasta_inpc.utilidades import guardar_csv, normalizar_texto, quitar_prefijo_numerico

# -- helpers ---------------------------------------------------------------


def _leer(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


# -- normalizar_texto -------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Árbol", "arbol"),
        ("ÁÉÍÓÚÜ", "aeiouu"),
        ("señor", "señor"),
        ("NIÑO", "niño"),
        ("hola, mundo!", "hola mundo"),
        ("hola   mundo", "hola mundo"),
        ("  hola  ", "hola"),
        ("01 alimentos", "01 alimentos"),
    ],
)
def test_normalizar_texto(texto: str, esperado: str) -> None:
    assert normalizar_texto(texto) == esperado


# -- quitar_prefijo_numerico -------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("01 alimentos", "alimentos"),
        ("3111 elaboracion de alimentos", "elaboracion de alimentos"),
        ("alimentos", "alimentos"),
        ("alimentos 01 bebidas", "alimentos 01 bebidas"),
        ("01 02 alimentos", "02 alimentos"),
    ],
)
def test_quitar_prefijo_numerico(texto: str, esperado: str) -> None:
    assert quitar_prefijo_numerico(texto) == esperado


def test_quitar_prefijo_numerico_debe_correr_despues_de_normalizar() -> None:
    # "01." no matchea ^\d+\s+ (el punto no es espacio) hasta que
    # normalizar_texto lo quita primero
    crudo = "01. Alimentos"
    assert quitar_prefijo_numerico(crudo) == crudo
    assert quitar_prefijo_numerico(normalizar_texto(crudo)) == "alimentos"


# -- guardar_csv --------------------------------------------------------


def test_guardar_csv_reindexa_a_columnas_base_y_rellena_vacio(tmp_path: Path) -> None:
    df = pd.DataFrame({"COG": ["alimentos"], "generico": ["arroz"]})
    ruta = tmp_path / "salida.csv"
    guardar_csv(df, ruta, 2018)
    leido = _leer(ruta)
    assert list(leido.columns) == list(COLUMNAS_BASE)
    assert leido.loc[0, "generico"] == "arroz"
    assert leido.loc[0, "ponderador"] == ""


def test_guardar_csv_preserva_string_exacto_de_ponderador(tmp_path: Path) -> None:
    # precision cruda del xlsx (notacion cientifica) no debe convertirse a float
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["3.0944225043218539E-2"]})
    ruta = tmp_path / "salida.csv"
    guardar_csv(df, ruta, 2018)
    leido = _leer(ruta)
    assert leido.loc[0, "ponderador"] == "3.0944225043218539E-2"


def test_guardar_csv_columna_extra_no_declarada_se_descarta(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "columna_inventada": ["x"]})
    ruta = tmp_path / "salida.csv"
    guardar_csv(df, ruta, 2018)
    leido = _leer(ruta)
    assert "columna_inventada" not in leido.columns


def test_guardar_csv_columna_extra_advierte_sin_lanzar(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderdor": ["10.5"]})
    ruta = tmp_path / "salida.csv"
    guardar_csv(df, ruta, 2018)  # no debe lanzar
    salida = capsys.readouterr().out
    assert "ponderdor" in salida


def test_guardar_csv_preserva_orden_de_filas_y_columnas_multirregistro(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "generico": ["arroz", "frijol", "tortilla"],
            "COG": ["alimentos", "alimentos", "alimentos"],
            "canasta basica": ["X", "-", "X"],
        }
    )
    ruta = tmp_path / "salida.csv"
    guardar_csv(df, ruta, 2018)
    leido = _leer(ruta)
    assert list(leido["generico"]) == ["arroz", "frijol", "tortilla"]
    assert list(leido["canasta basica"]) == ["X", "-", "X"]
    assert (leido["ponderador"] == "").all()
