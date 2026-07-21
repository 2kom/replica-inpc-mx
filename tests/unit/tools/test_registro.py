from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from canasta_inpc.registro import (
    _construir_detalle_genericos,
    _imprimir_resumen,
    _resumir_clasificacion,
    escribir_registro_xlsx,
)

# -- helpers ------------------------------------------------------------


def _args(tmp_path: Path, version: int = 2018, xlsx: str = "ruta/2018.xlsx") -> argparse.Namespace:
    return argparse.Namespace(salida=tmp_path, version=version, xlsx=Path(xlsx))


def _leer_json(ruta_salida: Path) -> dict:
    (archivo,) = ruta_salida.glob("xlsx_*.json")
    return json.loads(archivo.read_text(encoding="utf-8"))


# -- _resumir_clasificacion ---------------------------------------------


def test_resumir_clasificacion_cuenta_no_vacios_y_categorias_unicas() -> None:
    df = pd.DataFrame({"COG": ["alimentos", "alimentos", "vivienda", ""]})
    resumen = _resumir_clasificacion(df, "COG")
    assert resumen == {
        "genericos_clasificados": 3,
        "categorias_unicas": 2,
        "categorias": ["alimentos", "vivienda"],
    }


def test_resumir_clasificacion_categorias_vienen_ordenadas() -> None:
    df = pd.DataFrame({"COG": ["vivienda", "alimentos", "transporte"]})
    assert _resumir_clasificacion(df, "COG")["categorias"] == [
        "alimentos",
        "transporte",
        "vivienda",
    ]


def test_resumir_clasificacion_columna_totalmente_vacia() -> None:
    df = pd.DataFrame({"COG": ["", "", ""]})
    assert _resumir_clasificacion(df, "COG") == {
        "genericos_clasificados": 0,
        "categorias_unicas": 0,
        "categorias": [],
    }


# -- _construir_detalle_genericos ---------------------------------------------------


def test_construir_detalle_genericos_sin_encadenamiento() -> None:
    df = pd.DataFrame({"generico": ["arroz", "frijol"], "ponderador": ["0.5", "0.3"]})
    assert _construir_detalle_genericos(df, tiene_enc=False) == [
        {"generico": "arroz", "ponderador": "0.5"},
        {"generico": "frijol", "ponderador": "0.3"},
    ]


def test_construir_detalle_genericos_con_encadenamiento() -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": ["1.01"]})
    assert _construir_detalle_genericos(df, tiene_enc=True) == [
        {"generico": "arroz", "ponderador": "0.5", "encadenamiento": "1.01"}
    ]


def test_construir_detalle_genericos_respeta_orden_de_filas() -> None:
    df = pd.DataFrame({"generico": ["c", "a", "b"], "ponderador": ["1", "2", "3"]})
    assert [d["generico"] for d in _construir_detalle_genericos(df, tiene_enc=False)] == [
        "c",
        "a",
        "b",
    ]


# -- _imprimir_resumen ----------------------------------------------------


def test_imprimir_resumen_incluye_version_y_conteo_genericos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {
        "version": 2018,
        "genericos": 299,
        "encadenamientos": None,
        "clasificaciones": {},
    }
    _imprimir_resumen(registro, Path("a.csv"), Path("a.json"))
    salida = capsys.readouterr().out
    assert "version 2018: 299 genericos extraidos" in salida


def test_imprimir_resumen_omite_encadenamientos_si_es_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {
        "version": 2018,
        "genericos": 1,
        "encadenamientos": None,
        "clasificaciones": {},
    }
    _imprimir_resumen(registro, Path("a.csv"), Path("a.json"))
    assert "encadenamientos" not in capsys.readouterr().out


def test_imprimir_resumen_incluye_encadenamientos_si_no_es_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {
        "version": 2024,
        "genericos": 1,
        "encadenamientos": 292,
        "clasificaciones": {},
    }
    _imprimir_resumen(registro, Path("a.csv"), Path("a.json"))
    assert "encadenamientos: 292" in capsys.readouterr().out


def test_imprimir_resumen_incluye_clasificacion_y_rutas(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {
        "version": 2018,
        "genericos": 299,
        "encadenamientos": None,
        "clasificaciones": {"COG": {"genericos_clasificados": 299, "categorias_unicas": 8}},
    }
    _imprimir_resumen(registro, Path("salida/a.csv"), Path("salida/a.json"))
    salida = capsys.readouterr().out
    assert "COG: 299 clasificados, 8 categorias" in salida
    assert str(Path("salida/a.csv")) in salida
    assert str(Path("salida/a.json")) in salida


# -- escribir_registro_xlsx -----------------------------------------------


def test_escribir_registro_xlsx_nombre_de_archivo_con_version_y_timestamp(
    tmp_path: Path,
) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    escribir_registro_xlsx(df, _args(tmp_path, version=2018), tmp_path / "ponderadores_2018.csv")
    (archivo,) = list(tmp_path.glob("*.json"))
    assert re.match(r"^xlsx_2018_\d{8}_\d{6}_\d{6}\.json$", archivo.name)


def test_escribir_registro_xlsx_dos_corridas_seguidas_no_se_pisan(tmp_path: Path) -> None:
    # timestamp con microsegundos -- sin esto, dos corridas en el mismo
    # segundo pisaban el mismo archivo json
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    escribir_registro_xlsx(df, _args(tmp_path, version=2018), tmp_path / "a.csv")
    escribir_registro_xlsx(df, _args(tmp_path, version=2018), tmp_path / "b.csv")
    assert len(list(tmp_path.glob("xlsx_*.json"))) == 2


def test_escribir_registro_xlsx_campos_basicos_del_json(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz", "frijol"], "ponderador": ["0.5", "0.3"]})
    ruta_csv = tmp_path / "ponderadores_2018.csv"
    escribir_registro_xlsx(df, _args(tmp_path, version=2018, xlsx="entrada/2018.xlsx"), ruta_csv)
    registro = _leer_json(tmp_path)
    assert registro["tipo"] == "xlsx"
    assert registro["xlsx"] == str(Path("entrada/2018.xlsx"))
    assert registro["csv"] == str(ruta_csv)
    assert registro["version"] == 2018
    assert registro["genericos"] == 2


def test_escribir_registro_xlsx_ponderadores_cuenta_no_vacios(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz", "frijol"], "ponderador": ["0.5", ""]})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    assert _leer_json(tmp_path)["ponderadores"] == 1


def test_escribir_registro_xlsx_encadenamientos_none_si_columna_ausente(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    assert _leer_json(tmp_path)["encadenamientos"] is None


def test_escribir_registro_xlsx_encadenamientos_cuenta_si_columna_presente(
    tmp_path: Path,
) -> None:
    df = pd.DataFrame(
        {
            "generico": ["arroz", "frijol"],
            "ponderador": ["0.5", "0.3"],
            "encadenamiento": ["1.01", ""],
        }
    )
    escribir_registro_xlsx(df, _args(tmp_path, version=2013), tmp_path / "ponderadores_2013.csv")
    assert _leer_json(tmp_path)["encadenamientos"] == 1


def test_escribir_registro_xlsx_clasificaciones_excluye_generico_ponderador_encadenamiento(
    tmp_path: Path,
) -> None:
    df = pd.DataFrame(
        {
            "generico": ["arroz"],
            "ponderador": ["0.5"],
            "encadenamiento": ["1.01"],
            "COG": ["alimentos"],
        }
    )
    escribir_registro_xlsx(df, _args(tmp_path, version=2013), tmp_path / "ponderadores_2013.csv")
    assert set(_leer_json(tmp_path)["clasificaciones"]) == {"COG"}


def test_escribir_registro_xlsx_columna_fuera_de_esquema_no_aparece_en_clasificaciones(
    tmp_path: Path,
) -> None:
    # guardar_csv ya descarta columnas fuera de COLUMNAS_BASE con aviso; el
    # registro no debe reportarlas como si fueran una clasificacion real
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "columna_inventada": ["x"]})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    assert "columna_inventada" not in _leer_json(tmp_path)["clasificaciones"]


def test_escribir_registro_xlsx_genericos_detalle_una_entrada_por_fila(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz", "frijol"], "ponderador": ["0.5", "0.3"]})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    detalle = _leer_json(tmp_path)["genericos_detalle"]
    assert detalle == [
        {"generico": "arroz", "ponderador": "0.5"},
        {"generico": "frijol", "ponderador": "0.3"},
    ]


def test_escribir_registro_xlsx_preserva_acentos_sin_escapar(tmp_path: Path) -> None:
    # ensure_ascii=False: el json debe traer "ñ"/tildes literales, no "ñ"
    df = pd.DataFrame({"generico": ["alimentos para bebé, niño"], "ponderador": ["0.5"]})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    (archivo,) = list(tmp_path.glob("*.json"))
    assert "bebé, niño" in archivo.read_text(encoding="utf-8")


def test_escribir_registro_xlsx_df_vacio_no_lanza(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": [], "ponderador": []})
    escribir_registro_xlsx(df, _args(tmp_path), tmp_path / "ponderadores_2018.csv")
    registro = _leer_json(tmp_path)
    assert registro["genericos"] == 0
    assert registro["genericos_detalle"] == []


def test_escribir_registro_xlsx_imprime_resumen_a_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    ruta_csv = tmp_path / "ponderadores_2018.csv"
    escribir_registro_xlsx(df, _args(tmp_path, version=2018), ruta_csv)
    salida = capsys.readouterr().out
    assert "version 2018: 1 genericos extraidos" in salida
    assert str(ruta_csv) in salida
