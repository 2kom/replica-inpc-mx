from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from canasta_inpc.match import Resolucion, ResultadoMatch
from canasta_inpc.registro import (
    _construir_detalle_genericos_pdf,
    _construir_detalle_genericos_sincronizacion,
    _construir_detalle_genericos_xlsx,
    _imprimir_resumen_sincronizacion,
    _imprimir_resumen_xlsx,
    _resumir_clasificacion_pdf,
    _resumir_clasificacion_xlsx,
    escribir_registro_pdf,
    escribir_registro_sincronizacion,
    escribir_registro_xlsx,
)

# -- helpers ------------------------------------------------------------


def _args(tmp_path: Path, version: int = 2018, xlsx: str = "ruta/2018.xlsx") -> argparse.Namespace:
    return argparse.Namespace(salida=tmp_path, version=version, xlsx=Path(xlsx))


def _args_pdf(
    tmp_path: Path,
    version: int = 2013,
    xlsx: str = "ruta/2013.xlsx",
    pdf: str = "ruta/2013.pdf",
    preferir: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        salida=tmp_path, version=version, xlsx=Path(xlsx), pdf=Path(pdf), preferir=preferir
    )


def _resolucion(
    columna: str,
    genericos: tuple[str, ...],
    valor_final: str,
    origen: str = "pdf",
    metodo: str = "igual",
    valor_xlsx: str | None = None,
    valor_pdf: str | None = None,
) -> Resolucion:
    return Resolucion(columna, genericos, valor_xlsx, valor_pdf, valor_final, origen, metodo)  # type: ignore[arg-type]


def _leer_json(ruta_salida: Path) -> dict:
    (archivo,) = ruta_salida.glob("xlsx_*.json")
    return json.loads(archivo.read_text(encoding="utf-8"))


def _leer_json_pdf(ruta_salida: Path) -> dict:
    (archivo,) = ruta_salida.glob("pdf_*.json")
    return json.loads(archivo.read_text(encoding="utf-8"))


def _leer_json_sincronizacion(directorio: Path) -> dict:
    (archivo,) = directorio.glob("sincronizacion_*.json")
    return json.loads(archivo.read_text(encoding="utf-8"))


# -- _resumir_clasificacion_xlsx ---------------------------------------------


def test_resumir_clasificacion_cuenta_no_vacios_y_categorias_unicas() -> None:
    df = pd.DataFrame({"COG": ["alimentos", "alimentos", "vivienda", ""]})
    resumen = _resumir_clasificacion_xlsx(df, "COG")
    assert resumen == {
        "genericos_clasificados": 3,
        "categorias_unicas": 2,
        "categorias": {"alimentos": 2, "vivienda": 1},
    }


def test_resumir_clasificacion_categorias_cuentan_genericos_por_categoria() -> None:
    df = pd.DataFrame({"COG": ["vivienda", "alimentos", "transporte", "alimentos"]})
    assert _resumir_clasificacion_xlsx(df, "COG")["categorias"] == {
        "vivienda": 1,
        "alimentos": 2,
        "transporte": 1,
    }


def test_resumir_clasificacion_columna_totalmente_vacia() -> None:
    df = pd.DataFrame({"COG": ["", "", ""]})
    assert _resumir_clasificacion_xlsx(df, "COG") == {
        "genericos_clasificados": 0,
        "categorias_unicas": 0,
        "categorias": {},
    }


# -- _construir_detalle_genericos_xlsx ---------------------------------------------------


def test_construir_detalle_genericos_xlsx_sin_encadenamiento() -> None:
    df = pd.DataFrame({"generico": ["arroz", "frijol"], "ponderador": ["0.5", "0.3"]})
    assert _construir_detalle_genericos_xlsx(df, tiene_enc=False) == [
        {"generico": "arroz", "ponderador": "0.5"},
        {"generico": "frijol", "ponderador": "0.3"},
    ]


def test_construir_detalle_genericos_xlsx_con_encadenamiento() -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": ["1.01"]})
    assert _construir_detalle_genericos_xlsx(df, tiene_enc=True) == [
        {"generico": "arroz", "ponderador": "0.5", "encadenamiento": "1.01"}
    ]


def test_construir_detalle_genericos_xlsx_respeta_orden_de_filas() -> None:
    df = pd.DataFrame({"generico": ["c", "a", "b"], "ponderador": ["1", "2", "3"]})
    assert [d["generico"] for d in _construir_detalle_genericos_xlsx(df, tiene_enc=False)] == [
        "c",
        "a",
        "b",
    ]


# -- _imprimir_resumen_xlsx ----------------------------------------------------


def test_imprimir_resumen_incluye_version_y_conteo_genericos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {
        "version": 2018,
        "genericos": 299,
        "encadenamientos": None,
        "clasificaciones": {},
    }
    _imprimir_resumen_xlsx(registro, Path("a.csv"), Path("a.json"))
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
    _imprimir_resumen_xlsx(registro, Path("a.csv"), Path("a.json"))
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
    _imprimir_resumen_xlsx(registro, Path("a.csv"), Path("a.json"))
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
    _imprimir_resumen_xlsx(registro, Path("salida/a.csv"), Path("salida/a.json"))
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
    assert re.match(r"^xlsx_2018_\d{8}_\d{6}_\d{6}_[0-9a-f]{8}\.json$", archivo.name)


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


# -- _construir_detalle_genericos_pdf --------------------------------------


def test_construir_detalle_genericos_pdf_anida_valor_origen_metodo() -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    assert _construir_detalle_genericos_pdf(df, tiene_enc=False, resoluciones=resoluciones) == [
        {"generico": "arroz", "ponderador": {"valor": "0.5", "origen": "ambas", "metodo": "igual"}}
    ]


def test_construir_detalle_genericos_pdf_con_encadenamiento() -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": ["1.01"]})
    resoluciones = (
        _resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),
        _resolucion("encadenamiento", ("arroz",), "1.01", origen="xlsx", metodo="redondeo"),
    )
    detalle = _construir_detalle_genericos_pdf(df, tiene_enc=True, resoluciones=resoluciones)
    assert detalle == [
        {
            "generico": "arroz",
            "ponderador": {"valor": "0.5", "origen": "ambas", "metodo": "igual"},
            "encadenamiento": {"valor": "1.01", "origen": "xlsx", "metodo": "redondeo"},
        }
    ]


def test_construir_detalle_genericos_pdf_sin_encadenamiento_no_busca_metadata() -> None:
    # regresion: version sin encadenamiento en ninguna fuente (2010/2018) --
    # tiene_enc=False debe bastar para que ni se intente buscar metadata que
    # no existe, sin importar si el df trae la columna vacia
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": [""]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    detalle = _construir_detalle_genericos_pdf(df, tiene_enc=False, resoluciones=resoluciones)
    assert detalle == [
        {"generico": "arroz", "ponderador": {"valor": "0.5", "origen": "ambas", "metodo": "igual"}}
    ]


# -- _resumir_clasificacion_pdf ---------------------------------------------


def test_resumir_clasificacion_pdf_desglosa_metodos_por_categoria() -> None:
    df = pd.DataFrame({"COG": ["alimentos"] * 3 + ["vivienda"]})
    resoluciones = (
        _resolucion("COG", ("a", "b"), "alimentos", origen="ambas", metodo="igual"),
        _resolucion("COG", ("c",), "alimentos", origen="pdf", metodo="preferido"),
        _resolucion("COG", ("d",), "vivienda", origen="ambas", metodo="igual"),
    )
    resumen = _resumir_clasificacion_pdf(df, "COG", resoluciones)
    assert resumen == {
        "genericos": 4,
        "categorias_unicas": 2,
        "categorias": {
            "alimentos": {
                "genericos": 3,
                "metodos": {"igual": 2, "decision": 1},
                "origenes_igual": {"ambas": 2},
                "origenes_decision": {"pdf": 1},
            },
            "vivienda": {
                "genericos": 1,
                "metodos": {"igual": 1},
                "origenes_igual": {"ambas": 1},
            },
        },
    }


def test_resumir_clasificacion_pdf_columna_directo_trae_origenes_directo() -> None:
    # columna de una sola fuente (grupo C) -- bucket "directo" + su propio
    # origenes_directo (uniforme con igual/decision), sin origenes_igual ni
    # origenes_decision (no hubo comparacion real)
    df = pd.DataFrame({"COG": ["alimentos", "alimentos"]})
    resoluciones = (_resolucion("COG", ("a", "b"), "alimentos", origen="xlsx", metodo="directo"),)
    resumen = _resumir_clasificacion_pdf(df, "COG", resoluciones)
    assert resumen["categorias"] == {
        "alimentos": {"genericos": 2, "metodos": {"directo": 2}, "origenes_directo": {"xlsx": 2}}
    }


def test_resumir_clasificacion_pdf_decision_hacia_vacio_va_a_sin_clasificar() -> None:
    # regresion: xlsx sin clasificar, pdf si -- --preferir xlsx resuelve
    # hacia vacio, pero SI hubo una decision real; no debe desaparecer del
    # registro ni contar como si fuera una categoria valida
    df = pd.DataFrame({"COG": [""]})
    resoluciones = (
        _resolucion(
            "COG",
            ("arroz",),
            "",
            origen="xlsx",
            metodo="preferido",
            valor_xlsx="",
            valor_pdf="alimentos",
        ),
    )
    resumen = _resumir_clasificacion_pdf(df, "COG", resoluciones)
    assert resumen["genericos"] == 0  # no cuenta como clasificado
    assert resumen["categorias_unicas"] == 0  # "" no es una categoria real
    assert resumen["categorias"]["sin_clasificar"] == {
        "genericos": 1,
        "metodos": {"decision": 1},
        "origenes_decision": {"xlsx": 1},
    }


def test_resumir_clasificacion_pdf_categoria_hibrida_cuenta_por_origen_mixto() -> None:
    df = pd.DataFrame({"CCIF division": ["03 ropa y calzado"]})
    resoluciones = (
        _resolucion(
            "CCIF division",
            ("abrigo",),
            "03 ropa y calzado",
            origen="mixto",
            metodo="interactiva",
        ),
    )
    resumen = _resumir_clasificacion_pdf(df, "CCIF division", resoluciones)
    assert resumen["categorias"]["03 ropa y calzado"]["origenes_decision"] == {"mixto": 1}


# -- escribir_registro_pdf --------------------------------------------------


def test_escribir_registro_pdf_nombre_de_archivo_con_version_y_timestamp(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    resultado = ResultadoMatch(df=df, resoluciones=resoluciones)
    # 2018: encadenamiento vacio en FUENTES_POSIBLES, no hace falta en el df
    # de prueba (tiene_enc=False evita tocar esa columna)
    escribir_registro_pdf(
        resultado, _args_pdf(tmp_path, version=2018), tmp_path / "ponderadores_2018.csv"
    )
    (archivo,) = list(tmp_path.glob("*.json"))
    assert re.match(r"^pdf_2018_\d{8}_\d{6}_\d{6}_[0-9a-f]{8}\.json$", archivo.name)


def test_escribir_registro_pdf_tipo_es_dato_estructurado_no_texto(tmp_path: Path) -> None:
    # tipo fijo, no un string que mezcle prosa humana ("xlsx + pdf (preferir
    # pdf)") con el dato -- preferir va aparte, como campo propio
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    resultado = ResultadoMatch(df=df, resoluciones=resoluciones)
    escribir_registro_pdf(
        resultado, _args_pdf(tmp_path, version=2018, preferir="pdf"), tmp_path / "a.csv"
    )
    registro = _leer_json_pdf(tmp_path)
    assert registro["tipo"] == "xlsx_pdf"
    assert registro["preferir"] == "pdf"


def test_escribir_registro_pdf_preferir_none_si_no_vino_el_flag(tmp_path: Path) -> None:
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    resultado = ResultadoMatch(df=df, resoluciones=resoluciones)
    escribir_registro_pdf(
        resultado, _args_pdf(tmp_path, version=2018, preferir=None), tmp_path / "a.csv"
    )
    assert _leer_json_pdf(tmp_path)["preferir"] is None


def test_escribir_registro_pdf_encadenamiento_ausente_si_version_no_lo_tiene(
    tmp_path: Path,
) -> None:
    # regresion real: 2010/2018 tienen "encadenamiento" en FUENTES_POSIBLES
    # vacio (ninguna fuente la trae), pero match_dfs igual crea la columna en
    # el df (rellena con "", grupo D) -- antes esto causaba un KeyError en
    # _construir_detalle_genericos_pdf al buscar metadata que nunca se genero
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": [""]})
    resoluciones = (_resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),)
    resultado = ResultadoMatch(df=df, resoluciones=resoluciones)
    escribir_registro_pdf(resultado, _args_pdf(tmp_path, version=2018), tmp_path / "a.csv")
    registro = _leer_json_pdf(tmp_path)
    assert registro["encadenamientos"] is None
    assert "encadenamiento" not in registro["genericos_detalle"][0]


def test_escribir_registro_pdf_encadenamiento_presente_si_version_lo_tiene(
    tmp_path: Path,
) -> None:
    # 2013 si tiene encadenamiento en FUENTES_POSIBLES (xlsx y pdf)
    df = pd.DataFrame({"generico": ["arroz"], "ponderador": ["0.5"], "encadenamiento": ["1.01"]})
    resoluciones = (
        _resolucion("ponderador", ("arroz",), "0.5", origen="ambas", metodo="igual"),
        _resolucion("encadenamiento", ("arroz",), "1.01", origen="ambas", metodo="igual"),
    )
    resultado = ResultadoMatch(df=df, resoluciones=resoluciones)
    escribir_registro_pdf(resultado, _args_pdf(tmp_path, version=2013), tmp_path / "a.csv")
    registro = _leer_json_pdf(tmp_path)
    assert registro["encadenamientos"] == 1
    assert registro["genericos_detalle"][0]["encadenamiento"] == {
        "valor": "1.01",
        "origen": "ambas",
        "metodo": "igual",
    }


# -- _construir_detalle_genericos_sincronizacion -----------------------------


def test_construir_detalle_genericos_sincronizacion_incluye_cambio() -> None:
    df = pd.DataFrame(
        {
            "generico": ["arroz", "frijol"],
            "SCIAN sector": ["11 agricultura", "11 agricultura"],
            "SCIAN rama": ["1111 arroz", "1121 frijol"],
        }
    )
    cambios = {"arroz": True, "frijol": False}
    detalle = _construir_detalle_genericos_sincronizacion(df, cambios)
    assert detalle == [
        {
            "generico": "arroz",
            "SCIAN sector": "11 agricultura",
            "SCIAN rama": "1111 arroz",
            "cambio": True,
        },
        {
            "generico": "frijol",
            "SCIAN sector": "11 agricultura",
            "SCIAN rama": "1121 frijol",
            "cambio": False,
        },
    ]


# -- _imprimir_resumen_sincronizacion ----------------------------------------


def test_imprimir_resumen_sincronizacion_incluye_conteo_y_celdas(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registro: dict = {"genericos": 283, "celdas_actualizadas": 12, "clasificaciones": {}}
    _imprimir_resumen_sincronizacion(registro, Path("a.csv"), Path("a.json"))
    salida = capsys.readouterr().out
    assert "283 genericos sincronizados" in salida
    assert "celdas actualizadas: 12" in salida


# -- escribir_registro_sincronizacion ----------------------------------------


def _df_sincronizacion() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["arroz", "frijol"],
            "SCIAN sector": ["11 agricultura", "11 agricultura"],
            "SCIAN rama": ["1111 arroz", "1121 frijol"],
        }
    )


def test_escribir_registro_sincronizacion_nombre_de_archivo_con_timestamp(
    tmp_path: Path,
) -> None:
    csv_destino = tmp_path / "ponderadores_2010.csv"
    escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": True, "frijol": False},
        2,
        tmp_path / "ponderadores_2013.csv",
        csv_destino,
    )
    (archivo,) = list(tmp_path.glob("*.json"))
    assert re.match(r"^sincronizacion_\d{8}_\d{6}_\d{6}_[0-9a-f]{8}\.json$", archivo.name)


def test_escribir_registro_sincronizacion_se_escribe_junto_a_csv_destino(
    tmp_path: Path,
) -> None:
    # no hay -o en este modo -- el json va en el mismo directorio de
    # --csv-destino, aunque --csv-fuente viva en otro lado
    otro_dir = tmp_path / "otro"
    otro_dir.mkdir()
    dir_destino = tmp_path / "salida"
    dir_destino.mkdir()
    csv_destino = dir_destino / "ponderadores_2010.csv"
    escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": False, "frijol": False},
        0,
        otro_dir / "ponderadores_2013.csv",
        csv_destino,
    )
    assert list(otro_dir.glob("*.json")) == []
    assert len(list(dir_destino.glob("sincronizacion_*.json"))) == 1


def test_escribir_registro_sincronizacion_campos_basicos_del_json(tmp_path: Path) -> None:
    csv_fuente = tmp_path / "ponderadores_2013.csv"
    csv_destino = tmp_path / "ponderadores_2010.csv"
    escribir_registro_sincronizacion(
        _df_sincronizacion(), {"arroz": True, "frijol": False}, 2, csv_fuente, csv_destino
    )
    registro = _leer_json_sincronizacion(tmp_path)
    assert registro["tipo"] == "sincronizacion"
    assert registro["csv_fuente"] == str(csv_fuente)
    assert registro["csv_destino"] == str(csv_destino)
    assert registro["version_fuente"] == 2013
    assert registro["version_destino"] == 2010
    assert registro["genericos"] == 2
    assert registro["celdas_actualizadas"] == 2


def test_escribir_registro_sincronizacion_clasificaciones_reusa_resumen_xlsx(
    tmp_path: Path,
) -> None:
    # mismo shape que _resumir_clasificacion_xlsx (genericos_clasificados,
    # categorias_unicas, categorias) -- no reinventa nada nuevo
    escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": True, "frijol": False},
        1,
        tmp_path / "f.csv",
        tmp_path / "d.csv",
    )
    registro = _leer_json_sincronizacion(tmp_path)
    assert set(registro["clasificaciones"]) == {"SCIAN sector", "SCIAN rama"}
    assert registro["clasificaciones"]["SCIAN sector"] == {
        "genericos_clasificados": 2,
        "categorias_unicas": 1,
        "categorias": {"11 agricultura": 2},
    }


def test_escribir_registro_sincronizacion_genericos_detalle_incluye_cambio(
    tmp_path: Path,
) -> None:
    escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": True, "frijol": False},
        1,
        tmp_path / "f.csv",
        tmp_path / "d.csv",
    )
    detalle = _leer_json_sincronizacion(tmp_path)["genericos_detalle"]
    assert detalle[0] == {
        "generico": "arroz",
        "SCIAN sector": "11 agricultura",
        "SCIAN rama": "1111 arroz",
        "cambio": True,
    }
    assert detalle[1]["cambio"] is False


def test_escribir_registro_sincronizacion_preserva_acentos_sin_escapar(
    tmp_path: Path,
) -> None:
    df = pd.DataFrame(
        {
            "generico": ["educacion (colegiaturas)"],
            "SCIAN sector": ["61 servicios educativos"],
            "SCIAN rama": ["6111 educación básica"],
        }
    )
    escribir_registro_sincronizacion(
        df, {"educacion (colegiaturas)": False}, 0, tmp_path / "f.csv", tmp_path / "d.csv"
    )
    (archivo,) = list(tmp_path.glob("*.json"))
    assert "educación básica" in archivo.read_text(encoding="utf-8")


def test_escribir_registro_sincronizacion_imprime_resumen_a_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": True, "frijol": False},
        2,
        tmp_path / "f.csv",
        tmp_path / "d.csv",
    )
    salida = capsys.readouterr().out
    assert "2 genericos sincronizados" in salida
    assert "celdas actualizadas: 2" in salida


def test_escribir_registro_sincronizacion_devuelve_ruta_del_json(tmp_path: Path) -> None:
    ruta = escribir_registro_sincronizacion(
        _df_sincronizacion(),
        {"arroz": False, "frijol": False},
        0,
        tmp_path / "f.csv",
        tmp_path / "d.csv",
    )
    assert ruta.exists()
    assert ruta.parent == tmp_path
