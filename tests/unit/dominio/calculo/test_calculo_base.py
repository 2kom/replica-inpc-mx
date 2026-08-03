from __future__ import annotations

from typing import cast

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.base import (
    _construir_diagnostico,
    _promedio_ponderado_por_grupo,
    _recortar_series_fecha,
    _rellenar_dato_serie_faltante,
)
from replica_inpc.dominio.periodos import PeriodoQuincenal

_ANTES_2018 = PeriodoQuincenal(2018, 7, 1)
_INICIO_2018 = PeriodoQuincenal(2018, 7, 2)
_FIN_2018 = PeriodoQuincenal(2024, 7, 2)
_DESPUES_2018 = PeriodoQuincenal(2024, 8, 1)

_P1 = PeriodoQuincenal(2018, 7, 2)
_P2 = PeriodoQuincenal(2018, 8, 1)
_P3 = PeriodoQuincenal(2018, 8, 2)


def _serie(datos: dict[str, list[object]], periodos: list[PeriodoQuincenal]) -> pd.DataFrame:
    return pd.DataFrame(datos, index=periodos).T


# -- _recortar_series_fecha --


def test_recortar_incluye_ambos_extremos_del_rango() -> None:
    df = _serie(
        {"arroz": [1.0, 2.0, 3.0, 4.0]},
        [_ANTES_2018, _INICIO_2018, _FIN_2018, _DESPUES_2018],
    )
    resultado = _recortar_series_fecha(df, 2018)
    assert list(resultado.columns) == [_INICIO_2018, _FIN_2018]


def test_recortar_version_sin_fin_incluye_todo_lo_posterior_al_inicio() -> None:
    # 2024: RANGOS_CANASTAS[2024] = (2Q Jul 2024, None) — sin límite superior
    inicio_2024 = PeriodoQuincenal(2024, 7, 2)
    lejano = PeriodoQuincenal(2030, 1, 1)
    df = _serie({"arroz": [1.0, 2.0, 3.0]}, [_ANTES_2018, inicio_2024, lejano])
    resultado = _recortar_series_fecha(df, 2024)
    assert list(resultado.columns) == [inicio_2024, lejano]


# -- _rellenar_dato_serie_faltante --


def test_rellenar_hueco_interior_marca_rellenado_con_periodo_fuente() -> None:
    # arroz sin dato en 1Q Ago 2018 — bfill toma el dato del periodo SIGUIENTE
    # (2Q Ago 2018, que corre primero); ffill solo entra si bfill no alcanza
    df = _serie({"arroz": [100.0, None, 102.0], "frijol": [50.0, 51.0, 52.0]}, [_P1, _P2, _P3])
    rellenada, diagnostico, periodos_rel = _rellenar_dato_serie_faltante(df, 2018, "INPC")
    assert rellenada.at["arroz", _P2] == pytest.approx(102.0)
    assert periodos_rel == {_P2}
    fila = diagnostico.iloc[0]
    assert fila["generico"] == "arroz"
    assert fila["tipo_faltante"] == "rellenado"
    assert str(_P3) in fila["detalle"]


def test_rellenar_fila_totalmente_faltante_no_se_rellena_ni_se_marca() -> None:
    # huevo sin dato en NINGÚN periodo — bfill/ffill no tiene de dónde tomar
    df = _serie(
        {"arroz": [100.0, 101.0], "huevo": [None, None]},
        [_P1, _P2],
    )
    rellenada, diagnostico, periodos_rel = _rellenar_dato_serie_faltante(df, 2018, "INPC")
    assert cast("pd.Series[bool]", rellenada.loc["huevo"]).isna().all()
    assert "huevo" not in diagnostico["generico"].values
    assert periodos_rel == set()


def test_rellenar_sin_faltantes_devuelve_serie_intacta() -> None:
    df = _serie({"arroz": [100.0, 101.0]}, [_P1, _P2])
    rellenada, diagnostico, periodos_rel = _rellenar_dato_serie_faltante(df, 2018, "INPC")
    assert rellenada.equals(df)
    assert diagnostico.empty
    assert list(diagnostico.columns) == [
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
    assert periodos_rel == set()


# -- _promedio_ponderado_por_grupo --


def test_promedio_ponderado_por_grupo_valores_correctos() -> None:
    numerador = _serie({"a": [100.0], "b": [200.0], "c": [50.0], "d": [150.0]}, [_P1])
    ponderador = pd.Series({"a": 10.0, "b": 30.0, "c": 20.0, "d": 40.0})
    cat_por_gen = pd.Series({"a": "X", "b": "X", "c": "Y", "d": "Y"})
    resultado = _promedio_ponderado_por_grupo(numerador, ponderador, cat_por_gen)
    # a mano: X=(10*100+30*200)/40=175; Y=(20*50+40*150)/60=116.6667
    assert resultado.at["X", _P1] == pytest.approx(175.0)
    assert resultado.at["Y", _P1] == pytest.approx(116.6667, abs=1e-3)


def test_promedio_ponderado_por_grupo_un_solo_elemento_devuelve_su_propio_valor() -> None:
    numerador = _serie({"a": [80.0]}, [_P1])
    ponderador = pd.Series({"a": 15.0})
    cat_por_gen = pd.Series({"a": "X"})
    resultado = _promedio_ponderado_por_grupo(numerador, ponderador, cat_por_gen)
    assert resultado.at["X", _P1] == pytest.approx(80.0)


# -- _construir_diagnostico --


def test_construir_diagnostico_celda_nan_produce_fila_con_schema_correcto() -> None:
    df = _serie({"arroz": [100.0, None]}, [_P1, _P2])
    diagnostico = _construir_diagnostico(df, 2018, "INPC")
    assert len(diagnostico) == 1
    fila = diagnostico.iloc[0]
    assert fila["version"] == 2018
    assert fila["tipo"] == "INPC"
    assert fila["generico"] == "arroz"
    assert fila["periodo"] == _P2
    assert fila["tipo_faltante"] == "indice"
    assert "NaN" in fila["detalle"]


def test_construir_diagnostico_sin_nan_devuelve_df_vacio_con_columnas_correctas() -> None:
    df = _serie({"arroz": [100.0, 101.0]}, [_P1, _P2])
    diagnostico = _construir_diagnostico(df, 2018, "INPC")
    assert diagnostico.empty
    assert list(diagnostico.columns) == [
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
