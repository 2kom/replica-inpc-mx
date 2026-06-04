"""Fase 1: indice_incidencia interno + selección por fila en incidencias.

Cubre: los calculadores pueblan indice_incidencia (= i_tramo, antes de factor_h);
a_mensual lo promedia; rebasar lo deja intacto; empalmar lo preserva; las incidencias
lo usan within-canasta (exacto, rebase-invariante) y usan el visible en cross-canasta
(detectable por version_t != version_lag en .reporte, sin columna dedicada).
"""

from __future__ import annotations

from typing import TypeAlias, cast

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.incidencias import (
    _es_content_exact,
    _segmentos_entre,
    incidencia_desde,
    incidencia_periodica,
)
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import LaspeyresEncadenadoT2
from replica_inpc.dominio.conversion import (
    _construir_mapa_renombre,
    a_mensual,
    empalmar,
    rebasar,
)
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
Periodo: TypeAlias = PeriodoQuincenal | PeriodoMensual

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


def _canasta_solo_a(version: int) -> CanastaCanonica:
    """Canasta con solo la categoría A (B es alta inexistente en esta versión)."""
    df = pd.DataFrame(
        {
            "ponderador": ["100.0"],
            "encadenamiento": [float("nan")],
            "inflacion componente": ["A"],
        },
        index=pd.Index(["gen_a"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _canasta_ccif(categoria: str, version: int) -> CanastaCanonica:
    """Canasta de 1 categoría 'CCIF division' con su nombre NATIVO en esa versión."""
    df = pd.DataFrame(
        {
            "ponderador": ["100.0"],
            "encadenamiento": [float("nan")],
            "CCIF division": [categoria],
        },
        index=pd.Index(["gen_a"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _res_inc(
    data_rep: dict[str, list[tuple[Periodo, float | None]]],
    data_inc: dict[str, list[tuple[Periodo, float | None]]],
    *,
    tipo: str,
    id_corrida: str,
    version: int = 2018,
    periodo_referencia: Periodo | None = None,
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
    rows: list[tuple[Periodo, str, int, float, float, str]],
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
    largo = LaspeyresDirecto().calcular(can, serie, "c1", "inpc")._completo
    assert (largo["indice_incidencia"] == largo["indice_replicado"]).all()


def test_t2_indice_incidencia_es_i_tramo() -> None:
    ref = 134.471
    largo = (
        LaspeyresEncadenadoT2({"INPC": ref})
        .calcular(_canasta_t2(), _serie_t2(), "c1", "inpc")
        ._completo
    )
    # i_tramo en el traslape == 100 (serie/f_k = 100 por construcción T2)
    assert largo.at[(_TRASLAPE_T2, "INPC"), "indice_incidencia"] == pytest.approx(100.0)
    # indice_replicado = i_tramo * factor_h, con factor_h = ref/100
    rep = cast(float, largo.at[(_POST_T2, "INPC"), "indice_replicado"])
    inc = cast(float, largo.at[(_POST_T2, "INPC"), "indice_incidencia"])
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
    largo = a_mensual(r)._completo
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
    largo = rebasar(r, _Q1)._completo
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
    largo = empalmar([tramo_a, tramo_b])._completo
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
    inc_a = cast(float, largo.at[(_ENE, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(_ENE, "B"), "incidencia_pp"])
    # calculadas sobre i_tramo (no sobre el visible): 60*(110-100)/100, 40*(90-100)/100
    assert inc_a == pytest.approx(6.0)
    assert inc_b == pytest.approx(-4.0)
    # aditividad exacta: suma == variación del INPC (escala incidencia)
    var = (102.0 / 100.0 - 1) * 100
    assert inc_a + inc_b == pytest.approx(var, abs=1e-10)
    # within-canasta: misma versión en t y lag (no cruza junta), detectable en .reporte
    reporte = r.reporte
    assert reporte.at[(_ENE, "A"), "version_t"] == reporte.at[(_ENE, "A"), "version_lag"]


def test_rebase_within_canasta_invariante() -> None:
    base = incidencia_periodica(
        _inpc_within(), _clas_within(), {2018: _canasta_comp()}, "mensual"
    ).resultado.largo
    inpc_r = rebasar(_inpc_within(), _DIC18)
    clas_r = rebasar(_clas_within(), _DIC18)
    reb = incidencia_periodica(inpc_r, clas_r, {2018: _canasta_comp()}, "mensual").resultado.largo
    for indice in ("A", "B"):
        assert cast(float, reb.at[(_ENE, indice), "incidencia_pp"]) == pytest.approx(
            cast(float, base.at[(_ENE, indice), "incidencia_pp"])
        )


def test_cross_canasta_detectable_y_usa_visible() -> None:
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
    res = incidencia_periodica(inpc, clas, canastas, "mensual")
    largo = res.resultado.largo
    # FEB cruza canastas y es mensual SIN _frontera → cae a cross_sin_frontera: emite el
    # valor VISIBLE (no NaN), detectable por version_t != version_lag y por el marcador.
    reporte = res.reporte
    assert reporte.at[(_FEB, "A"), "version_t"] != reporte.at[(_FEB, "A"), "version_lag"]
    assert reporte.at[(_FEB, "A"), "metodo_incidencia"] == "cross_sin_frontera"
    # usó indice_replicado (visible=142), no i_tramo (100): contribución != 0
    assert cast(float, largo.at[(_FEB, "A"), "incidencia_pp"]) != pytest.approx(0.0)


def test_frontera_version_mixta_detecta_por_fila_no_por_periodo() -> None:
    # FEB es frontera con versiones MIXTAS: A(2018) y B(alta 2024). MAR: ambos 2024.
    # Para (MAR, B) el base es FEB; la versión POR PERIODO (groupby first) tomaría 2018
    # (de A) y buscaría el ponderador de B en la canasta 2018 (no existe) → la fila caería
    # como no computable. La selección POR FILA usa el base real de B en FEB = 2024 →
    # computable con el ponderador 2024, y version_lag correcto.
    feb = PeriodoMensual(2024, 2)
    mar = PeriodoMensual(2024, 3)
    inpc = _res_multi(
        [(feb, "INPC", 2024, 100.0, 100.0, "ok"), (mar, "INPC", 2024, 102.0, 102.0, "ok")],
        tipo="inpc",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (feb, "A", 2018, 100.0, 100.0, "ok"),  # primera fila de feb → groupby first = 2018
            (feb, "B", 2024, 100.0, 100.0, "ok"),  # alta 2024 en la misma frontera
            (mar, "A", 2024, 101.0, 101.0, "ok"),
            (mar, "B", 2024, 104.0, 104.0, "ok"),
        ],
        tipo="inflacion componente",
        id_corrida="cc",
    )
    canastas = {2018: _canasta_solo_a(2018), 2024: _canasta_comp(2024)}
    res = incidencia_periodica(inpc, clas, canastas, "mensual")
    # (mar, B) within-2024 → debe ser COMPUTABLE (el bug per-periodo la tiraba)
    assert (mar, "B") in res.resultado.largo.index
    # etiqueta de versión base correcta (per-fila 2024), no la per-periodo (2018)
    assert res.reporte.at[(mar, "B"), "version_lag"] == 2024


def test_cross_canasta_renombre_alinea_ponderador() -> None:
    # Categoría renombrada entre canastas: el resultado empalmado usa el nombre CANÓNICO
    # (2024), pero el ponderador 2018 se indexa con el nombre NATIVO. Sin alinear vocabularios
    # la fila cross (base 2018) caería como "sin ponderador". El fix renombra el ponderador
    # al vocabulario canónico antes de buscarlo.
    mapa = _construir_mapa_renombre("CCIF division", 2018, 2024)
    nativo_2018, canonico = next((k, v) for k, v in mapa.items() if k != v)
    feb = PeriodoMensual(2024, 2)
    mar = PeriodoMensual(2024, 3)
    inpc = _res_multi(
        [(feb, "INPC", 2018, 100.0, 100.0, "ok"), (mar, "INPC", 2024, 102.0, 102.0, "ok")],
        tipo="inpc",
        id_corrida="ci",
    )
    # clasificación ya normalizada al nombre canónico; versiones mixtas frontera/post
    clas = _res_multi(
        [(feb, canonico, 2018, 100.0, 100.0, "ok"), (mar, canonico, 2024, 104.0, 104.0, "ok")],
        tipo="CCIF division",
        id_corrida="cc",
    )
    canastas = {2018: _canasta_ccif(nativo_2018, 2018), 2024: _canasta_ccif(canonico, 2024)}
    res = incidencia_periodica(inpc, clas, canastas, "mensual")
    # (mar, canonico) es cross (2024 vs base 2018) pero debe ser COMPUTABLE: el ponderador
    # base 2018 se encuentra tras alinear su nombre nativo al canónico del resultado.
    assert (mar, canonico) in res.resultado.largo.index
    assert res.reporte.at[(mar, canonico), "version_lag"] == 2018


def test_vc_inferido_soporta_version_nombres_no_max() -> None:
    # Resultado normalizado al vocabulario 2018 (como empalmar(version_nombres=2018)): los
    # nombres de índice son los NATIVOS de 2018 aunque haya filas versión 2024. `vc` NO puede
    # inferirse como max(version)=2024; se infiere como la versión cuyos nombres caben en su
    # canasta nativa (2018). Si fallara, la fila cross caería como "sin ponderador".
    mapa = _construir_mapa_renombre("CCIF division", 2018, 2024)
    nativo_2018, nativo_2024 = next((k, v) for k, v in mapa.items() if k != v)
    feb = PeriodoMensual(2024, 2)
    mar = PeriodoMensual(2024, 3)
    inpc = _res_multi(
        [(feb, "INPC", 2018, 100.0, 100.0, "ok"), (mar, "INPC", 2024, 102.0, 102.0, "ok")],
        tipo="inpc",
        id_corrida="ci",
    )
    # vocabulario 2018: nombre nativo_2018 incluso en la fila versión 2024
    clas = _res_multi(
        [
            (feb, nativo_2018, 2018, 100.0, 100.0, "ok"),
            (mar, nativo_2018, 2024, 104.0, 104.0, "ok"),
        ],
        tipo="CCIF division",
        id_corrida="cc",
    )
    canastas = {2018: _canasta_ccif(nativo_2018, 2018), 2024: _canasta_ccif(nativo_2024, 2024)}
    res = incidencia_periodica(inpc, clas, canastas, "mensual")
    assert (mar, nativo_2018) in res.resultado.largo.index


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


# -- Fase 2A: incidencia cross-canasta exacta por segmentos ---------------------

_B_Q = PeriodoQuincenal(2024, 6, 2)  # 2018, pre-junta
_E24 = PeriodoQuincenal(2024, 7, 2)  # junta 2018→2024 (la posee 2018)
_T_Q = PeriodoQuincenal(2024, 8, 1)  # 2024, post-junta


def _con_frontera(r: ResultadoIndice, frontera: pd.DataFrame | None) -> ResultadoIndice:
    return ResultadoIndice(
        r._df_completo,
        r.manifiesto,
        r.reporte,
        r.diagnostico,
        periodo_referencia=r.periodo_referencia,
        frontera=frontera,
    )


def _fr(filas: list[tuple[Periodo, str, int, int, float, float]]) -> pd.DataFrame:
    """Construye una tabla `_frontera`. filas = (e, indice, v_old, v_new, inc_old, rep_old)."""
    return pd.DataFrame(
        [
            {
                "periodo": e,
                "indice": ind,
                "version_old": vo,
                "version_new": vn,
                "indice_incidencia_old": inc,
                "indice_replicado_old": rep,
            }
            for e, ind, vo, vn, inc, rep in filas
        ]
    ).set_index(["periodo", "indice"])


def _inpc_cross_2seg(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    """INPC con escala consistente (★) cruzando la junta 2018→2024.

    J_INPC: b=102, e=104, t(2024)=101. visible: b=102, e=104, t=104/100*101=105.04.
    Si `e` es None, omite la fila de junta (caso mensual; va a `_frontera`).
    """
    filas = [(b, "INPC", 2018, 102.0, 102.0, "ok"), (t, "INPC", 2024, 105.04, 101.0, "ok")]
    if e is not None:
        filas.insert(1, (e, "INPC", 2018, 104.0, 104.0, "ok"))
    return _res_multi(filas, tipo="inpc", id_corrida="ci")


def _clas_cross_2seg(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    """Componente A/B consistente con `_inpc_cross_2seg` (w_A=60, w_B=40)."""
    filas = [
        (b, "A", 2018, 110.0, 110.0, "ok"),
        (b, "B", 2018, 90.0, 90.0, "ok"),
        (t, "A", 2024, 109.2, 105.0, "ok"),  # 105 * 1.04
        (t, "B", 2024, 98.8, 95.0, "ok"),  # 95 * 1.04
    ]
    if e is not None:
        filas[2:2] = [(e, "A", 2018, 120.0, 120.0, "ok"), (e, "B", 2018, 80.0, 80.0, "ok")]
    return _res_multi(filas, tipo="inflacion componente", id_corrida="cc")


def test_cross_segmentado_quincenal_es_aditivo() -> None:
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _clas_cross_2seg(_B_Q, _E24, _T_Q)
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=_B_Q, hasta=_T_Q)
    largo = res.resultado.largo
    inc_a = cast(float, largo.at[(_T_Q, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(_T_Q, "B"), "incidencia_pp"])
    assert inc_a == pytest.approx(912 / 102)
    assert inc_b == pytest.approx(-608 / 102)
    var = (105.04 / 102 - 1) * 100
    assert inc_a + inc_b == pytest.approx(var, abs=1e-9)
    assert res.reporte.at[(_T_Q, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_segmentado_periodica_quincenal_base_junta() -> None:
    # incidencia_periodica quincenal: base de _T_Q = _E24 (la junta). b==e → seg1=0.
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _clas_cross_2seg(_B_Q, _E24, _T_Q)
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_periodica(inpc, clas, canastas, "quincenal")
    largo = res.resultado.largo
    suma = cast(float, largo.at[(_T_Q, "A"), "incidencia_pp"]) + cast(
        float, largo.at[(_T_Q, "B"), "incidencia_pp"]
    )
    var = (105.04 / 104 - 1) * 100  # vs la junta
    assert suma == pytest.approx(var, abs=1e-9)
    assert res.reporte.at[(_T_Q, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_segmentado_mensual_con_frontera() -> None:
    jun, ago = PeriodoMensual(2024, 6), PeriodoMensual(2024, 8)
    inpc = _con_frontera(
        _inpc_cross_2seg(jun, None, ago),
        _fr([(_E24, "INPC", 2018, 2024, 104.0, 104.0)]),
    )
    clas = _con_frontera(
        _clas_cross_2seg(jun, None, ago),
        _fr(
            [
                (_E24, "A", 2018, 2024, 120.0, float("nan")),
                (_E24, "B", 2018, 2024, 80.0, float("nan")),
            ]
        ),
    )
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=jun, hasta=ago)
    largo = res.resultado.largo
    inc_a = cast(float, largo.at[(ago, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(ago, "B"), "incidencia_pp"])
    assert inc_a == pytest.approx(912 / 102)
    assert inc_b == pytest.approx(-608 / 102)
    assert inc_a + inc_b == pytest.approx((105.04 / 102 - 1) * 100, abs=1e-9)
    assert res.reporte.at[(ago, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_mensual_sin_frontera_emite_visible() -> None:
    jun, ago = PeriodoMensual(2024, 6), PeriodoMensual(2024, 8)
    inpc = _inpc_cross_2seg(jun, None, ago)  # sin _frontera
    clas = _clas_cross_2seg(jun, None, ago)
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=jun, hasta=ago)
    largo = res.resultado.largo
    assert res.reporte.at[(ago, "A"), "metodo_incidencia"] == "cross_sin_frontera"
    # valor visible (no segmentado): 60*(109.2-110)/102, NO 912/102
    assert cast(float, largo.at[(ago, "A"), "incidencia_pp"]) == pytest.approx(
        60 * (109.2 - 110) / 102
    )


def test_rebase_mensual_preserva_cross_segmentado() -> None:
    jun, ago = PeriodoMensual(2024, 6), PeriodoMensual(2024, 8)
    inpc = _con_frontera(
        _inpc_cross_2seg(jun, None, ago), _fr([(_E24, "INPC", 2018, 2024, 104.0, 104.0)])
    )
    clas = _con_frontera(
        _clas_cross_2seg(jun, None, ago),
        _fr(
            [
                (_E24, "A", 2018, 2024, 120.0, float("nan")),
                (_E24, "B", 2018, 2024, 80.0, float("nan")),
            ]
        ),
    )
    inpc_r = rebasar(inpc, jun)  # k_INPC = 100/102; reescala INPC_visible y su frontera
    clas_r = rebasar(clas, jun)  # k_K propios; preserva indice_incidencia_old
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc_r, clas_r, canastas, desde=jun, hasta=ago)
    largo = res.resultado.largo
    # Σ inc == var SIGUE sosteniéndose tras el rebase (k cancela en S_m).
    suma = cast(float, largo.at[(ago, "A"), "incidencia_pp"]) + cast(
        float, largo.at[(ago, "B"), "incidencia_pp"]
    )
    assert suma == pytest.approx(304 / 102, abs=1e-9)
    assert res.reporte.at[(ago, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_tres_segmentos_aditivo() -> None:
    # Rango 2013 → 2024 cruza 2 juntas (2QJul2018, 2QJul2024): 3 segmentos, Σ_m S_m.
    # El tramo 2013 es el PRIMER segmento (lado viejo, J de dato) → exacto, NO cross_t1_diferido.
    b = PeriodoQuincenal(2018, 1, 2)  # 2013
    e1 = PeriodoQuincenal(2018, 7, 2)  # junta 2013→2018
    e2 = PeriodoQuincenal(2024, 7, 2)  # junta 2018→2024
    t = PeriodoQuincenal(2024, 8, 1)  # 2024
    inpc = _res_multi(
        [
            (b, "INPC", 2013, 102.0, 102.0, "ok"),
            (e1, "INPC", 2013, 104.0, 104.0, "ok"),
            (e2, "INPC", 2018, 108.16, 104.0, "ok"),  # vis = 104 * 1.04
            (t, "INPC", 2024, 109.2416, 101.0, "ok"),  # vis = 101 * 1.0816
        ],
        tipo="inpc",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (b, "A", 2013, 110.0, 110.0, "ok"),
            (b, "B", 2013, 90.0, 90.0, "ok"),
            (e1, "A", 2013, 120.0, 120.0, "ok"),
            (e1, "B", 2013, 80.0, 80.0, "ok"),
            (e2, "A", 2018, 124.8, 120.0, "ok"),  # 120 * 1.04
            (e2, "B", 2018, 83.2, 80.0, "ok"),
            (t, "A", 2024, 113.568, 105.0, "ok"),  # 105 * 1.0816
            (t, "B", 2024, 102.752, 95.0, "ok"),
        ],
        tipo="inflacion componente",
        id_corrida="cc",
    )
    canastas = {2013: _canasta_comp(2013), 2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=b, hasta=t)
    largo = res.resultado.largo
    suma = cast(float, largo.at[(t, "A"), "incidencia_pp"]) + cast(
        float, largo.at[(t, "B"), "incidencia_pp"]
    )
    var = (109.2416 / 102 - 1) * 100
    assert suma == pytest.approx(var, abs=1e-9)
    # 2013 es el primer segmento (lado viejo, J de dato) → exacto, no aprox.
    assert res.reporte.at[(t, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_t1_diferido_cruza_2010_2013() -> None:
    # Rango 2010 → 2013 cruza la junta 2Q Mar 2013: el tramo 2013 (T1) es el LADO NUEVO,
    # pero su i_tramo NO ancla en 100 (el contrato J(e)=100 es solo de directo/T2). La
    # segmentación no aplica → cae al visible (Fase 1) marcado cross_t1_diferido. Exacto → 2B.
    b = PeriodoQuincenal(2013, 1, 2)  # 2010, pre-junta
    e = PeriodoQuincenal(2013, 3, 2)  # junta 2010→2013 (la posee 2010)
    t = PeriodoQuincenal(2013, 4, 1)  # 2013, post-junta
    inpc = _res_multi(
        [
            (b, "INPC", 2010, 102.0, 102.0, "ok"),
            (e, "INPC", 2010, 104.0, 104.0, "ok"),
            (t, "INPC", 2013, 105.04, 101.0, "ok"),
        ],
        tipo="inpc",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (b, "A", 2010, 110.0, 110.0, "ok"),
            (b, "B", 2010, 90.0, 90.0, "ok"),
            (e, "A", 2010, 120.0, 120.0, "ok"),
            (e, "B", 2010, 80.0, 80.0, "ok"),
            (t, "A", 2013, 109.2, 105.0, "ok"),
            (t, "B", 2013, 98.8, 95.0, "ok"),
        ],
        tipo="inflacion componente",
        id_corrida="cc",
    )
    canastas = {2010: _canasta_comp(2010), 2013: _canasta_comp(2013)}
    res = incidencia_desde(inpc, clas, canastas, desde=b, hasta=t)
    largo = res.resultado.largo
    assert res.reporte.at[(t, "A"), "metodo_incidencia"] == "cross_t1_diferido"
    # emite el VISIBLE (Fase 1), NO el segmentado: 60*(109.2-110)/102 con ponderador base 2010.
    assert cast(float, largo.at[(t, "A"), "incidencia_pp"]) == pytest.approx(
        60 * (109.2 - 110) / 102
    )


def _canasta_cb(version: int) -> CanastaCanonica:
    """Canasta 'canasta basica' content-exact (mismas categorías ambas versiones)."""
    df = pd.DataFrame(
        {
            "ponderador": ["60.0", "40.0"],
            "encadenamiento": [float("nan"), float("nan")],
            "canasta basica": ["dentro", "fuera"],
        },
        index=pd.Index(["gen_a", "gen_b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def test_cross_segmentado_tipo_content_exact_no_componente() -> None:
    # Alcance ampliado (decisión usuario, opción B): cualquier tipo content-exact obtiene
    # segmentación exacta, no solo componente/subcomponente. 'canasta basica' es content-exact
    # con los CSV reales → cross_segmentado. (Sin indicador BIE; exactitud algebraica.)
    canastas = {2018: _canasta_cb(2018), 2024: _canasta_cb(2024)}
    assert _es_content_exact("canasta basica", canastas) is True
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _res_multi(
        [
            (_B_Q, "dentro", 2018, 110.0, 110.0, "ok"),
            (_B_Q, "fuera", 2018, 90.0, 90.0, "ok"),
            (_E24, "dentro", 2018, 120.0, 120.0, "ok"),
            (_E24, "fuera", 2018, 80.0, 80.0, "ok"),
            (_T_Q, "dentro", 2024, 109.2, 105.0, "ok"),
            (_T_Q, "fuera", 2024, 98.8, 95.0, "ok"),
        ],
        tipo="canasta basica",
        id_corrida="cc",
    )
    res = incidencia_desde(inpc, clas, canastas, desde=_B_Q, hasta=_T_Q)
    largo = res.resultado.largo
    suma = cast(float, largo.at[(_T_Q, "dentro"), "incidencia_pp"]) + cast(
        float, largo.at[(_T_Q, "fuera"), "incidencia_pp"]
    )
    assert suma == pytest.approx((105.04 / 102 - 1) * 100, abs=1e-9)
    assert res.reporte.at[(_T_Q, "dentro"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_visible_no_content_exact() -> None:
    # tipo no content-exact (un genérico cruza de categoría) → cross_visible (Fase 1).
    can2018 = CanastaCanonica(
        pd.DataFrame(
            {
                "ponderador": ["60.0", "40.0"],
                "encadenamiento": [None, None],
                "SCIAN rama": ["X", "Y"],
            },
            index=["g1", "g2"],
        ),
        2018,
    )
    can2024 = CanastaCanonica(
        pd.DataFrame(
            {
                "ponderador": ["60.0", "40.0"],
                "encadenamiento": [None, None],
                "SCIAN rama": ["Y", "X"],
            },
            index=["g1", "g2"],  # g1 cruza X→Y: NO content-exact
        ),
        2024,
    )
    assert _es_content_exact("SCIAN rama", {2018: can2018, 2024: can2024}) is False
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _res_multi(
        [
            (_B_Q, "X", 2018, 110.0, 110.0, "ok"),
            (_E24, "X", 2018, 120.0, 120.0, "ok"),
            (_T_Q, "X", 2024, 109.2, 105.0, "ok"),
        ],
        tipo="SCIAN rama",
        id_corrida="cc",
    )
    res = incidencia_desde(inpc, clas, {2018: can2018, 2024: can2024}, desde=_B_Q, hasta=_T_Q)
    assert res.reporte.at[(_T_Q, "X"), "metodo_incidencia"] == "cross_visible"


def test_es_content_exact_componente_true() -> None:
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    assert _es_content_exact("inflacion componente", canastas) is True


def test_es_content_exact_categoria_distinta_false() -> None:
    # conjunto de categorías distinto entre versiones → no content-exact.
    can2018 = _canasta_comp(2018)  # {A, B}
    can2024 = _canasta_solo_a(2024)  # {A}
    assert _es_content_exact("inflacion componente", {2018: can2018, 2024: can2024}) is False


def test_segmentos_entre_dos_y_tres_segmentos() -> None:
    dos = _segmentos_entre(2018, 2024, _B_Q, _T_Q)
    assert [s[0] for s in dos] == [2018, 2024]
    assert dos[0][2] == PeriodoQuincenal(2024, 7, 2)  # fin seg1 = junta
    assert dos[1][3] is True  # inicio seg2 es junta nueva
    tres = _segmentos_entre(2013, 2024, _B_Q, _T_Q)
    assert [s[0] for s in tres] == [2013, 2018, 2024]


def test_segmentos_entre_sin_cruce_lanza() -> None:
    with pytest.raises(InvarianteViolado):
        _segmentos_entre(2024, 2024, _B_Q, _T_Q)
    with pytest.raises(InvarianteViolado):
        _segmentos_entre(2024, 2018, _T_Q, _B_Q)


def test_metodo_incidencia_no_en_largo_si_en_reporte() -> None:
    res = incidencia_periodica(_inpc_within(), _clas_within(), {2018: _canasta_comp()}, "mensual")
    assert "metodo_incidencia" not in res.resultado.largo.columns
    assert "metodo_incidencia" in res.reporte.columns
    assert res.reporte.at[(_ENE, "A"), "metodo_incidencia"] == "within"
