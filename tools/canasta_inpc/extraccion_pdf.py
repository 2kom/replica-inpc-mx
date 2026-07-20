import re
from pathlib import Path

import pandas as pd
import pdftotext

from canasta_inpc.esquema import VersionCanasta
from canasta_inpc.utilidades import normalizar_texto, quitar_prefijo_numerico


def extraer_pdf(ruta: Path, version: VersionCanasta) -> pd.DataFrame:

    if version == 2010:
        return _extraccion_2010(ruta)
    if version == 2013:
        return _extraccion_2013(ruta)
    if version == 2018:
        return _extraccion_2018(ruta)
    return _extraccion_2024(ruta)


# ------------------------------------------------------------


# 2010
def _extraccion_2010(ruta: Path) -> pd.DataFrame:

    return pd.DataFrame()


# ------------------------------------------------------------


# 2013

_PAGINAS_CCIF_2013 = (61, 71)
_PAGINAS_SCIAN_2013 = (72, 82)

_NUM = r"-?\d+\.\d+"
_FILA_RE = re.compile(
    rf"^\s*(?P<nombre>\S.*?)\s{{2,}}(?P<ponderador>{_NUM})\s+(?P<factor>{_NUM})\s*$"
)
_SOLO_NUMEROS_RE = re.compile(rf"^\s*{_NUM}\s+{_NUM}\s*$")

_CCIF_CLASE_RE = re.compile(r"^(\d{2}\.\d\.\d)\s+(.+)$")
_CCIF_GRUPO_RE = re.compile(r"^(\d{2}\.\d)\s+(.+)$")
_CCIF_DIVISION_RE = re.compile(r"^(\d{2})\s+(.+)$")

_SCIAN_SECTOR_RE = re.compile(r"^\d{2}(?:-\d{2})?\.\s+(.+)$")
_SCIAN_RAMA_RE = re.compile(r"^Rama\s+(\d{4})\.\s+(.+)$")

_RUIDO_RE = re.compile(
    r"Documento Metodológico INPC"
    r"|^\s*Anexo [IVX]+\s*$"
    r"|Ponderadores y Factor de Encadenamiento"
    r"|Clasificación del Consumo Individual por Finalidades"
    r"|Clasificación SCIAN"
    r"|Concepto\s+Ponderación"
    r"|La suma de ponderadores puede no ser"
    r"|^\s*\d{1,4}\s*$"
)
_SALTAR_2013 = {
    "inpc",
    "indice general",
    "sector economico primario",
    "sector economico secundario",
    "sector economico terciario",
}


def _extraccion_2013(ruta: Path) -> pd.DataFrame:
    """Extrae CCIF (Anexo I) y SCIAN (Anexo II) del manual completo 2013.

    Ver: tools/uso_generar_canasta.md §Diseño futuro: PDF y sincronización.
    """
    with open(ruta, "rb") as f:
        pdf = pdftotext.PDF(f, physical=True)

    ccif = _ccif_2013(_lineas(pdf, *_PAGINAS_CCIF_2013))
    scian = _scian_2013(_lineas(pdf, *_PAGINAS_SCIAN_2013))

    return ccif.merge(scian, on="generico", how="left")


def _lineas(pdf: "pdftotext.PDF", desde: int, hasta: int) -> list[str]:
    """Texto de las paginas `desde`-`hasta` (1-indexadas, inclusivas), separado por linea."""
    lineas: list[str] = []
    for i in range(desde - 1, hasta):
        lineas.extend(pdf[i].split("\n"))
    return lineas


def _reconstruir_filas(lineas: list[str]) -> list[tuple[str, str, str]]:
    """Filtra ruido y arma (nombre, ponderador, factor) por fila.

    Nombres largos se parten en 2 lineas fisicas con los valores numericos
    quedando entre las 2 mitades (quirk real del layout del pdf, no del
    extractor) -- se reconstruye juntando texto-numeros-texto en una sola fila.
    """
    filas: list[tuple[str, str, str]] = []
    nombre_parcial: str | None = None
    numeros_parciales: tuple[str, str] | None = None

    for linea in lineas:
        if _RUIDO_RE.search(linea):
            continue

        m = _FILA_RE.match(linea)
        if m:
            if nombre_parcial is None:
                filas.append((m["nombre"], m["ponderador"], m["factor"]))
            else:
                # continuacion con numeros pegados al fragmento de texto
                # (no siempre los numeros quedan solos en su propia linea)
                nombre_parcial = f"{nombre_parcial} {m['nombre']}"
                numeros_parciales = (m["ponderador"], m["factor"])
            continue

        m_num = _SOLO_NUMEROS_RE.match(linea)
        if m_num and nombre_parcial is not None and numeros_parciales is None:
            ponderador, factor = linea.split()
            numeros_parciales = (ponderador, factor)
            continue

        texto = linea.strip()
        if not texto:
            continue

        if nombre_parcial is None:
            nombre_parcial = texto
        else:
            nombre_completo = f"{nombre_parcial} {texto}"
            if numeros_parciales is not None:
                filas.append((nombre_completo, *numeros_parciales))
            nombre_parcial = None
            numeros_parciales = None

    return filas


def _ccif_2013(lineas: list[str]) -> pd.DataFrame:
    """generico/ponderador/encadenamiento/CCIF division/grupo/clase del Anexo I."""
    division = grupo = clase = ""
    filas: list[dict] = []

    for nombre, ponderador, factor in _reconstruir_filas(lineas):
        if normalizar_texto(nombre) in _SALTAR_2013:
            continue

        m = _CCIF_CLASE_RE.match(nombre)
        if m:
            clase = f"{m[1]} {normalizar_texto(m[2])}"
            continue
        m = _CCIF_GRUPO_RE.match(nombre)
        if m:
            grupo = f"{m[1]} {normalizar_texto(m[2])}"
            clase = ""
            continue
        m = _CCIF_DIVISION_RE.match(nombre)
        if m:
            division = f"{m[1]} {normalizar_texto(m[2])}"
            grupo = clase = ""
            continue

        filas.append(
            {
                "generico": quitar_prefijo_numerico(normalizar_texto(nombre)),
                "ponderador": ponderador,
                "encadenamiento": factor,
                "CCIF division": division,
                "CCIF grupo": grupo,
                "CCIF clase": clase,
            }
        )

    return pd.DataFrame(filas)


def _scian_2013(lineas: list[str]) -> pd.DataFrame:
    """generico/SCIAN sector/SCIAN rama del Anexo II.

    El codigo de `SCIAN sector` se deduce de los primeros 2 digitos de la
    `SCIAN rama` actual, no del encabezado de sector del pdf -- ese encabezado
    a veces trae un rango compuesto (ej. "48-49. Transportes...") que no es
    un codigo de 2 digitos valido por si solo.
    """
    sector_nombre = ""
    rama_codigo = rama_nombre = ""
    filas: list[dict] = []

    for nombre, _, _ in _reconstruir_filas(lineas):
        if nombre.strip() == "Anexo III":
            break
        if normalizar_texto(nombre) in _SALTAR_2013:
            continue

        m = _SCIAN_RAMA_RE.match(nombre)
        if m:
            rama_codigo, rama_nombre = m[1], m[2]
            continue
        m = _SCIAN_SECTOR_RE.match(nombre)
        if m:
            sector_nombre = m[1]
            continue

        filas.append(
            {
                "generico": quitar_prefijo_numerico(normalizar_texto(nombre)),
                "SCIAN sector": f"{rama_codigo[:2]} {normalizar_texto(sector_nombre)}",
                "SCIAN rama": f"{rama_codigo} {normalizar_texto(rama_nombre)}",
            }
        )

    return pd.DataFrame(filas)


# ------------------------------------------------------------


# 2018
def _extraccion_2018(ruta: Path) -> pd.DataFrame:

    return pd.DataFrame()


# ------------------------------------------------------------


# 2024
def _extraccion_2024(ruta: Path) -> pd.DataFrame:

    return pd.DataFrame()
