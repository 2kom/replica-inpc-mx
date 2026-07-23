from __future__ import annotations

import argparse
import json
from pathlib import Path

import generar_canasta
import pandas as pd
import pytest
from generar_canasta import main, parsear_args

# -- helpers ---------------------------------------------------------------


def _xlsx(tmp_path: Path) -> Path:
    ruta = tmp_path / "canasta.xlsx"
    ruta.write_bytes(b"fake")
    return ruta


def _pdf(tmp_path: Path) -> Path:
    ruta = tmp_path / "anexo.pdf"
    ruta.write_bytes(b"fake")
    return ruta


def _csv(tmp_path: Path, nombre: str) -> Path:
    ruta = tmp_path / nombre
    ruta.write_text("generico,ponderador\n")
    return ruta


def _dir(tmp_path: Path, nombre: str = "no_es_archivo") -> Path:
    ruta = tmp_path / nombre
    ruta.mkdir()
    return ruta


def _error(capsys: pytest.CaptureFixture[str], argv: list[str]) -> str:
    with pytest.raises(SystemExit) as exc:
        parsear_args(argv)
    assert exc.value.code == 2
    return capsys.readouterr().err


# -- modo: xlsx solo ----------------------------------------------


def test_xlsx_solo_valido(tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    args = parsear_args(["--version", "2018", "--xlsx", str(xlsx), "-o", str(tmp_path)])
    assert args.version == 2018
    assert args.xlsx == xlsx
    assert args.pdf is None


def test_falta_version(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    err = _error(capsys, ["--xlsx", str(xlsx), "-o", str(tmp_path)])
    assert "--version es obligatorio" in err


def test_falta_xlsx(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    err = _error(capsys, ["--version", "2018", "-o", str(tmp_path)])
    assert "--xlsx es obligatorio" in err


def test_falta_salida(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    err = _error(capsys, ["--version", "2018", "--xlsx", str(xlsx)])
    assert "-o es obligatorio" in err


def test_version_fuera_de_choices(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    err = _error(capsys, ["--version", "1999", "--xlsx", str(xlsx), "-o", str(tmp_path)])
    assert "invalid choice" in err


def test_xlsx_no_existe(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    err = _error(
        capsys,
        ["--version", "2018", "--xlsx", str(tmp_path / "no_existe.xlsx"), "-o", str(tmp_path)],
    )
    assert "No se encontró --xlsx" in err


def test_xlsx_es_directorio(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    directorio = _dir(tmp_path)
    err = _error(capsys, ["--version", "2018", "--xlsx", str(directorio), "-o", str(tmp_path)])
    assert "--xlsx" in err
    assert "directorio" in err


def test_salida_existe_como_archivo_es_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    xlsx = _xlsx(tmp_path)
    salida = tmp_path / "salida_es_archivo.txt"
    salida.write_text("ya existo")
    err = _error(capsys, ["--version", "2018", "--xlsx", str(xlsx), "-o", str(salida)])
    assert "-o" in err
    assert "directorio" in err


# -- modo: xlsx + pdf ---------------------------------------------


def test_xlsx_pdf_valido(tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    pdf = _pdf(tmp_path)
    args = parsear_args(
        ["--version", "2018", "--xlsx", str(xlsx), "--pdf", str(pdf), "-o", str(tmp_path)]
    )
    assert args.pdf == pdf


def test_pdf_no_existe(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    err = _error(
        capsys,
        [
            "--version",
            "2018",
            "--xlsx",
            str(xlsx),
            "--pdf",
            str(tmp_path / "no.pdf"),
            "-o",
            str(tmp_path),
        ],
    )
    assert "No se encontró --pdf" in err


def test_pdf_es_directorio(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    directorio = _dir(tmp_path)
    err = _error(
        capsys,
        ["--version", "2018", "--xlsx", str(xlsx), "--pdf", str(directorio), "-o", str(tmp_path)],
    )
    assert "--pdf" in err
    assert "directorio" in err


# -- modo: xlsx + pdf + preferir -----------------------------------


def test_preferir_valido_con_pdf(tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    pdf = _pdf(tmp_path)
    args = parsear_args(
        [
            "--version",
            "2018",
            "--xlsx",
            str(xlsx),
            "--pdf",
            str(pdf),
            "--preferir",
            "pdf",
            "-o",
            str(tmp_path),
        ]
    )
    assert args.preferir == "pdf"


def test_preferir_fuera_de_choices(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    pdf = _pdf(tmp_path)
    err = _error(
        capsys,
        [
            "--version",
            "2018",
            "--xlsx",
            str(xlsx),
            "--pdf",
            str(pdf),
            "--preferir",
            "excel",
            "-o",
            str(tmp_path),
        ],
    )
    assert "invalid choice" in err


def test_preferir_sin_pdf_es_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    err = _error(
        capsys,
        ["--version", "2018", "--xlsx", str(xlsx), "--preferir", "pdf", "-o", str(tmp_path)],
    )
    assert "--preferir requiere --pdf" in err


def test_preferir_xlsx_valido_con_pdf(tmp_path: Path) -> None:
    xlsx = _xlsx(tmp_path)
    pdf = _pdf(tmp_path)
    args = parsear_args(
        [
            "--version",
            "2018",
            "--xlsx",
            str(xlsx),
            "--pdf",
            str(pdf),
            "--preferir",
            "xlsx",
            "-o",
            str(tmp_path),
        ]
    )
    assert args.preferir == "xlsx"


# -- modo: sincronización -------------------------------------------------------


def test_sincronizar_valido(tmp_path: Path) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    destino = _csv(tmp_path, "2010.csv")
    args = parsear_args(
        ["--sincronizar", "--csv-fuente", str(fuente), "--csv-destino", str(destino)]
    )
    assert args.sincronizar is True


def test_sincronizar_rechaza_salida(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    destino = _csv(tmp_path, "2010.csv")
    err = _error(
        capsys,
        [
            "--sincronizar",
            "--csv-fuente",
            str(fuente),
            "--csv-destino",
            str(destino),
            "-o",
            str(tmp_path),
        ],
    )
    assert "-o no aplica con --sincronizar" in err


def test_sincronizar_falta_csv_fuente(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    destino = _csv(tmp_path, "2010.csv")
    err = _error(capsys, ["--sincronizar", "--csv-destino", str(destino)])
    assert "--sincronizar requiere" in err


def test_sincronizar_falta_csv_destino(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    err = _error(capsys, ["--sincronizar", "--csv-fuente", str(fuente)])
    assert "--sincronizar requiere" in err


def test_sincronizar_csv_fuente_no_existe(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    destino = _csv(tmp_path, "2010.csv")
    err = _error(
        capsys,
        ["--sincronizar", "--csv-fuente", str(tmp_path / "no.csv"), "--csv-destino", str(destino)],
    )
    assert "No se encontró --csv-fuente" in err


def test_sincronizar_csv_destino_no_existe(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    err = _error(
        capsys,
        ["--sincronizar", "--csv-fuente", str(fuente), "--csv-destino", str(tmp_path / "no.csv")],
    )
    assert "No se encontró --csv-destino" in err


def test_sincronizar_csv_fuente_es_directorio(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    directorio = _dir(tmp_path)
    destino = _csv(tmp_path, "2010.csv")
    err = _error(
        capsys,
        ["--sincronizar", "--csv-fuente", str(directorio), "--csv-destino", str(destino)],
    )
    assert "--csv-fuente" in err
    assert "directorio" in err


def test_sincronizar_csv_destino_es_directorio(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    directorio = _dir(tmp_path)
    err = _error(
        capsys,
        ["--sincronizar", "--csv-fuente", str(fuente), "--csv-destino", str(directorio)],
    )
    assert "--csv-destino" in err
    assert "directorio" in err


# -- main: dispatch de los 3 modos (mockeado, sin tocar canasta_inpc.*) ---------


def test_main_modo_xlsx_llama_ejecutar_xlsx(mocker, tmp_path: Path) -> None:
    ejecutar = mocker.patch.object(generar_canasta, "_ejecutar_xlsx")
    xlsx = _xlsx(tmp_path)
    salida = tmp_path / "salida"
    main(["--version", "2018", "--xlsx", str(xlsx), "-o", str(salida)])
    ejecutar.assert_called_once()
    assert salida.is_dir()


def test_main_modo_xlsx_pdf_llama_ejecutar_xlsx_pdf(mocker, tmp_path: Path) -> None:
    ejecutar = mocker.patch.object(generar_canasta, "_ejecutar_xlsx_pdf")
    xlsx = _xlsx(tmp_path)
    pdf = _pdf(tmp_path)
    salida = tmp_path / "salida"
    main(["--version", "2018", "--xlsx", str(xlsx), "--pdf", str(pdf), "-o", str(salida)])
    ejecutar.assert_called_once()
    assert salida.is_dir()


def test_main_modo_sincronizar_llama_ejecutar_sincronizacion(mocker, tmp_path: Path) -> None:
    ejecutar = mocker.patch.object(generar_canasta, "_ejecutar_sincronizacion")
    fuente = _csv(tmp_path, "2013.csv")
    destino = _csv(tmp_path, "2010.csv")
    main(["--sincronizar", "--csv-fuente", str(fuente), "--csv-destino", str(destino)])
    ejecutar.assert_called_once()


# -- _ejecutar_xlsx_pdf: wiring completo (match_dfs real, solo se mockea I/O) ---


def _xlsx_2013_min() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["pan", "aceite"],
            "ponderador": ["2.5", "1.23456"],
            "encadenamiento": ["0.87654", "0.9"],
            "COG": ["panaderia", "aceites y grasas"],
            "CCIF division": ["alimentos", "alimentos"],
            "inflacion componente": ["subyacente", "subyacente"],
            "inflacion subcomponente": ["mercancias", "mercancias"],
            "inflacion agrupacion": ["alimentos bebidas y tabaco"] * 2,
            "canasta basica": ["-", "X"],
        }
    )


def _pdf_2013_min() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["aceite", "pan"],
            "ponderador": ["1.2346", "2.5"],
            "encadenamiento": ["0.900", "0.8765"],
            "CCIF division": ["01 alimentos", "01 alimentos"],
            "CCIF grupo": ["01.1 aceites y grasas", "01.2 pan y cereales"],
            "CCIF clase": ["01.1.1 aceites comestibles", "01.2.1 pan de trigo"],
            "SCIAN sector": ["11 agricultura", "31 industrias manufactureras"],
            "SCIAN rama": ["1111 cultivo", "3118 panificacion"],
        }
    )


def test_ejecutar_xlsx_pdf_encadena_extraer_match_guardar_y_registro(
    mocker, tmp_path: Path
) -> None:
    # a diferencia de test_main_modo_xlsx_pdf_llama_ejecutar_xlsx_pdf (que
    # mockea _ejecutar_xlsx_pdf entera), esto corre match_dfs real sobre
    # fixtures chicas -- confirma que guardar_csv/escribir_registro_pdf
    # reciben el MISMO resultado.df que produjo match_dfs, sin reconstruir
    # nada aparte (el bug que motivo esta prueba: durante esta sesion,
    # _ejecutar_xlsx_pdf nunca llamo escribir_registro_pdf, y ningun test lo
    # detecto -- solo correr el CLI a mano lo mostro)
    mocker.patch("canasta_inpc.extraccion_xlsx.extraer_xlsx", return_value=_xlsx_2013_min())
    mocker.patch("canasta_inpc.extraccion_pdf.extraer_pdf", return_value=_pdf_2013_min())
    guardar_csv_mock = mocker.patch("canasta_inpc.utilidades.guardar_csv")
    registro_mock = mocker.patch("canasta_inpc.registro.escribir_registro_pdf")

    args = argparse.Namespace(
        version=2013,
        xlsx=Path("entrada.xlsx"),
        pdf=Path("entrada.pdf"),
        preferir="pdf",
        salida=tmp_path,
    )
    generar_canasta._ejecutar_xlsx_pdf(args)

    guardar_csv_mock.assert_called_once()
    df_guardado = guardar_csv_mock.call_args[0][0]
    # confirma que match_dfs corrio de verdad (alineo/ordeno "aceite" antes
    # que "pan"), no un mock ni un df vacio
    assert list(df_guardado["generico"]) == ["aceite", "pan"]

    registro_mock.assert_called_once()
    resultado_pasado = registro_mock.call_args[0][0]
    assert resultado_pasado.df is df_guardado  # mismo objeto, no reconstruido
    assert len(resultado_pasado.resoluciones) > 0
    assert registro_mock.call_args[0][1] is args


def test_ejecutar_xlsx_pdf_produce_json_valido_sin_mockear_el_registro(
    mocker, tmp_path: Path
) -> None:
    # a diferencia de la prueba de arriba (que mockea escribir_registro_pdf
    # para verificar SOLO el wiring), esta corre match_dfs -> escribir_registro_pdf
    # de punta a punta de verdad -- sin construir ningun Resolucion a mano,
    # para que un mismatch real entre lo que match_dfs produce y lo que
    # escribir_registro_pdf espera (como los 2 KeyError de esta sesion) no
    # pueda esconderse detras de un mock
    mocker.patch("canasta_inpc.extraccion_xlsx.extraer_xlsx", return_value=_xlsx_2013_min())
    mocker.patch("canasta_inpc.extraccion_pdf.extraer_pdf", return_value=_pdf_2013_min())
    mocker.patch("canasta_inpc.utilidades.guardar_csv")

    args = argparse.Namespace(
        version=2013,
        xlsx=Path("entrada.xlsx"),
        pdf=Path("entrada.pdf"),
        preferir="pdf",
        salida=tmp_path,
    )
    generar_canasta._ejecutar_xlsx_pdf(args)

    (archivo,) = list(tmp_path.glob("pdf_*.json"))
    registro = json.loads(archivo.read_text(encoding="utf-8"))
    assert registro["tipo"] == "xlsx_pdf"
    assert registro["preferir"] == "pdf"
    assert registro["genericos"] == 2
    assert {d["generico"] for d in registro["genericos_detalle"]} == {"aceite", "pan"}
    assert "COG" in registro["clasificaciones"]


# -- _ejecutar_sincronizacion: wiring completo (sincronizar_scian real) --------


def _csv_scian(tmp_path: Path, nombre: str, filas: list[dict]) -> Path:
    ruta = tmp_path / nombre
    pd.DataFrame(filas).to_csv(ruta, index=False)
    return ruta


def _fila_scian(generico: str, sector: str = "11 agricultura", rama: str = "1111 cultivo") -> dict:
    return {
        "generico": generico,
        "ponderador": "1.0",
        "SCIAN sector": sector,
        "SCIAN rama": rama,
    }


def test_ejecutar_sincronizacion_pasa_a_registro_el_resultado_de_sincronizar_scian(
    mocker, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # mismo motivo que test_ejecutar_xlsx_pdf_encadena_extraer_match_guardar_y_registro:
    # sincronizar_scian corre de verdad, solo se mockea escribir_registro_sincronizacion,
    # para confirmar que recibe el MISMO df/cambios/celdas que produjo la sincronizacion real
    monkeypatch.setattr("builtins.input", lambda _="": "s")
    registro_mock = mocker.patch("canasta_inpc.registro.escribir_registro_sincronizacion")

    fuente = _csv_scian(
        tmp_path, "2013.csv", [_fila_scian("arroz", sector="11 nuevo", rama="1111 nuevo")]
    )
    destino = _csv_scian(
        tmp_path, "2010.csv", [_fila_scian("arroz", sector="00 viejo", rama="0000 viejo")]
    )

    args = argparse.Namespace(csv_fuente=fuente, csv_destino=destino)
    generar_canasta._ejecutar_sincronizacion(args)

    registro_mock.assert_called_once()
    df_pasado, cambios_pasado, celdas_pasadas, csv_fuente_pasado, csv_destino_pasado = (
        registro_mock.call_args[0]
    )
    assert list(df_pasado["SCIAN sector"]) == ["11 nuevo"]
    assert cambios_pasado == {"arroz": True}
    assert celdas_pasadas == 2
    assert csv_fuente_pasado == fuente
    assert csv_destino_pasado == destino


def test_ejecutar_sincronizacion_produce_json_valido_sin_mockear_el_registro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # de punta a punta de verdad, sin mocks -- mismo motivo que
    # test_ejecutar_xlsx_pdf_produce_json_valido_sin_mockear_el_registro
    monkeypatch.setattr("builtins.input", lambda _="": "s")
    fuente = _csv_scian(
        tmp_path, "2013.csv", [_fila_scian("arroz", sector="11 nuevo", rama="1111 nuevo")]
    )
    destino = _csv_scian(
        tmp_path, "2010.csv", [_fila_scian("arroz", sector="00 viejo", rama="0000 viejo")]
    )

    args = argparse.Namespace(csv_fuente=fuente, csv_destino=destino)
    generar_canasta._ejecutar_sincronizacion(args)

    (archivo,) = list(tmp_path.glob("sincronizacion_*.json"))
    registro = json.loads(archivo.read_text(encoding="utf-8"))
    assert registro["tipo"] == "sincronizacion"
    assert registro["genericos"] == 1
    assert registro["celdas_actualizadas"] == 2

    releido = pd.read_csv(destino, dtype=str).fillna("")
    assert releido.loc[0, "SCIAN sector"] == "11 nuevo"


def test_ejecutar_sincronizacion_cancelada_no_escribe_csv_ni_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("builtins.input", lambda _="": "n")
    fuente = _csv_scian(
        tmp_path, "2013.csv", [_fila_scian("arroz", sector="11 nuevo", rama="1111 nuevo")]
    )
    destino = _csv_scian(
        tmp_path, "2010.csv", [_fila_scian("arroz", sector="00 viejo", rama="0000 viejo")]
    )
    contenido_previo = destino.read_text(encoding="utf-8")

    args = argparse.Namespace(csv_fuente=fuente, csv_destino=destino)
    with pytest.raises(RuntimeError, match="cancelada"):
        generar_canasta._ejecutar_sincronizacion(args)

    assert destino.read_text(encoding="utf-8") == contenido_previo
    assert list(tmp_path.glob("sincronizacion_*.json")) == []
