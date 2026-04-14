from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    ColumnasMinFaltantes,
    EncodingNoLegible,
)
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv

"""
La canasta queda como:
generico | ponderador | encadenamiento | COG   | CCIF division | inflacion componente | inflacion subcomponente | inflacion agrupacion | SCIAN sector    | SCIAN rama      | canasta basica | canasta consumo minimo |
arroz    | 10.0       | None           | COG 1 | CCIF 1        | inf 1.1              | inf 2.1                 | inf 3.1              | SCIAN sect 1.1  | SCIAN rama 2.1  | x              | X                      |
frijol   | 20.0       | None           | COG 1 | CCIF 1        | inf 1.1              | inf 2.1                 | inf 3.1              | SCIAN sect 1.1  | SCIAN rama 2.1  | x              | x                      |
leche    | 30.0       | None           | COG 2 | CCIF 2        | inf 1.2              | inf 2.2                 | inf 3.2              | SCIAN sect 1.2  | SCIAN rama 2.2  |                |                        |
huevo    | 40.0       | None           | COG 3 | CCIF 3        | inf 1.3              | inf 2.3                 | inf 3.3              | SCIAN sect 1.3  | SCIAN rama 2.3  | x              |                        |
"""
df_canasta = pd.DataFrame(
    {
        "generico": ["arroz", "frijol", "leche", "huevo"],
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
        "COG": [
            "COG 1",
            "COG 1",
            "COG 2",
            "COG 3",
        ],
        "CCIF division": ["CCIF 1", "CCIF 1", "CCIF 2", "CCIF 3"],
        "inflacion componente": ["inf 1.1", "inf 1.1", "inf 1.2", "inf 1.3"],
        "inflacion subcomponente": ["inf 2.1", "inf 2.1", "inf 2.2", "inf 2.3"],
        "inflacion agrupacion": ["inf 3.1", "inf 3.1", "inf 3.2", "inf 3.3"],
        "SCIAN sector": ["SCIAN sect 1.1", "SCIAN sect 1.1", "SCIAN sect 1.2", "SCIAN sect 1.3"],
        "SCIAN rama": ["SCIAN rama 2.1", "SCIAN rama 2.1", "SCIAN rama 2.2", "SCIAN rama 2.3"],
        "canasta basica": ["x", "x", "", "x"],
        "canasta consumo minimo": ["x", "x", None, None],
    }
).set_index("generico")

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "inputs"


def test_lector_canasta_csv_valido(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_prueba.csv"
    df_canasta.to_csv(ruta_canasta)
    resultado = LectorCanastaCsv().leer(ruta_canasta, 2018)
    assert isinstance(resultado, CanastaCanonica)
    assert list(resultado.df.index) == ["arroz", "frijol", "leche", "huevo"]
    assert resultado.df["ponderador"].dtype == object


def test_lector_canasta_csv_archivo_no_encontrado(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_inexistente.csv"
    with pytest.raises(ArchivoNoEncontrado):
        LectorCanastaCsv().leer(ruta_canasta, 2018)


def test_lector_canasta_csv_archivo_vacio(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_vacia.csv"
    ruta_canasta.touch()  # Crea un archivo vacío
    with pytest.raises(ArchivoVacio):
        LectorCanastaCsv().leer(ruta_canasta, 2018)


def test_lector_canasta_csv_archivo_corrupto(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_corrupta.csv"
    ruta_canasta.write_text(
        'generico,ponderador\n"comilla sin cerrar,10.0\n', encoding="utf-8"
    )
    with pytest.raises(ArchivoCorrupto):
        LectorCanastaCsv().leer(ruta_canasta, 2018)


def test_lector_canasta_csv_columnas_faltantes(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_faltante_columnas.csv"
    df_canasta.drop(columns=["COG", "CCIF division"]).to_csv(ruta_canasta)
    with pytest.raises(ColumnasMinFaltantes):
        LectorCanastaCsv().leer(ruta_canasta, 2018)


def test_lector_canasta_csv_encoding_no_legible(tmp_path: Path):
    ruta_canasta = tmp_path / "canasta_encoding_invalido.csv"
    with open(ruta_canasta, "w", encoding="utf-16") as f:
        f.write(df_canasta.to_csv())
    with pytest.raises(EncodingNoLegible):
        LectorCanastaCsv().leer(ruta_canasta, 2018)


@pytest.mark.requires_data
def test_lector_canasta_csv_real_2018():
    ruta = DATA_DIR / "ponderadores_2018.csv"
    resultado = LectorCanastaCsv().leer(ruta, 2018)
    assert isinstance(resultado, CanastaCanonica)
    assert len(resultado.df) == 299
