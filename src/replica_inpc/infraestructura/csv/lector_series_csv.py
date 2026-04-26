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
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.infraestructura.csv._utils import _normalizar

_PATRON_PERIODO = re.compile(r"^[12]Q \w+ \d{4}$")
_PATRON_GENERICO = re.compile(r"\b\d{3}\b\s*(.*)")
_PATRON_CCIF = re.compile(r"^\s*\d{2}(?:\.\d){1,2}\s+")
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

        extracciones = self._extraer_por_codigo(data)
        if self._requiere_extraccion_jerarquica(extracciones):
            extracciones = self._extraer_por_jerarquia_bie(data)

        if not extracciones:
            raise SerieVacia("Error al procesar serie, no se encontraron genéricos en el título")

        periodos = [PeriodoQuincenal.desde_str(c) for c in data.columns]

        genericos_originales = [original for original, _, _ in extracciones]
        genericos_limpios = [limpio for _, limpio, _ in extracciones]
        filas = [fila for _, _, fila in extracciones]

        df_num = pd.DataFrame(filas, columns=data.columns).apply(pd.to_numeric, errors="coerce")
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
                raise ArchivoCorrupto(f"El archivo está corrupto o no es un CSV válido: {ruta}")
            except UnicodeDecodeError:
                continue

        raise EncodingNoLegible(f"No se pudo leer el archivo debido al encoding: {ruta}")

    def _horizontal(self, df: pd.DataFrame) -> pd.DataFrame:
        columnas_validas = [col for col in df.columns if _PATRON_PERIODO.match(str(col))]
        return df.set_index("Título")[columnas_validas]

    def _vertical(self, df: pd.DataFrame) -> pd.DataFrame:
        filas_validas = df[df.iloc[:, 0].apply(lambda x: bool(_PATRON_PERIODO.match(str(x))))]
        filas_validas = filas_validas.set_index("Título").T

        return filas_validas

    def _extraer_por_codigo(self, data: pd.DataFrame) -> list[_Extraccion]:
        extracciones: list[_Extraccion] = []
        for titulo, fila in data.iterrows():
            m = _PATRON_GENERICO.search(str(titulo))
            if m is None:
                continue
            nombre = m.group(1).strip()
            extracciones.append((nombre, _normalizar(nombre), fila))
        return extracciones

    def _requiere_extraccion_jerarquica(self, extracciones: list[_Extraccion]) -> bool:
        if not extracciones:
            return True

        muestra = extracciones[:10]
        return all(limpio.startswith("quincenal ") for _, limpio, _ in muestra)

    def _extraer_por_jerarquia_bie(self, data: pd.DataFrame) -> list[_Extraccion]:
        titulos = [str(titulo) for titulo in data.index]
        extracciones: list[_Extraccion] = []

        for pos, titulo in enumerate(titulos):
            if self._tiene_hijos(titulo, titulos, pos):
                continue

            partes = [parte.strip() for parte in titulo.split(",") if parte.strip()]
            ultimo_codigo = self._ultimo_componente_ccif(partes)
            if ultimo_codigo == -1 or ultimo_codigo == len(partes) - 1:
                continue

            cola = partes[ultimo_codigo + 1 :]
            fila = data.iloc[pos]
            for inicio in range(len(cola)):
                nombre = ", ".join(cola[inicio:]).strip()
                limpio = _ALIASES_BIE_2010.get(_normalizar(nombre), _normalizar(nombre))
                extracciones.append((nombre, limpio, fila))

        return extracciones

    def _tiene_hijos(self, titulo: str, titulos: list[str], pos: int) -> bool:
        prefijo = f"{titulo},"
        return any(i != pos and otro.startswith(prefijo) for i, otro in enumerate(titulos))

    def _ultimo_componente_ccif(self, partes: list[str]) -> int:
        ultimo_codigo = -1
        for pos, parte in enumerate(partes):
            if _PATRON_CCIF.match(parte):
                ultimo_codigo = pos
        return ultimo_codigo
