"""Extracción de clasificaciones complementarias de PDFs INEGI."""

import re
from pathlib import Path

import pandas as pd
import pdfplumber

from canasta_inpc.normalizar import normalizar_celda


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

# Genérico sin prefijo numérico (2010): "Arroz 0.1215"
_RE_GENERICO_SIN_PREFIJO = re.compile(
    r"^([A-ZÁÉÍÓÚÜÑa-záéíóúüñ].*?)\s+(\d+\.\d+)\s*$"
)

# Ponderador suelto (línea que es solo un número decimal)
_RE_SOLO_PONDERADOR = re.compile(r"^\d+\.\d+$")
# Ponderador + factor (formato 2013)
_RE_SOLO_PONDERADOR_FACTOR = re.compile(r"^\d+\.\d+\s+\d+\.\d+$")

# ---------------------------------------------------------------------------
# Patrones 2024 (sidebar-tolerant: \b / (?<!\d) en vez de ^)
# ---------------------------------------------------------------------------
_RE_CCIF_GENERICO_2024 = re.compile(
    r"\b(\d{3})\s+(.+?)\s+(No duradero|Semiduradero|Duradero|Servicio)\s+([\d.]+)\b"
)
_RE_CCIF_CLASE_2024 = re.compile(r"(?<!\d)(\d{2}\.\d\.\d)\s+(.+?)\s+([\d.]+)(?:\s+.+)?$")
_RE_CCIF_GRUPO_2024 = re.compile(r"(?<!\d)(\d{2}\.\d)\s+(.+?)\s+([\d.]+)(?:\s+.+)?$")
_RE_CCIF_DIVISION_2024 = re.compile(
    r"(?<!\d)(0[1-9]|1[0-3])\s+(.+?)\s+([\d.]+)(?:\s+.+)?$"
)

_CODIGOS_SECTOR_SCIAN = (
    r"11|21|22|23|31|32|33|31-33|43|46|48|49|48-49|51|52|53|54|56|61|62|71|72|81|93"
)
_RE_SCIAN_GENERICO_2024 = re.compile(
    r"\b(\d{3})\s+(.+?)\s+(?:Primario|Secundario|Terciario)\s+([\d.]+)\b"
)
_RE_SCIAN_SECTOR_2024 = re.compile(
    rf"(?<!\d)({_CODIGOS_SECTOR_SCIAN})\s+(.+?)\s+([\d.]+)(?:\s+.+)?$"
)
_RE_SCIAN_RAMA_2024 = re.compile(
    r"(?<!\d)(\d{4})\s+(.+?)\s+([\d.]+)(?:\s+.+)?$"
)

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
    # 2010
    "serodarednop", "erbmeicid", "la", "noc", "ona",
    ".ocirotsih", ".8002", "hgine",
}

# Encabezados de sección y títulos de página
_ENCABEZADOS = (
    "Canasta del INPC clasificada",
    "Anexo C.", "Anexo D.", "Anexo E.", "Anexo F.",
    "C. Canasta", "D. Canasta",
    "Concepto Ponderador",
    "Concepto Ponderación",
    "Concepto Durabilidad Ponderador",
    "relativos a la segunda quincena",
    "dos a la segunda quincena",
)


def extraer_pdf(ruta: Path, version: int) -> pd.DataFrame:
    """Extrae clasificaciones complementarias del PDF INEGI.

    Devuelve DataFrame con columnas: generico, ponderador, + columnas PDF de la versión.
    """
    if version == 2010:
        return _extraer_2010(ruta)
    if version == 2013:
        return _extraer_2013(ruta)
    if version == 2018:
        return _extraer_2018(ruta)
    if version == 2024:
        return _extraer_2024(ruta)
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

        if "(Contin" in l or "Total general" in l or l.startswith("Nota:"):
            pagina_bloqueada = p
            continue

        if _es_ruido(l):
            continue

        resultado.append((p, l))

    return resultado


def _es_ruido(linea: str) -> bool:
    # Líneas muy cortas (fragmentos de sidebar, puntuación)
    if len(linea) <= 3:
        return True
    # Headers de página
    if linea.startswith("Documento Metodológico") or linea.startswith("Dooccuummeennttoo"):
        return True
    if linea.startswith("Concepto Ponderación") or linea.startswith("CCoonncceeppttoo"):
        return True
    if "ndice" in linea and "onsumidor" in linea and "INEGI" in linea:
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


# ---------------------------------------------------------------------------
# 2010
# ---------------------------------------------------------------------------

_MARCADORES_2010 = {
    "ccif": "CCIF y ponderaciones",
}


def _extraer_2010(ruta: Path) -> pd.DataFrame:
    paginas = _leer_paginas(ruta)
    secciones = _separar_secciones(paginas, _MARCADORES_2010)
    lineas = _reconstruir_multilinea(_filtrar_ruido(secciones["ccif"]))
    datos = _parsear_ccif_2010(lineas)
    if not datos:
        return pd.DataFrame()
    return pd.DataFrame(datos)


def _parsear_ccif_2010(lineas: list[str]) -> list[dict]:
    division = ""
    grupo = ""
    clase = ""
    resultados: list[dict] = []

    for linea in lineas:
        # Clase: "01.1.1 Pan y cereales 3.6767"
        m = _RE_CCIF_CLASE.match(linea)
        if m:
            clase = m.group(2)
            continue

        # Grupo: "01.1 ALIMENTOS 16.9006"
        m = _RE_CCIF_GRUPO.match(linea)
        if m:
            grupo = m.group(2)
            clase = ""
            continue

        # División: "01 ALIMENTOS Y BEBIDAS NO ALCOHÓLICAS 18.9173"
        m = _RE_CCIF_DIVISION.match(linea)
        if m:
            division = m.group(2)
            grupo = ""
            clase = ""
            continue

        # Genérico: "Arroz 0.1215" (sin prefijo numérico)
        m = _RE_GENERICO_SIN_PREFIJO.match(linea)
        if m:
            nombre = m.group(1)
            # Saltar líneas de agregado (INPC, Total)
            if nombre.upper() in ("INPC", "TOTAL"):
                continue
            if not division:
                continue
            resultados.append({
                "generico": nombre,
                "ponderador": m.group(2),
                "CCIF division": division,
                "CCIF grupo": grupo,
                "CCIF clase": clase,
            })

    return resultados


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
    """True si la línea parece continuación de un nombre (no empieza con dígito, no es ruido, sin ponderador propio)."""
    if not linea or len(linea) < 4:
        return False
    if linea[0].isdigit():
        return False
    if _es_ruido(linea):
        return False
    if _tiene_ponderador_final(linea):
        return False
    return True


# ---------------------------------------------------------------------------
# 2013
# ---------------------------------------------------------------------------

_MARCADORES_2013 = {
    "scian": "Anexo II",   # verificar antes que "Anexo I" (es substring)
    "ccif": "Anexo I",
}

# Línea con concepto + ponderador + factor (formato 2013)
_RE_LINEA_2013 = re.compile(r"^(.+?)\s+([\d.]+)\s+([\d.]+)$")
# División: "01 NOMBRE... pond factor"
_RE_DIVISION_2013 = re.compile(r"^(\d{2})\s+(.+?)\s+[\d.]+\s+[\d.]+$")
# Sub-nivel CCIF: "01.1" o "01.1.1"
_RE_SUBNIVEL_2013 = re.compile(r"^\d{2}(?:\.\d)+")
# Sector SCIAN: "11. Nombre" o "31-33. Nombre" con pond+factor
_RE_SECTOR_2013 = re.compile(
    r"^(\d{2}(?:-\d{2})?)\.?\s+(.+?)\s+([\d.]+)\s+([\d.]+)$"
)
# Rama SCIAN: "Rama 1111. Nombre" con pond+factor
_RE_RAMA_2013 = re.compile(
    r"^Rama\s+(\d{4})\.?\s+(.+?)\s+([\d.]+)\s+([\d.]+)$", re.IGNORECASE
)


def _des_duplicar_bold(texto: str) -> str:
    """Des-duplica texto bold del PDF 2013 donde cada carácter aparece dos veces.

    Opera token por token y solo colapsa los casos donde casi todos los
    caracteres vienen en pares consecutivos (CClLaassee -> Clase, 1111.. -> 11.).
    Evita degradar tokens válidos como II, III, 11 o 22.
    """
    palabras = texto.split(" ")
    resultado: list[str] = []
    for palabra in palabras:
        if len(palabra) == 2 and palabra[0] == palabra[1] and palabra[0].islower():
            resultado.append(palabra[0])
            continue
        if len(palabra) < 4:
            resultado.append(palabra)
            continue

        limite_pares = len(palabra) - (len(palabra) % 2)
        total_pares = limite_pares // 2
        pares_ok = sum(
            1
            for i in range(0, limite_pares, 2)
            if palabra[i] == palabra[i + 1]
        )
        if total_pares == 0 or (pares_ok / total_pares) < 0.8:
            resultado.append(palabra)
            continue

        chars = [palabra[i] for i in range(0, limite_pares, 2)]
        if len(palabra) % 2:
            chars.append(palabra[-1])
        resultado.append("".join(chars))
    return " ".join(resultado)


def _preprocesar_2013(lineas: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Aplica des-duplicación de bold a cada línea."""
    return [(p, _des_duplicar_bold(l)) for p, l in lineas]


def _separar_secciones_2013(
    lineas: list[tuple[int, str]],
) -> dict[str, list[tuple[int, str]]]:
    """Separa anexos 2013 por coincidencia exacta en el PDF crudo.

    No reutiliza _separar_secciones porque "Anexo I" es substring de
    "Anexo II" y "Anexo III", y la des-duplicación puede alterar los romanos.
    """
    secciones = {"ccif": [], "scian": []}
    seccion_actual: str | None = None

    for pagina, linea in lineas:
        if linea == "Anexo I":
            seccion_actual = "ccif"
            continue
        if linea == "Anexo II":
            seccion_actual = "scian"
            continue
        if linea == "Anexo III":
            seccion_actual = None
            continue

        if seccion_actual is not None:
            secciones[seccion_actual].append((pagina, linea))

    return secciones


def _reconstruir_multilinea_2013(lineas: list[tuple[int, str]]) -> list[str]:
    """Reconstruye líneas 2013 con patrón texto + ponderador/factor + continuación.

    A diferencia de 2018/2024, aquí cada fila válida termina con dos números
    (ponderador y factor). No hacemos una pasada general de continuaciones para
    no mezclar genéricos completos con la siguiente rama o sector.
    """
    resultado: list[str] = []
    i = 0

    while i < len(lineas):
        _, linea = lineas[i]

        if i + 2 < len(lineas):
            _, l1 = lineas[i + 1]
            _, l2 = lineas[i + 2]
            if (
                _parece_inicio_estructura_2013(linea)
                and not _tiene_ponderador_y_factor_final(linea)
                and _RE_SOLO_PONDERADOR_FACTOR.match(l1)
                and _es_continuacion_texto(l2)
            ):
                resultado.append(f"{linea} {l2} {l1}")
                i += 3
                continue

            m_l1 = _extraer_texto_y_numeros_final_2013(l1)
            if (
                _parece_inicio_estructura_2013(linea)
                and not _tiene_ponderador_y_factor_final(linea)
                and m_l1
                and m_l1[0]
                and m_l1[0][0].islower()
                and _es_continuacion_texto(l2)
            ):
                resultado.append(f"{linea} {m_l1[0]} {l2} {m_l1[1]}")
                i += 3
                continue

        if i + 1 < len(lineas):
            _, l1 = lineas[i + 1]
            if (
                _parece_inicio_estructura_2013(linea)
                and not _tiene_ponderador_y_factor_final(linea)
                and _RE_SOLO_PONDERADOR_FACTOR.match(l1)
            ):
                resultado.append(f"{linea} {l1}")
                i += 2
                continue

            m_l1 = _extraer_texto_y_numeros_final_2013(l1)
            if (
                _parece_inicio_estructura_2013(linea)
                and not _tiene_ponderador_y_factor_final(linea)
                and m_l1
                and m_l1[0]
                and m_l1[0][0].islower()
            ):
                resultado.append(f"{linea} {m_l1[0]} {m_l1[1]}")
                i += 2
                continue

        resultado.append(linea)
        i += 1

    return resultado


def _extraer_2013(ruta: Path) -> pd.DataFrame:
    paginas = _leer_paginas(ruta)
    secciones_raw = _separar_secciones_2013(paginas)
    secciones = {
        nombre: _preprocesar_2013(datos)
        for nombre, datos in secciones_raw.items()
    }

    lineas_ccif = _reconstruir_multilinea_2013(_filtrar_ruido(secciones["ccif"]))
    lineas_scian = _reconstruir_multilinea_2013(_filtrar_ruido(secciones["scian"]))

    datos_ccif = _parsear_ccif_2013(lineas_ccif)
    datos_scian = _parsear_scian_2013(lineas_scian)
    return _combinar_2013(datos_ccif, datos_scian)


def _parsear_ccif_2013(lineas: list[str]) -> list[dict]:
    division = ""
    grupo = ""
    clase = ""
    resultados: list[dict] = []

    for linea in lineas:
        if "Factor de Encadenamiento" in linea or linea.startswith("Anexo"):
            continue

        m = _RE_LINEA_2013.match(linea)
        if not m:
            continue

        concepto = m.group(1).strip()
        ponderador = m.group(2)

        # División: "01 NOMBRE"
        m_div = _RE_DIVISION_2013.match(linea)
        if m_div:
            division = m_div.group(2)
            grupo = ""
            clase = ""
            continue

        if concepto.lower() in {"inpc", "indice general", "índice general"}:
            continue

        # Sub-nivel (grupo o clase): "01.1" o "01.1.1"
        m_sub = _RE_SUBNIVEL_2013.match(concepto)
        if m_sub:
            codigo = m_sub.group()
            nombre = concepto[len(codigo):].strip()
            if codigo.count(".") == 1:
                grupo = nombre
                clase = ""
            elif codigo.count(".") == 2:
                clase = nombre
            continue

        if re.match(r"^\d{1,2}\s+", concepto):
            continue
        if not division:
            continue
        if len(concepto) < 3:
            continue

        resultados.append({
            "generico": concepto,
            "ponderador": ponderador,
            "CCIF division": division,
            "CCIF grupo": grupo,
            "CCIF clase": clase,
        })

    return resultados


def _parsear_scian_2013(lineas: list[str]) -> list[dict]:
    sector = ""
    rama = ""
    resultados: list[dict] = []

    for linea in lineas:
        linea = _normalizar_codigo_scian_2013(linea)
        if linea.startswith("Anexo") or "Clasificación SCIAN" in linea:
            continue
        if linea.lower().startswith("sector econ"):
            continue

        # Rama: "Rama 1111. Nombre pond factor"
        m_rama = _RE_RAMA_2013.match(linea)
        if m_rama:
            rama = f"{m_rama.group(1)} {m_rama.group(2)}"
            continue

        # Sector: "11. Nombre pond factor"
        m_sector = _RE_SECTOR_2013.match(linea)
        if m_sector:
            codigo = m_sector.group(1)
            # Evitar confundir rama (4 dígitos) como sector
            if codigo.isdigit() and len(codigo) == 4:
                pass
            else:
                sector = f"{codigo} {m_sector.group(2)}"
                rama = ""
                continue

        # Genérico: "Nombre pond factor"
        m = _RE_LINEA_2013.match(linea)
        if not m:
            continue

        concepto = m.group(1).strip()
        ponderador = m.group(2)

        if concepto.lower() in {"indice general", "índice general"}:
            continue
        if concepto.lower().startswith("rama "):
            continue
        if re.match(r"^\d{2}(?:-\d{2})?\.?\s", concepto):
            continue
        if concepto and concepto[0].islower():
            continue
        if not sector or not rama:
            continue
        if len(concepto) < 3:
            continue

        resultados.append({
            "generico": concepto,
            "SCIAN sector": sector,
            "SCIAN rama": rama,
        })

    return resultados


def _combinar_2013(ccif: list[dict], scian: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(ccif)
    if df.empty:
        return pd.DataFrame()

    df_scian = pd.DataFrame(scian)
    if not df_scian.empty:
        df["_clave_generico"] = df["generico"].map(normalizar_celda)
        df_scian["_clave_generico"] = df_scian["generico"].map(normalizar_celda)
        df = df.merge(
            df_scian.drop(columns=["generico"]),
            on="_clave_generico",
            how="left",
        )
        df.drop(columns=["_clave_generico"], inplace=True)

    for col in ("SCIAN sector", "SCIAN rama"):
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("")

    return df


def _tiene_ponderador_y_factor_final(linea: str) -> bool:
    return bool(re.search(r"\d+\.\d+\s+\d+\.\d+\s*$", linea))


def _extraer_texto_y_numeros_final_2013(linea: str) -> tuple[str, str] | None:
    m = re.match(r"^(.+?)\s+(\d+\.\d+\s+\d+\.\d+)\s*$", linea)
    if not m:
        return None
    return m.group(1).strip(), m.group(2)


def _parece_inicio_estructura_2013(linea: str) -> bool:
    return bool(
        re.match(r"^(?:Rama\s+\d{4}\.?|(?:\d{2}(?:-\d{2})?|\d{2}\.\d(?:\.\d)?)\.?)\s", linea)
    )


def _normalizar_codigo_scian_2013(linea: str) -> str:
    return re.sub(r"^(\d{2})-(\d)\2(\d)\3\.\.", r"\1-\2\3.", linea)


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


# ---------------------------------------------------------------------------
# 2024
# ---------------------------------------------------------------------------

_MARCADORES_2024 = {
    "ccif": "la CCIF",
    "scian": "SCIAN 2023",
}


def _extraer_2024(ruta: Path) -> pd.DataFrame:
    paginas = _leer_paginas(ruta)
    secciones = _separar_secciones(paginas, _MARCADORES_2024)

    lineas_ccif = _reconstruir_multilinea(_filtrar_ruido(secciones["ccif"]))
    lineas_scian = _reconstruir_multilinea(_filtrar_ruido(secciones["scian"]))

    datos_ccif = _parsear_ccif_2024(lineas_ccif)
    datos_scian = _parsear_scian_2024(lineas_scian)
    return _combinar_2024(datos_ccif, datos_scian)


def _parsear_ccif_2024(lineas: list[str]) -> list[dict]:
    division = ""
    grupo = ""
    clase = ""
    resultados: list[dict] = []

    for linea in lineas:
        m = _RE_CCIF_GENERICO_2024.search(linea)
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

        m = _RE_CCIF_CLASE_2024.search(linea)
        if m:
            clase = m.group(2)
            continue

        m = _RE_CCIF_GRUPO_2024.search(linea)
        if m:
            grupo = m.group(2)
            clase = ""
            continue

        m = _RE_CCIF_DIVISION_2024.search(linea)
        if m:
            division = m.group(2)
            grupo = ""
            clase = ""

    return resultados


def _parsear_scian_2024(lineas: list[str]) -> list[dict]:
    sector = ""
    rama = ""
    resultados: list[dict] = []

    for linea in lineas:
        m = _RE_SCIAN_RAMA_2024.search(linea)
        if m:
            rama = f"{m.group(1)} {m.group(2)}"
            continue

        m = _RE_SCIAN_SECTOR_2024.search(linea)
        if m:
            sector = f"{m.group(1)} {m.group(2)}"
            rama = ""
            continue

        m = _RE_SCIAN_GENERICO_2024.search(linea)
        if m:
            resultados.append({
                "generico": m.group(2),
                "SCIAN sector": sector,
                "SCIAN rama": rama,
            })

    return resultados


def _combinar_2024(ccif: list[dict], scian: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(ccif)
    if df.empty:
        return pd.DataFrame()

    df_scian = pd.DataFrame(scian)
    if not df_scian.empty:
        df = df.merge(df_scian, on="generico", how="left")

    for col in ("SCIAN sector", "SCIAN rama"):
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("")

    return df
