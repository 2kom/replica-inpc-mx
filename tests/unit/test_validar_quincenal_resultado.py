from __future__ import annotations

import uuid

import pandas as pd

from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.validar_inpc import validar_quincenal_resultado

_ID = str(uuid.uuid4())

_PQ1 = PeriodoQuincenal(2018, 8, 1)
_PQ2 = PeriodoQuincenal(2018, 8, 2)
_PQ3 = PeriodoQuincenal(2024, 8, 1)


def _resultado(periodos, estados, versiones=None, valores=None):
    if versiones is None:
        versiones = [2018] * len(periodos)
    if valores is None:
        valores = [103.5 if e == "ok" else None for e in estados]
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    motivos = [None if e == "ok" else "faltantes" for e in estados]
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
        r = _resultado([_PQ1], ["ok"])
        resultado = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert len(resultado) == 3

    def test_estado_ok_dentro_tolerancia(self):
        r = _resultado([_PQ1], ["ok"])
        _, reporte, _ = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]

    def test_estado_ok_fuera_tolerancia(self):
        r = _resultado([_PQ1], ["ok"])
        _, reporte, _ = validar_quincenal_resultado(r, _inegi([_PQ1], [104.0]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "diferencia_detectada"  # type: ignore[index]

    def test_inegi_vacio_no_disponible(self):
        r = _resultado([_PQ1], ["ok"])
        _, reporte, _ = validar_quincenal_resultado(r, {})
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "no_disponible"  # type: ignore[index]

    def test_diagnostico_siempre_vacio(self):
        r = _resultado([_PQ1, _PQ2], ["ok", "ok"])
        _, _, diag = validar_quincenal_resultado(r, _inegi([_PQ1, _PQ2], [103.5, 104.0]))
        assert diag.df.empty

    def test_cobertura_nan(self):
        r = _resultado([_PQ1], ["ok"])
        _, reporte, _ = validar_quincenal_resultado(r, {})
        assert pd.isna(reporte.df.loc[(_PQ1, "INPC"), "cobertura_genericos_pct"])  # type: ignore[index]


class TestVersionCombinada:
    def test_version_simple_es_int(self):
        r = _resultado([_PQ1, _PQ2], ["ok", "ok"])
        resumen, _, _ = validar_quincenal_resultado(r, _inegi([_PQ1, _PQ2], [103.5, 104.0]))
        assert resumen.df.loc[_ID, "version"] == 2018

    def test_version_combinada_es_string(self):
        r = _resultado([_PQ1, _PQ3], ["ok", "ok"], versiones=[2018, 2024])
        resumen, _, _ = validar_quincenal_resultado(r, _inegi([_PQ1, _PQ3], [103.5, 148.0]))
        assert resumen.df.loc[_ID, "version"] == "2018+2024"


class TestResumen:
    def test_estado_corrida_ok(self):
        r = _resultado([_PQ1, _PQ2], ["ok", "ok"])
        resumen, _, _ = validar_quincenal_resultado(r, {})
        assert resumen.df.loc[_ID, "estado_corrida"] == "ok"

    def test_estado_corrida_fallida(self):
        r = _resultado([_PQ1, _PQ2], ["null_por_faltantes", "null_por_faltantes"])
        resumen, _, _ = validar_quincenal_resultado(r, {})
        assert resumen.df.loc[_ID, "estado_corrida"] == "fallida"

    def test_periodo_inicio_fin(self):
        r = _resultado([_PQ1, _PQ2], ["ok", "ok"])
        resumen, _, _ = validar_quincenal_resultado(r, {})
        assert resumen.df.loc[_ID, "periodo_inicio"] == _PQ1
        assert resumen.df.loc[_ID, "periodo_fin"] == _PQ2
