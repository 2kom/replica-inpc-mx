import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado, PeriodoNoInterpretable
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.variaciones import (
    variacion_acumulada_anual,
    variacion_desde,
    variacion_periodica,
)

# -- helpers -------------------------------------------------------------------


def _mk_resultado(
    data: dict[str, list[tuple[PeriodoQuincenal, float | None]]],
    tipo: str = "inpc",
    version: int = 2018,
    id_corrida: str = "test",
) -> ResultadoCalculo:
    rows = []
    for indice, pv_list in data.items():
        for periodo, valor in pv_list:
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if valor is None else float(valor),
                    "estado_calculo": "ok" if valor is not None else "null_por_faltantes",
                    "motivo_error": None if valor is not None else "faltantes en serie",
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    return ResultadoCalculo(df, id_corrida)


def _mk_df_var(*pares: tuple[PeriodoQuincenal, str, float]) -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples([(p, i) for p, i, _ in pares], names=["periodo", "indice"])
    return pd.DataFrame({"variacion": [v for _, _, v in pares]}, index=idx)


# -- períodos de prueba --------------------------------------------------------
#
# Aritmética quincenal relevante (lag=2 → mensual):
#   _restar_quincenas(P2, 2) = P0   — base válida
#   _restar_quincenas(P1, 2) = 1Q Jul 2018  — no existe
#   _restar_quincenas(P0, 2) = 2Q Jun 2018  — no existe
#   _restar_quincenas(P3, 2) = P1           — existe con NaN en test_drop_keep

_P0 = PeriodoQuincenal(2018, 7, 2)  # "2Q Jul 2018"
_P1 = PeriodoQuincenal(2018, 8, 1)  # "1Q Ago 2018"
_P2 = PeriodoQuincenal(2018, 8, 2)  # "2Q Ago 2018"
_P3 = PeriodoQuincenal(2018, 9, 1)  # "1Q Sep 2018"
_P_DIC18 = PeriodoQuincenal(2018, 12, 2)  # "2Q Dic 2018"
_P_ENE19_1 = PeriodoQuincenal(2019, 1, 1)  # "1Q Ene 2019"
_P_ENE19_2 = PeriodoQuincenal(2019, 1, 2)  # "2Q Ene 2019"


# -- ResultadoVariacion invariantes --------------------------------------------


def test_rv_construccion_valida():
    df = _mk_df_var((_P0, "INPC", 0.01))
    rv = ResultadoVariacion(df, tipo="inpc", descripcion="anual")
    assert rv.tipo == "inpc"
    assert rv.descripcion == "anual"
    assert rv.indices_parciales == {}


def test_rv_df_vacio():
    idx = pd.MultiIndex.from_tuples([], names=["periodo", "indice"])
    df = pd.DataFrame({"variacion": pd.Series([], dtype=float)}, index=idx)
    with pytest.raises(InvarianteViolado):
        ResultadoVariacion(df, tipo="inpc", descripcion="x")


def test_rv_indice_incorrecto():
    df = pd.DataFrame({"variacion": [0.01]})
    with pytest.raises(InvarianteViolado):
        ResultadoVariacion(df, tipo="inpc", descripcion="x")


def test_rv_columna_faltante():
    idx = pd.MultiIndex.from_tuples([(_P0, "INPC")], names=["periodo", "indice"])
    df = pd.DataFrame({"otro": [0.01]}, index=idx)
    with pytest.raises(InvarianteViolado):
        ResultadoVariacion(df, tipo="inpc", descripcion="x")


def test_rv_tipo_vacio():
    df = _mk_df_var((_P0, "INPC", 0.01))
    with pytest.raises(InvarianteViolado):
        ResultadoVariacion(df, tipo="", descripcion="x")


def test_rv_descripcion_vacia():
    df = _mk_df_var((_P0, "INPC", 0.01))
    with pytest.raises(InvarianteViolado):
        ResultadoVariacion(df, tipo="inpc", descripcion="")


# -- variacion_periodica -------------------------------------------------------


def test_periodica_mensual_basico():
    # lag=2: base de P2=P0 → 103/100-1=0.03; P0 y P1 sin base → DROP
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 101.0), (_P2, 103.0)]})
    rv = variacion_periodica(r, "mensual")
    assert list(rv.df.index.get_level_values("periodo")) == [_P2]
    assert pytest.approx(rv.df.loc[(_P2, "INPC"), "variacion"]) == 0.03  # type: ignore[index]
    assert rv.tipo == "inpc"
    assert rv.descripcion == "mensual"
    assert rv.indices_parciales == {}


def test_periodica_drop_keep():
    # P1(NaN) → KEEP; P2 valid → KEEP; P0 sin base → DROP; P3 base=P1(NaN) → DROP
    r = _mk_resultado(
        {
            "INPC": [
                (_P0, 100.0),
                (_P1, None),  # I[t] NaN → KEEP
                (_P2, 103.0),  # base=P0 → KEEP
                (_P3, 105.0),  # base=P1(NaN) → DROP
            ]
        }
    )
    rv = variacion_periodica(r, "mensual")
    periodos = list(rv.df.index.get_level_values("periodo"))
    assert _P0 not in periodos
    assert _P1 in periodos
    assert _P2 in periodos
    assert _P3 not in periodos
    assert pd.isna(rv.df.loc[(_P1, "INPC"), "variacion"])  # type: ignore[index]
    assert pytest.approx(rv.df.loc[(_P2, "INPC"), "variacion"]) == 0.03  # type: ignore[index]


def test_periodica_tipo_no_homogeneo():
    idx = pd.MultiIndex.from_tuples(
        [(_P0, "INPC"), (_P1, "Alimentos")], names=["periodo", "indice"]
    )
    df = pd.DataFrame(
        {
            "version": 2018,
            "tipo": ["inpc", "CCIF division"],
            "indice_replicado": [100.0, 100.0],
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    with pytest.raises(InvarianteViolado):
        variacion_periodica(ResultadoCalculo(df, "test"), "mensual")


def test_periodica_gap_b():
    r = _mk_resultado({"INPC": [(_P0, 100.0)]})
    with pytest.raises(InvarianteViolado, match="Se requieren"):
        variacion_periodica(r, "mensual")


# -- variacion_desde -----------------------------------------------------------


def test_desde_basico():
    # desde="1Q Ago 2018" → desde_p=P1, base=P0; rango [P1,P2]
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0)]})
    rv = variacion_desde(r, "1Q Ago 2018")
    assert (_P0, "INPC") not in rv.df.index
    assert (_P1, "INPC") in rv.df.index
    assert (_P2, "INPC") in rv.df.index
    assert pytest.approx(rv.df.loc[(_P1, "INPC"), "variacion"]) == 0.02  # type: ignore[index]
    assert pytest.approx(rv.df.loc[(_P2, "INPC"), "variacion"]) == 0.04  # type: ignore[index]
    assert rv.descripcion == f"desde {_P1} hasta {_P2}"
    assert rv.indices_parciales == {}


def test_desde_hasta_explicito():
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0), (_P3, 106.0)]})
    rv = variacion_desde(r, "1Q Ago 2018", hasta="2Q Ago 2018")
    periodos = list(rv.df.index.get_level_values("periodo"))
    assert _P2 in periodos
    assert _P3 not in periodos


def test_desde_hasta_menor_que_desde():
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0)]})
    with pytest.raises(InvarianteViolado, match="posterior"):
        variacion_desde(r, "2Q Ago 2018", hasta="1Q Ago 2018")


def test_desde_base_no_existe_error_descriptivo():
    # desde=P0 → base=1Q Jul 2018 → no existe; mínimo válido debe ser P1
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 102.0)]})
    with pytest.raises(InvarianteViolado, match="mínimo válido"):
        variacion_desde(r, "2Q Jul 2018")


def test_desde_string_invalido():
    r = _mk_resultado({"INPC": [(_P0, 100.0)]})
    with pytest.raises(PeriodoNoInterpretable):
        variacion_desde(r, "enero-2018")


def test_desde_sin_parciales_excluye_sin_base():
    # CAT_B no tiene dato en base(P0) → excluido con incluir_parciales=False
    r = _mk_resultado(
        {
            "INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0)],
            "CAT_B": [(_P2, 200.0), (_P3, 202.0)],
        }
    )
    rv = variacion_desde(r, "1Q Ago 2018", incluir_parciales=False)
    assert set(rv.df.index.get_level_values("indice")) == {"INPC"}


def test_desde_con_parciales_incluye_cat_b():
    # CAT_B parcial: t0=P2, base=P2 → variacion en P2=0, en P3=202/200-1
    r = _mk_resultado(
        {
            "INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0), (_P3, 106.0)],
            "CAT_B": [(_P2, 200.0), (_P3, 202.0)],
        }
    )
    rv = variacion_desde(r, "1Q Ago 2018", incluir_parciales=True)
    assert "INPC" in rv.df.index.get_level_values("indice")
    assert "CAT_B" in rv.df.index.get_level_values("indice")
    assert pytest.approx(rv.df.loc[(_P2, "CAT_B"), "variacion"]) == 0.0  # type: ignore[index]
    assert pytest.approx(rv.df.loc[(_P3, "CAT_B"), "variacion"]) == pytest.approx(202 / 200 - 1)  # type: ignore[index]
    assert "CAT_B" in rv.indices_parciales
    assert rv.indices_parciales["CAT_B"] == _P2


def test_desde_con_parciales_no_parcial_usa_base_periodo():
    # INPC no-parcial: no debe aparecer en indices_parciales y usa base=P0
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 102.0), (_P2, 104.0)]})
    rv = variacion_desde(r, "1Q Ago 2018", incluir_parciales=True)
    assert "INPC" not in rv.indices_parciales
    assert pytest.approx(rv.df.loc[(_P1, "INPC"), "variacion"]) == 0.02  # type: ignore[index]


# -- variacion_acumulada_anual -------------------------------------------------


def test_acumulada_anual_basico():
    # P_DIC18 → DROP (base=2Q Dic 2017 no existe); P_ENE19_* → base=P_DIC18
    r = _mk_resultado(
        {
            "INPC": [
                (_P_DIC18, 100.0),
                (_P_ENE19_1, 101.0),
                (_P_ENE19_2, 102.0),
            ]
        }
    )
    rv = variacion_acumulada_anual(r)
    assert (_P_DIC18, "INPC") not in rv.df.index
    assert pytest.approx(rv.df.loc[(_P_ENE19_1, "INPC"), "variacion"]) == 0.01  # type: ignore[index]
    assert pytest.approx(rv.df.loc[(_P_ENE19_2, "INPC"), "variacion"]) == 0.02  # type: ignore[index]
    assert rv.descripcion == "acumulada_anual"
    assert rv.indices_parciales == {}


def test_acumulada_anual_gap_b():
    # Solo 2018 → no existe 2Q Dic 2017 → todos DROP
    r = _mk_resultado({"INPC": [(_P0, 100.0), (_P1, 101.0)]})
    with pytest.raises(InvarianteViolado, match="base anual"):
        variacion_acumulada_anual(r)


def test_acumulada_anual_tipo_no_homogeneo():
    idx = pd.MultiIndex.from_tuples(
        [(_P_DIC18, "INPC"), (_P_ENE19_1, "X")], names=["periodo", "indice"]
    )
    df = pd.DataFrame(
        {
            "version": 2018,
            "tipo": ["inpc", "CCIF division"],
            "indice_replicado": [100.0, 100.0],
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    with pytest.raises(InvarianteViolado):
        variacion_acumulada_anual(ResultadoCalculo(df, "test"))
