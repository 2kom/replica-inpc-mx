import pandas as pd

from replica_inpc.dominio.calculo.encadenado import LaspeyresEncadenado
from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica

"""
La canasta queda como:
generico | ponderador | encadenamiento
arroz    | 10.0       | None
frijol   | 20.0       | None
leche    | 30.0       | None
huevo    | 40.0       | None
"""
df_canasta_sin_encadenamiento = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)

canasta_sin_encadenamiento = CanastaCanonica(df_canasta_sin_encadenamiento, 2018)
canasta_con_encadenamiento = CanastaCanonica(
    df_canasta_sin_encadenamiento.assign(encadenamiento=[1, 2, 3, 4]), 2018
)


def test_para_canasta_sin_encadenamiento():

    # verificar que para_canasta devuelva una instancia de LaspeyresDirecto
    tipo_canasta = para_canasta(canasta_sin_encadenamiento)

    assert isinstance(tipo_canasta, LaspeyresDirecto)


def test_para_laspeyres_con_encadenamiento():

    # verificar que para_canasta devuelva una instancia de LaspeyresEncadenado
    tipo_canasta = para_canasta(canasta_con_encadenamiento)

    assert isinstance(tipo_canasta, LaspeyresEncadenado)
