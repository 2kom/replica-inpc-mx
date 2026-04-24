from __future__ import annotations

import uuid

import pandas as pd

from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.validar_inpc import validar_mensual

_ID = str(uuid.uuid4())

_PM1 = PeriodoMensual(2018, 8)
_PM2 = PeriodoMensual(2018, 9)
_PM3 = PeriodoMensual(2024, 8)


def _resultado(periodos, estados, versiones=None, valores=None):
    if versiones is None:
        versiones = [2018] * len(periodos)
    if valores is None:
        valores = [103.5 if e in {"ok", "semi_ok"} else None for e in estados]
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    motivos = [None if e in {"ok", "semi_ok"} else "faltantes" for e in estados]
    return ResultadoCalculo(
        pd.DataFrame(
            {
                "version": versiones,
                "tipo": "inpc",
                "indice_replicado": pd.array(valores, dtype="Float64"),
                "estado_calculo": estados,
                "motivo_error": motivos,
            },
            index=idx,
        ),
        _ID,
    )


def _inegi(periodos, valores):
    return {"INPC": dict(zip(periodos, valores))}


class TestBasico:
    def test_retorna_tupla_de_tres(self):
        r = _resultado([_PM1], ["ok"])
        resultado = validar_mensual(r, _inegi([_PM1], [103.5]))
        assert len(resultado) == 3

    def test_estado_ok_dentro_tolerancia(self):
        r = _resultado([_PM1], ["ok"])
        _, reporte, _ = validar_mensual(r, _inegi([_PM1], [103.5]))
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "ok"

    def test_estado_ok_fuera_tolerancia(self):
        r = _resultado([_PM1], ["ok"])
        _, reporte, _ = validar_mensual(r, _inegi([_PM1], [104.0]))
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "diferencia_detectada"

    def test_inegi_vacio_no_disponible(self):
        r = _resultado([_PM1], ["ok"])
        _, reporte, _ = validar_mensual(r, {})
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "no_disponible"

    def test_diagnostico_siempre_vacio(self):
        r = _resultado([_PM1, _PM2], ["ok", "ok"])
        _, _, diag = validar_mensual(r, _inegi([_PM1, _PM2], [103.5, 105.0]))
        assert diag.df.empty


class TestSemiOk:
    def test_semi_ok_se_valida_igual_que_ok(self):
        r = _resultado([_PM1], ["semi_ok"])
        _, reporte, _ = validar_mensual(r, _inegi([_PM1], [103.5]))
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "ok"

    def test_semi_ok_fuera_tolerancia(self):
        r = _resultado([_PM1], ["semi_ok"])
        _, reporte, _ = validar_mensual(r, _inegi([_PM1], [104.5]))
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "diferencia_detectada"

    def test_null_por_faltantes_no_se_valida(self):
        r = _resultado([_PM1], ["null_por_faltantes"])
        _, reporte, _ = validar_mensual(r, _inegi([_PM1], [103.5]))
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "no_disponible"


class TestVersionCombinada:
    def test_version_simple_es_int(self):
        r = _resultado([_PM1, _PM2], ["ok", "ok"])
        resumen, _, _ = validar_mensual(r, _inegi([_PM1, _PM2], [103.5, 105.0]))
        assert resumen.df.loc[_ID, "version"] == 2018

    def test_version_combinada_es_string(self):
        r = _resultado([_PM1, _PM3], ["ok", "ok"], versiones=[2018, 2024])
        resumen, _, _ = validar_mensual(r, _inegi([_PM1, _PM3], [103.5, 148.0]))
        assert resumen.df.loc[_ID, "version"] == "2018+2024"

    def test_tolerancia_por_version(self):
        # cada version usa su propia tolerancia; error < 0.0009 → ok para ambas
        r = _resultado(
            [_PM1, _PM3],
            ["ok", "ok"],
            versiones=[2018, 2024],
            valores=[103.5, 148.0],
        )
        inegi = {"INPC": {_PM1: 103.5008, _PM3: 148.0008}}
        _, reporte, _ = validar_mensual(r, inegi)
        assert reporte.df.loc[(_PM1, "INPC"), "estado_validacion"] == "ok"
        assert reporte.df.loc[(_PM3, "INPC"), "estado_validacion"] == "ok"


class TestResumen:
    def test_estado_corrida_ok(self):
        r = _resultado([_PM1, _PM2], ["ok", "ok"])
        resumen, _, _ = validar_mensual(r, {})
        assert resumen.df.loc[_ID, "estado_corrida"] == "ok"

    def test_estado_corrida_fallida(self):
        r = _resultado([_PM1, _PM2], ["null_por_faltantes", "null_por_faltantes"])
        resumen, _, _ = validar_mensual(r, {})
        assert resumen.df.loc[_ID, "estado_corrida"] == "fallida"

    def test_semi_ok_no_cuenta_como_null(self):
        r = _resultado([_PM1], ["semi_ok"])
        resumen, _, _ = validar_mensual(r, {})
        assert resumen.df.loc[_ID, "estado_corrida"] == "ok"
        assert resumen.df.loc[_ID, "total_periodos_con_null"] == 0

    def test_periodo_inicio_fin(self):
        r = _resultado([_PM1, _PM2], ["ok", "ok"])
        resumen, _, _ = validar_mensual(r, {})
        assert resumen.df.loc[_ID, "periodo_inicio"] == _PM1
        assert resumen.df.loc[_ID, "periodo_fin"] == _PM2

    def test_cobertura_nan_en_reporte(self):
        r = _resultado([_PM1], ["ok"])
        _, reporte, _ = validar_mensual(r, {})
        assert pd.isna(reporte.df.loc[(_PM1, "INPC"), "cobertura_genericos_pct"])
        assert pd.isna(reporte.df.loc[(_PM1, "INPC"), "total_genericos_esperados"])

    def test_id_corrida_en_resumen(self):
        r = _resultado([_PM1], ["ok"])
        resumen, reporte, _ = validar_mensual(r, {})
        assert _ID in resumen.df.index
        assert reporte.id_corrida == _ID
