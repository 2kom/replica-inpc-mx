from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    EncodingNoLegible,
    OrientacionNoDetectable,
    SerieVacia,
)
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import Periodo
from replica_inpc.infraestructura.csv._utils import _normalizar

_PATRON_PERIODO = re.compile(r"^[12]Q \w+ \d{4}$")
_PATRON_GENERICO = re.compile(r"\b\d{3}\b\s*(.*)")


class LectorSeriesCsv:
    def leer(self, ruta: Path) -> SerieNormalizada:

        df = self._leer_csv(ruta)
        if not df.columns[0] == "Título":
            raise ArchivoCorrupto(
                f"La primera columna sin importar orientación debe ser 'Título', pero se encontró: {df.columns[0]}"
            )

        if "Cifra" in df.columns:
            data = self._horizontal(df)
        elif "Cifra" in df.iloc[:, 0].values:
            data = self._vertical(df)
        else:
            raise OrientacionNoDetectable(
                "No se pudo detectar orientacion de la serie, se esperaba encontrar 'Serie' y 'Cifra' como columnas o filas"
            )

        mascara = data.index.to_series().apply(
            lambda t: bool(_PATRON_GENERICO.search(str(t)))
        )
        data = data.loc[mascara]
        if data.empty:
            raise SerieVacia(
                "Error al procesar serie, no se encontraron filas con codigo de generico de 3 digitos"
            )

        genericos_originales = []
        genericos_limpios = []
        for titulo in data.index:
            m = _PATRON_GENERICO.search(str(titulo))
            nombre = m.group(1).strip()  # type: ignore[union-attr]

            genericos_originales.append(nombre)
            genericos_limpios.append(_normalizar(nombre))

        periodos = [Periodo.desde_str(c) for c in data.columns]

        df_num = data.apply(pd.to_numeric, errors="coerce")
        df_num.index = pd.Index(genericos_limpios, name="generico_limpio")
        df_num.columns = periodos
        mapeo = dict(zip(genericos_limpios, genericos_originales))
        return SerieNormalizada(df_num, mapeo)

    def _leer_csv(self, ruta: Path) -> pd.DataFrame:
        for encoding in ["utf-8", "cp1252", "latin-1"]:
            try:
                df = pd.read_csv(ruta, skiprows=5, dtype=str, encoding=encoding)
                return df
            except FileNotFoundError:
                raise ArchivoNoEncontrado(f"No se encontró el archivo: {ruta}")
            except pd.errors.EmptyDataError:
                raise ArchivoVacio(f"El archivo está vacío: {ruta}")
            except pd.errors.ParserError:
                raise ArchivoCorrupto(
                    f"El archivo está corrupto o no es un CSV válido: {ruta}"
                )
            except UnicodeDecodeError:
                continue

        raise EncodingNoLegible(
            f"No se pudo leer el archivo debido al encoding: {ruta}"
        )

    def _horizontal(self, df: pd.DataFrame) -> pd.DataFrame:
        columnas_validas = [
            col for col in df.columns if _PATRON_PERIODO.match(str(col))
        ]
        return df.set_index("Título")[columnas_validas]

    def _vertical(self, df: pd.DataFrame) -> pd.DataFrame:
        filas_validas = df[
            df.iloc[:, 0].apply(lambda x: bool(_PATRON_PERIODO.match(str(x))))
        ]
        filas_validas = filas_validas.set_index("Título").T

        return filas_validas
