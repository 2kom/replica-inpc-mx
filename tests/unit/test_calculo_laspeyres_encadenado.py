from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import (
    LaspeyresEncadenadoT1,
    LaspeyresEncadenadoT2,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

# ---------- T2 (v2024) ----------

_traslape_t2 = PeriodoQuincenal(2024, 7, 2)
_post_t2 = PeriodoQuincenal(2024, 8, 1)


def _canasta_t2(encadenamiento: list[str | None] | None = None) -> CanastaCanonica:
    enc = encadenamiento if encadenamiento is not None else ["1.5", "1.4", "1.6", "1.3"]
    df = pd.DataFrame(
        {"ponderador": ["10.0", "20.0", "30.0", "40.0"], "encadenamiento": enc},
        index=["arroz", "frijol", "leche", "huevo"],
    )
    return CanastaCanonica(df, 2024)


def _serie_t2() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [150.0, 151.5],
            "frijol": [140.0, 144.2],
            "leche": [160.0, 168.0],
            "huevo": [130.0, 132.6],
        },
        index=[_traslape_t2, _post_t2],
    ).T
    return SerieNormalizada(df, {g: g.capitalize() for g in df.index})


_F_H_T2 = (10 * 1.5 + 20 * 1.4 + 30 * 1.6 + 40 * 1.3) / 100


def test_t2_traslape_es_fh_por_100_sin_referencia() -> None:
    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")
    valor = r.df.at[(_traslape_t2, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(_F_H_T2 * 100)


def test_t2_difiere_de_directo() -> None:
    enc = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")
    directo = LaspeyresDirecto().calcular(
        CanastaCanonica(
            pd.DataFrame(
                {
                    "ponderador": ["10.0", "20.0", "30.0", "40.0"],
                    "encadenamiento": [None, None, None, None],
                },
                index=["arroz", "frijol", "leche", "huevo"],
            ),
            2018,
        ),
        _serie_t2(),
        "c2",
        "inpc",
    )
    val_enc = enc.df.at[(_post_t2, "INPC"), "indice_replicado"]
    val_dir = directo.df.at[(_post_t2, "INPC"), "indice_replicado"]
    assert val_enc != pytest.approx(val_dir)


def test_t2_con_referencia_ancla_traslape_en_ref() -> None:
    ref = 134.471
    r = LaspeyresEncadenadoT2({"INPC": ref}).calcular(
        _canasta_t2(), _serie_t2(), "c1", "inpc"
    )
    # factor_h = ref/100, i_tramo[traslape] = 100 (porque serie/f_k = 100 en traslape)
    valor = r.df.at[(_traslape_t2, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(ref)


def test_t2_fk_desde_serie_igual_a_desde_canasta() -> None:
    r_can = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")
    r_ser = LaspeyresEncadenadoT2().calcular(
        _canasta_t2([None, None, None, None]), _serie_t2(), "c1", "inpc"
    )
    assert r_can.df["indice_replicado"].tolist() == pytest.approx(
        r_ser.df["indice_replicado"].tolist()
    )


def test_t2_manifiesto() -> None:
    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "cX", "inpc")
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresEncadenadoT2"
    assert m.version == 2024


def test_t2_rechaza_canasta_no_2024() -> None:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": ["1.5", "1.4", "1.6", "1.3"],
        },
        index=["arroz", "frijol", "leche", "huevo"],
    )
    canasta_2013 = CanastaCanonica(df, 2013)
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT2().calcular(canasta_2013, _serie_t2(), "c1", "inpc")


# ---------- T1 (v2013) ----------

_traslape_t1 = PeriodoQuincenal(2013, 3, 2)
_post_t1 = PeriodoQuincenal(2013, 4, 1)


def _canasta_t1() -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": ["1.2", "0.8", "1.1", "0.9"],
        },
        index=["arroz", "frijol", "leche", "huevo"],
    )
    return CanastaCanonica(df, 2013)


def _serie_t1() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [120.0, 123.0],
            "frijol": [80.0, 82.0],
            "leche": [110.0, 113.0],
            "huevo": [90.0, 91.5],
        },
        index=[_traslape_t1, _post_t1],
    ).T
    return SerieNormalizada(df, {g: g.capitalize() for g in df.index})


def test_t1_sin_referencia_factor_h_es_1() -> None:
    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "c1", "inpc")
    f_k = _canasta_t1().df["encadenamiento"].astype(float)
    pond = _canasta_t1().df["ponderador"].astype(float)
    serie_div = _serie_t1().df.divide(f_k, axis=0)
    esperado = (serie_div[_traslape_t1] * pond).sum() / pond.sum()
    valor = r.df.at[(_traslape_t1, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(esperado)


def test_t1_con_referencia_ancla_traslape() -> None:
    ref = 109.172
    r = LaspeyresEncadenadoT1({"INPC": ref}).calcular(
        _canasta_t1(), _serie_t1(), "c1", "inpc"
    )
    valor = r.df.at[(_traslape_t1, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(ref)


def test_t1_manifiesto() -> None:
    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "cZ", "inpc")
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresEncadenadoT1"
    assert m.version == 2013


def test_t1_rechaza_canasta_no_2013() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT1().calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")


def test_t1_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "c1", "no_existe")


def test_t2_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "c1", "no_existe")
