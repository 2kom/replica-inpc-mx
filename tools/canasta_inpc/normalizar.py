import re
import unicodedata

import pandas as pd

_COLUMNAS_SIN_NORMALIZAR = {"ponderador", "encadenamiento", "canasta basica", "canasta consumo minimo"}

_RE_PREFIJO_NUMERICO = re.compile(r"^\d+[\.\-\)\s]\s*")


def quitar_tildes(texto: str) -> str:
    """Quita tildes conservando la ñ."""
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
    """Minúsculas, sin tildes (con ñ), espacios normalizados."""
    texto = str(texto).replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = quitar_tildes(texto)
    return texto.lower()


def quitar_prefijo_numerico(texto: str) -> str:
    """Quita prefijos como '1.', '01-', '2)' al inicio del texto."""
    return _RE_PREFIJO_NUMERICO.sub("", texto)


def normalizar_celda(texto: str) -> str:
    """Normalización completa para genéricos y clasificaciones."""
    texto = normalizar_texto(texto)
    texto = quitar_prefijo_numerico(texto)
    return texto


def normalizar_genericos(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza las columnas de texto del DataFrame.

    Ponderador y encadenamiento se dejan tal cual.
    """
    df = df.copy()
    for col in df.columns:
        if col in _COLUMNAS_SIN_NORMALIZAR:
            continue
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str).map(normalizar_celda)
    return df
