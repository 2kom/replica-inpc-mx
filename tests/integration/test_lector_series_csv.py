from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.dominio.correspondencia import alinear_genericos
from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    OrientacionNoDetectable,
    SerieVacia,
)
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "inputs"

"""
La serie sintética queda como (orientación horizontal):

Ponderaciones: Arroz=10, Frijol=20, Leche=30, Huevo=40
Subíndices de categoría = suma_ponderada / ponderación_total

Título                  | Cifra   | Serie | 1Q Ene 2018 | 2Q Jul 2018 | 1Q Ago 2018 | 2Q Ago 2018 |
01 Legumbres            | Indices | 54321 | 91.67       | 100.00      | 101.67      | 103.33      |
01 Legumbres 001 Arroz  | Indices | 12345 | 95.00       | 100.00      | 101.00      | 102.00      |
01 Legumbres 002 Frijol | Indices | 67890 | 90.00       | 100.00      | 102.00      | 104.00      |
02 Lacteos              | Indices | 11111 | 85.00       | 100.00      | 103.00      | 106.00      |
02 Lacteos 003 Leche    | Indices | 13579 | 85.00       | 100.00      | 103.00      | 106.00      |
03 Huevos               | Indices | 22222 | 80.00       | 100.00      | 104.00      | 108.00      |
03 Huevos 004 Huevo     | Indices | 24680 | 80.00       | 100.00      | 104.00      | 108.00      |

El encabezado BIE ocupa 5 líneas (skiprows=5).
Los agregados (01 Legumbres, 02 Lacteos, 03 Huevos) se descartan — no tienen código de 3 dígitos.
Los genéricos resultantes son: arroz, frijol y derivados, leche, huevo (normalizados).
2Q Jul 2018 es el periodo base (índice = 100).
"""

_ENCABEZADO_BIE = "Instituto Nacional de Estadística y Geografía\n\n\n\n\n"

df_series = pd.DataFrame(
    {
        "Título": [
            "01 Legumbres",
            "01 Legumbres 001 Arroz",
            "01 Legumbres 002 Frijol",
            "02 Lacteos",
            "02 Lacteos 003 Leche",
            "03 Huevos",
            "03 Huevos 004 Huevo",
        ],
        "Cifra": ["Indices"] * 7,
        "Serie": ["54321", "12345", "67890", "11111", "13579", "22222", "24680"],
        "1Q Ene 2018": ["91.67", "95.00", "90.00", "85.00", "85.00", "80.00", "80.00"],
        "2Q Jul 2018": [
            "100.00",
            "100.00",
            "100.00",
            "100.00",
            "100.00",
            "100.00",
            "100.00",
        ],
        "1Q Ago 2018": [
            "101.67",
            "101.00",
            "102.00",
            "103.00",
            "103.00",
            "104.00",
            "104.00",
        ],
        "2Q Ago 2018": [
            "103.33",
            "102.00",
            "104.00",
            "106.00",
            "106.00",
            "108.00",
            "108.00",
        ],
    }
)


def _escribir_csv(ruta, df=df_series):
    contenido = _ENCABEZADO_BIE + df.to_csv(index=False)
    ruta.write_text(contenido, encoding="latin-1")


def test_lector_series_csv_archivo_no_encontrado(tmp_path: Path):
    ruta = tmp_path / "serie_inexistente.csv"
    with pytest.raises(ArchivoNoEncontrado):
        LectorSeriesCsv().leer(ruta)


def test_lector_series_csv_archivo_vacio(tmp_path: Path):
    ruta = tmp_path / "serie_vacia.csv"
    ruta.touch()  # Crea un archivo vacío
    with pytest.raises(ArchivoVacio):
        LectorSeriesCsv().leer(ruta)


def test_lector_series_csv_archivo_corrupto(tmp_path: Path):
    ruta = tmp_path / "serie_corrupta.csv"
    df_sin_titulo = df_series.rename(columns={"Título": "Encabezado"})
    _escribir_csv(ruta, df_sin_titulo)
    with pytest.raises(ArchivoCorrupto):
        LectorSeriesCsv().leer(ruta)


def test_lector_series_csv_orientacion_no_detectable(tmp_path: Path):
    ruta = tmp_path / "serie_orientacion_no_detectable.csv"
    df_sin_cifra = df_series.drop(columns=["Cifra", "Serie"])
    _escribir_csv(ruta, df_sin_cifra)
    with pytest.raises(OrientacionNoDetectable):
        LectorSeriesCsv().leer(ruta)


def test_lector_series_csv_serie_vacia(tmp_path: Path):
    ruta = tmp_path / "serie_vacia_genericos.csv"
    df_sin_genericos = df_series.copy()
    df_sin_genericos["Título"] = [
        "Alimentos",
        "Bebidas",
        "Lacteos",
        "Carnes",
        "Verduras",
        "Frutas",
        "Cereales",
    ]
    _escribir_csv(ruta, df_sin_genericos)
    with pytest.raises(SerieVacia):
        LectorSeriesCsv().leer(ruta)


@pytest.mark.requires_data
def test_lector_series_csv_real_2018_horizontal_metadata():
    ruta = DATA_DIR / "series2018_horizontal_metadata.CSV"
    resultado = LectorSeriesCsv().leer(ruta)
    assert isinstance(resultado, SerieNormalizada)
    assert not resultado.df.index.duplicated().any()
    assert len(resultado.df) == 299


@pytest.mark.requires_data
def test_lector_series_csv_real_2018_horizontal_nometadata():
    ruta = DATA_DIR / "series2018_horizontal_nometadata.CSV"
    resultado = LectorSeriesCsv().leer(ruta)
    assert isinstance(resultado, SerieNormalizada)
    assert not resultado.df.index.duplicated().any()
    assert len(resultado.df) == 299


@pytest.mark.requires_data
def test_lector_series_csv_real_2018_vertical_metadata():
    ruta = DATA_DIR / "series2018_vertical_metadata.CSV"
    resultado = LectorSeriesCsv().leer(ruta)
    assert isinstance(resultado, SerieNormalizada)
    assert not resultado.df.index.duplicated().any()
    assert len(resultado.df) == 299


@pytest.mark.requires_data
def test_lector_series_csv_real_2018_vertical_nometadata():
    ruta = DATA_DIR / "series2018_vertical_nometadata.CSV"
    resultado = LectorSeriesCsv().leer(ruta)
    assert isinstance(resultado, SerieNormalizada)
    assert not resultado.df.index.duplicated().any()
    assert len(resultado.df) == 299


@pytest.mark.requires_data
@pytest.mark.parametrize(
    "archivo",
    [
        "series2010_horizontal_metadata.CSV",
        "series2010_horizontal_nometadata.CSV",
        "series2010_vertical_metadata.CSV",
        "series2010_vertical_nometadata.CSV",
    ],
)
def test_lector_series_csv_real_2010_bie_alinea_canasta(archivo: str):
    canasta = LectorCanastaCsv().leer(DATA_DIR / "ponderadores_2010.csv", 2010)
    resultado = LectorSeriesCsv().leer(DATA_DIR / archivo)
    resultado_alineado = alinear_genericos(canasta, resultado)

    assert isinstance(resultado, SerieNormalizada)
    assert not resultado.df.index.duplicated().any()
    assert len(resultado.df) == 360
    assert len(resultado_alineado.df) == 283
    assert resultado_alineado.df.index.equals(canasta.df.index)
