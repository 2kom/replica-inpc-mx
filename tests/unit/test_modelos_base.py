from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Resultado, Validacion, Vista
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestDerivado, ManifestUnidad


def _df_largo_1col() -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples(
        [(PeriodoQuincenal(2024, 1, 1), "001"), (PeriodoQuincenal(2024, 1, 2), "001")],
        names=["periodo", "indice"],
    )
    return pd.DataFrame({"x": [1.0, 2.0]}, index=idx)


def _df_largo_ncols(con_nan: bool = False) -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples(
        [
            (PeriodoQuincenal(2024, 1, 1), "001"),
            (PeriodoQuincenal(2024, 1, 2), "001"),
            (PeriodoQuincenal(2024, 1, 1), "002"),
            (PeriodoQuincenal(2024, 1, 2), "002"),
        ],
        names=["periodo", "indice"],
    )
    if con_nan:
        return pd.DataFrame(
            {"a": [1.0, 2.0, np.nan, 4.0], "b": [10.0, np.nan, 30.0, 40.0]},
            index=idx,
        )
    return pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [10.0, 20.0, 30.0, 40.0]}, index=idx)


class _ResultadoMinimo(Resultado):
    @property
    def resultado(self) -> Vista:
        return Vista(self.df, ["x"])

    @property
    def resumen(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def reporte(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def diagnostico(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _repr_html_(self) -> str:
        return ""


class _ValidacionMinima(Validacion):
    @property
    def resultado(self) -> Vista:
        return Vista(_df_largo_1col(), ["x"])

    @property
    def resumen(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def reporte(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def diagnostico(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _repr_html_(self) -> str:
        return ""


# ---------- Vista ----------

def test_vista_largo_retorna_df_sin_transformar() -> None:
    df = _df_largo_1col()
    assert Vista(df, ["x"]).largo is df


def test_vista_ancho_1col_filas_indice_cols_periodo() -> None:
    ancho = Vista(_df_largo_1col(), ["x"]).ancho
    assert ancho.index.name == "indice"
    assert ancho.columns.name == "periodo"
    assert ancho.shape == (1, 2)


def test_vista_ancho_ncols_filas_multiindex() -> None:
    ancho = Vista(_df_largo_ncols(), ["a", "b"]).ancho
    assert isinstance(ancho.index, pd.MultiIndex)
    assert ancho.columns.name == "periodo"


def test_vista_repr_html_devuelve_string() -> None:
    html = Vista(_df_largo_1col(), ["x"])._repr_html_()
    assert isinstance(html, str)
    assert len(html) > 0


def test_vista_ancho_ncols_preserva_nan() -> None:
    df = _df_largo_ncols(con_nan=True)
    ancho = Vista(df, ["a", "b"]).ancho
    q1 = PeriodoQuincenal(2024, 1, 1)
    q2 = PeriodoQuincenal(2024, 1, 2)
    assert ancho.shape == (4, 2)
    assert set(ancho.index) == {("001", "a"), ("001", "b"), ("002", "a"), ("002", "b")}
    assert pd.isna(ancho.loc[("002", "a"), q1])
    assert pd.isna(ancho.loc[("001", "b"), q2])
    assert ancho.loc[("001", "a"), q1] == 1.0
    assert ancho.loc[("002", "b"), q2] == 40.0


# ---------- Resultado ----------

def test_resultado_no_instanciable_directamente() -> None:
    with pytest.raises(TypeError):
        Resultado(_df_largo_1col())  # type: ignore[abstract]


def test_resultado_subclase_minima_construye() -> None:
    r = _ResultadoMinimo(_df_largo_1col())
    assert r.df.shape == (2, 1)


def test_resultado_df_vacio_falla() -> None:
    idx = pd.MultiIndex.from_tuples([], names=["periodo", "indice"])
    df_vacio = pd.DataFrame({"x": []}, index=idx)
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df_vacio)


def test_resultado_df_sin_multiindex_falla() -> None:
    df_plano = pd.DataFrame({"x": [1.0, 2.0]})
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df_plano)


def test_resultado_df_multiindex_nombres_incorrectos_falla() -> None:
    idx = pd.MultiIndex.from_tuples([("a", 1), ("b", 2)], names=["foo", "bar"])
    df = pd.DataFrame({"x": [1.0, 2.0]}, index=idx)
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df)


def test_resultado_df_multiindex_nlevels_distinto_de_2_falla() -> None:
    idx = pd.MultiIndex.from_tuples(
        [("p", "i", "extra"), ("p2", "i2", "extra2")],
        names=["periodo", "indice", "extra"],
    )
    df = pd.DataFrame({"x": [1.0, 2.0]}, index=idx)
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df)


def test_resultado_df_multicolumna_falla() -> None:
    df = _df_largo_ncols()
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df)


def test_resultado_df_con_duplicados_falla() -> None:
    p = PeriodoQuincenal(2024, 1, 1)
    idx = pd.MultiIndex.from_tuples([(p, "001"), (p, "001")], names=["periodo", "indice"])
    df = pd.DataFrame({"x": [1.0, 2.0]}, index=idx)
    with pytest.raises(InvarianteViolado):
        _ResultadoMinimo(df)


def test_resultado_df_property_retorna_lo_guardado() -> None:
    df = _df_largo_1col()
    r = _ResultadoMinimo(df)
    assert r.df is df


def test_resultado_pipe_aplica_funcion() -> None:
    r = _ResultadoMinimo(_df_largo_1col())
    assert r.pipe(lambda res: res.df.shape) == (2, 1)


# ---------- Validacion ----------

def test_validacion_no_instanciable_directamente() -> None:
    with pytest.raises(TypeError):
        Validacion()  # type: ignore[abstract]


def test_validacion_subclase_minima_construye() -> None:
    v = _ValidacionMinima()
    assert isinstance(v.resultado, Vista)


def test_validacion_instancia_sin_df_ni_pipe() -> None:
    v = _ValidacionMinima()
    assert hasattr(v, "df") is False
    assert hasattr(v, "pipe") is False


# ---------- ManifestDerivado ----------

def test_manifest_derivado_clase_vacia_falla() -> None:
    with pytest.raises(InvarianteViolado):
        ManifestDerivado(
            id_corrida=["x"],
            tipo="inpc",
            clase="",
            descripcion="",
            fecha=datetime(2024, 1, 1),
        )


def test_manifest_derivado_solo_inpc_ids_falla() -> None:
    with pytest.raises(InvarianteViolado):
        ManifestDerivado(
            id_corrida=["x"],
            tipo="inpc",
            clase="periodica_mensual",
            descripcion="",
            fecha=datetime(2024, 1, 1),
            inpc_ids=None,
            clasificacion_ids=["c"],
        )


def test_manifest_derivado_solo_clasificacion_ids_falla() -> None:
    with pytest.raises(InvarianteViolado):
        ManifestDerivado(
            id_corrida=["x"],
            tipo="inpc",
            clase="periodica_mensual",
            descripcion="",
            fecha=datetime(2024, 1, 1),
            inpc_ids=["x"],
            clasificacion_ids=None,
        )


def test_manifest_derivado_ambos_none_construye() -> None:
    m = ManifestDerivado(
        id_corrida=["x"],
        tipo="inpc",
        clase="periodica_mensual",
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    assert m.inpc_ids is None
    assert m.clasificacion_ids is None


def test_manifest_derivado_ambos_presentes_construye() -> None:
    m = ManifestDerivado(
        id_corrida=["x", "y"],
        tipo="inflacion componente",
        clase="periodica_mensual",
        descripcion="",
        fecha=datetime(2024, 1, 1),
        inpc_ids=["x"],
        clasificacion_ids=["y"],
    )
    assert m.inpc_ids == ["x"]
    assert m.clasificacion_ids == ["y"]


# ---------- ManifestUnidad ----------

def test_manifest_unidad_construccion_valida() -> None:
    m = ManifestUnidad(
        id_corrida="abc",
        version=2018,
        tipo="inpc",
        calculador="LaspeyresDirecto",
        ruta_canasta=Path("/tmp/c.csv"),
        ruta_series=Path("/tmp/s.csv"),
        fecha=datetime(2024, 1, 1),
    )
    assert m.id_corrida == "abc"
