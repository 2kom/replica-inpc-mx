import pandas as pd
import pytest

from replica_inpc.dominio.correspondencia import alinear_genericos
from replica_inpc.dominio.errores import CorrespondenciaInsuficiente
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
generico | 2018-07-02 | 2018-08-01 | 2018-08-02
arroz    | 100        | 101        | 102
frijol   | 100        | 102        | 104
leche    | 100        | 103        | 106
huevo    | 100        | 104        | 108
"""
periodos = [Periodo(2018, 7, 2), Periodo(2018, 8, 1), Periodo(2018, 8, 2)]
df_serie = pd.DataFrame(
    {
        "arroz": [100, 101, 102],
        "frijol": [100, 102, 104],
        "leche": [100, 103, 106],
        "huevo": [100, 104, 108],
    },
    index=periodos,
).T

mapeo_serie = {
    "Arroz": "arroz",
    "Frijol": "frijol",
    "Leche": "leche",
    "Huevo": "huevo",
}

canasta = CanastaCanonica(df_canasta, 2018)
serie = SerieNormalizada(df_serie, mapeo_serie)


def test_alinear_genericos_valido():
    serie_alineada = alinear_genericos(canasta, serie)
    # verificar que el indice de la serie alineada sea igual al indice de la canasta
    assert serie_alineada.df.index.equals(canasta.df.index)
    # verificar que el mapeo de la serie alineada tenga las mismas claves que el mapeo original
    assert set(serie_alineada.mapeo.values()) == set(canasta.df.index)


def test_alinear_genericos_sobrantes():
    df_extra = df_serie.copy()
    df_extra.loc["azucar"] = [100, 105, 110]
    mapeo_extra = mapeo_serie.copy()
    mapeo_extra["Azucar"] = "azucar"
    serie_extra = SerieNormalizada(df_extra, mapeo_extra)

    serie_alineada = alinear_genericos(canasta, serie_extra)

    # verificar que el indice de la serie alineada sea igual al indice de la canasta aun con el generico extra
    assert set(serie_alineada.mapeo.values()) == set(canasta.df.index)


def test_alinear_genericos_insuficiente():
    df_faltante = df_serie.copy()
    df_faltante.drop("huevo", inplace=True)
    mapeo_faltante = mapeo_serie.copy()
    del mapeo_faltante["Huevo"]
    serie_faltante = SerieNormalizada(df_faltante, mapeo_faltante)

    # verificar que alinear_genericos lance CorrespondenciaInsuficiente al faltar un generico de la canasta en la serie
    with pytest.raises(CorrespondenciaInsuficiente):
        alinear_genericos(canasta, serie_faltante)
