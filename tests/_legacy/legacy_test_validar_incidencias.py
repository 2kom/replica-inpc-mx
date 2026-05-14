from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.validacion import ReporteValidacionIncidencias
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.validar_incidencias import validar_incidencias

_PERIODOS = [PeriodoMensual(2019, m) for m in range(1, 10)]


def _ri(
    periodos: list[PeriodoMensual],
    semiok: set[PeriodoMensual] | None = None,
    valores: list[float | None] | None = None,
) -> ResultadoIncidencia:
    if valores is None:
        valores = [0.3] * len(periodos)  # type: ignore[assignment]
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    pp_list = [float("nan") if v is None else float(v) for v in valores]  # type: ignore[list-item]
    ec_list = [float("nan") if v is None else "ok" for v in valores]  # type: ignore[list-item]
    df = pd.DataFrame(
        {
            "incidencia_pp": pd.array(pp_list, dtype="Float64"),
            "tipo": "inpc",
            "frecuencia": "anual",
            "clase_incidencia": "periodica",
            "estado_calculo": ec_list,
        },
        index=idx,
    )
    ps = frozenset(semiok) if semiok else frozenset()
    return ResultadoIncidencia(df, clase_incidencia="periodica", periodos_semiok=ps)


def _inegi_vacio() -> dict:
    return {"INPC": {}}


def _inegi_con_valores(periodos: list[PeriodoMensual], valor_pp: float = 0.3) -> dict:
    return {"INPC": {p: valor_pp for p in periodos}}


# -- tipo de retorno -----------------------------------------------------------


class TestRetornoTipo:
    def test_retorna_reporte(self):
        ri = _ri(_PERIODOS)
        result = validar_incidencias(ri, "periodica", _inegi_vacio())
        assert isinstance(result, ReporteValidacionIncidencias)

    def test_indice_tres_niveles(self):
        ri = _ri(_PERIODOS)
        reporte = validar_incidencias(ri, "periodica", _inegi_vacio())
        assert reporte.df.index.names == ["tipo_incidencia", "periodo", "indice"]

    def test_tipo_incidencia_en_indice(self):
        ri = _ri(_PERIODOS)
        reporte = validar_incidencias(ri, "periodica", _inegi_vacio())
        tipos = reporte.df.index.get_level_values("tipo_incidencia").unique().tolist()
        assert tipos == ["periodica"]


# -- estados -------------------------------------------------------------------


class TestEstadoValidacion:
    def test_sin_inegi_es_fuera_de_rango(self):
        ri = _ri(_PERIODOS)
        reporte = validar_incidencias(ri, "periodica", _inegi_vacio())
        assert (reporte.df["estado_validacion"] == "fuera_de_rango_inegi").all()

    def test_inegi_none_es_no_disponible(self):
        ri = _ri(_PERIODOS)
        inegi: dict = {"INPC": {p: None for p in _PERIODOS}}
        reporte = validar_incidencias(ri, "periodica", inegi)
        assert (reporte.df["estado_validacion"] == "no_disponible").all()

    def test_dentro_tolerancia_es_ok(self):
        ri = _ri(_PERIODOS, valores=[0.3] * len(_PERIODOS))  # type: ignore[list-item]
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=0.3)
        reporte = validar_incidencias(ri, "periodica", inegi)
        assert (reporte.df["estado_validacion"] == "ok").all()

    def test_fuera_tolerancia_es_diferencia_detectada(self):
        ri = _ri(_PERIODOS, valores=[0.3] * len(_PERIODOS))  # type: ignore[list-item]
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=5.0)
        reporte = validar_incidencias(ri, "periodica", inegi)
        assert (reporte.df["estado_validacion"] == "diferencia_detectada").all()

    def test_periodo_semiok_excluido(self):
        semiok = {PeriodoMensual(2019, 1)}
        ri = _ri(_PERIODOS, semiok=semiok)
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=0.3)
        reporte = validar_incidencias(ri, "periodica", inegi)
        estado_ene = reporte.df.loc[
            ("periodica", PeriodoMensual(2019, 1), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado_ene == "excluido_semi_ok"

    def test_periodo_no_semiok_no_excluido(self):
        ri = _ri(_PERIODOS)
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=0.3)
        reporte = validar_incidencias(ri, "periodica", inegi)
        estado = reporte.df.loc[
            ("periodica", PeriodoMensual(2019, 1), "INPC"), "estado_validacion"  # type: ignore[union-attr]
        ]
        assert estado == "ok"

    def test_incidencia_replicada_almacenada_directamente(self):
        ri = _ri(_PERIODOS, valores=[0.285] * len(_PERIODOS))  # type: ignore[list-item]
        inegi = _inegi_con_valores(_PERIODOS, valor_pp=0.285)
        reporte = validar_incidencias(ri, "periodica", inegi)
        assert reporte.df["incidencia_replicada_pp"].tolist() == pytest.approx(
            [0.285] * len(_PERIODOS)
        )


# -- columnas ------------------------------------------------------------------


class TestColumnas:
    def test_columnas_esperadas(self):
        ri = _ri(_PERIODOS)
        reporte = validar_incidencias(ri, "periodica", _inegi_vacio())
        assert set(reporte.df.columns) == {
            "incidencia_replicada_pp",
            "incidencia_inegi_pp",
            "error_absoluto_pp",
            "estado_validacion",
        }


# -- invariantes del modelo ----------------------------------------------------


class TestInvariantesModelo:
    def test_reporte_vacio_lanza_error(self):
        idx = pd.MultiIndex.from_tuples([], names=["tipo_incidencia", "periodo", "indice"])
        df = pd.DataFrame(
            {
                "incidencia_replicada_pp": [],
                "incidencia_inegi_pp": [],
                "error_absoluto_pp": [],
                "estado_validacion": [],
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ReporteValidacionIncidencias(df)

    def test_estado_invalido_lanza_error(self):
        idx = pd.MultiIndex.from_tuples(
            [("periodica", PeriodoMensual(2019, 1), "INPC")],
            names=["tipo_incidencia", "periodo", "indice"],
        )
        df = pd.DataFrame(
            {
                "incidencia_replicada_pp": [0.3],
                "incidencia_inegi_pp": [0.3],
                "error_absoluto_pp": [0.0],
                "estado_validacion": ["invalido"],
            },
            index=idx,
        )
        with pytest.raises(InvarianteViolado):
            ReporteValidacionIncidencias(df)


# -- como_tabla ----------------------------------------------------------------


class TestComoTabla:
    def test_largo_retorna_sin_nivel_tipo(self):
        ri = _ri(_PERIODOS)
        reporte = validar_incidencias(ri, "periodica", _inegi_vacio())
        tabla = reporte.como_tabla(ancho=False)
        assert "tipo_incidencia" not in tabla.index.names

    def test_ancho_pivota_periodos(self):
        ri = _ri(_PERIODOS[:3])
        inegi = _inegi_con_valores(_PERIODOS[:3], valor_pp=0.3)
        reporte = validar_incidencias(ri, "periodica", inegi)
        tabla = reporte.como_tabla(ancho=True)
        assert tabla.shape[1] == len(_PERIODOS[:3])
