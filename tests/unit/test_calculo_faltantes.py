from __future__ import annotations

import math

import pandas as pd

from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

_periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]


def _canasta() -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["40.0", "60.0"],
            "encadenamiento": [None, None],
        },
        index=["arroz", "frijol"],
    )
    return CanastaCanonica(df, 2018)


def _serie_con_nan() -> SerieNormalizada:
    df = pd.DataFrame(
        {"arroz": [100.0, float("nan")], "frijol": [100.0, 102.0]}, index=_periodos
    ).T
    return SerieNormalizada(df, {"arroz": "Arroz", "frijol": "Frijol"})


def test_periodo_con_nan_rellenable_marca_rellenado() -> None:
    # arroz NaN en 1Q Aug — fillable via ffill desde 2Q Jul
    r = LaspeyresDirecto().calcular(_canasta(), _serie_con_nan(), "c1", "inpc")
    p_nan = _periodos[1]
    fila = r.resultado.largo.loc[(p_nan, "INPC")]
    assert fila["estado_calculo"] == "rellenado"
    assert not math.isnan(fila["indice_replicado"])


def test_periodo_sin_nan_es_ok() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie_con_nan(), "c1", "inpc")
    p_ok = _periodos[0]
    fila = r.resultado.largo.loc[(p_ok, "INPC")]
    assert fila["estado_calculo"] == "ok"
    assert fila["indice_replicado"] == 100.0


def test_reporte_cobertura_correcta() -> None:
    # Después de relleno, arroz tiene dato → cobertura 100%
    r = LaspeyresDirecto().calcular(_canasta(), _serie_con_nan(), "c1", "inpc")
    p_nan = _periodos[1]
    fila_rep = r.reporte.loc[(p_nan, "INPC")]
    assert fila_rep["genericos_esperados"] == 2
    assert fila_rep["genericos_con_indice"] == 2
    assert fila_rep["genericos_sin_indice"] == 0
    assert fila_rep["cobertura_genericos_pct"] == 100.0
    assert fila_rep["ponderador_esperado"] == 100.0
    assert fila_rep["ponderador_cubierto"] == 100.0


def test_diagnostico_lista_faltante() -> None:
    # NaN rellenado → tipo_faltante="rellenado", no "indice"
    r = LaspeyresDirecto().calcular(_canasta(), _serie_con_nan(), "c1", "inpc")
    diag = r.diagnostico
    assert len(diag) == 1
    fila = diag.iloc[0]
    assert fila["id_corrida"] == "c1"
    assert fila["version"] == 2018
    assert fila["tipo"] == "inpc"
    assert fila["generico"] == "arroz"
    assert fila["periodo"] == _periodos[1]
    assert fila["tipo_faltante"] == "rellenado"


def test_diagnostico_vacio_cuando_serie_completa() -> None:
    df = pd.DataFrame(
        {"arroz": [100.0, 101.0], "frijol": [100.0, 102.0]}, index=_periodos
    ).T
    serie = SerieNormalizada(df, {"arroz": "Arroz", "frijol": "Frijol"})
    r = LaspeyresDirecto().calcular(_canasta(), serie, "c1", "inpc")
    assert len(r.diagnostico) == 0
    assert list(r.diagnostico.columns) == [
        "id_corrida",
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
