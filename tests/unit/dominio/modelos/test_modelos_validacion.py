from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Vista
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import (
    ValidacionIncidencia,
    ValidacionIndice,
    ValidacionVariacion,
)
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo, ManifestDerivado

# ---------- Fixtures helpers ----------

def _manif_calculo(tipo: str = "inpc", version: int = 2018, id_corrida: str = "c") -> ManifestCalculo:
    return ManifestCalculo(
        id_corrida=id_corrida,
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador="LaspeyresDirecto",
        ruta_canasta=Path("/tmp/c.csv"),
        ruta_series=Path("/tmp/s.csv"),
        fecha=datetime(2024, 1, 1),
    )


def _manif_derivado(tipo: str = "inpc", clase: str = "periodica_mensual") -> ManifestDerivado:
    return ManifestDerivado(
        id_corrida=["c1"],
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )


def _df_indice(tipo: str = "inpc", version: int = 2018) -> pd.DataFrame:
    periodos = [PeriodoQuincenal(2024, m, 2) for m in (1, 2)]
    idx = pd.MultiIndex.from_tuples(
        [(p, "INPC") for p in periodos], names=["periodo", "indice"]
    )
    return pd.DataFrame(
        {
            "version": [version, version],
            "tipo": [tipo, tipo],
            "indice_replicado": [100.0, 101.0],
            "estado_calculo": ["ok", "ok"],
            "motivo_error": [None, None],
        },
        index=idx,
    )


def _df_variacion(tipo: str = "inpc") -> pd.DataFrame:
    periodos = [PeriodoQuincenal(2024, m, 2) for m in (1, 2)]
    idx = pd.MultiIndex.from_tuples(
        [(p, "INPC") for p in periodos], names=["periodo", "indice"]
    )
    return pd.DataFrame(
        {
            "tipo": [tipo, tipo],
            "clase_variacion": ["periodica_mensual", "periodica_mensual"],
            "variacion_pp": [0.5, 0.6],
            "estado_calculo": ["ok", "ok"],
            "version_t": [2024, 2024],
        },
        index=idx,
    )


def _df_incidencia(tipo: str = "inpc") -> pd.DataFrame:
    periodos = [PeriodoQuincenal(2024, m, 2) for m in (1, 2)]
    idx = pd.MultiIndex.from_tuples(
        [(p, "INPC") for p in periodos], names=["periodo", "indice"]
    )
    return pd.DataFrame(
        {
            "tipo": [tipo, tipo],
            "clase_incidencia": ["periodica_mensual", "periodica_mensual"],
            "incidencia_pp": [0.3, 0.4],
            "estado_calculo": ["ok", "ok"],
            "version_t": [2024, 2024],
        },
        index=idx,
    )


def _resultado_indice(tipo: str = "inpc") -> ResultadoIndice:
    return ResultadoIndice(
        _df_indice(tipo=tipo),
        [_manif_calculo(tipo=tipo)],
        pd.DataFrame(),
        pd.DataFrame(),
    )


def _resultado_variacion(tipo: str = "inpc") -> ResultadoVariacion:
    return ResultadoVariacion(
        _df_variacion(tipo=tipo),
        _manif_derivado(tipo=tipo),
        pd.DataFrame(),
        pd.DataFrame(),
    )


def _resultado_incidencia(tipo: str = "inpc") -> ResultadoIncidencia:
    return ResultadoIncidencia(
        _df_incidencia(tipo=tipo),
        _manif_derivado(tipo=tipo),
        pd.DataFrame(),
        pd.DataFrame(),
    )


def _largo_indice_extendido() -> pd.DataFrame:
    base = _df_indice()
    base["indice_inegi"] = [100.0, 101.0]
    base["error_absoluto"] = [0.0, 0.0]
    base["estado_validacion"] = ["ok", "ok"]
    return base


def _largo_variacion_extendido() -> pd.DataFrame:
    base = _df_variacion()
    base["variacion_inegi_pp"] = [0.5, 0.6]
    base["error_absoluto_pp"] = [0.0, 0.0]
    base["estado_validacion"] = ["ok", "ok"]
    return base


def _largo_incidencia_extendido() -> pd.DataFrame:
    base = _df_incidencia()
    base["incidencia_inegi_pp"] = [0.3, 0.4]
    base["error_absoluto_pp"] = [0.0, 0.0]
    base["estado_validacion"] = ["ok", "ok"]
    return base


# ---------- ValidacionIndice ----------

def test_indice_construccion_valida() -> None:
    v = ValidacionIndice(
        _resultado_indice(),
        _largo_indice_extendido(),
        pd.DataFrame({"x": [1]}),
        pd.DataFrame({"y": [2]}),
        pd.DataFrame({"z": [3]}),
    )
    assert isinstance(v.resultado, Vista)


@pytest.mark.parametrize("tipo_invalido", ["cobertura", "durabilidad", "canasta basica"])
def test_indice_tipo_invalido_falla(tipo_invalido: str) -> None:
    r = ResultadoIndice(
        _df_indice(tipo=tipo_invalido),
        [_manif_calculo(tipo=tipo_invalido)],
        pd.DataFrame(),
        pd.DataFrame(),
    )
    with pytest.raises(InvarianteViolado):
        ValidacionIndice(
            r, _largo_indice_extendido(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


def test_indice_manifiesto_mixto_falla() -> None:
    df = pd.concat([_df_indice(tipo="inpc"), _df_indice(tipo="cobertura").rename(
        index={p: p for p in []}  # noop
    )])
    df = _df_indice(tipo="inpc")
    df2 = _df_indice(tipo="cobertura")
    df2.index = pd.MultiIndex.from_tuples(
        [(PeriodoQuincenal(2024, m, 1), "INPC") for m in (1, 2)],
        names=["periodo", "indice"],
    )
    df_concat = pd.concat([df, df2])
    r = ResultadoIndice(
        df_concat,
        [_manif_calculo(tipo="inpc"), _manif_calculo(tipo="cobertura", id_corrida="c2")],
        pd.DataFrame(),
        pd.DataFrame(),
    )
    with pytest.raises(InvarianteViolado):
        ValidacionIndice(
            r, _largo_indice_extendido(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


@pytest.mark.parametrize(
    "falta", ["indice_replicado", "indice_inegi", "error_absoluto", "estado_validacion"]
)
def test_indice_falta_col_vista_falla(falta: str) -> None:
    largo = _largo_indice_extendido().drop(columns=[falta])
    with pytest.raises(InvarianteViolado):
        ValidacionIndice(
            _resultado_indice(), largo, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


def test_indice_resultado_cols_correctas() -> None:
    v = ValidacionIndice(
        _resultado_indice(),
        _largo_indice_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    vista = v.resultado
    for col in ("indice_replicado", "indice_inegi", "error_absoluto", "estado_validacion"):
        assert col in vista.largo.columns


def test_indice_propagacion_resumen_reporte_diagnostico() -> None:
    s, r, d = pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}), pd.DataFrame({"c": [3]})
    v = ValidacionIndice(_resultado_indice(), _largo_indice_extendido(), s, r, d)
    assert v.resumen is s
    assert v.reporte is r
    assert v.diagnostico is d


def test_indice_sin_df_ni_pipe() -> None:
    v = ValidacionIndice(
        _resultado_indice(),
        _largo_indice_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert hasattr(v, "df") is False
    assert hasattr(v, "pipe") is False


def test_indice_repr_html_string() -> None:
    v = ValidacionIndice(
        _resultado_indice(),
        _largo_indice_extendido(),
        pd.DataFrame({"a": [1]}),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(v._repr_html_(), str)


# ---------- ValidacionVariacion ----------

def test_variacion_construccion_valida() -> None:
    v = ValidacionVariacion(
        _resultado_variacion(),
        _largo_variacion_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(v.resultado, Vista)


@pytest.mark.parametrize("tipo_invalido", ["cobertura", "durabilidad"])
def test_variacion_tipo_invalido_falla(tipo_invalido: str) -> None:
    r = _resultado_variacion(tipo=tipo_invalido)
    with pytest.raises(InvarianteViolado):
        ValidacionVariacion(
            r, _largo_variacion_extendido(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


@pytest.mark.parametrize(
    "falta",
    ["variacion_pp", "variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"],
)
def test_variacion_falta_col_vista_falla(falta: str) -> None:
    largo = _largo_variacion_extendido().drop(columns=[falta])
    with pytest.raises(InvarianteViolado):
        ValidacionVariacion(
            _resultado_variacion(), largo, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


def test_variacion_resultado_cols_correctas() -> None:
    v = ValidacionVariacion(
        _resultado_variacion(),
        _largo_variacion_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    for col in ("variacion_pp", "variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"):
        assert col in v.resultado.largo.columns


def test_variacion_propagacion() -> None:
    s, r, d = pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}), pd.DataFrame({"c": [3]})
    v = ValidacionVariacion(_resultado_variacion(), _largo_variacion_extendido(), s, r, d)
    assert v.resumen is s
    assert v.reporte is r
    assert v.diagnostico is d


def test_variacion_sin_df_ni_pipe() -> None:
    v = ValidacionVariacion(
        _resultado_variacion(),
        _largo_variacion_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert hasattr(v, "df") is False
    assert hasattr(v, "pipe") is False


def test_variacion_repr_html_string() -> None:
    v = ValidacionVariacion(
        _resultado_variacion(),
        _largo_variacion_extendido(),
        pd.DataFrame({"a": [1]}),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(v._repr_html_(), str)


# ---------- ValidacionIncidencia ----------

def test_incidencia_construccion_valida() -> None:
    v = ValidacionIncidencia(
        _resultado_incidencia(),
        _largo_incidencia_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(v.resultado, Vista)


@pytest.mark.parametrize("tipo_invalido", ["cobertura", "durabilidad"])
def test_incidencia_tipo_invalido_falla(tipo_invalido: str) -> None:
    r = _resultado_incidencia(tipo=tipo_invalido)
    with pytest.raises(InvarianteViolado):
        ValidacionIncidencia(
            r, _largo_incidencia_extendido(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


@pytest.mark.parametrize(
    "falta",
    ["incidencia_pp", "incidencia_inegi_pp", "error_absoluto_pp", "estado_validacion"],
)
def test_incidencia_falta_col_vista_falla(falta: str) -> None:
    largo = _largo_incidencia_extendido().drop(columns=[falta])
    with pytest.raises(InvarianteViolado):
        ValidacionIncidencia(
            _resultado_incidencia(), largo, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )


def test_incidencia_resultado_cols_correctas() -> None:
    v = ValidacionIncidencia(
        _resultado_incidencia(),
        _largo_incidencia_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    for col in (
        "incidencia_pp",
        "incidencia_inegi_pp",
        "error_absoluto_pp",
        "estado_validacion",
    ):
        assert col in v.resultado.largo.columns


def test_incidencia_propagacion() -> None:
    s, r, d = pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}), pd.DataFrame({"c": [3]})
    v = ValidacionIncidencia(_resultado_incidencia(), _largo_incidencia_extendido(), s, r, d)
    assert v.resumen is s
    assert v.reporte is r
    assert v.diagnostico is d


def test_incidencia_sin_df_ni_pipe() -> None:
    v = ValidacionIncidencia(
        _resultado_incidencia(),
        _largo_incidencia_extendido(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert hasattr(v, "df") is False
    assert hasattr(v, "pipe") is False


def test_incidencia_repr_html_string() -> None:
    v = ValidacionIncidencia(
        _resultado_incidencia(),
        _largo_incidencia_extendido(),
        pd.DataFrame({"a": [1]}),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(v._repr_html_(), str)
