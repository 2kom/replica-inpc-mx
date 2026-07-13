import re
import unicodedata

import pandas as pd

_COLUMNAS_SIN_NORMALIZAR = {
    "ponderador",
    "encadenamiento",
    "canasta basica",
    "canasta consumo minimo",
}
_COLUMNAS_CONSERVAR_PREFIJO = {"SCIAN sector", "SCIAN rama"}

_RE_PREFIJO_NUMERICO = re.compile(r"^\d+[\.\-\)\s]\s*")
_RE_PUNTUACION = re.compile(r"[^\w\s]", re.UNICODE)


def quitar_tildes(texto: str) -> str:
    """Quita tildes conservando la ñ.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    resultado: list[str] = []
    for ch in unicodedata.normalize("NFD", texto):
        if unicodedata.combining(ch):
            # Conservar la tilde de la ñ (combining tilde U+0303)
            if resultado and resultado[-1] == "n" and ch == "\u0303":
                resultado[-1] = "ñ"
            elif resultado and resultado[-1] == "N" and ch == "\u0303":
                resultado[-1] = "Ñ"
            continue
        resultado.append(ch)
    return "".join(resultado)


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin tildes (con ñ), espacios normalizados.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    texto = str(texto).replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = quitar_tildes(texto)
    return texto.lower()


def quitar_prefijo_numerico(texto: str) -> str:
    """Quita prefijos como '1.', '01-', '2)' al inicio del texto.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    return _RE_PREFIJO_NUMERICO.sub("", texto)


def quitar_puntuacion(texto: str) -> str:
    """Quita comas, puntos, paréntesis y demás signos; conserva letras/dígitos/espacios.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    texto = _RE_PUNTUACION.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_celda(texto: str) -> str:
    """Minúsculas, tildes y puntuación fuera. Estándar para comparar/matchear genéricos.

    No toca prefijos numéricos — eso es un paso aparte (`quitar_prefijos`),
    posterior al matching, no parte del estándar de comparación.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    texto = normalizar_texto(texto)
    return quitar_puntuacion(texto)


def normalizar_genericos(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza las columnas de texto del DataFrame para comparar/matchear.

    Ponderador y encadenamiento se dejan tal cual.

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    df = df.copy()
    for col in df.columns:
        if col in _COLUMNAS_SIN_NORMALIZAR:
            continue
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str).map(normalizar_celda)
    return df


def quitar_prefijos(df: pd.DataFrame) -> pd.DataFrame:
    """Quita prefijos numéricos de las columnas de texto, justo antes de escribir el CSV.

    Se aplica DESPUÉS de resolver diferencias xlsx/pdf, no antes del matching
    (`normalizar_genericos`) — el prefijo nunca participa en la comparación.
    `SCIAN sector`/`SCIAN rama` lo conservan a propósito (es su código).

    Ver: tools/uso_generar_canasta.md §Normalizacion de texto
    """
    df = df.copy()
    for col in df.columns:
        if col in _COLUMNAS_SIN_NORMALIZAR or col in _COLUMNAS_CONSERVAR_PREFIJO:
            continue
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str).map(quitar_prefijo_numerico)
    return df
