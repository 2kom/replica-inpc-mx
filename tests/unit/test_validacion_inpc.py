import uuid

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.modelos.validacion import ResumenValidacion
from replica_inpc.dominio.periodos import Periodo
from replica_inpc.dominio.validar_inpc import validar

ID_CORRIDA = str(uuid.uuid4())

"""
La canasta queda como:
generico | ponderador | encadenamiento
arroz    | 10.0       | None
frijol   | 20.0       | None
leche    | 30.0       | None
huevo    | 40.0       | None
"""
df_canasta = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)

"""
La serie queda como:
generico | 2018-Jul-2Q | 2018-Ago-1Q | 2018-Ago-2Q | 2018-Sep-1Q
arroz    | 100         | 101         | 102         | 103
frijol   | 100         | 102         | 104         | 106
leche    | 100         | 103         | 106         | 109
huevo    | 100         | 104         | 108         | 112
"""
periodos = [
    Periodo(2018, 7, 2),
    Periodo(2018, 8, 1),
    Periodo(2018, 8, 2),
    Periodo(2018, 9, 1),
]
df_serie = pd.DataFrame(
    {
        "arroz": [100, 101, 102, 103],
        "frijol": [100, 102, 104, 106],
        "leche": [100, 103, 106, 109],
        "huevo": [100, 104, 108, 112],
    },
    index=periodos,
).T

mapeo_serie = {
    "arroz": "Arroz",
    "frijol": "Frijol",
    "leche": "Leche",
    "huevo": "Huevo",
}


canasta = CanastaCanonica(df_canasta, 2018)
serie = SerieNormalizada(df_serie, mapeo_serie)

resultado = LaspeyresDirecto().calcular(
    canasta, serie, ID_CORRIDA, indice="INPC", tipo="inpc"
)


def test_validar_inpc_estado_corrida_y_validacion_validos():

    inegi: dict[Periodo, float | None] = {
        Periodo(2018, 7, 2): 100.0,
        Periodo(2018, 8, 1): 103.0,
        Periodo(2018, 8, 2): 106.0,
        Periodo(2018, 9, 1): 109.0,
    }

    resumen, reporte, diagnostico = validar(
        resultado, inegi, canasta, serie, ID_CORRIDA
    )

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok"
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "ok"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_calculados"] == 4
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 0
    assert resumen.df.loc[ID_CORRIDA, "periodo_inicio"] == Periodo(2018, 7, 2)
    assert resumen.df.loc[ID_CORRIDA, "periodo_fin"] == Periodo(2018, 9, 1)

    assert (reporte.df["estado_validacion"] == "ok").all()
    assert (reporte.df["estado_calculo"] == "ok").all()
    assert reporte.df["error_absoluto"].max() == 0.0
    assert reporte.df["error_relativo"].max() == 0.0

    assert diagnostico.df.empty


def test_validar_inpc_diferencia_detectada():

    inegi: dict[Periodo, float | None] = {
        Periodo(2018, 7, 2): 100.0,
        Periodo(2018, 8, 1): 103.0,
        Periodo(2018, 8, 2): 107.0,
        Periodo(2018, 9, 1): 111.0,
    }

    resumen, reporte, diagnostico = validar(
        resultado, inegi, canasta, serie, ID_CORRIDA
    )

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok"
    assert (
        resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "diferencia_detectada"
    )
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_calculados"] == 4
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 0
    assert resumen.df.loc[ID_CORRIDA, "periodo_inicio"] == Periodo(2018, 7, 2)
    assert resumen.df.loc[ID_CORRIDA, "periodo_fin"] == Periodo(2018, 9, 1)

    assert (reporte.df["estado_validacion"] == "diferencia_detectada").sum() == 2
    assert (reporte.df["estado_calculo"] == "ok").all()
    assert reporte.df["error_absoluto"].max() == 2.0

    assert diagnostico.df.empty


def test_validar_inpc_estado_corrida_fallida():

    serie_null = serie.df.copy()
    for periodo in periodos:
        serie_null.loc["arroz", periodo] = float("nan")
    serie_fallida = SerieNormalizada(serie_null, mapeo_serie)
    resultado_fallido = LaspeyresDirecto().calcular(
        canasta, serie_fallida, ID_CORRIDA, indice="INPC", tipo="inpc"
    )

    resumen, reporte, diagnostico = validar(
        resultado_fallido, {}, canasta, serie_fallida, ID_CORRIDA
    )

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "fallida"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 4
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "no_disponible"

    assert (reporte.df["estado_calculo"] == "null_por_faltantes").all()

    assert len(diagnostico.df) == 4
    assert (diagnostico.df["nivel_faltante"] == "estructural").all()
    assert (diagnostico.df["generico"] == "arroz").all()


def test_validar_inpc_inegi_no_disponible():
    (
        resumen,
        reporte,
        diagnostico,
    ) = validar(resultado, {}, canasta, serie, ID_CORRIDA)

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok"
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "no_disponible"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_calculados"] == 4
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 0
    assert resumen.df.loc[ID_CORRIDA, "periodo_inicio"] == Periodo(2018, 7, 2)
    assert resumen.df.loc[ID_CORRIDA, "periodo_fin"] == Periodo(2018, 9, 1)

    assert len(reporte.df) == 4
    assert (reporte.df["estado_validacion"] == "no_disponible").all()
    assert (reporte.df["estado_calculo"] == "ok").all()

    assert diagnostico.df.empty


def test_validar_inpc_serie_con_nan():

    serie_con_nan = serie.df.copy()
    serie_con_nan.loc["arroz", Periodo(2018, 8, 2)] = float("nan")
    serie_nan = SerieNormalizada(serie_con_nan, mapeo_serie)
    resultado_nan = LaspeyresDirecto().calcular(
        canasta, serie_nan, ID_CORRIDA, indice="INPC", tipo="inpc"
    )

    resumen, reporte, diagnostico = validar(
        resultado_nan, {}, canasta, serie_nan, ID_CORRIDA
    )

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok_parcial"
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "no_disponible"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_calculados"] == 4
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 1

    assert len(reporte.df) == 4
    assert (reporte.df["estado_validacion"] == "no_disponible").all()
    assert (reporte.df["estado_calculo"] == "null_por_faltantes").sum() == 1
    assert (reporte.df["estado_calculo"] == "ok").sum() == 3

    assert len(diagnostico.df) == 1
    assert diagnostico.df.iloc[0]["periodo"] == Periodo(2018, 8, 2)
    assert diagnostico.df.iloc[0]["generico"] == "arroz"
    assert diagnostico.df.iloc[0]["nivel_faltante"] == "periodo"
    assert diagnostico.df.iloc[0]["tipo_faltante"] == "indice"


def test_validar_inpc_dentro_de_tolerancia():

    inegi = {
        Periodo(2018, 7, 2): 100.0,
        Periodo(2018, 8, 1): 103.0,
        Periodo(2018, 8, 2): None,
        Periodo(2018, 9, 1): None,
    }

    resumen, reporte, diagnostico = validar(
        resultado, inegi, canasta, serie, ID_CORRIDA
    )

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok"
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "ok_parcial"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_calculados"] == 4
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 0

    assert (
        reporte.df.loc[(Periodo(2018, 7, 2), "INPC"), "estado_validacion"]  # type: ignore[index]
        == "ok"
    )
    assert (
        reporte.df.loc[(Periodo(2018, 7, 2), "INPC"), "error_absoluto"] == 0.0  # type: ignore[index]
    )
    assert (
        reporte.df.loc[(Periodo(2018, 7, 2), "INPC"), "indice_inegi"] == 100.0  # type: ignore[index]
    )

    assert (
        reporte.df.loc[(Periodo(2018, 8, 2), "INPC"), "estado_validacion"]  # type: ignore[index]
        == "no_disponible"
    )
    assert pd.isna(
        reporte.df.loc[(Periodo(2018, 8, 2), "INPC"), "error_absoluto"]  # type: ignore[index]
    )
    assert pd.isna(
        reporte.df.loc[(Periodo(2018, 8, 2), "INPC"), "indice_inegi"]  # type: ignore[index]
    )

    assert (reporte.df["estado_validacion"] == "no_disponible").sum() == 2

    assert diagnostico.df.empty


def test_resumen_validacion_invariante_periodo_inicio_mayor_que_fin():
    df = pd.DataFrame(
        {
            "version": 2018,
            "tipo": "inpc",
            "periodo_inicio": Periodo(2018, 9, 1),
            "periodo_fin": Periodo(2018, 7, 2),
            "total_periodos_esperados": 4,
            "total_periodos_calculados": 4,
            "total_periodos_con_null": 0,
            "error_absoluto_max": float("nan"),
            "error_relativo_max": float("nan"),
            "total_faltantes_indice": 0,
            "total_faltantes_ponderador": 0,
            "estado_validacion_global": "no_disponible",
            "estado_corrida": "ok",
        },
        index=[ID_CORRIDA],
    )
    with pytest.raises(InvarianteViolado, match="periodo_inicio"):
        ResumenValidacion(df)
