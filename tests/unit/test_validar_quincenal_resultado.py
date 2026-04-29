from __future__ import annotations

import uuid

from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.validacion import ReporteValidacionIndices
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.validar_inpc import validar_quincenal_resultado

import pandas as pd

_ID = str(uuid.uuid4())

_PQ1 = PeriodoQuincenal(2018, 8, 1)
_PQ2 = PeriodoQuincenal(2018, 8, 2)
_PQ3 = PeriodoQuincenal(2024, 8, 1)


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
    def test_retorna_reporte_unico(self):
        r = _resultado([_PQ1], ["ok"])
        resultado = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert isinstance(resultado, ReporteValidacionIndices)

    def test_estado_ok_dentro_tolerancia(self):
        r = _resultado([_PQ1], ["ok"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]

    def test_estado_ok_fuera_tolerancia(self):
        r = _resultado([_PQ1], ["ok"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [104.0]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "diferencia_detectada"  # type: ignore[index]

    def test_inegi_vacio_fuera_de_rango(self):
        r = _resultado([_PQ1], ["ok"])
        reporte = validar_quincenal_resultado(r, {})
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "fuera_de_rango_inegi"  # type: ignore[index]


class TestSemiOk:
    def test_semi_ok_se_valida_igual_que_ok(self):
        r = _resultado([_PQ1], ["semi_ok"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]

    def test_null_por_faltantes_no_se_valida(self):
        r = _resultado([_PQ1], ["null_por_faltantes"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "no_disponible"  # type: ignore[index]


class TestVersionCombinada:
    def test_version_simple_es_int(self):
        r = _resultado([_PQ1, _PQ2], ["ok", "ok"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1, _PQ2], [103.5, 104.0]))
        assert reporte.df.loc[(_PQ1, "INPC"), "version"] == 2018  # type: ignore[index]

    def test_tolerancia_por_version(self):
        r = _resultado(
            [_PQ1, _PQ3],
            ["ok", "ok"],
            versiones=[2018, 2024],
            valores=[103.5, 148.0],
        )
        inegi = {"INPC": {_PQ1: 103.5008, _PQ3: 148.0008}}
        reporte = validar_quincenal_resultado(r, inegi)
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]
        assert reporte.df.loc[(_PQ3, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]


class TestForma:
    def test_conserva_estado_calculo_y_motivo_error(self):
        r = _resultado([_PQ1], ["null_por_faltantes"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        assert reporte.df.loc[(_PQ1, "INPC"), "estado_calculo"] == "null_por_faltantes"  # type: ignore[index]
        assert reporte.df.loc[(_PQ1, "INPC"), "motivo_error"] == "faltantes"  # type: ignore[index]

    def test_como_tabla_ancha(self):
        r = _resultado([_PQ1], ["ok"])
        reporte = validar_quincenal_resultado(r, _inegi([_PQ1], [103.5]))
        ancho = reporte.como_tabla(ancho=True)
        assert "INPC_indice_replicado" in ancho.index
        assert "INPC_estado_validacion" in ancho.index
