import pandas as pd

from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import Periodo

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
    "Arroz": "arroz",
    "Frijol": "frijol",
    "Leche": "leche",
    "Huevo": "huevo",
}


"""
El INPC para los 4 periodos en este ejemplo es:
periodo     | INPC
2018-Jul-2Q | 100.0
2018-Ago-1Q | 103.0
2018-Ago-2Q | 106.0
2018-Sep-1Q | 109.0
"""

canasta = CanastaCanonica(df_canasta, 2018)
serie = SerieNormalizada(df_serie, mapeo_serie)


def test_laspeyres_valido():

    # INPC esperado para cada periodo
    inpc_esperado = [100.0, 103.0, 106.0, 109.0]

    df_calculado = LaspeyresDirecto().calcular(canasta, serie, "")

    # extraemos los valores de INPC calculados y periodos del resultado para compararlos con los esperados
    valores_inpc = df_calculado.df["inpc_replicado"].tolist()
    periodos_de_calculo = df_calculado.df.index.tolist()

    assert periodos == periodos_de_calculo
    assert inpc_esperado == valores_inpc


def test_laspeyres_estructura_valida():

    df_calculado = LaspeyresDirecto().calcular(canasta, serie, "")

    # verificamos que el df tenga las columnas esperadas
    columnas_esperadas = ["version", "inpc_replicado", "estado_calculo", "motivo_error"]
    assert all(col in df_calculado.df.columns for col in columnas_esperadas)

    # verificamos que cada columna tenga el tipo de dato esperado
    assert df_calculado.df["version"].dtype == int

    # si estado_calculo == "ok", entonces inpc_replicado debe ser float y motivo_error debe ser None
    if df_calculado.df["estado_calculo"].eq("ok").all():
        assert df_calculado.df["inpc_replicado"].dtype == float
        assert df_calculado.df["motivo_error"].isnull().all()
