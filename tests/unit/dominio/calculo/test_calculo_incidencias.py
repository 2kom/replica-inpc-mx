"""Contrato de incidencia_periodica/_acumulada_anual/_desde: indice_incidencia interno,
selección de escala por fila, y segmentación cross-canasta exacta.

Los calculadores pueblan indice_incidencia (= i_tramo, antes de factor_h); a_mensual lo
promedia; rebasar lo deja intacto; empalmar lo preserva. Las incidencias lo usan
within-canasta (exacto, rebase-invariante) y, cruzando canasta, descomponen por segmentos
derivando el ancla del lado nuevo de cada junta por continuidad del visible — exacto para
las 3 juntas. Los tipos no content-exact caen al visible (cross_visible).

Varios fixtures dan a cada categoría su PROPIO factor de encadenamiento, distinto del
factor del INPC. No es cosmético: con factores uniformes no hay no-aditividad que
corregir, el visible coincide con el segmentado y el test deja de distinguir un método
del otro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeAlias, cast

import pandas as pd
import pytest

import replica_inpc as rep
from replica_inpc.dominio.calculo.incidencias import (
    _es_content_exact,
    _segmentos_entre,
    incidencia_acumulada_anual,
    incidencia_desde,
    incidencia_periodica,
)
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import LaspeyresEncadenadoT2
from replica_inpc.dominio.calculo.variaciones import variacion_periodica
from replica_inpc.dominio.conversion import a_mensual, empalmar, rebasar
from replica_inpc.dominio.correspondencia_canastas import _construir_mapa_renombre
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo

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


def _indice(
    data: dict[str, list[tuple[object, float | None]]],
    *,
    tipo: str,
    id_corrida: str,
    version: int = 2018,
    estados: dict[tuple[object, str], str] | None = None,
    periodo_referencia: Periodo | None = None,
) -> ResultadoIndice:
    rows = []
    for indice, pares in data.items():
        for periodo, valor in pares:
            est = "ok" if valor is not None else "sin_datos"
            if estados and (periodo, indice) in estados:
                est = estados[(periodo, indice)]
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if valor is None else float(valor),
                    "estado_calculo": est,
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = [ManifestCalculo(version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
    return ResultadoIndice(df, manifiesto, pd.DataFrame(), pd.DataFrame(), periodo_referencia)


def _inpc(estados: dict[tuple[object, str], str] | None = None) -> ResultadoIndice:
    # INPC = (60*I_A + 40*I_B) / 100 — consistente con la canasta.
    return _indice(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0), (_FEB, 104.0)]},
        tipo="INPC",
        id_corrida="ci",
        estados=estados,
    )


def _clas(estados: dict[tuple[object, str], str] | None = None) -> ResultadoIndice:
    return _indice(
        {
            "A": [(_DIC18, 100.0), (_ENE, 110.0), (_FEB, 120.0)],
            "B": [(_DIC18, 100.0), (_ENE, 90.0), (_FEB, 80.0)],
        },
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
        estados=estados,
    )


def _clas_b_sin_dic() -> ResultadoIndice:
    """Clasificación donde el genérico 'B' no tiene dato en `_DIC18`."""
    return _indice(
        {
            "A": [(_DIC18, 100.0), (_ENE, 110.0), (_FEB, 120.0)],
            "B": [(_DIC18, None), (_ENE, 90.0), (_FEB, 80.0)],
        },
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
    )


def _canasta_comp(version: int = 2018) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["60.0", "40.0"],
            "encadenamiento": [float("nan"), float("nan")],
            "INFLACION COMPONENTE": ["A", "B"],
        },
        index=pd.Index(["gen_a", "gen_b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _canastas() -> dict[int, CanastaCanonica]:
    return {2018: _canasta_comp()}


def _canasta_solo_a(version: int) -> CanastaCanonica:
    """Canasta con solo la categoría A (B es alta inexistente en esta versión)."""
    df = pd.DataFrame(
        {
            "ponderador": ["100.0"],
            "encadenamiento": [float("nan")],
            "INFLACION COMPONENTE": ["A"],
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
            "CCIF DIVISION": [categoria],
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
        for (periodo, replicado), (_, inc) in zip(data_rep[indice], data_inc[indice]):
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if replicado is None else float(replicado),
                    "indice_incidencia": float("nan") if inc is None else float(inc),
                    "estado_calculo": "ok" if replicado is not None else "sin_datos",
                    "motivo_error": None,
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = [ManifestCalculo(version, tipo, "LaspeyresEncadenadoT2")]  # type: ignore[arg-type]
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
            "motivo_error": None,  # `a_mensual` la exige al reconstruir el df mensual
        }
        for p, i, v, rep, inc, est in rows
    ]
    df = pd.DataFrame(filas).set_index(["periodo", "indice"])
    versiones = {v for _, _, v, _, _, _ in rows}
    manifiesto = [ManifestCalculo(v, tipo, "LaspeyresDirecto") for v in versiones]  # type: ignore[arg-type]
    # `a_mensual` reconstruye el reporte a partir de este, así que necesita el MultiIndex.
    reporte = pd.DataFrame(
        {"version": df["version"].to_numpy(), "estado_calculo": df["estado_calculo"].to_numpy()},
        index=df.index,
    )
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame())


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
    return SerieNormalizada(df)


def _inpc_within() -> ResultadoIndice:
    # visible = i_tramo * 1.3 ; i_tramo: DIC=100, ENE=102
    return _res_inc(
        {"INPC": [(_DIC18, 130.0), (_ENE, 132.6)]},
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="INPC",
        id_corrida="ci",
    )


def _clas_within() -> ResultadoIndice:
    # factor_h por categoría DISTINTO (A*1.5, B*2.0) — rompería la suma si se usara visible
    return _res_inc(
        {"A": [(_DIC18, 150.0), (_ENE, 165.0)], "B": [(_DIC18, 200.0), (_ENE, 180.0)]},
        {"A": [(_DIC18, 100.0), (_ENE, 110.0)], "B": [(_DIC18, 100.0), (_ENE, 90.0)]},
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
    )


def _con_frontera(r: ResultadoIndice, frontera: pd.DataFrame | None) -> ResultadoIndice:
    return ResultadoIndice(
        r._df_resultado,
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


_B_Q = PeriodoQuincenal(2024, 6, 2)  # 2018, pre-junta
_E24 = PeriodoQuincenal(2024, 7, 2)  # junta 2018→2024 (la posee 2018)
_T_Q = PeriodoQuincenal(2024, 8, 1)  # 2024, post-junta


def _inpc_cross_2seg(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    """INPC con escala consistente (★) cruzando la junta 2018→2024.

    J_INPC: b=102, e=104, t(2024)=101. visible: b=102, e=104, t=104/100*101=105.04.
    Si `e` es None, omite la fila de junta (caso mensual; va a `_frontera`).
    """
    filas = [(b, "INPC", 2018, 102.0, 102.0, "ok"), (t, "INPC", 2024, 105.04, 101.0, "ok")]
    if e is not None:
        filas.insert(1, (e, "INPC", 2018, 104.0, 104.0, "ok"))
    return _res_multi(filas, tipo="INPC", id_corrida="ci")


def _clas_cross_2seg(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    """Componente A/B consistente con `_inpc_cross_2seg` (w_A=60, w_B=40).

    Cada categoría lleva su PROPIO factor de encadenamiento, como en un T2 real
    (`factor_h_K = referencia_empalme_K / 100`, ver `laspeyres_encadenado.py`):
    `factor_A = 120/100 = 1.2`, `factor_B = 80/100 = 0.8`. Usar el factor del INPC
    (`104/100 = 1.04`) para ambas volvería el fixture degenerado — con `s_K = s_INPC` no
    hay no-aditividad que corregir y el visible coincidiría con el segmentado, así que el
    test dejaría de distinguir un método del otro.

    J es Laspeyres-consistente con el INPC en los tres periodos:
    `(60·110 + 40·90)/100 = 102`, `(60·120 + 40·80)/100 = 104`, `(60·105 + 40·95)/100 = 101`.
    """
    filas = [
        (b, "A", 2018, 110.0, 110.0, "ok"),
        (b, "B", 2018, 90.0, 90.0, "ok"),
        (t, "A", 2024, 126.0, 105.0, "ok"),  # 105 * 1.2
        (t, "B", 2024, 76.0, 95.0, "ok"),  # 95 * 0.8
    ]
    if e is not None:
        filas[2:2] = [(e, "A", 2018, 120.0, 120.0, "ok"), (e, "B", 2018, 80.0, 80.0, "ok")]
    return _res_multi(filas, tipo="INFLACION COMPONENTE", id_corrida="cc")


def _canasta_cb(version: int) -> CanastaCanonica:
    """Canasta 'canasta basica' content-exact (mismas categorías ambas versiones)."""
    df = pd.DataFrame(
        {
            "ponderador": ["60.0", "40.0"],
            "encadenamiento": [float("nan"), float("nan")],
            "CANASTA BASICA": ["dentro", "fuera"],
        },
        index=pd.Index(["gen_a", "gen_b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


# -- incidencia_periodica ------------------------------------------------------


def test_periodica_retorna_resultado_incidencia() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert isinstance(r, ResultadoIncidencia)


def test_periodica_clase_embebe_frecuencia() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.manifiesto.clase == "periodica_mensual"
    assert (r.resultado.largo["clase_incidencia"] == "periodica_mensual").all()


def test_periodica_suma_igual_variacion_inpc() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    var = variacion_periodica(_inpc(), "mensual")
    for periodo in (_ENE, _FEB):
        suma = r.df.xs(periodo, level="periodo")["incidencia_pp"].sum()
        esperada = var.df.loc[cast(Any, (periodo, "INPC")), "variacion_pp"]
        assert suma == pytest.approx(esperada)


def test_periodica_indices_parciales_none() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.indices_parciales is None


def test_periodica_manifiesto_ids() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.manifiesto.versiones == [2018, 2018]


def test_periodica_estado_parcial_propagado() -> None:
    clas = _clas(estados={(_FEB, "A"): "parcial"})
    r = incidencia_periodica(_inpc(), clas, _canastas(), "mensual")
    assert r.resultado.largo.loc[cast(Any, (_FEB, "A")), "estado_calculo"] == "parcial"
    assert r.resultado.largo.loc[cast(Any, (_FEB, "B")), "estado_calculo"] == "ok"


def test_periodica_frecuencia_invalida_falla() -> None:
    with pytest.raises(InvarianteViolado):
        incidencia_periodica(_inpc(), _clas(), _canastas(), "decenal")  # type: ignore[arg-type]


# -- incidencia_acumulada_anual ------------------------------------------------


def test_acumulada_suma_igual_variacion_inpc() -> None:
    r = incidencia_acumulada_anual(_inpc(), _clas(), _canastas())
    suma = r.df.xs(_FEB, level="periodo")["incidencia_pp"].sum()
    # variacion acumulada FEB vs DIC18 = (104/100 - 1) * 100
    assert suma == pytest.approx(4.0)


# -- validaciones de entrada ---------------------------------------------------


def test_tipo_inpc_invalido_falla() -> None:
    falso_inpc = _indice(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="INFLACION COMPONENTE",
        id_corrida="ci",
    )
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(falso_inpc, _clas(), _canastas(), "mensual")


def test_tipo_clasificacion_invalido_falla() -> None:
    clas = _indice(
        {"A": [(_DIC18, 100.0), (_ENE, 110.0)]},
        tipo="categoria inventada",
        id_corrida="cc",
    )
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(_inpc(), clas, _canastas(), "mensual")


def test_falta_canasta_para_version_falla() -> None:
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(_inpc(), _clas(), {2024: _canasta_comp(2024)}, "mensual")


# -- incidencia_desde ----------------------------------------------------------


def test_desde_una_fila_por_generico() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas(), desde=_DIC18, hasta=_FEB)
    assert len(r.df) == 2
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}
    assert (r.df.index.get_level_values("periodo") == _FEB).all()


def test_desde_con_none_usa_extremos() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas())
    assert len(r.df) == 2
    assert r.manifiesto.clase == "desde"


def test_desde_indices_parciales_dataframe_vacio() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas())
    assert r.indices_parciales is not None
    assert r.indices_parciales.empty


def test_desde_suma_igual_variacion_inpc() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas(), desde=_DIC18, hasta=_FEB)
    assert r.df["incidencia_pp"].sum() == pytest.approx(4.0)


def test_desde_incluir_parciales_ajusta_periodo() -> None:
    r = incidencia_desde(
        _inpc(),
        _clas_b_sin_dic(),
        _canastas(),
        desde=_DIC18,
        hasta=_FEB,
        incluir_parciales=True,
    )
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}
    assert r.indices_parciales is not None
    assert r.indices_parciales.loc["B", "periodo_desde_real"] == _ENE
    assert r.indices_parciales.loc["B", "periodo_hasta_real"] == _FEB
    assert (_FEB, "B") in r.df.index


def test_desde_sin_parciales_excluye_generico() -> None:
    # 'B' no tiene dato exacto en `_DIC18`; sin parciales queda excluido.
    r = incidencia_desde(
        _inpc(),
        _clas_b_sin_dic(),
        _canastas(),
        desde=_DIC18,
        hasta=_FEB,
        incluir_parciales=False,
    )
    assert set(r.df.index.get_level_values("indice")) == {"A"}
    assert r.indices_parciales is not None
    assert r.indices_parciales.empty


def test_desde_sin_parciales_excluye_generico_con_estado_parcial() -> None:
    # 'A' tiene extremos exactos pero estado parcial en `_FEB`.
    clas = _clas(estados={(_FEB, "A"): "parcial"})
    r_con = incidencia_desde(
        _inpc(), clas, _canastas(), desde=_DIC18, hasta=_FEB, incluir_parciales=True
    )
    assert set(r_con.df.index.get_level_values("indice")) == {"A", "B"}
    r_sin = incidencia_desde(
        _inpc(), clas, _canastas(), desde=_DIC18, hasta=_FEB, incluir_parciales=False
    )
    assert set(r_sin.df.index.get_level_values("indice")) == {"B"}


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
        pd.DataFrame({"gen_a": [100.0, 110.0], "gen_b": [100.0, 90.0]}, index=[_Q1, _Q2]).T
    )
    largo = LaspeyresDirecto().calcular(can, serie, "INPC")._completo
    assert (largo["indice_incidencia"] == largo["indice_replicado"]).all()


def test_t2_indice_incidencia_es_i_tramo() -> None:
    ref = 134.471
    largo = (
        LaspeyresEncadenadoT2({"INPC": ref}).calcular(_canasta_t2(), _serie_t2(), "INPC")._completo
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
        tipo="INPC",
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
        tipo="INPC",
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
        tipo="INPC",
        id_corrida="a",
        version=2024,
    )
    tramo_b = _res_inc(
        {"INPC": [(p2, 153.0), (p3, 156.0)]},
        {"INPC": [(p2, 102.0), (p3, 104.0)]},
        tipo="INPC",
        id_corrida="b",
        version=2024,
    )
    largo = empalmar([tramo_a, tramo_b])._completo
    assert largo.at[(p1, "INPC"), "indice_incidencia"] == pytest.approx(100.0)
    assert largo.at[(p3, "INPC"), "indice_incidencia"] == pytest.approx(104.0)


# -- incidencias: within-canasta usa indice_incidencia -------------------------


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
        tipo="INPC",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (_ENE, "A", 2018, 100.0, 100.0, "ok"),
            (_FEB, "A", 2024, 142.0, 100.0, "ok"),
            (_ENE, "B", 2018, 100.0, 100.0, "ok"),
            (_FEB, "B", 2024, 142.0, 100.0, "ok"),
        ],
        tipo="INFLACION COMPONENTE",
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
        tipo="INPC",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (feb, "A", 2018, 100.0, 100.0, "ok"),  # primera fila de feb → groupby first = 2018
            (feb, "B", 2024, 100.0, 100.0, "ok"),  # alta 2024 en la misma frontera
            (mar, "A", 2024, 101.0, 101.0, "ok"),
            (mar, "B", 2024, 104.0, 104.0, "ok"),
        ],
        tipo="INFLACION COMPONENTE",
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
    mapa = _construir_mapa_renombre("CCIF DIVISION", 2018, 2024)
    nativo_2018, (canonico, _codigo) = next((k, v) for k, v in mapa.items() if v[0] != k)
    feb = PeriodoMensual(2024, 2)
    mar = PeriodoMensual(2024, 3)
    inpc = _res_multi(
        [(feb, "INPC", 2018, 100.0, 100.0, "ok"), (mar, "INPC", 2024, 102.0, 102.0, "ok")],
        tipo="INPC",
        id_corrida="ci",
    )
    # clasificación ya normalizada al nombre canónico; versiones mixtas frontera/post
    clas = _res_multi(
        [(feb, canonico, 2018, 100.0, 100.0, "ok"), (mar, canonico, 2024, 104.0, 104.0, "ok")],
        tipo="CCIF DIVISION",
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
    mapa = _construir_mapa_renombre("CCIF DIVISION", 2018, 2024)
    nativo_2018, (nativo_2024, _codigo) = next((k, v) for k, v in mapa.items() if v[0] != k)
    feb = PeriodoMensual(2024, 2)
    mar = PeriodoMensual(2024, 3)
    inpc = _res_multi(
        [(feb, "INPC", 2018, 100.0, 100.0, "ok"), (mar, "INPC", 2024, 102.0, 102.0, "ok")],
        tipo="INPC",
        id_corrida="ci",
    )
    # vocabulario 2018: nombre nativo_2018 incluso en la fila versión 2024
    clas = _res_multi(
        [
            (feb, nativo_2018, 2018, 100.0, 100.0, "ok"),
            (mar, nativo_2018, 2024, 104.0, 104.0, "ok"),
        ],
        tipo="CCIF DIVISION",
        id_corrida="cc",
    )
    canastas = {2018: _canasta_ccif(nativo_2018, 2018), 2024: _canasta_ccif(nativo_2024, 2024)}
    res = incidencia_periodica(inpc, clas, canastas, "mensual")
    assert (mar, nativo_2018) in res.resultado.largo.index


def test_periodica_verifica_periodo_referencia() -> None:
    inpc = _res_inc(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="INPC",
        id_corrida="ci",
        periodo_referencia=_ENE,
    )
    clas = _clas_within()  # periodo_referencia = None
    with pytest.raises(InvarianteViolado):
        incidencia_periodica(inpc, clas, {2018: _canasta_comp()}, "mensual")


# -- Fase 2A: incidencia cross-canasta exacta por segmentos ---------------------


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
                (_E24, "A", 2018, 2024, 120.0, 120.0),
                (_E24, "B", 2018, 2024, 80.0, 80.0),
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
    # valor visible (no segmentado): 60*(126-110)/102, NO 912/102
    assert cast(float, largo.at[(ago, "A"), "incidencia_pp"]) == pytest.approx(
        60 * (126 - 110) / 102
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
                (_E24, "A", 2018, 2024, 120.0, 120.0),
                (_E24, "B", 2018, 2024, 80.0, 80.0),
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


def test_cross_tres_segmentos_factores_distintos_por_categoria() -> None:
    """Rango 2013 → 2024 cruza 2 juntas (2QJul2018, 2QJul2024): 3 segmentos.

    Cada categoría lleva su PROPIO factor de encadenamiento en cada tramo, distinto del
    factor del INPC — es lo que hace que el visible no sea aditivo y que la segmentación
    sobre `J` sea necesaria. Con factores uniformes el test no distinguiría un método
    del otro.

                        INPC        A           B        w: A=60, B=40
      b        (2013)   102/102     110/110     90/90     (visible = J)
      e1 junta (viejo)  104/104     120/120     80/80
      e1       (2018)   J_new = 100 en las 3   (serie 2018 base 2QJul2018 = 100)
      f^(2018)          1.04        1.2         0.8       ← distintos
      e2 junta (viejo)  110.24/106  156/130     56/70
      e2       (2024)   J_new = 100 en las 3   (T2 ancla i_tramo en 100)
      f^(2024)          1.1024      1.56        0.56      ← distintos
      t        (2024)   111.3424/101 163.8/105  53.2/95

    J es Laspeyres-consistente en cada tramo: (60·110+40·90)/100 = 102,
    (60·120+40·80)/100 = 104, (60·130+40·70)/100 = 106, (60·105+40·95)/100 = 101.
    """
    b = PeriodoQuincenal(2018, 1, 2)  # 2013
    e1 = PeriodoQuincenal(2018, 7, 2)  # junta 2013→2018
    e2 = PeriodoQuincenal(2024, 7, 2)  # junta 2018→2024
    t = PeriodoQuincenal(2024, 8, 1)  # 2024
    inpc = _res_multi(
        [
            (b, "INPC", 2013, 102.0, 102.0, "ok"),
            (e1, "INPC", 2013, 104.0, 104.0, "ok"),
            (e2, "INPC", 2018, 110.24, 106.0, "ok"),  # f = 104/100 = 1.04
            (t, "INPC", 2024, 111.3424, 101.0, "ok"),  # f = 110.24/100 = 1.1024
        ],
        tipo="INPC",
        id_corrida="ci",
    )
    clas = _res_multi(
        [
            (b, "A", 2013, 110.0, 110.0, "ok"),
            (b, "B", 2013, 90.0, 90.0, "ok"),
            (e1, "A", 2013, 120.0, 120.0, "ok"),
            (e1, "B", 2013, 80.0, 80.0, "ok"),
            (e2, "A", 2018, 156.0, 130.0, "ok"),  # f_A = 120/100 = 1.2
            (e2, "B", 2018, 56.0, 70.0, "ok"),  # f_B = 80/100 = 0.8
            (t, "A", 2024, 163.8, 105.0, "ok"),  # f_A = 156/100 = 1.56
            (t, "B", 2024, 53.2, 95.0, "ok"),  # f_B = 56/100 = 0.56
        ],
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
    )
    canastas = {2013: _canasta_comp(2013), 2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=b, hasta=t)
    largo = res.resultado.largo
    inc_a = cast(float, largo.at[(t, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(t, "B"), "incidencia_pp"])
    # A = [1·60·(120−110) + 1.04·60·(130−100) + 1.1024·60·(105−100)] / 102
    assert inc_a == pytest.approx((600 + 1.04 * 1800 + 1.1024 * 300) / 102)
    # B = [1·40·(80−90) + 1.04·40·(70−100) + 1.1024·40·(95−100)] / 102
    assert inc_b == pytest.approx((-400 - 1.04 * 1200 - 1.1024 * 200) / 102)
    assert inc_a + inc_b == pytest.approx((111.3424 / 102 - 1) * 100, abs=1e-12)
    assert res.reporte.at[(t, "A"), "metodo_incidencia"] == "cross_segmentado"


# -- T1 (junta 2010→2013): el lado nuevo NO ancla en 100 -----------------------
#
# Escenario con TRES factores de encadenamiento distintos, uno por serie — sin eso el
# fixture es degenerado: si `s_K == s_INPC` no hay no-aditividad que corregir, el visible
# coincide con el segmentado y el test no distingue un método del otro.
#
#                       INPC        A         B
#   b, visible = J      102        110        90      (tramo 2010, directo)
#   junta, visible      104        120        80      (lado viejo, lo posee 2010)
#   junta, J lado nuevo 108        120        90      (tramo 2013, T1: NO es 100)
#   t, J                109.08     125        85.2
#   t, visible          105.04     125        75.7333…
#   factor_h            104/108     1        80/90
#
# Laspeyres consistente en los 4 renglones de J con w_A=60, w_B=40:
#   (60·110+40·90)/100 = 102   (60·120+40·80)/100 = 104
#   (60·120+40·90)/100 = 108   (60·125+40·85.2)/100 = 109.08
_T1_B = PeriodoQuincenal(2013, 1, 2)  # 2010, pre-junta
_T1_E = PeriodoQuincenal(2013, 3, 2)  # junta 2010→2013 (la posee 2010)
_T1_T = PeriodoQuincenal(2013, 4, 1)  # 2013, post-junta
_T1_VIS_B = 85.2 * 80 / 90  # visible de B en t = 75.7333…

# Valores derivados a mano (ver derivación en el docstring del test):
#   A = 600/102 + (26/27)·60·5/102      = 24000/2754
#   B = -400/102 + (26/27)·40·(-4.8)/102 = -15792/2754
_T1_INC_A = 24000 / 2754
_T1_INC_B = -15792 / 2754


def _t1_inpc(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    filas = [(b, "INPC", 2010, 102.0, 102.0, "ok"), (t, "INPC", 2013, 105.04, 109.08, "ok")]
    if e is not None:
        filas.insert(1, (e, "INPC", 2010, 104.0, 104.0, "ok"))
    return _res_multi(filas, tipo="INPC", id_corrida="ci")


def _t1_clas(b: Periodo, e: Periodo | None, t: Periodo) -> ResultadoIndice:
    filas = [
        (b, "A", 2010, 110.0, 110.0, "ok"),
        (b, "B", 2010, 90.0, 90.0, "ok"),
        (t, "A", 2013, 125.0, 125.0, "ok"),
        (t, "B", 2013, _T1_VIS_B, 85.2, "ok"),
    ]
    if e is not None:
        filas[2:2] = [(e, "A", 2010, 120.0, 120.0, "ok"), (e, "B", 2010, 80.0, 80.0, "ok")]
    return _res_multi(filas, tipo="INFLACION COMPONENTE", id_corrida="cc")


def test_cross_t1_quincenal_es_exacto() -> None:
    """Junta 2010→2013 (T1): el lado nuevo ancla en 108, no en 100.

    El ancla se deriva del visible, continuo en el enlace: `J_K(e)_new = I_K_vis(e)/f_K`
    → A: `120/1 = 120`; B: `80/(80/90) = 90`. Ambos coinciden con la columna "J lado
    nuevo" de arriba, que es justo lo que el contrato `=100` daba mal.

    Segmento 1 (2010, `f_INPC = 104/104 = 1`):
        A: 1·60·(120−110)/102 = 600/102     B: 1·40·(80−90)/102 = −400/102
    Segmento 2 (2013, `f_INPC = 105.04/109.08 = 26/27`):
        A: (26/27)·60·(125−120)/102          B: (26/27)·40·(85.2−90)/102
    """
    inpc = _t1_inpc(_T1_B, _T1_E, _T1_T)
    clas = _t1_clas(_T1_B, _T1_E, _T1_T)
    canastas = {2010: _canasta_comp(2010), 2013: _canasta_comp(2013)}
    res = incidencia_desde(inpc, clas, canastas, desde=_T1_B, hasta=_T1_T)
    largo = res.resultado.largo
    inc_a = cast(float, largo.at[(_T1_T, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(_T1_T, "B"), "incidencia_pp"])
    # Los valores van ANTES del marcador a propósito: restaurar el corto-circuito o los
    # literales 100.0 debe romper una aserción numérica, no solo un nombre de método.
    assert inc_a == pytest.approx(_T1_INC_A)
    assert inc_b == pytest.approx(_T1_INC_B)
    # Aditividad: Σ incidencias == variación del INPC visible. Régimen interno → 1e-12.
    assert inc_a + inc_b == pytest.approx((105.04 / 102 - 1) * 100, abs=1e-12)
    assert res.reporte.at[(_T1_T, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_t1_mensual_frontera_de_a_mensual_es_exacto() -> None:
    """Mismo escenario T1, mensual, con `_frontera` construida por `a_mensual()` real.

    No se inyecta la frontera a mano: si se inyectara, restaurar el gate `es_inpc` de
    `conversion._construir_frontera` no rompería ningún número y el test no protegería
    nada. Al construirla de verdad, `I_K_visible(e)` viene del camino de producción.
    """
    inpc_m = a_mensual(_t1_inpc(_T1_B, _T1_E, _T1_T))
    clas_m = a_mensual(_t1_clas(_T1_B, _T1_E, _T1_T))
    assert clas_m._frontera is not None
    # El insumo del ancla: I_K_visible(e) por categoría (lo que el gate `es_inpc` tiraba).
    assert clas_m._frontera.at[(_T1_E, "A"), "indice_replicado_old"] == pytest.approx(120.0)
    assert clas_m._frontera.at[(_T1_E, "B"), "indice_replicado_old"] == pytest.approx(80.0)

    b_m, t_m = PeriodoMensual(2013, 1), PeriodoMensual(2013, 4)
    canastas = {2010: _canasta_comp(2010), 2013: _canasta_comp(2013)}
    res = incidencia_desde(inpc_m, clas_m, canastas, desde=b_m, hasta=t_m)
    largo = res.resultado.largo
    inc_a = cast(float, largo.at[(t_m, "A"), "incidencia_pp"])
    inc_b = cast(float, largo.at[(t_m, "B"), "incidencia_pp"])
    assert inc_a == pytest.approx(_T1_INC_A)
    assert inc_b == pytest.approx(_T1_INC_B)
    assert inc_a + inc_b == pytest.approx((105.04 / 102 - 1) * 100, abs=1e-12)
    assert res.reporte.at[(t_m, "A"), "metodo_incidencia"] == "cross_segmentado"


def test_cross_segmentado_tipo_content_exact_no_componente() -> None:
    # Alcance ampliado (decisión usuario, opción B): cualquier tipo content-exact obtiene
    # segmentación exacta, no solo componente/subcomponente. 'canasta basica' es content-exact
    # con los CSV reales → cross_segmentado. (Sin indicador BIE; exactitud algebraica.)
    canastas = {2018: _canasta_cb(2018), 2024: _canasta_cb(2024)}
    assert _es_content_exact("CANASTA BASICA", canastas) is True
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _res_multi(
        [
            (_B_Q, "dentro", 2018, 110.0, 110.0, "ok"),
            (_B_Q, "fuera", 2018, 90.0, 90.0, "ok"),
            (_E24, "dentro", 2018, 120.0, 120.0, "ok"),
            (_E24, "fuera", 2018, 80.0, 80.0, "ok"),
            # factor_h propio por categoría (120/100, 80/100), no el del INPC (104/100)
            (_T_Q, "dentro", 2024, 126.0, 105.0, "ok"),
            (_T_Q, "fuera", 2024, 76.0, 95.0, "ok"),
        ],
        tipo="CANASTA BASICA",
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
                "SCIAN RAMA": ["X", "Y"],
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
                "SCIAN RAMA": ["Y", "X"],
            },
            index=["g1", "g2"],  # g1 cruza X→Y: NO content-exact
        ),
        2024,
    )
    assert _es_content_exact("SCIAN RAMA", {2018: can2018, 2024: can2024}) is False
    inpc = _inpc_cross_2seg(_B_Q, _E24, _T_Q)
    clas = _res_multi(
        [
            (_B_Q, "X", 2018, 110.0, 110.0, "ok"),
            (_E24, "X", 2018, 120.0, 120.0, "ok"),
            (_T_Q, "X", 2024, 109.2, 105.0, "ok"),
        ],
        tipo="SCIAN RAMA",
        id_corrida="cc",
    )
    res = incidencia_desde(inpc, clas, {2018: can2018, 2024: can2024}, desde=_B_Q, hasta=_T_Q)
    assert res.reporte.at[(_T_Q, "X"), "metodo_incidencia"] == "cross_visible"


def test_es_content_exact_componente_true() -> None:
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    assert _es_content_exact("INFLACION COMPONENTE", canastas) is True


def test_es_content_exact_categoria_distinta_false() -> None:
    # conjunto de categorías distinto entre versiones → no content-exact.
    can2018 = _canasta_comp(2018)  # {A, B}
    can2024 = _canasta_solo_a(2024)  # {A}
    assert _es_content_exact("INFLACION COMPONENTE", {2018: can2018, 2024: can2024}) is False


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


# -- Guardias de las divisiones del cross (regla 3 de data/reglas_codigo/calculo.md) ----
#
# Cada divisor de `_incidencia_cross_encadenada` viene de dato agregado real, así que
# necesita guardia. Los tres casos por divisor: dato faltante (fila no computable, sin
# excepción), cero, y no finito. La salida esperada NO es la misma en los tres: solo
# cero e infinito lanzan; el faltante cae a `cross_sin_frontera` con el visible.


def _cross_2seg_mutado(
    *,
    inpc_filas: dict[tuple[Periodo, str], tuple[float, float]] | None = None,
    clas_filas: dict[tuple[Periodo, str], tuple[float, float]] | None = None,
) -> tuple[ResultadoIndice, ResultadoIndice]:
    """`_inpc_cross_2seg`/`_clas_cross_2seg` quincenal con celdas `(visible, J)` mutadas."""
    inpc_base = {
        (_B_Q, "INPC"): (102.0, 102.0, 2018),
        (_E24, "INPC"): (104.0, 104.0, 2018),
        (_T_Q, "INPC"): (105.04, 101.0, 2024),
    }
    clas_base = {
        (_B_Q, "A"): (110.0, 110.0, 2018),
        (_B_Q, "B"): (90.0, 90.0, 2018),
        (_E24, "A"): (120.0, 120.0, 2018),
        (_E24, "B"): (80.0, 80.0, 2018),
        (_T_Q, "A"): (126.0, 105.0, 2024),
        (_T_Q, "B"): (76.0, 95.0, 2024),
    }
    for base, mut in ((inpc_base, inpc_filas), (clas_base, clas_filas)):
        for clave, (vis, j) in (mut or {}).items():
            base[clave] = (vis, j, base[clave][2])  # type: ignore[index]
    inpc = _res_multi(
        [(p, i, v, vis, j, "ok") for (p, i), (vis, j, v) in inpc_base.items()],
        tipo="INPC",
        id_corrida="ci",
    )
    clas = _res_multi(
        [(p, i, v, vis, j, "ok") for (p, i), (vis, j, v) in clas_base.items()],
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
    )
    return inpc, clas


@pytest.mark.parametrize(
    ("divisor", "celda", "valor"),
    [
        # (visible, J) — se anula el J del periodo `fin` de cada segmento, que es el
        # denominador de f^(m); y el visible de `b`, denominador de la contribución.
        ("J_INPC(fin_m)", ("inpc", _T_Q, "INPC"), (105.04, 0.0)),
        ("J_K(fin_m)", ("clas", _T_Q, "A"), (126.0, 0.0)),
        ("f_K^(m)", ("clas", _T_Q, "A"), (0.0, 105.0)),  # f_K = 0/105 = 0
        ("INPC_visible(b)", ("inpc", _B_Q, "INPC"), (0.0, 102.0)),
    ],
)
def test_cross_divisor_cero_lanza(
    divisor: str, celda: tuple[str, Periodo, str], valor: tuple[float, float]
) -> None:
    destino, periodo, indice = celda
    mut = {(periodo, indice): valor}
    inpc, clas = _cross_2seg_mutado(
        inpc_filas=mut if destino == "inpc" else None,
        clas_filas=mut if destino == "clas" else None,
    )
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    with pytest.raises(InvarianteViolado, match="incidencias:"):
        incidencia_desde(inpc, clas, canastas, desde=_B_Q, hasta=_T_Q)


@pytest.mark.parametrize(
    ("celda", "valor"),
    [
        (("inpc", _T_Q, "INPC"), (105.04, float("inf"))),
        (("clas", _T_Q, "A"), (float("inf"), 105.0)),
        (("inpc", _B_Q, "INPC"), (float("-inf"), 102.0)),
    ],
)
def test_cross_operando_no_finito_lanza(
    celda: tuple[str, Periodo, str], valor: tuple[float, float]
) -> None:
    destino, periodo, indice = celda
    mut = {(periodo, indice): valor}
    inpc, clas = _cross_2seg_mutado(
        inpc_filas=mut if destino == "inpc" else None,
        clas_filas=mut if destino == "clas" else None,
    )
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    with pytest.raises(InvarianteViolado, match="no finito"):
        incidencia_desde(inpc, clas, canastas, desde=_B_Q, hasta=_T_Q)


def test_cross_ancla_faltante_no_lanza_cae_a_visible() -> None:
    # Tercer caso de la regla 3: dato FALTANTE. No es invalidez — el rango no puede
    # segmentarse, así que cae al visible marcado `cross_sin_frontera`, sin excepción.
    jun, ago = PeriodoMensual(2024, 6), PeriodoMensual(2024, 8)
    inpc = _inpc_cross_2seg(jun, None, ago)  # mensual sin _frontera → falta el ancla
    clas = _clas_cross_2seg(jun, None, ago)
    canastas = {2018: _canasta_comp(2018), 2024: _canasta_comp(2024)}
    res = incidencia_desde(inpc, clas, canastas, desde=jun, hasta=ago)
    assert res.reporte.at[(ago, "A"), "metodo_incidencia"] == "cross_sin_frontera"
    assert pd.notna(res.resultado.largo.at[(ago, "A"), "incidencia_pp"])


# -- Guardias de Fase 1 en _construir_resultado ---------------------------------
#
# Los tres casos de la regla 3 NO comparten salida esperada: el dato faltante deja la
# fila no computable sin excepción; el cero en el divisor y el no finito lanzan; y el
# overflow lo atrapa la guardia del resultado, que corre después de la sobrescritura de
# Fase 2A (un `inf` provisional de Fase 1 que la fórmula exacta sustituye no debe
# rechazarse).


def _inpc_f1(dic: float) -> ResultadoIndice:
    return _indice({"INPC": [(_DIC18, dic), (_ENE, 102.0)]}, tipo="INPC", id_corrida="ci")


def _clas_f1(a_ene: float | None) -> ResultadoIndice:
    return _indice(
        {"A": [(_DIC18, 100.0), (_ENE, a_ene)], "B": [(_DIC18, 100.0), (_ENE, 90.0)]},
        tipo="INFLACION COMPONENTE",
        id_corrida="cc",
    )


def test_fase1_operando_faltante_no_lanza_deja_fila_no_computable() -> None:
    # 'A' sin dato en ENE: fila no computable, sin excepción. 'B' sigue válida — si
    # desaparecieran todas, el cálculo lanzaría "sin genéricos computables" y el test
    # no demostraría la semántica de ausencia.
    res = incidencia_periodica(_inpc_f1(100.0), _clas_f1(None), _canastas(), "mensual")
    largo = res.resultado.largo
    assert (_ENE, "A") not in largo.index
    assert cast(float, largo.at[(_ENE, "B"), "incidencia_pp"]) == pytest.approx(
        40 * (90.0 - 100.0) / 100.0
    )
    assert res.reporte.at[(_ENE, "A"), "estado_calculo"] == "sin_datos"


@pytest.mark.parametrize(
    ("caso", "dic_inpc", "a_ene", "patron"),
    [
        ("divisor cero", 0.0, 110.0, "INPC base = 0"),
        ("operando no finito", 100.0, float("inf"), "no finito"),
        ("overflow del resultado", 100.0, 1e308, "overflow"),
    ],
)
def test_fase1_dato_invalido_lanza(caso: str, dic_inpc: float, a_ene: float, patron: str) -> None:
    _ = caso
    with pytest.raises(InvarianteViolado, match=patron):
        incidencia_periodica(_inpc_f1(dic_inpc), _clas_f1(a_ene), _canastas(), "mensual")


# -- End-to-end contra dato real y contra la publicación oficial ----------------

_DATA_INPUTS = Path(__file__).parent.parent.parent.parent.parent / "data" / "inputs"

# Incidencia ANUAL publicada por INEGI para marzo de 2014, en puntos porcentuales.
# Comunicado de prensa del 9 de abril de 2014, cuadro "INPC, SUBYACENTE Y NO SUBYACENTE",
# columna "Incidencia anual 1/":
# https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2014/inpc_2q/inpc_2q2014_04.pdf
#
# Marzo de 2014 contra marzo de 2013 CRUZA la junta de canasta de la segunda quincena de
# marzo de 2013, así que valida el camino cross-canasta de T1 — y valida el reparto entre
# categorías, no solo que el total cierre. Es la única referencia externa que existe para
# ese caso: INEGI dejó de publicar la incidencia anual en los 12 meses posteriores a un
# cambio de canasta a partir de 2018.
_OFICIAL_MAR_2014_COMPONENTE = {"subyacente": 2.204, "no subyacente": 1.554}
_OFICIAL_MAR_2014_SUBCOMPONENTE = {
    "mercancias": 1.002,
    "servicios": 1.202,
    "agropecuarios": 0.134,
    "energeticos y tarifas autorizadas por el gobierno": 1.420,
}


def _historia_mensual(tipo: str) -> ResultadoIndice:
    """Cadena completa 2010-2024, mensual. Rebasa 2010-2013 antes de empalmar con 2018."""
    can = {
        v: rep.cargar_canasta(str(_DATA_INPUTS / "pdf" / f"ponderadores_{v}.csv"), v)
        for v in (2010, 2013, 2018, 2024)
    }
    ser = {
        v: rep.cargar_serie(str(_DATA_INPUTS / f"series{s}_horizontal_metadata.CSV"), v)  # type: ignore[arg-type]
        for v, s in ((2010, 2010), (2013, 2010), (2018, 2018), (2024, 2024))
    }
    r10 = rep.calcular_indice(can[2010], ser[2010], tipo)
    r13 = rep.calcular_indice(can[2013], ser[2013], tipo, r10)
    r18 = rep.calcular_indice(can[2018], ser[2018], tipo)
    r24 = rep.calcular_indice(can[2024], ser[2024], tipo, r18)
    # `rebasar` de dominio espera un Periodo; el parseo de "2Q Jul 2018" vive en la capa api.
    viejo = rebasar(empalmar([r10, r13]), PeriodoQuincenal(2018, 7, 2))
    return a_mensual(empalmar([viejo, empalmar([r18, r24])]))


def _canastas_reales() -> dict[int, CanastaCanonica]:
    return {
        v: rep.cargar_canasta(str(_DATA_INPUTS / "pdf" / f"ponderadores_{v}.csv"), v)
        for v in (2010, 2013, 2018, 2024)
    }


@pytest.mark.requires_data
@pytest.mark.parametrize(
    ("tipo", "oficial"),
    [
        ("inflacion componente", _OFICIAL_MAR_2014_COMPONENTE),
        ("inflacion subcomponente", _OFICIAL_MAR_2014_SUBCOMPONENTE),
    ],
)
def test_incidencia_anual_mar_2014_contra_publicacion_oficial(
    tipo: str, oficial: dict[str, float]
) -> None:
    # Referencia EXTERNA → tolerancia del proyecto (0.009 pp), no el régimen interno.
    inpc_m = _historia_mensual("inpc")
    clas_m = _historia_mensual(tipo)
    inc = incidencia_periodica(inpc_m, clas_m, _canastas_reales(), "anual")
    largo = inc.resultado.largo
    mar_2014 = PeriodoMensual(2014, 3)
    for categoria, esperado in oficial.items():
        obtenido = cast(float, largo.at[(mar_2014, categoria), "incidencia_pp"])
        assert abs(obtenido - esperado) <= 0.009, (
            f"{categoria}: replicado {obtenido:.6f} vs oficial {esperado} "
            f"(error {abs(obtenido - esperado):.6f} pp)"
        )
    assert inc.reporte.at[(mar_2014, next(iter(oficial))), "metodo_incidencia"] == (
        "cross_segmentado"
    )


@pytest.mark.requires_data
@pytest.mark.parametrize("tipo", ["inflacion componente", "inflacion subcomponente"])
def test_incidencia_anual_es_aditiva_en_toda_la_historia(tipo: str) -> None:
    # Aditividad = consistencia aritmética interna → régimen estricto, no 0.009.
    # Cubre las 3 juntas de canasta: los 36 periodos anuales que las cruzan salen
    # `cross_segmentado`, ninguno cae al visible.
    inpc_m = _historia_mensual("inpc")
    clas_m = _historia_mensual(tipo)
    inc = incidencia_periodica(inpc_m, clas_m, _canastas_reales(), "anual")
    var = variacion_periodica(inpc_m, "anual")
    largo, vdf = inc.resultado.largo, var.resultado.largo
    categorias = sorted(set(largo.index.get_level_values("indice")))

    periodos_cross = set()
    for periodo in sorted(set(largo.index.get_level_values("periodo"))):
        suma = sum(cast(float, largo.at[(periodo, c), "incidencia_pp"]) for c in categorias)
        esperado = cast(float, vdf.at[(periodo, "INPC"), "variacion_pp"])
        assert abs(suma - esperado) <= 1e-12, f"{periodo}: residuo {abs(suma - esperado):.3e}"
        if inc.reporte.at[(periodo, categorias[0]), "metodo_incidencia"] == "cross_segmentado":
            periodos_cross.add(periodo)

    # 12 periodos por junta x 3 juntas. `metodo_incidencia` vive por (periodo, categoría),
    # así que el conteo se hace sobre periodos únicos, no sobre filas del reporte.
    assert len(periodos_cross) == 36
    assert "cross_visible" not in set(inc.reporte["metodo_incidencia"])
