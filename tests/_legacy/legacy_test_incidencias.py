from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.incidencias import (
    incidencia_acumulada_anual,
    incidencia_desde,
    incidencia_periodica,
)
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

# -- helpers -------------------------------------------------------------------


def _mk_rc(
    data: dict[str, list[tuple[PeriodoQuincenal | PeriodoMensual, float | None]]],
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
                    "motivo_error": None if valor is not None else "faltantes",
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    return ResultadoCalculo(df, id_corrida)


def _mk_rc_semiok(
    indice: str,
    periodos_vals: list[tuple[PeriodoQuincenal | PeriodoMensual, float]],
    semiok_periodos: set[PeriodoQuincenal | PeriodoMensual],
    tipo: str = "inpc",
    version: int = 2018,
) -> ResultadoCalculo:
    rows = []
    for periodo, valor in periodos_vals:
        rows.append(
            {
                "periodo": periodo,
                "indice": indice,
                "version": version,
                "tipo": tipo,
                "indice_replicado": float(valor),
                "estado_calculo": "semi_ok" if periodo in semiok_periodos else "ok",
                "motivo_error": None,
            }
        )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    return ResultadoCalculo(df, "test")


def _mk_canasta(
    genericos: list[str],
    ponderadores: list[float],
    componentes: list[str],
    tipo_col: str = "inflacion componente",
    version: int = 2018,
) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": [str(p) for p in ponderadores],
            "encadenamiento": [float("nan")] * len(genericos),
            tipo_col: componentes,
        },
        index=pd.Index(genericos, name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _mk_canasta_enc(
    genericos: list[str],
    ponderadores: list[float],
    componentes: list[str],
    encadenamiento: list[float],
    tipo_col: str = "inflacion componente",
    version: int = 2024,
) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": [str(p) for p in ponderadores],
            "encadenamiento": encadenamiento,
            tipo_col: componentes,
        },
        index=pd.Index(genericos, name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


# Periodos de prueba (mensuales)
_P_ENE = PeriodoMensual(2019, 1)
_P_FEB = PeriodoMensual(2019, 2)
_P_MAR = PeriodoMensual(2019, 3)
_P_DIC18 = PeriodoMensual(2018, 12)

# Periodos quincenales
_Q0 = PeriodoQuincenal(2018, 12, 2)
_Q1 = PeriodoQuincenal(2019, 1, 1)
_Q2 = PeriodoQuincenal(2019, 1, 2)


# -- fixtures ------------------------------------------------------------------


def _inpc_mensual() -> ResultadoCalculo:
    return _mk_rc({"INPC": [(_P_DIC18, 100.0), (_P_ENE, 101.0), (_P_FEB, 102.0), (_P_MAR, 103.0)]})


def _clas_mensual() -> ResultadoCalculo:
    return _mk_rc(
        {
            "subyacente": [
                (_P_DIC18, 70.0),
                (_P_ENE, 71.4),
                (_P_FEB, 72.8),
                (_P_MAR, 74.2),
            ],
            "no subyacente": [
                (_P_DIC18, 30.0),
                (_P_ENE, 30.6),
                (_P_FEB, 31.2),
                (_P_MAR, 31.8),
            ],
        },
        tipo="inflacion componente",
    )


def _canasta_componente() -> CanastaCanonica:
    return _mk_canasta(
        genericos=["gen_sub_1", "gen_sub_2", "gen_nosub"],
        ponderadores=[42.0, 28.0, 30.0],
        componentes=["subyacente", "subyacente", "no subyacente"],
    )


# pond_sub = 70, pond_nosub = 30, pond_total = 100

# incidencia_sub(FEB) = (72.8 - 71.4) * 70 / (100 * 101.0) = 1.4 * 70 / 10100 ≈ 0.009703
# incidencia_nosub(FEB) = (31.2 - 30.6) * 30 / (100 * 101.0) = 0.6 * 30 / 10100 ≈ 0.001782

# -- ResultadoIncidencia model -------------------------------------------------


class TestResultadoIncidenciaInvariantes:
    def _df_valido(self) -> pd.DataFrame:
        idx = pd.MultiIndex.from_tuples([(_P_ENE, "subyacente")], names=["periodo", "indice"])
        return pd.DataFrame(
            {
                "incidencia_pp": [0.01],
                "tipo": ["inflacion componente"],
                "frecuencia": ["mensual"],
                "clase_incidencia": ["periodica"],
                "estado_calculo": ["ok"],
            },
            index=idx,
        )

    def test_construccion_valida(self):
        df = self._df_valido()
        ri = ResultadoIncidencia(df, clase_incidencia="periodica")
        assert isinstance(ri, ResultadoIncidencia)

    def test_df_vacio_lanza_error(self):
        idx = pd.MultiIndex.from_tuples([], names=["periodo", "indice"])
        df = pd.DataFrame(
            {
                "incidencia_pp": [],
                "tipo": [],
                "frecuencia": [],
                "clase_incidencia": [],
                "estado_calculo": [],
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ResultadoIncidencia(df, clase_incidencia="periodica")

    def test_clase_invalida_lanza_error(self):
        df = self._df_valido()
        with pytest.raises(InvarianteViolado):
            ResultadoIncidencia(df, clase_incidencia="invalida")  # type: ignore[arg-type]

    def test_pp_nan_sin_estado_nan_lanza_error(self):
        idx = pd.MultiIndex.from_tuples([(_P_ENE, "sub")], names=["periodo", "indice"])
        df = pd.DataFrame(
            {
                "incidencia_pp": [float("nan")],
                "tipo": ["inflacion componente"],
                "frecuencia": ["mensual"],
                "clase_incidencia": ["periodica"],
                "estado_calculo": ["ok"],  # debería ser NaN
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ResultadoIncidencia(df, clase_incidencia="periodica")

    def test_indice_duplicado_lanza_error(self):
        idx = pd.MultiIndex.from_tuples(
            [(_P_ENE, "sub"), (_P_ENE, "sub")], names=["periodo", "indice"]
        )
        df = pd.DataFrame(
            {
                "incidencia_pp": [0.01, 0.02],
                "tipo": ["inflacion componente"] * 2,
                "frecuencia": ["mensual"] * 2,
                "clase_incidencia": ["periodica"] * 2,
                "estado_calculo": ["ok"] * 2,
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ResultadoIncidencia(df, clase_incidencia="periodica")

    def test_propiedades(self):
        df = self._df_valido()
        ri = ResultadoIncidencia(df, clase_incidencia="periodica")
        assert ri.tipo == "inflacion componente"
        assert ri.frecuencia == "mensual"
        assert ri.clase_incidencia == "periodica"
        assert ri.periodos_semiok == frozenset()


# -- incidencia_periodica ------------------------------------------------------


class TestIncidenciaPeriodica:
    def _canastas(self) -> dict[int, CanastaCanonica]:
        return {2018: _canasta_componente()}

    def test_retorna_resultado_incidencia(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        assert isinstance(ri, ResultadoIncidencia)

    def test_clase_es_periodica(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        assert ri.clase_incidencia == "periodica"

    def test_frecuencia_almacenada(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        assert ri.frecuencia == "mensual"

    def test_tipo_almacenado(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        assert ri.tipo == "inflacion componente"

    def test_formula_mensual(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        # FEB: base=ENE; incidencia = w * (I_t - I_base) / INPC_base
        # sub: 70 * (72.8 - 71.4) / 101.0
        inc_sub_feb = float(ri.df.loc[(_P_FEB, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc_sub_feb == pytest.approx(1.4 * 70 / 101.0, rel=1e-6)
        # nosub: 30 * (31.2 - 30.6) / 101.0
        inc_nosub_feb = float(ri.df.loc[(_P_FEB, "no subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc_nosub_feb == pytest.approx(0.6 * 30 / 101.0, rel=1e-6)

    def test_primer_periodo_excluido_sin_base(self):
        # DIC18 no tiene base (lag=1 → NOV18 no existe), se excluye
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        periodos = ri.df.index.get_level_values("periodo").unique()
        assert _P_DIC18 not in periodos

    def test_estado_ok_cuando_base_ok(self):
        ri = incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "mensual")
        estados = ri.df.loc[_P_FEB]["estado_calculo"].unique()  # type: ignore[union-attr]
        assert list(estados) == ["ok"]

    def test_estado_semiok_cuando_base_semiok(self):
        # ENE es semi_ok → FEB debe ser semi_ok
        inpc = _mk_rc_semiok(
            "INPC",
            [(_P_DIC18, 100.0), (_P_ENE, 101.0), (_P_FEB, 102.0)],
            semiok_periodos={_P_ENE},
        )
        clas = _mk_rc(
            {
                "subyacente": [(_P_DIC18, 70.0), (_P_ENE, 71.4), (_P_FEB, 72.8)],
                "no subyacente": [(_P_DIC18, 30.0), (_P_ENE, 30.6), (_P_FEB, 31.2)],
            },
            tipo="inflacion componente",
        )
        ri = incidencia_periodica(inpc, clas, self._canastas(), "mensual")
        estados_feb = ri.df.loc[_P_FEB]["estado_calculo"].unique()  # type: ignore[union-attr]
        assert list(estados_feb) == ["semi_ok"]
        assert _P_FEB in ri.periodos_semiok

    def test_error_tipo_inpc_invalido(self):
        with pytest.raises(ErrorConfiguracion, match="tipo 'inpc'"):
            incidencia_periodica(_clas_mensual(), _clas_mensual(), self._canastas(), "mensual")

    def test_error_tipo_clasificacion_invalido(self):
        with pytest.raises(ErrorConfiguracion):
            incidencia_periodica(_inpc_mensual(), _inpc_mensual(), self._canastas(), "mensual")

    def test_error_canasta_faltante_para_version(self):
        # clas tiene versión 2024 pero canastas solo tiene 2018 → error
        clas_2024 = _mk_rc(
            {"subyacente": [(_P_ENE, 71.4)], "no subyacente": [(_P_ENE, 30.6)]},
            tipo="inflacion componente",
            version=2024,
        )
        with pytest.raises(ErrorConfiguracion, match="canasta"):
            incidencia_periodica(_inpc_mensual(), clas_2024, self._canastas(), "mensual")

    def test_resultado_combinado_con_ambas_canastas(self):
        # resultado combinado 2018+2024 funciona si se proveen ambas canastas
        rows = []
        for p, v, ver in [(_P_ENE, 71.4, 2018), (_P_FEB, 72.8, 2024)]:
            rows.append(
                {
                    "periodo": p,
                    "indice": "subyacente",
                    "version": ver,
                    "tipo": "inflacion componente",
                    "indice_replicado": v,
                    "estado_calculo": "ok",
                    "motivo_error": None,
                }
            )
        for p, v, ver in [(_P_ENE, 30.6, 2018), (_P_FEB, 31.2, 2024)]:
            rows.append(
                {
                    "periodo": p,
                    "indice": "no subyacente",
                    "version": ver,
                    "tipo": "inflacion componente",
                    "indice_replicado": v,
                    "estado_calculo": "ok",
                    "motivo_error": None,
                }
            )
        df = pd.DataFrame(rows).set_index(["periodo", "indice"])
        clas_combinada = ResultadoCalculo(df, "test")
        canasta_2024 = _mk_canasta(
            genericos=["gen_sub_1", "gen_sub_2", "gen_nosub"],
            ponderadores=[45.0, 25.0, 30.0],
            componentes=["subyacente", "subyacente", "no subyacente"],
            version=2024,
        )
        canastas = {2018: _canasta_componente(), 2024: canasta_2024}
        ri = incidencia_periodica(_inpc_mensual(), clas_combinada, canastas, "mensual")
        assert isinstance(ri, ResultadoIncidencia)

    def test_canasta_encadenada_deencadenamiento_valores(self):
        # f_h_sub=1.2 (sub_traslape=120), f_h_nosub=0.9 (nosub_traslape=90), f_h_INPC=1.1
        # Valores combinados = raw * f_h; traslape = P_ENE (version=2024)
        # Raw P_FEB: sub=102, nosub=101 → inc_sub=70*(102-100)/100=1.4, inc_nosub=30*(101-100)/100=0.3
        canasta_enc = _mk_canasta_enc(
            genericos=["gen_sub_1", "gen_sub_2", "gen_nosub"],
            ponderadores=[42.0, 28.0, 30.0],
            componentes=["subyacente", "subyacente", "no subyacente"],
            encadenamiento=[1.0, 1.0, 1.0],
        )
        inpc = _mk_rc({"INPC": [(_P_ENE, 110.0), (_P_FEB, 111.87)]}, version=2024)
        clas = _mk_rc(
            {
                "subyacente": [(_P_ENE, 120.0), (_P_FEB, 122.4)],
                "no subyacente": [(_P_ENE, 90.0), (_P_FEB, 90.9)],
            },
            tipo="inflacion componente",
            version=2024,
        )
        ri = incidencia_periodica(inpc, clas, {2024: canasta_enc}, "mensual")
        inc_sub = float(ri.df.loc[(_P_FEB, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        inc_nosub = float(ri.df.loc[(_P_FEB, "no subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc_sub == pytest.approx(1.4, rel=1e-5)
        assert inc_nosub == pytest.approx(0.3, rel=1e-5)

    def test_canasta_encadenada_sigma(self):
        # Σ inc_i debe igualar variación INPC (1.7 pp) tras de-encadenamiento
        canasta_enc = _mk_canasta_enc(
            genericos=["gen_sub_1", "gen_sub_2", "gen_nosub"],
            ponderadores=[42.0, 28.0, 30.0],
            componentes=["subyacente", "subyacente", "no subyacente"],
            encadenamiento=[1.0, 1.0, 1.0],
        )
        inpc = _mk_rc({"INPC": [(_P_ENE, 110.0), (_P_FEB, 111.87)]}, version=2024)
        clas = _mk_rc(
            {
                "subyacente": [(_P_ENE, 120.0), (_P_FEB, 122.4)],
                "no subyacente": [(_P_ENE, 90.0), (_P_FEB, 90.9)],
            },
            tipo="inflacion componente",
            version=2024,
        )
        ri = incidencia_periodica(inpc, clas, {2024: canasta_enc}, "mensual")
        inc_sub = float(ri.df.loc[(_P_FEB, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        inc_nosub = float(ri.df.loc[(_P_FEB, "no subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        # INPC raw: P_ENE=100, P_FEB=101.7 → variación=1.7 pp
        assert inc_sub + inc_nosub == pytest.approx(1.7, rel=1e-5)

    def test_multicanasta_transicion_usa_pond_base(self):
        # P_FEB (version=2024) base=P_ENE (version=2018): usa ponderadores canasta 2018
        # canasta 2018: sub=70, nosub=30; canasta 2024: sub=75, nosub=25
        # Si se usaran pond 2024 el resultado sería distinto
        canasta_2024_diff = _mk_canasta(
            genericos=["gen_sub_1", "gen_sub_2", "gen_nosub"],
            ponderadores=[50.0, 25.0, 25.0],
            componentes=["subyacente", "subyacente", "no subyacente"],
            version=2024,
        )
        rows = []
        for p, v, ver in [(_P_ENE, 71.4, 2018), (_P_FEB, 72.8, 2024)]:
            rows.append(
                {
                    "periodo": p,
                    "indice": "subyacente",
                    "version": ver,
                    "tipo": "inflacion componente",
                    "indice_replicado": v,
                    "estado_calculo": "ok",
                    "motivo_error": None,
                }
            )
        for p, v, ver in [(_P_ENE, 30.6, 2018), (_P_FEB, 31.2, 2024)]:
            rows.append(
                {
                    "periodo": p,
                    "indice": "no subyacente",
                    "version": ver,
                    "tipo": "inflacion componente",
                    "indice_replicado": v,
                    "estado_calculo": "ok",
                    "motivo_error": None,
                }
            )
        df = pd.DataFrame(rows).set_index(["periodo", "indice"])
        clas_combinada = ResultadoCalculo(df, "test")
        canastas = {2018: _canasta_componente(), 2024: canasta_2024_diff}
        ri = incidencia_periodica(_inpc_mensual(), clas_combinada, canastas, "mensual")
        # P_FEB base=P_ENE (version=2018) → ponderadores 2018: sub=70, nosub=30
        inc_sub = float(ri.df.loc[(_P_FEB, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        inc_nosub = float(ri.df.loc[(_P_FEB, "no subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        # Con pond 2018: 70*(72.8-71.4)/101 y 30*(31.2-30.6)/101
        assert inc_sub == pytest.approx(70 * (72.8 - 71.4) / 101.0, rel=1e-5)
        assert inc_nosub == pytest.approx(30 * (31.2 - 30.6) / 101.0, rel=1e-5)

    def test_error_frecuencia_invalida(self):
        with pytest.raises(ErrorConfiguracion, match="Frecuencia"):
            incidencia_periodica(_inpc_mensual(), _clas_mensual(), self._canastas(), "quincenal")

    def test_quincenal(self):
        inpc_q = _mk_rc({"INPC": [(_Q0, 100.0), (_Q1, 101.0), (_Q2, 102.0)]})
        clas_q = _mk_rc(
            {
                "subyacente": [(_Q0, 70.0), (_Q1, 71.0), (_Q2, 72.0)],
                "no subyacente": [(_Q0, 30.0), (_Q1, 30.5), (_Q2, 31.0)],
            },
            tipo="inflacion componente",
        )
        ri = incidencia_periodica(inpc_q, clas_q, {2018: _canasta_componente()}, "quincenal")
        # Q1: base=Q0; sub: 70 * (71.0-70.0) / 100.0 = 0.7
        inc_sub_q1 = float(ri.df.loc[(_Q1, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc_sub_q1 == pytest.approx(1.0 * 70 / 100.0, rel=1e-6)


# -- incidencia_acumulada_anual ------------------------------------------------


class TestIncidenciaAcumuladaAnual:
    def _inpc(self) -> ResultadoCalculo:
        return _mk_rc(
            {
                "INPC": [
                    (PeriodoMensual(2018, 12), 100.0),
                    (PeriodoMensual(2019, 1), 101.5),
                    (PeriodoMensual(2019, 6), 103.0),
                ]
            }
        )

    def _clas(self) -> ResultadoCalculo:
        return _mk_rc(
            {
                "subyacente": [
                    (PeriodoMensual(2018, 12), 70.0),
                    (PeriodoMensual(2019, 1), 71.05),
                    (PeriodoMensual(2019, 6), 72.1),
                ],
                "no subyacente": [
                    (PeriodoMensual(2018, 12), 30.0),
                    (PeriodoMensual(2019, 1), 30.45),
                    (PeriodoMensual(2019, 6), 30.9),
                ],
            },
            tipo="inflacion componente",
        )

    def _canastas(self) -> dict[int, CanastaCanonica]:
        return {2018: _canasta_componente()}

    def test_retorna_resultado_incidencia(self):
        ri = incidencia_acumulada_anual(self._inpc(), self._clas(), self._canastas())
        assert isinstance(ri, ResultadoIncidencia)

    def test_clase_es_acumulada_anual(self):
        ri = incidencia_acumulada_anual(self._inpc(), self._clas(), self._canastas())
        assert ri.clase_incidencia == "acumulada_anual"

    def test_base_es_dic_anio_anterior(self):
        # base de ENE 2019 debe ser DIC 2018
        ri = incidencia_acumulada_anual(self._inpc(), self._clas(), self._canastas())
        # DIC 2018 en el resultado sería base de sí mismo → inc=0
        # pero DIC 2018 base sería DIC 2017 (no disponible) → excluido
        periodos = ri.df.index.get_level_values("periodo").unique()
        assert PeriodoMensual(2018, 12) not in periodos

    def test_formula_acumulada(self):
        ri = incidencia_acumulada_anual(self._inpc(), self._clas(), self._canastas())
        # ENE 2019: base = DIC 2018; sub: 70 * (71.05 - 70.0) / 100.0
        inc = float(ri.df.loc[(PeriodoMensual(2019, 1), "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc == pytest.approx(1.05 * 70 / 100.0, rel=1e-6)

    def test_quincenal_base_2q_dic(self):
        inpc_q = _mk_rc({"INPC": [(_Q0, 100.0), (_Q1, 101.0)]})
        clas_q = _mk_rc(
            {
                "subyacente": [(_Q0, 70.0), (_Q1, 71.0)],
                "no subyacente": [(_Q0, 30.0), (_Q1, 30.5)],
            },
            tipo="inflacion componente",
        )
        # Q0 = 2Q Dic 2018; base para Q1 (1Q Ene 2019) = 2Q Dic 2018 = Q0
        ri = incidencia_acumulada_anual(inpc_q, clas_q, {2018: _canasta_componente()})
        periodos = ri.df.index.get_level_values("periodo").unique()
        assert _Q1 in periodos


# -- incidencia_desde ----------------------------------------------------------


class TestIncidenciaDesde:
    def _canastas(self) -> dict[int, CanastaCanonica]:
        return {2018: _canasta_componente()}

    def test_retorna_resultado_incidencia(self):
        ri = incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), _P_ENE, _P_MAR)
        assert isinstance(ri, ResultadoIncidencia)

    def test_clase_es_desde(self):
        ri = incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), _P_ENE, _P_MAR)
        assert ri.clase_incidencia == "desde"

    def test_rango_incluye_desde_hasta(self):
        ri = incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), _P_ENE, _P_MAR)
        periodos = ri.df.index.get_level_values("periodo").unique()
        assert _P_ENE in periodos
        assert _P_MAR in periodos
        assert _P_DIC18 not in periodos

    def test_incidencia_en_desde_es_cero(self):
        ri = incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), _P_ENE, _P_MAR)
        # En ENE (=desde), base=ENE → incidencia = 0
        inc = float(ri.df.loc[(_P_ENE, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc == pytest.approx(0.0, abs=1e-10)

    def test_formula_desde(self):
        ri = incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), _P_ENE, _P_MAR)
        # FEB: base=ENE; sub: 70 * (72.8 - 71.4) / 101.0
        inc = float(ri.df.loc[(_P_FEB, "subyacente"), "incidencia_pp"])  # type: ignore[union-attr]
        assert inc == pytest.approx(1.4 * 70 / 101.0, rel=1e-6)

    def test_rango_vacio_lanza_error(self):
        futuro = PeriodoMensual(2030, 1)
        with pytest.raises(InvarianteViolado):
            incidencia_desde(_inpc_mensual(), _clas_mensual(), self._canastas(), futuro, futuro)
