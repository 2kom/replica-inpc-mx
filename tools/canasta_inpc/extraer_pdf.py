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

# Ponderador suelto (línea que es solo un número decimal)
_RE_SOLO_PONDERADOR = re.compile(r"^\d+\.\d+$")

# ---------------------------------------------------------------------------
# Detección de secciones
# ---------------------------------------------------------------------------
_MARCADORES_SECCION = {
    "ccif": "clasificada por CCIF",
    "cog": "Objeto del gasto",
    "scian": "clasificada por SCIAN",
}

# Sidebar invertido: palabras conocidas del texto vertical del PDF
_SIDEBAR_INVERTIDO = {
    "ed", "oiluj", "anecniuq", "adnuges", "esab",
    "ocigolodotem", "otnemucod", "rodimunsnoc",
    "laciremoc", "noicubirtsid", "noisimsnart", "noicareneg",
    "soicerp", "lanoican", "ecidni", ".igeni",
}

# Encabezados de sección y títulos de página
_ENCABEZADOS = (
    "Canasta del INPC clasificada",
    "Anexo C.", "Anexo D.", "Anexo E.", "Anexo F.",
    "C. Canasta", "D. Canasta",
    "Concepto Ponderador",
    "Concepto Durabilidad Ponderador",
    "relativos a la segunda quincena",
    "dos a la segunda quincena",
)


def extraer_pdf(ruta: Path, version: int) -> pd.DataFrame:
    """Extrae clasificaciones complementarias del PDF INEGI.

    Devuelve DataFrame con columnas: generico, ponderador, + columnas PDF de la versión.
    """
    if version == 2018:
        return _extraer_2018(ruta)
    raise NotImplementedError(f"Versión {version} no implementada aún")


# ---------------------------------------------------------------------------
# Pipeline de preprocesamiento
# ---------------------------------------------------------------------------


def _leer_paginas(ruta: Path) -> list[tuple[int, str]]:
    """Paso 1: lee el PDF y devuelve (pagina, linea) para cada línea."""
    resultado: list[tuple[int, str]] = []
    with pdfplumber.open(ruta) as pdf:
        for i, page in enumerate(pdf.pages):
            texto = page.extract_text() or ""
            for raw in texto.split("\n"):
                linea = " ".join(raw.split()).strip()
                if linea:
                    resultado.append((i, linea))
    return resultado


def _filtrar_ruido(lineas: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Paso 2: elimina líneas que no son datos.

    Después de un marcador de fin de datos en una página, todo lo restante
    de esa página se descarta (sidebar invertido, pie de página).
    """
    resultado: list[tuple[int, str]] = []
    pagina_bloqueada: int | None = None

    for p, l in lineas:
        if p != pagina_bloqueada:
            pagina_bloqueada = None

        if pagina_bloqueada is not None:
            continue

        if l.startswith("(Contin") or l.startswith("Total general") or l.startswith("Nota:"):
            pagina_bloqueada = p
            continue

        if _es_ruido(l):
            continue

        resultado.append((p, l))

    return resultado


def _es_ruido(linea: str) -> bool:
    # Líneas cortas sin letras (fragmentos numéricos sueltos, puntuación)
    if len(linea) <= 3 and not re.search(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]", linea):
        return True
    # Headers de página
    if linea.startswith("Documento Metodológico") or linea.startswith("Dooccuummeennttoo"):
        return True
    if linea.startswith("Concepto Ponderación") or linea.startswith("CCoonncceeppttoo"):
        return True
    if "INEGI. Índice nacional de precios al consumidor" in linea:
        return True
    # Encabezados de sección
    if any(linea.startswith(e) for e in _ENCABEZADOS):
        return True
    # Sidebar invertido por nombre
    if linea.lower() in _SIDEBAR_INVERTIDO:
        return True
    # Sidebar invertido por patrón: corto y termina en mayúscula
    if linea[-1].isupper() and len(linea) < 15 and not linea[0].isdigit():
        return True
    return False


def _separar_secciones(
    lineas: list[tuple[int, str]],
    marcadores: dict[str, str],
) -> dict[str, list[tuple[int, str]]]:
    """Paso 3: agrupa líneas por sección según marcadores de texto."""
    secciones: dict[str, list[tuple[int, str]]] = {k: [] for k in marcadores}
    seccion_actual: str | None = None

    for pagina, linea in lineas:
        # Detectar cambio de sección
        nueva = None
        for nombre, marcador in marcadores.items():
            if marcador in linea:
                nueva = nombre
                break
        if nueva:
            seccion_actual = nueva
            continue

        if seccion_actual is not None and seccion_actual in secciones:
            secciones[seccion_actual].append((pagina, linea))

    return secciones


def _reconstruir_multilinea(lineas: list[tuple[int, str]]) -> list[str]:
    """Paso 4: une líneas partidas y devuelve líneas limpias sin número de página."""
    resultado: list[str] = []

    i = 0
    while i < len(lineas):
        _, linea = lineas[i]

        # Patrón b+c: línea sin ponderador + línea solo ponderador + continuación
        if i + 2 < len(lineas):
            _, l1 = lineas[i + 1]
            _, l2 = lineas[i + 2]
            if (
                linea[0].isdigit()
                and not _RE_SOLO_PONDERADOR.match(linea)
                and not _tiene_ponderador_final(linea)
                and _RE_SOLO_PONDERADOR.match(l1)
                and _es_continuacion_texto(l2)
            ):
                resultado.append(f"{linea} {l2} {l1}")
                i += 3
                continue

        # Patrón b: línea sin ponderador + línea solo ponderador
        if i + 1 < len(lineas):
            _, l1 = lineas[i + 1]
            if (
                linea[0].isdigit()
                and not _RE_SOLO_PONDERADOR.match(linea)
                and not _tiene_ponderador_final(linea)
                and _RE_SOLO_PONDERADOR.match(l1)
            ):
                resultado.append(f"{linea} {l1}")
                i += 2
                continue

        resultado.append(linea)
        i += 1

    # Segunda pasada: unir continuaciones simples (patrón a)
    final: list[str] = []
    for linea in resultado:
        if final and _es_continuacion_texto(linea):
            prev = final[-1]
            m = re.search(r"\s+([\d.]+)\s*$", prev)
            if m:
                nombre = prev[: m.start()]
                ponderador = m.group(1)
                final[-1] = f"{nombre} {linea} {ponderador}"
            else:
                final[-1] = f"{prev} {linea}"
        else:
            final.append(linea)

    return final


def _tiene_ponderador_final(linea: str) -> bool:
    return bool(re.search(r"\d+\.\d+\s*$", linea))


def _es_continuacion_texto(linea: str) -> bool:
    """True si la línea parece continuación de un nombre (no empieza con dígito, no es ruido)."""
    if not linea or len(linea) < 4:
        return False
    if linea[0].isdigit():
        return False
    if _es_ruido(linea):
        return False
    return True


# ---------------------------------------------------------------------------
# 2018
# ---------------------------------------------------------------------------


def _extraer_2018(ruta: Path) -> pd.DataFrame:
    paginas = _leer_paginas(ruta)
    secciones = _separar_secciones(paginas, _MARCADORES_SECCION)

    lineas_ccif = _reconstruir_multilinea(_filtrar_ruido(secciones["ccif"]))
    lineas_cog = _reconstruir_multilinea(_filtrar_ruido(secciones["cog"]))
    lineas_scian = _reconstruir_multilinea(_filtrar_ruido(secciones["scian"]))

    datos_ccif = _parsear_ccif_2018(lineas_ccif)
    datos_cog = _parsear_cog_2018(lineas_cog)
    datos_scian = _parsear_scian_2018(lineas_scian)
    return _combinar_2018(datos_ccif, datos_cog, datos_scian)


# ---------------------------------------------------------------------------
# Parsers 2018 (sin cambios respecto a la versión anterior)
# ---------------------------------------------------------------------------


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
