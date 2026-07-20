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

_PAGINAS_COG_2010 = (61, 66)
_PAGINAS_CCIF_2010 = (67, 72)

_NUM = r"-?\d+\.\d+"
_FILA_RE_2010_CCIF = re.compile(rf"^\s*(?P<nombre>\S.*?)\s{{2,}}(?P<ponderador>{_NUM})\s*$")
_FILA_RE_2010_COG = re.compile(rf"^(?P<nombre>\S.*?)\s+(?P<ponderador>{_NUM})\s*$")

_CCIF_CLASE_RE = re.compile(r"^(\d{2}\.\d\.\d)\s+(.+)$")
_CCIF_GRUPO_RE = re.compile(r"^(\d{2}\.\d)\s+(.+)$")
_CCIF_DIVISION_RE = re.compile(r"^(\d{2})\s+(.+)$")

_SALTAR_2010 = {"total", "inpc"}

# categorias COG de 2010 (Anexo D): sin codigo numerico ni palabra clave que
# las distinga de un generico por regex sola, asi que se detectan contra
# esta lista fija -- confirmado 1:1 contra el COG real de extraccion_xlsx.py
_COG_CATEGORIAS_2010 = {
    "alimentos bebidas y tabaco",
    "ropa calzado y accesorios",
    "vivienda",
    "muebles aparatos y accesorios domesticos",
    "salud y cuidado personal",
    "transporte",
    "educacion y esparcimiento",
    "otros servicios",
}

# Anexo D tiene texto justificado -- en modo raw (el que usa _cog_2010) casi
# no glitchea, salvo estos 3 nombres reales (letras pegadas o partidas por
# el espaciado de la justificacion, confirmado contra el COG real del xlsx:
# sin esta correccion, "otros servicios" ni se detecta como categoria y
# arrastra su ponderador de subtotal como si fuera un generico mas)
_CORRECCIONES_COG_2010 = {
    "otroschilesfrescos": "otros chiles frescos",
    "otrosm ariscos": "otros mariscos",
    "otrosse rvicios": "otros servicios",
}


def _extraccion_2010(ruta: Path) -> pd.DataFrame:
    """Extrae CCIF (Anexo E) y COG (Anexo D) del manual completo 2010.

    2010 no trae SCIAN en el pdf (se copia de 2013 via `--sincronizar`, ver
    `FUENTES_POSIBLES`) ni `encadenamiento` (la version no tiene esa columna
    en ninguna fuente). Anexo D usa modo `raw` de pdftotext, no `physical`
    como el resto de la extraccion -- en `physical`, el texto justificado de
    Anexo D inserta espacios espurios dentro de palabras (ej. "a ccesorios"
    en vez de "accesorios"), confirmado comparando contra el COG real del
    xlsx; `raw` lo evita casi por completo.

    Ver: tools/uso_generar_canasta.md §Cruce `xlsx` + `pdf`.
    """
    with open(ruta, "rb") as f:
        pdf_physical = pdftotext.PDF(f, physical=True)
    with open(ruta, "rb") as f:
        pdf_raw = pdftotext.PDF(f, raw=True)

    ccif = _ccif_2010(_lineas(pdf_physical, *_PAGINAS_CCIF_2010))
    cog = _cog_2010(_lineas(pdf_raw, *_PAGINAS_COG_2010))

    return ccif.merge(cog, on="generico", how="left")


def _ccif_2010(lineas: list[str]) -> pd.DataFrame:
    """generico/ponderador/CCIF division/grupo/clase del Anexo E.

    A diferencia de 2013, cada fila es una sola linea fisica -- el pdf 2010
    no tiene el quirk de nombres partidos en 2 lineas, asi que no hace falta
    reconstruir filas.
    """
    division = grupo = clase = ""
    filas: list[dict] = []

    for linea in lineas:
        m = _FILA_RE_2010_CCIF.match(linea)
        if not m:
            continue
        nombre, ponderador = m["nombre"], m["ponderador"]
        if normalizar_texto(nombre) in _SALTAR_2010:
            continue

        m_clase = _CCIF_CLASE_RE.match(nombre)
        if m_clase:
            clase = f"{m_clase[1]} {normalizar_texto(m_clase[2])}"
            continue
        m_grupo = _CCIF_GRUPO_RE.match(nombre)
        if m_grupo:
            grupo = f"{m_grupo[1]} {normalizar_texto(m_grupo[2])}"
            clase = ""
            continue
        m_division = _CCIF_DIVISION_RE.match(nombre)
        if m_division:
            division = f"{m_division[1]} {normalizar_texto(m_division[2])}"
            grupo = clase = ""
            continue

        filas.append(
            {
                "generico": quitar_prefijo_numerico(normalizar_texto(nombre)),
                "ponderador": ponderador,
                "CCIF division": division,
                "CCIF grupo": grupo,
                "CCIF clase": clase,
            }
        )

    return pd.DataFrame(filas)


def _cog_2010(lineas: list[str]) -> pd.DataFrame:
    """generico/COG del Anexo D."""
    categoria = ""
    filas: list[dict] = []

    for linea in lineas:
        m = _FILA_RE_2010_COG.match(linea)
        if not m:
            continue
        norm = normalizar_texto(m["nombre"])
        norm = _CORRECCIONES_COG_2010.get(norm, norm)
        if norm in _SALTAR_2010:
            continue
        if norm in _COG_CATEGORIAS_2010:
            categoria = norm
            continue

        filas.append({"generico": quitar_prefijo_numerico(norm), "COG": categoria})

    return pd.DataFrame(filas)


# ------------------------------------------------------------


# 2013

_PAGINAS_CCIF_2013 = (61, 71)
_PAGINAS_SCIAN_2013 = (72, 82)

_FILA_RE = re.compile(
    rf"^\s*(?P<nombre>\S.*?)\s{{2,}}(?P<ponderador>{_NUM})\s+(?P<factor>{_NUM})\s*$"
)
_SOLO_NUMEROS_RE = re.compile(rf"^\s*{_NUM}\s+{_NUM}\s*$")

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

    Ver: tools/uso_generar_canasta.md §Cruce `xlsx` + `pdf`.
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
