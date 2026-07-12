from __future__ import annotations

from pathlib import Path

import generar_canasta
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


def test_preferir_csv_valido_con_pdf(tmp_path: Path) -> None:
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
            "csv",
            "-o",
            str(tmp_path),
        ]
    )
    assert args.preferir == "csv"


# -- modo: sincronización -------------------------------------------------------


def test_sincronizar_valido(tmp_path: Path) -> None:
    fuente = _csv(tmp_path, "2013.csv")
    destino = _csv(tmp_path, "2010.csv")
    args = parsear_args(
        ["--sincronizar", "--csv-fuente", str(fuente), "--csv-destino", str(destino)]
    )
    assert args.sincronizar is True


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
