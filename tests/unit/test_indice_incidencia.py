"""Fase 1: indice_incidencia interno + selección por fila en incidencias.

Cubre: los calculadores pueblan indice_incidencia (= i_tramo, antes de factor_h);
a_mensual lo promedia; rebasar lo deja intacto; empalmar lo preserva; y las
incidencias lo usan within-canasta (exacto, rebase-invariante) y marcan cross-canasta.
"""

from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.incidencias import incidencia_periodica
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import LaspeyresEncadenadoT2
from replica_inpc.dominio.conversion import a_mensual, empalmar, rebasar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestUnidad

# -- periodos ------------------------------------------------------------------

_Q1 = PeriodoQuincenal(2024, 1, 1)
_Q2 = PeriodoQuincenal(2024, 1, 2)
_TRASLAPE_T2 = PeriodoQuincenal(2024, 7, 2)
_POST_T2 = PeriodoQuincenal(2024, 8, 1)
_DIC18 = PeriodoMensual(2018, 12)
_ENE = PeriodoMensual(2019, 1)
_FEB = PeriodoMensual(2019, 2)

# -- helpers -------------------------------------------------------------------


def _canasta_comp(version: int = 2018) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["60.0", "40.0"],
            "encadenamiento": [float("nan"), float("nan")],
            "inflacion componente": ["A", "B"],
        },
        index=pd.Index(["gen_a", "gen_b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _res_inc(
    data_rep: dict[str, list[tuple[object, float | None]]],
    data_inc: dict[str, list[tuple[object, float | None]]],
    *,
    tipo: str,
    id_corrida: str,
    version: int = 2018,
    periodo_referencia: object | None = None,
) -> ResultadoIndice:
    """ResultadoIndice con indice_replicado e indice_incidencia separados (1 versión)."""
    rows = []
    for indice in data_rep:
        for (periodo, rep), (_, inc) in zip(data_rep[indice], data_inc[indice]):
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if rep is None else float(rep),
                    "indice_incidencia": float("nan") if inc is None else float(inc),
                    "estado_calculo": "ok" if rep is not None else "sin_datos",
                    "motivo_error": None,
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = [ManifestUnidad(id_corrida, version, tipo, "LaspeyresEncadenadoT2")]  # type: ignore[arg-type]
    reporte = pd.DataFrame(
        {"version": version, "estado_calculo": df["estado_calculo"].to_numpy()},
        index=df.index,
    )
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame(), periodo_referencia)


def _res_multi(
    rows: list[tuple[object, str, int, float, float, str]],
    *,
    tipo: str,
    id_corrida: str,
) -> ResultadoIndice:
    """ResultadoIndice multi-versión. rows = (periodo, indice, version, rep, inc, estado)."""
    filas = [
        {
            "periodo": p,
            "indice": i,
            "version": v,
            "tipo": tipo,
            "indice_replicado": rep,
            "indice_incidencia": inc,
            "estado_calculo": est,
        }
        for p, i, v, rep, inc, est in rows
    ]
    df = pd.DataFrame(filas).set_index(["periodo", "indice"])
    versiones = {v for _, _, v, _, _, _ in rows}
    manifiesto = [ManifestUnidad(id_corrida, v, tipo, "LaspeyresDirecto") for v in versiones]  # type: ignore[arg-type]
    return ResultadoIndice(df, manifiesto, pd.DataFrame(), pd.DataFrame())


def _canasta_t2() -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": ["1.5", "1.4", "1.6", "1.3"],
        },
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
        index=[_TRASLAPE_T2, _POST_T2],
    ).T
    return SerieNormalizada(df, {g: g.capitalize() for g in df.index})


# -- calculadores pueblan indice_incidencia ------------------------------------


def test_directo_indice_incidencia_igual_replicado() -> None:
    can = CanastaCanonica(
        pd.DataFrame(
            {"ponderador": ["60.0", "40.0"], "encadenamiento": [None, None]},
            index=["gen_a", "gen_b"],
        ),
        2018,
    )
    serie = SerieNormalizada(
        pd.DataFrame({"gen_a": [100.0, 110.0], "gen_b": [100.0, 90.0]}, index=[_Q1, _Q2]).T,
        {"gen_a": "gen_a", "gen_b": "gen_b"},
    )
    largo = LaspeyresDirecto().calcular(can, serie, "c1", "inpc").resultado.largo
    assert (largo["indice_incidencia"] == largo["indice_replicado"]).all()


def test_t2_indice_incidencia_es_i_tramo() -> None:
    ref = 134.471
    largo = (
        LaspeyresEncadenadoT2({"INPC": ref})
        .calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")
        .resultado.largo
    )
    # i_tramo en el traslape == 100 (serie/f_k = 100 por construcción T2)
    assert largo.at[(_TRASLAPE_T2, "INPC"), "indice_incidencia"] == pytest.approx(100.0)
    # indice_replicado = i_tramo * factor_h, con factor_h = ref/100
    rep = largo.at[(_POST_T2, "INPC"), "indice_replicado"]
    inc = largo.at[(_POST_T2, "INPC"), "indice_incidencia"]
    assert rep == pytest.approx(inc * ref / 100.0)
    assert rep != pytest.approx(inc)  # factor_h != 1 → visible difiere del crudo


# -- conversion ----------------------------------------------------------------


def test_a_mensual_promedia_indice_incidencia() -> None:
    r = _res_inc(
        {"INPC": [(_Q1, 150.0), (_Q2, 153.0)]},
        {"INPC": [(_Q1, 100.0), (_Q2, 102.0)]},
        tipo="inpc",
        id_corrida="ci",
        version=2024,
    )
    largo = a_mensual(r).resultado.largo
    ene = PeriodoMensual(2024, 1)
    assert largo.at[(ene, "INPC"), "indice_replicado"] == pytest.approx(151.5)
    assert largo.at[(ene, "INPC"), "indice_incidencia"] == pytest.approx(101.0)


def test_rebasar_no_toca_indice_incidencia() -> None:
    r = _res_inc(
        {"INPC": [(_Q1, 150.0), (_Q2, 300.0)]},
        {"INPC": [(_Q1, 90.0), (_Q2, 180.0)]},
        tipo="inpc",
        id_corrida="ci",
        version=2024,
    )
    largo = rebasar(r, _Q1).resultado.largo
    # indice_replicado reescalado (factor 100/150)
    assert largo.at[(_Q1, "INPC"), "indice_replicado"] == pytest.approx(100.0)
    assert largo.at[(_Q2, "INPC"), "indice_replicado"] == pytest.approx(200.0)
    # indice_incidencia INTACTO (no reescalado)
    assert largo.at[(_Q1, "INPC"), "indice_incidencia"] == pytest.approx(90.0)
    assert largo.at[(_Q2, "INPC"), "indice_incidencia"] == pytest.approx(180.0)


def test_empalmar_preserva_indice_incidencia() -> None:
    p1 = PeriodoQuincenal(2024, 1, 1)
    p2 = PeriodoQuincenal(2024, 1, 2)  # frontera
    p3 = PeriodoQuincenal(2024, 2, 1)
    tramo_a = _res_inc(
        {"INPC": [(p1, 150.0), (p2, 153.0)]},
        {"INPC": [(p1, 100.0), (p2, 102.0)]},
        tipo="inpc",
        id_corrida="a",
        version=2024,
    )
    tramo_b = _res_inc(
        {"INPC": [(p2, 153.0), (p3, 156.0)]},
        {"INPC": [(p2, 102.0), (p3, 104.0)]},
        tipo="inpc",
        id_corrida="b",
        version=2024,
    )
    largo = empalmar([tramo_a, tramo_b]).resultado.largo
    assert largo.at[(p1, "INPC"), "indice_incidencia"] == pytest.approx(100.0)
    assert largo.at[(p3, "INPC"), "indice_incidencia"] == pytest.approx(104.0)


# -- incidencias: within-canasta usa indice_incidencia -------------------------


def _inpc_within() -> ResultadoIndice:
    # visible = i_tramo * 1.3 ; i_tramo: DIC=100, ENE=102
    return _res_inc(
        {"INPC": [(_DIC18, 130.0), (_ENE, 132.6)]},
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="inpc",
        id_corrida="ci",
    )


def _clas_within() -> ResultadoIndice:
    # factor_h por categoría DISTINTO (A*1.5, B*2.0) — rompería la suma si se usara visible
    return _res_inc(
        {"A": [(_DIC18, 150.0), (_ENE, 165.0)], "B": [(_DIC18, 200.0), (_ENE, 180.0)]},
        {"A": [(_DIC18, 100.0), (_ENE, 110.0)], "B": [(_DIC18, 100.0), (_ENE, 90.0)]},
        tipo="inflacion componente",
        id_corrida="cc",
    )


def test_within_canasta_usa_indice_incidencia_y_es_aditivo() -> None:
    r = incidencia_periodica(_inpc_within(), _clas_within(), {2018: _canasta_comp()}, "mensual")
    largo = r.resultado.largo
    inc_a = largo.loc[(_ENE, "A"), "incidencia_pp"]
    inc_b = largo.loc[(_ENE, "B"), "incidencia_pp"]
    # calculadas sobre i_tramo (no sobre el visible): 60*(110-100)/100, 40*(90-100)/100
    assert inc_a == pytest.approx(6.0)
    assert inc_b == pytest.approx(-4.0)
    # aditividad exacta: suma == variación del INPC (escala incidencia)
    var = (102.0 / 100.0 - 1) * 100
    assert inc_a + inc_b == pytest.approx(var, abs=1e-10)
    # marcado como within / exacto
    assert not bool(largo.loc[(_ENE, "A"), "es_cross_canasta"])
    assert largo.loc[(_ENE, "A"), "garantia_aditiva"] == "exacta"


def test_rebase_within_canasta_invariante() -> None:
    base = incidencia_periodica(
        _inpc_within(), _clas_within(), {2018: _canasta_comp()}, "mensual"
    ).resultado.largo
    inpc_r = rebasar(_inpc_within(), _DIC18)
    clas_r = rebasar(_clas_within(), _DIC18)
    reb = incidencia_periodica(inpc_r, clas_r, {2018: _canasta_comp()}, "mensual").resultado.largo
    for indice in ("A", "B"):
        assert reb.loc[(_ENE, indice), "incidencia_pp"] == pytest.approx(
            base.loc[(_ENE, indice), "incidencia_pp"]
        )


def test_cross_canasta_marcado_y_usa_visible() -> None:
    # ENE en 2018, FEB en 2024 → la comparación FEB vs ENE cruza canastas.
    inpc = _res_multi(
        [(_ENE, "INPC", 2018, 100.0, 100.0, "ok"), (_FEB, "INPC", 2024, 142.0, 100.0, "ok")],
        tipo="inpc",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (_ENE, "A", 2018, 100.0, 100.0, "ok"),
            (_FEB, "A", 2024, 142.0, 100.0, "ok"),
            (_ENE, "B", 2018, 100.0, 100.0, "ok"),
            (_FEB, "B", 2024, 142.0, 100.0, "ok"),
        ],
        tipo="inflacion componente",
        id_corrida="cc",
    )
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    largo = incidencia_periodica(inpc, clas, canastas, "mensual").resultado.largo
    # solo FEB es computable (ENE no tiene base) y cruza canastas
    assert bool(largo.loc[(_FEB, "A"), "es_cross_canasta"])
    assert largo.loc[(_FEB, "A"), "garantia_aditiva"] == "no_garantizada"
    # usó indice_replicado (visible=142), no i_tramo (100): contribución != 0
    assert largo.loc[(_FEB, "A"), "incidencia_pp"] != pytest.approx(0.0)


def test_periodica_verifica_periodo_referencia() -> None:
    inpc = _res_inc(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="inpc",
        id_corrida="ci",
        periodo_referencia=_ENE,
    )
    clas = _clas_within()  # periodo_referencia = None
    with pytest.raises(InvarianteViolado):
        incidencia_periodica(inpc, clas, {2018: _canasta_comp()}, "mensual")
