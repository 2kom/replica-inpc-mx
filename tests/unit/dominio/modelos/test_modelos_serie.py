from __future__ import annotations

from typing import Any, cast

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

_GENERICOS = ("arroz", "frijol", "leche")
_PERIODOS = (
    PeriodoQuincenal(2018, 7, 2),
    PeriodoQuincenal(2018, 8, 1),
    PeriodoQuincenal(2018, 8, 2),
)
_VALORES = (
    (100.0, 101.0, 102.0),
    (100.0, 102.0, 104.0),
    (100.0, None, 106.0),
)


def _df(
    genericos: tuple[str, ...] = _GENERICOS,
    periodos: tuple[PeriodoQuincenal, ...] = _PERIODOS,
    valores: tuple[tuple[float | None, ...], ...] = _VALORES,
) -> pd.DataFrame:
    return pd.DataFrame(
        list(valores),
        index=pd.Index(list(genericos), name="generico"),
        columns=list(periodos),
    )


# ---------- Construcción ----------


def test_construccion_valida() -> None:
    s = SerieNormalizada(_df())
    assert list(s.df.index) == list(_GENERICOS)


# ---------- Invariantes ----------


def test_indice_duplicado_falla() -> None:
    df = _df(genericos=("arroz", "arroz", "leche"))
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_indice_con_cadena_vacia_falla() -> None:
    df = _df(genericos=("arroz", "", "leche"))
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_sin_columnas_falla() -> None:
    df = pd.DataFrame(index=pd.Index(list(_GENERICOS), name="generico"))
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_columna_no_periodo_quincenal_falla() -> None:
    df = _df()
    df.columns = cast(Any, ["no_es_periodo", *list(_PERIODOS[1:])])
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_columnas_periodo_duplicadas_falla() -> None:
    df = _df(periodos=(_PERIODOS[0], _PERIODOS[0], _PERIODOS[2]))
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_valores_negativos_falla() -> None:
    df = _df(valores=((100.0, -1.0, 102.0), (100.0, 102.0, 104.0), (100.0, None, 106.0)))
    with pytest.raises(InvarianteViolado):
        SerieNormalizada(df)


def test_valores_con_nan_no_falla() -> None:
    SerieNormalizada(_df())


# ---------- Properties ----------


def test_columnas_desordenadas_se_ordenan_cronologicamente() -> None:
    # calculo/base.py rellena NaN con bfill/ffill por posición física de columna —
    # si SerieNormalizada no ordena, el relleno propaga el dato del vecino físico
    # equivocado en vez del cronológico.
    periodos_desordenados = (_PERIODOS[0], _PERIODOS[2], _PERIODOS[1])
    df = _df(periodos=periodos_desordenados)
    s = SerieNormalizada(df)
    pd.testing.assert_frame_equal(s.df, df.sort_index(axis=1))


def test_repr_html_devuelve_string() -> None:
    s = SerieNormalizada(_df())
    assert isinstance(s._repr_html_(), str)
