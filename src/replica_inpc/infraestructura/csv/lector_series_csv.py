from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    OrientacionNoDetectable,
    SerieVacia,
)
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.infraestructura.csv._utils import _normalizar

_PATRON_PERIODO = re.compile(r"^[12]Q \w+ \d{4}$")
_PATRON_GENERICO = re.compile(r"\b\d{3}\b\s*(.*)")
_ALIASES_BIE_2010 = {
    _normalizar("Vestidos, faldas y pantalones para niña"): _normalizar(
        "vestidos faldas y pantalones para niñas"
    ),
    _normalizar("Papel higiénico y pañuelos deshechables"): _normalizar(
        "papel higienico y pañuelos desechables"
    ),
}

_Extraccion = tuple[str, str, pd.Series]


class LectorSeriesCsv:
    def leer(self, ruta: Path) -> SerieNormalizada:
        serie = self._leer_csv(ruta)
        if not serie.columns[0] == "Título":
            raise ArchivoCorrupto(
                f"La primera columna sin importar orientación debe ser 'Título', pero se encontró: {serie.columns[0]}"
            )

        if "Cifra" in serie.columns:
            data = self._horizontal(serie)
        elif "Cifra" in serie.iloc[:, 0].values:
            data = self._vertical(serie)
        else:
            raise OrientacionNoDetectable(
                "No se pudo detectar orientacion de la serie, se esperaba encontrar 'Serie' y 'Cifra' como columnas o filas"
            )

        extracciones = self._extraer_por_codigo(data)
        if self._requiere_extraccion_jerarquica(extracciones):
            extracciones = self._extraer_por_jerarquia(data)

        if not extracciones:
            raise SerieVacia("Error al procesar serie, no se encontraron genéricos en el título")

        periodos = [PeriodoQuincenal.desde_str(c) for c in data.columns]

        _, genericos_limpios, series_valores = zip(*extracciones)

        df_serie = pd.DataFrame(series_valores, columns=data.columns).apply(
            pd.to_numeric, errors="coerce"
        )
        df_serie.index = pd.Index(genericos_limpios, name="generico")
        df_serie.columns = periodos
        df_serie.attrs["origen"] = ruta

        return SerieNormalizada(df_serie)

    def _leer_csv(self, ruta: Path) -> pd.DataFrame:
        for encoding in ["utf-8", "cp1252"]:
            try:
                return pd.read_csv(ruta, skiprows=5, dtype=str, encoding=encoding)
            except FileNotFoundError:
                raise ArchivoNoEncontrado(f"No se encontró el archivo: {ruta}")
            except pd.errors.EmptyDataError:
                raise ArchivoVacio(f"El archivo está vacío: {ruta}")
            except pd.errors.ParserError:
                raise ArchivoCorrupto(f"El archivo está corrupto o no es un CSV válido: {ruta}")
            except UnicodeDecodeError:
                continue

        # latin-1 decodifica cualquier secuencia de bytes sin error — último intento, sin fallback.
        try:
            return pd.read_csv(ruta, skiprows=5, dtype=str, encoding="latin-1")
        except FileNotFoundError:
            raise ArchivoNoEncontrado(f"No se encontró el archivo: {ruta}")
        except pd.errors.EmptyDataError:
            raise ArchivoVacio(f"El archivo está vacío: {ruta}")
        except pd.errors.ParserError:
            raise ArchivoCorrupto(f"El archivo está corrupto o no es un CSV válido: {ruta}")

    def _horizontal(self, serie: pd.DataFrame) -> pd.DataFrame:
        columnas_validas = [col for col in serie.columns if _PATRON_PERIODO.match(str(col))]
        return serie.set_index("Título")[columnas_validas]

    def _vertical(self, serie: pd.DataFrame) -> pd.DataFrame:
        filas_validas = serie[serie.iloc[:, 0].apply(lambda x: bool(_PATRON_PERIODO.match(str(x))))]
        return filas_validas.set_index("Título").T

    def _extraer_por_codigo(self, data: pd.DataFrame) -> list[_Extraccion]:
        extracciones: list[_Extraccion] = []
        for pos, titulo in enumerate(data.index):
            match = _PATRON_GENERICO.search(str(titulo))
            if match is None:
                continue
            nombre = match.group(1).strip()
            extracciones.append((nombre, _normalizar(nombre), data.iloc[pos]))
        return extracciones

    def _requiere_extraccion_jerarquica(self, extracciones: list[_Extraccion]) -> bool:
        if not extracciones:
            return True

        muestra = extracciones[:10]
        return all(limpio.startswith("quincenal ") for _, limpio, _ in muestra)

    def _extraer_por_jerarquia(self, data: pd.DataFrame) -> list[_Extraccion]:
        titulos = [str(titulo) for titulo in data.index]
        titulos_set = set(titulos)

        # Precomputar qué títulos son padres (agregados, no genéricos): O(N×D) en vez de O(N²)
        padres_set: set[str] = set()
        for titulo in titulos:
            partes = titulo.split(",")
            for i in range(1, len(partes)):
                prefijo = ",".join(partes[:i])
                if prefijo in titulos_set:
                    padres_set.add(prefijo)

        extracciones: list[_Extraccion] = []
        for pos, titulo in enumerate(titulos):
            if titulo in padres_set:
                continue

            partes = titulo.split(",")
            inicio_generico = None
            for i in range(len(partes) - 1, 0, -1):
                if ",".join(partes[:i]) in titulos_set:
                    inicio_generico = i
                    break
            if inicio_generico is None:
                continue

            nombre = ",".join(partes[inicio_generico:]).strip().lstrip(",").strip()
            limpio = _ALIASES_BIE_2010.get(_normalizar(nombre), _normalizar(nombre))
            extracciones.append((nombre, limpio, data.iloc[pos]))

        return extracciones
