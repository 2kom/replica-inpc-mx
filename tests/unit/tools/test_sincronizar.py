from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from canasta_inpc.esquema import COLUMNAS_BASE
from canasta_inpc.sincronizar import (
    ResultadoSincronizacion,
    _confirmar_sobrescritura,
    _leer_csv,
    _mapear_por_generico,
    _validar_columnas,
    _validar_genericos_coinciden,
    _validar_scian_completo,
    sincronizar_scian,
)

# -- helpers --------------------------------------------------------------


def _csv(tmp_path: Path, nombre: str, filas: list[dict]) -> Path:
    ruta = tmp_path / nombre
    pd.DataFrame(filas).to_csv(ruta, index=False)
    return ruta


def _fila(generico: str, sector: str = "11 agricultura", rama: str = "1111 cultivo") -> dict:
    return {
        "generico": generico,
        "ponderador": "1.0",
        "SCIAN sector": sector,
        "SCIAN rama": rama,
    }


def _sin_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_: object, **__: object) -> str:
        raise AssertionError("no deberia pedir confirmacion en este caso")

    monkeypatch.setattr("builtins.input", _boom)


def _confirmar(monkeypatch: pytest.MonkeyPatch, respuesta: str = "s") -> None:
    monkeypatch.setattr("builtins.input", lambda _="": respuesta)


# -- _leer_csv --------------------------------------------------------------


def test_leer_csv_convierte_nan_a_vacio(tmp_path: Path) -> None:
    ruta = tmp_path / "a.csv"
    ruta.write_text("generico,SCIAN sector\narroz,\n", encoding="utf-8")
    df = _leer_csv(ruta)
    assert df["SCIAN sector"].tolist() == [""]


# -- _validar_columnas --------------------------------------------------------------


def test_validar_columnas_ok_si_estan_todas() -> None:
    df = pd.DataFrame(columns=["generico", "SCIAN sector", "SCIAN rama"])
    _validar_columnas(df, Path("a.csv"))  # no lanza


def test_validar_columnas_lanza_si_falta_alguna() -> None:
    df = pd.DataFrame(columns=["generico", "SCIAN sector"])
    with pytest.raises(ValueError, match="SCIAN rama"):
        _validar_columnas(df, Path("a.csv"))


# -- _validar_scian_completo --------------------------------------------------------------


def test_validar_scian_completo_ok_si_no_hay_vacios() -> None:
    df = pd.DataFrame({"SCIAN sector": ["11 agricultura"], "SCIAN rama": ["1111 cultivo"]})
    _validar_scian_completo(df, Path("a.csv"))  # no lanza


def test_validar_scian_completo_lanza_si_hay_vacio_en_sector() -> None:
    df = pd.DataFrame({"SCIAN sector": [""], "SCIAN rama": ["1111 cultivo"]})
    with pytest.raises(ValueError, match="SCIAN completo"):
        _validar_scian_completo(df, Path("2013.csv"))


def test_validar_scian_completo_lanza_si_hay_vacio_en_rama() -> None:
    df = pd.DataFrame({"SCIAN sector": ["11 agricultura"], "SCIAN rama": [""]})
    with pytest.raises(ValueError, match="SCIAN completo"):
        _validar_scian_completo(df, Path("2013.csv"))


# -- _mapear_por_generico --------------------------------------------------------------


def test_mapear_por_generico_usa_texto_normalizado_como_llave() -> None:
    df = pd.DataFrame({"generico": ["Arroz Blanco"], "SCIAN sector": ["11 agricultura"]})
    mapa = _mapear_por_generico(df, Path("a.csv"))
    assert "arroz blanco" in mapa
    assert mapa["arroz blanco"]["generico"] == "Arroz Blanco"


def test_mapear_por_generico_lanza_si_hay_duplicados_tras_normalizar() -> None:
    df = pd.DataFrame({"generico": ["Arroz", "arroz"], "SCIAN sector": ["a", "b"]})
    with pytest.raises(ValueError, match="duplicados"):
        _mapear_por_generico(df, Path("a.csv"))


# -- _validar_genericos_coinciden --------------------------------------------------------------


def test_validar_genericos_coinciden_ok_si_sets_iguales() -> None:
    mapa = {"arroz": {"generico": "arroz"}}
    _validar_genericos_coinciden(mapa, mapa, Path("f.csv"), Path("d.csv"))  # no lanza


def test_validar_genericos_coinciden_lanza_si_falta_en_destino() -> None:
    fuente = {"arroz": {"generico": "arroz"}, "frijol": {"generico": "frijol"}}
    destino = {"arroz": {"generico": "arroz"}}
    with pytest.raises(ValueError, match="frijol"):
        _validar_genericos_coinciden(fuente, destino, Path("f.csv"), Path("d.csv"))


def test_validar_genericos_coinciden_lanza_si_sobra_en_destino() -> None:
    fuente = {"arroz": {"generico": "arroz"}}
    destino = {"arroz": {"generico": "arroz"}, "sobrante": {"generico": "sobrante"}}
    with pytest.raises(ValueError, match="sobrante"):
        _validar_genericos_coinciden(fuente, destino, Path("f.csv"), Path("d.csv"))


# -- _confirmar_sobrescritura --------------------------------------------------------------


def test_confirmar_sobrescritura_acepta_variantes_de_si(monkeypatch: pytest.MonkeyPatch) -> None:
    for respuesta in ("s", "si", "sí", "y", "yes", "S", "SI"):
        monkeypatch.setattr("builtins.input", lambda _="", r=respuesta: r)
        _confirmar_sobrescritura(Path("f.csv"), Path("d.csv"), 1)  # no lanza


def test_confirmar_sobrescritura_cancela_si_responde_no(monkeypatch: pytest.MonkeyPatch) -> None:
    _confirmar(monkeypatch, "n")
    with pytest.raises(RuntimeError, match="cancelada"):
        _confirmar_sobrescritura(Path("f.csv"), Path("d.csv"), 1)


def test_confirmar_sobrescritura_cancela_si_respuesta_vacia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _confirmar(monkeypatch, "")
    with pytest.raises(RuntimeError, match="cancelada"):
        _confirmar_sobrescritura(Path("f.csv"), Path("d.csv"), 1)


def test_confirmar_sobrescritura_eof_lanza_runtimeerror_explicito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _eof(*_: object, **__: object) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)
    with pytest.raises(RuntimeError, match="stdin"):
        _confirmar_sobrescritura(Path("f.csv"), Path("d.csv"), 1)


# -- sincronizar_scian: validaciones end-to-end --------------------------------------------------------------


def test_sincronizar_scian_lanza_si_fuente_sin_scian_completo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sin_prompt(monkeypatch)
    fuente = _csv(
        tmp_path, "2013.csv", [{"generico": "arroz", "SCIAN sector": "", "SCIAN rama": ""}]
    )
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz")])
    with pytest.raises(ValueError, match="SCIAN completo"):
        sincronizar_scian(fuente, destino)


def test_sincronizar_scian_lanza_si_genericos_no_coinciden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sin_prompt(monkeypatch)
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz"), _fila("frijol")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz")])
    with pytest.raises(ValueError, match="no coinciden"):
        sincronizar_scian(fuente, destino)


def test_sincronizar_scian_cancela_no_escribe_nada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch, "n")
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz", rama="1112 nueva rama")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz", rama="1111 vieja rama")])
    contenido_previo = destino.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError):
        sincronizar_scian(fuente, destino)
    assert destino.read_text(encoding="utf-8") == contenido_previo


# -- sincronizar_scian: copia real --------------------------------------------------------------


def test_sincronizar_scian_copia_por_generico_no_por_orden_de_fila(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # fuente y destino en orden distinto -- si el match fuera posicional, el
    # SCIAN de "arroz" terminaria en la fila de "frijol"
    _confirmar(monkeypatch)
    fuente = _csv(
        tmp_path,
        "2013.csv",
        [
            _fila("frijol", sector="11 agricultura", rama="1121 frijol"),
            _fila("arroz", sector="11 agricultura", rama="1111 arroz"),
        ],
    )
    destino = _csv(
        tmp_path,
        "2010.csv",
        [
            _fila("arroz", sector="00 vacio", rama="0000 vacio"),
            _fila("frijol", sector="00 vacio", rama="0000 vacio"),
        ],
    )
    resultado = sincronizar_scian(fuente, destino)
    por_generico = resultado.df.set_index("generico")
    assert por_generico.loc["arroz", "SCIAN rama"] == "1111 arroz"
    assert por_generico.loc["frijol", "SCIAN rama"] == "1121 frijol"


def test_sincronizar_scian_cuenta_celdas_actualizadas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(
        tmp_path,
        "2013.csv",
        [_fila("arroz", sector="11 nuevo", rama="1111 nuevo"), _fila("frijol")],
    )
    destino = _csv(
        tmp_path,
        "2010.csv",
        [_fila("arroz", sector="00 viejo", rama="0000 viejo"), _fila("frijol")],
    )
    resultado = sincronizar_scian(fuente, destino)
    # "arroz": sector Y rama cambian (2 celdas); "frijol": ya coincidia (0)
    assert resultado.celdas_actualizadas == 2


def test_sincronizar_scian_cambios_marca_true_solo_donde_hubo_diferencia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(
        tmp_path,
        "2013.csv",
        [_fila("arroz", sector="11 nuevo", rama="1111 nuevo"), _fila("frijol")],
    )
    destino = _csv(
        tmp_path,
        "2010.csv",
        [_fila("arroz", sector="00 viejo", rama="0000 viejo"), _fila("frijol")],
    )
    resultado = sincronizar_scian(fuente, destino)
    assert resultado.cambios == {"arroz": True, "frijol": False}


def test_sincronizar_scian_idempotente_segunda_corrida_no_actualiza_nada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz", sector="11 nuevo", rama="1111 nuevo")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz", sector="00 viejo", rama="0000 viejo")])

    primera = sincronizar_scian(fuente, destino)
    assert primera.celdas_actualizadas == 2

    segunda = sincronizar_scian(fuente, destino)
    assert segunda.celdas_actualizadas == 0
    assert segunda.cambios == {"arroz": False}


def test_sincronizar_scian_no_toca_columnas_ajenas_a_scian(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz", sector="11 nuevo", rama="1111 nuevo")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz")])
    resultado = sincronizar_scian(fuente, destino)
    assert resultado.df.loc[0, "ponderador"] == "1.0"


def test_sincronizar_scian_escribe_csv_con_columnas_del_esquema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz")])
    sincronizar_scian(fuente, destino)
    releido = pd.read_csv(destino, dtype=str).fillna("")
    assert releido.columns.tolist() == list(COLUMNAS_BASE)


def test_sincronizar_scian_devuelve_resultado_sincronizacion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _confirmar(monkeypatch)
    fuente = _csv(tmp_path, "2013.csv", [_fila("arroz")])
    destino = _csv(tmp_path, "2010.csv", [_fila("arroz")])
    resultado = sincronizar_scian(fuente, destino)
    assert isinstance(resultado, ResultadoSincronizacion)
