"""Extracción de clasificaciones complementarias de PDFs INEGI."""

import re
from pathlib import Path

import pandas as pd
import pdfplumber


# ---------------------------------------------------------------------------
# Patrones CCIF (Anexo C en 2018)
# ---------------------------------------------------------------------------
# Genérico: "001 Arroz No duradero 0.2064"
_RE_CCIF_GENERICO = re.compile(
    r"^(\d{3})\s+(.+?)\s+(No duradero|Semiduradero|Duradero|Servicio)\s+([\d.]+)\s*$"
)
# Clase: "01.1.1 Pan y cereales 5.3194"
_RE_CCIF_CLASE = re.compile(r"^(\d{2}\.\d\.\d)\s+(.+?)\s+([\d.]+)\s*$")
# Grupo: "01.1 Alimentos 22.2216"
_RE_CCIF_GRUPO = re.compile(r"^(\d{2}\.\d)\s+(.+?)\s+([\d.]+)\s*$")
# División: "01 Alimentos y bebidas no alcohólicas 25.7630"
_RE_CCIF_DIVISION = re.compile(r"^(\d{2})\s+(.+?)\s+([\d.]+)\s*$")

# ---------------------------------------------------------------------------
# Patrones SCIAN (Anexo E en 2018)
# ---------------------------------------------------------------------------
# Rama: "3111 Elaboración de alimentos para animales 0.5610"
_RE_SCIAN_RAMA = re.compile(r"^(\d{4})\s+(.+?)\s+([\d.]+)\s*$")
# Sector: "11 Agricultura, cría y explotación... 6.2546"
_RE_SCIAN_SECTOR = re.compile(r"^(\d{2})\s+(.+?)\s+([\d.]+)\s*$")
# Genérico: "041 Alimento para mascotas 0.5610"
_RE_SCIAN_GENERICO = re.compile(r"^(\d{3})\s+(.+?)\s+([\d.]+)\s*$")

# ---------------------------------------------------------------------------
# Patrones COG (Anexo D en 2018)
# ---------------------------------------------------------------------------
# Top-level: "1. Alimentos, bebidas y tabaco 30.2908"
_RE_COG_TOPLEVEL = re.compile(r"^(\d)\.\s+(.+?)\s+([\d.]+)\s*$")
# Genérico: "001 Botanas elaboradas con cereales 0.1628"
_RE_COG_GENERICO = re.compile(r"^(\d{3})\s+(.+?)\s+([\d.]+)\s*$")

# Ponderador al final de una línea
_RE_PONDERADOR_FINAL = re.compile(r"\s+([\d.]+)\s*$")

# ---------------------------------------------------------------------------
# Detección de secciones
# ---------------------------------------------------------------------------
_MARCADORES_SECCION = {
    "ccif": "clasificada por CCIF",
    "cog": "Objeto del gasto",
    "scian": "clasificada por SCIAN",
}


def extraer_pdf(ruta: Path, version: int) -> pd.DataFrame:
    """Extrae clasificaciones complementarias del PDF INEGI.

    Devuelve DataFrame con columnas: generico, ponderador, + columnas PDF de la versión.
    """
    if version == 2018:
        return _extraer_2018(ruta)
    raise NotImplementedError(f"Versión {version} no implementada aún")


# ---------------------------------------------------------------------------
# 2018
# ---------------------------------------------------------------------------


def _extraer_2018(ruta: Path) -> pd.DataFrame:
    lineas_por_anexo = _clasificar_lineas(ruta)
    datos_ccif = _parsear_ccif_2018(lineas_por_anexo["ccif"])
    datos_cog = _parsear_cog_2018(lineas_por_anexo["cog"])
    datos_scian = _parsear_scian_2018(lineas_por_anexo["scian"])
    return _combinar_2018(datos_ccif, datos_cog, datos_scian)


def _clasificar_lineas(ruta: Path) -> dict[str, list[str]]:
    """Lee el PDF y separa líneas de datos por anexo, uniendo multi-línea."""
    raw: dict[str, list[str]] = {"ccif": [], "cog": [], "scian": []}
    seccion: str | None = None

    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            fin_datos = False
            for linea in texto.split("\n"):
                linea = linea.strip()
                if not linea:
                    continue

                # Marcar fin de datos en esta página: después de estos
                # marcadores solo hay pie de página y sidebar invertido
                if linea.startswith("(Contin") or linea.startswith("Total general") or linea.startswith("Nota:"):
                    fin_datos = True
                    continue

                if fin_datos:
                    continue

                # Detectar cambio de sección
                nueva_seccion = _detectar_seccion(linea)
                if nueva_seccion:
                    seccion = nueva_seccion
                    continue

                if seccion not in raw:
                    continue

                if _es_linea_datos(linea):
                    raw[seccion].append(linea)
                elif _es_continuacion(linea, raw[seccion]):
                    _unir_continuacion(raw[seccion], linea)

    return raw


def _detectar_seccion(linea: str) -> str | None:
    for seccion, marcador in _MARCADORES_SECCION.items():
        if marcador in linea:
            return seccion
    return None


def _es_linea_datos(linea: str) -> bool:
    if len(linea) < 5:
        return False
    return linea[0].isdigit()


def _es_continuacion(linea: str, buffer: list[str]) -> bool:
    """True si la línea parece ser continuación de un nombre multi-línea."""
    if not buffer:
        return False
    if len(linea) < 4:
        return False
    if linea[0].isdigit():
        return False
    # Descartar ruido: headers, footers, texto invertido del sidebar
    if linea[0] in ".(" or linea.startswith("INEGI") or linea.startswith("SNIEG"):
        return False
    # Texto invertido del sidebar tiene mayúsculas al final (ecidnÍ, lanoicaN)
    if linea[-1].isupper() and len(linea) < 15:
        return False
    return True


def _unir_continuacion(buffer: list[str], continuacion: str) -> None:
    """Une la continuación al nombre de la línea anterior, antes del ponderador."""
    prev = buffer[-1]
    m = _RE_PONDERADOR_FINAL.search(prev)
    if m:
        nombre = prev[: m.start()]
        ponderador = m.group(1)
        buffer[-1] = f"{nombre} {continuacion} {ponderador}"
    else:
        buffer[-1] = f"{prev} {continuacion}"


def _parsear_ccif_2018(lineas: list[str]) -> list[dict]:
    division = ""
    grupo = ""
    clase = ""
    resultados: list[dict] = []

    for linea in lineas:
        m = _RE_CCIF_GENERICO.match(linea)
        if m:
            resultados.append({
                "generico": m.group(2),
                "ponderador": m.group(4),
                "CCIF division": division,
                "CCIF grupo": grupo,
                "CCIF clase": clase,
                "durabilidad": m.group(3),
            })
            continue

        m = _RE_CCIF_CLASE.match(linea)
        if m:
            clase = m.group(2)
            continue

        m = _RE_CCIF_GRUPO.match(linea)
        if m:
            grupo = m.group(2)
            clase = ""
            continue

        m = _RE_CCIF_DIVISION.match(linea)
        if m:
            division = m.group(2)
            grupo = ""
            clase = ""

    return resultados


def _parsear_cog_2018(lineas: list[str]) -> list[dict]:
    cog = ""
    resultados: list[dict] = []

    for linea in lineas:
        m = _RE_COG_GENERICO.match(linea)
        if m:
            resultados.append({
                "generico": m.group(2),
                "COG": cog,
            })
            continue

        m = _RE_COG_TOPLEVEL.match(linea)
        if m:
            cog = m.group(2)

    return resultados


def _parsear_scian_2018(lineas: list[str]) -> list[dict]:
    sector = ""
    rama = ""
    resultados: list[dict] = []

    for linea in lineas:
        m = _RE_SCIAN_RAMA.match(linea)
        if m:
            rama = f"{m.group(1)} {m.group(2)}"
            continue

        m = _RE_SCIAN_SECTOR.match(linea)
        if m:
            sector = f"{m.group(1)} {m.group(2)}"
            rama = ""
            continue

        m = _RE_SCIAN_GENERICO.match(linea)
        if m:
            resultados.append({
                "generico": m.group(2),
                "SCIAN sector": sector,
                "SCIAN rama": rama,
            })

    return resultados


def _combinar_2018(ccif: list[dict], cog: list[dict], scian: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(ccif)
    if df.empty:
        return pd.DataFrame()

    for datos in [cog, scian]:
        df_extra = pd.DataFrame(datos)
        if not df_extra.empty:
            df = df.merge(df_extra, on="generico", how="left")

    for col in ("COG", "SCIAN sector", "SCIAN rama"):
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("")

    return df
