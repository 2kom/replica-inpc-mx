from __future__ import annotations

from pathlib import Path

import pandas as pd

from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    ColumnasMinFaltantes,
    EncodingNoLegible,
)
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv._utils import _normalizar

COLUMNAS_REQUERIDAS = [
    "ponderador",
    "encadenamiento",
    "COG",
    "CCIF",
    "inflacion 1",
    "inflacion 2",
    "inflacion 3",
    "SCIAN sector",
    "SCIAN rama",
    "canasta basica",
    "canasta consumo minimo",
]


class LectorCanastaCsv:
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica:

        # leemos la canasta desde el csv
        try:
            df = pd.read_csv(
                ruta,
                index_col="generico",
                dtype={"ponderador": str, "encadenamiento": str},
            )
        except FileNotFoundError:
            raise ArchivoNoEncontrado(f"No se encontró el archivo: {ruta}")
        except pd.errors.EmptyDataError:
            raise ArchivoVacio(f"El archivo está vacío: {ruta}")
        except pd.errors.ParserError:
            raise ArchivoCorrupto(
                f"El archivo está corrupto o no es un CSV válido: {ruta}"
            )
        except UnicodeDecodeError:
            raise EncodingNoLegible(
                f"No se pudo leer el archivo debido a un problema de encoding: {ruta}"
            )

        df.index = pd.Index([_normalizar(g) for g in df.index], name="generico")

        if not all(col in df.columns for col in COLUMNAS_REQUERIDAS):
            columnas_faltantes = [
                col for col in COLUMNAS_REQUERIDAS if col not in df.columns
            ]
            raise ColumnasMinFaltantes(
                f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}"
            )

        return CanastaCanonica(df, version)
