from __future__ import annotations

import uuid

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.validacion import ReporteValidacionVariaciones
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.validar_variaciones import (
    _base_periodo,
    _restar_quincenas,
    validar_variaciones,
)

_ID = str(uuid.uuid4())

_PERIODOS = [PeriodoMensual(2019, m) for m in range(1, 10)]


def _rv(periodos, semiok=None, clase="periodica", descripcion="mensual", valores=None):
    if valores is None:
        valores = [100.0 + i * 0.5 for i in range(len(periodos))]
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    df = pd.DataFrame({"variacion": pd.array(valores, dtype="Float64")}, index=idx)
    return ResultadoVariacion(
        df,
        tipo="inpc",
        descripcion=descripcion,
        clase_variacion=clase,  # type: ignore[arg-type]
        periodos_semiok=frozenset(semiok) if semiok else None,
    )


def _inegi_vacio():
    return {"INPC": {}}


def _inegi_con_valores(periodos, valor_pp=0.5):
    return {"INPC": {p: valor_pp for p in periodos}}


class TestRetornoTipo:
    def test_retorna_reporte(self):
        rv = _rv(_PERIODOS)
        result = validar_variaciones(rv, "periodica", _inegi_vacio())
        assert isinstance(result, ReporteValidacionVariaciones)

    def test_indice_tiene_tres_niveles(self):
        rv = _rv(_PERIODOS)
        reporte = validar_variaciones(rv, "periodica", _inegi_vacio())
        assert reporte.df.index.names == ["tipo_variacion", "periodo", "indice"]

    def test_tipo_variacion_en_indice(self):
        rv = _rv(_PERIODOS)
        reporte = validar_variaciones(rv, "interanual", _inegi_vacio())
        tipos = reporte.df.index.get_level_values("tipo_variacion").unique().tolist()
        assert tipos == ["interanual"]


class TestEstadoValidacion:
    def test_sin_inegi_es_fuera_de_rango_inegi(self):
        rv = _rv(_PERIODOS)
        reporte = validar_variaciones(rv, "periodica", _inegi_vacio())
        assert (reporte.df["estado_validacion"] == "fuera_de_rango_inegi").all()

    def test_inegi_none_es_no_disponible(self):
        rv = _rv(_PERIODOS)
        inegi: dict = {"INPC": {p: None for p in _PERIODOS}}
        reporte = validar_variaciones(rv, "periodica", inegi)
        assert (reporte.df["estado_validacion"] == "no_disponible").all()

    def test_dentro_tolerancia_es_ok(self):
        rv = _rv(_PERIODOS, valores=[1.005] * len(_PERIODOS))
        # variacion decimal 1.005 × 100 = 100.5 pp; inegi = 100.5 → error 0
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=100.5)
        reporte = validar_variaciones(rv, "periodica", inegi)  # type: ignore[arg-type]
        assert (reporte.df["estado_validacion"] == "ok").all()

    def test_variacion_replicada_almacenada_en_pp(self):
        rv = _rv(_PERIODOS, valores=[0.005] * len(_PERIODOS))
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=0.5)
        reporte = validar_variaciones(rv, "periodica", inegi)  # type: ignore[arg-type]
        assert reporte.df["variacion_replicada_pp"].tolist() == pytest.approx(
            [0.5] * len(_PERIODOS)
        )

    def test_fuera_tolerancia_es_diferencia_detectada(self):
        rv = _rv(_PERIODOS, valores=[0.005] * len(_PERIODOS))
        # variacion decimal 0.005 × 100 = 0.5 pp; inegi = 5.0 → error 4.5 pp > 0.09
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=5.0)
        reporte = validar_variaciones(rv, "periodica", inegi)  # type: ignore[arg-type]
        assert (reporte.df["estado_validacion"] == "diferencia_detectada").all()

    def test_base_semiok_excluye_periodica(self):
        # periodica lag=1: base de Feb 2019 es Ene 2019
        semiok = {PeriodoMensual(2019, 1)}
        rv = _rv(_PERIODOS, semiok=semiok)
        reporte = validar_variaciones(rv, "periodica", _inegi_vacio())
        estado_feb = reporte.df.loc[
            ("periodica", PeriodoMensual(2019, 2), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado_feb == "excluido_semi_ok"

    def test_base_semiok_excluye_interanual(self):
        # interanual lag=12: base de Ene 2019 es Ene 2018
        semiok = {PeriodoMensual(2018, 1)}
        rv = _rv(_PERIODOS, semiok=semiok)
        reporte = validar_variaciones(rv, "interanual", _inegi_vacio())
        estado = reporte.df.loc[
            ("interanual", PeriodoMensual(2019, 1), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado == "excluido_semi_ok"

    def test_base_semiok_excluye_acumulada(self):
        # acumulada: base de Ene 2019 es Dic 2018
        semiok = {PeriodoMensual(2018, 12)}
        rv = _rv(_PERIODOS, semiok=semiok, clase="acumulada_anual", descripcion="acumulada_anual")
        reporte = validar_variaciones(rv, "acumulada_anual", _inegi_vacio())
        estado = reporte.df.loc[
            ("acumulada_anual", PeriodoMensual(2019, 1), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado == "excluido_semi_ok"

    def test_periodo_no_excluido_sin_semiok(self):
        rv = _rv(_PERIODOS)
        reporte = validar_variaciones(rv, "periodica", _inegi_vacio())
        estado_feb = reporte.df.loc[
            ("periodica", PeriodoMensual(2019, 2), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado_feb == "fuera_de_rango_inegi"


class TestColumnas:
    def test_columnas_esperadas(self):
        rv = _rv(_PERIODOS)
        reporte = validar_variaciones(rv, "periodica", _inegi_vacio())
        assert set(reporte.df.columns) == {
            "variacion_replicada_pp",
            "variacion_inegi_pp",
            "error_absoluto_pp",
            "estado_validacion",
        }


class TestInvariantesModelos:
    def test_reporte_vacio_lanza_error(self):
        df = pd.DataFrame(
            {
                "variacion_replicada": [],
                "variacion_inegi_pp": [],
                "error_absoluto_pp": [],
                "estado_validacion": [],
            },
        )
        df.index = pd.MultiIndex.from_tuples([], names=["tipo_variacion", "periodo", "indice"])
        with pytest.raises(InvarianteViolado):
            ReporteValidacionVariaciones(df)

    def test_reporte_estado_invalido_lanza_error(self):
        idx = pd.MultiIndex.from_tuples(
            [("periodica", PeriodoMensual(2019, 1), "INPC")],
            names=["tipo_variacion", "periodo", "indice"],
        )
        df = pd.DataFrame(
            {
                "variacion_replicada": [0.005],
                "variacion_inegi_pp": [0.5],
                "error_absoluto_pp": [0.0],
                "estado_validacion": ["invalido"],
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ReporteValidacionVariaciones(df)


_PERIODOS_Q = [PeriodoQuincenal(2019, m, q) for m in range(1, 4) for q in (1, 2)]


class TestRestarQuincenas:
    def test_resta_una_quincena_dentro_del_mes(self):
        assert _restar_quincenas(PeriodoQuincenal(2019, 2, 1), 1) == PeriodoQuincenal(2019, 1, 2)

    def test_resta_una_quincena_cruzando_mes(self):
        assert _restar_quincenas(PeriodoQuincenal(2019, 1, 1), 1) == PeriodoQuincenal(2018, 12, 2)

    def test_resta_24_quincenas_es_interanual(self):
        assert _restar_quincenas(PeriodoQuincenal(2019, 2, 1), 24) == PeriodoQuincenal(2018, 2, 1)

    def test_resta_24_quincenas_cruzando_anio(self):
        assert _restar_quincenas(PeriodoQuincenal(2019, 1, 1), 24) == PeriodoQuincenal(2018, 1, 1)


class TestBasePeriodoQuincenal:
    def test_periodica_resta_una_quincena(self):
        assert _base_periodo(PeriodoQuincenal(2019, 3, 1), "periodica") == PeriodoQuincenal(
            2019, 2, 2
        )

    def test_interanual_resta_24_quincenas(self):
        assert _base_periodo(PeriodoQuincenal(2019, 3, 1), "interanual") == PeriodoQuincenal(
            2018, 3, 1
        )

    def test_acumulada_anual_es_dic2q_anio_anterior(self):
        assert _base_periodo(PeriodoQuincenal(2019, 3, 1), "acumulada_anual") == PeriodoQuincenal(
            2018, 12, 2
        )


class TestFueraDeRangoInegi:
    def test_periodo_ausente_del_dict_es_fuera_de_rango(self):
        rv = _rv(_PERIODOS_Q)
        reporte = validar_variaciones(rv, "periodica", {"INPC": {}})
        assert (reporte.df["estado_validacion"] == "fuera_de_rango_inegi").all()

    def test_periodo_con_none_es_no_disponible(self):
        rv = _rv(_PERIODOS_Q)
        inegi: dict = {"INPC": {p: None for p in _PERIODOS_Q}}
        reporte = validar_variaciones(rv, "periodica", inegi)
        assert (reporte.df["estado_validacion"] == "no_disponible").all()
