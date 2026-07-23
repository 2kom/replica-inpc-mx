from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from canasta_inpc.esquema import VersionCanasta
from canasta_inpc.utilidades import guardar_csv, normalizar_texto

_COLUMNAS_SCIAN = ("SCIAN sector", "SCIAN rama")
_VERSION_DESTINO: VersionCanasta = 2010


@dataclass
class ResultadoSincronizacion:
    """Df de 2010 ya sincronizado, mas el detalle de que genericos cambiaron."""

    df: pd.DataFrame
    cambios: dict[str, bool]
    celdas_actualizadas: int


def sincronizar_scian(csv_fuente: Path, csv_destino: Path) -> ResultadoSincronizacion:
    """Copia SCIAN sector/rama de la canasta 2013 a la 2010, por generico normalizado.

    `csv_fuente` se asume 2013, `csv_destino` se asume 2010 -- ambas columnas
    se sobrescriben in-place en `csv_destino`. El match es por `generico`
    normalizado (no por orden de fila): 2010 y 2013 comparten la misma
    canasta pero no hay garantia de que el CSV este ordenado igual. Pide
    confirmacion interactiva antes de escribir -- `data/` esta en
    `.gitignore`, una sobrescritura mala no se recupera con git, solo
    regenerando desde xlsx/pdf de nuevo.

    Ver: tools/uso_generar_canasta.md §Sincronización SCIAN 2013 → 2010
    """
    df_fuente = _leer_csv(csv_fuente)
    df_destino = _leer_csv(csv_destino)

    _validar_columnas(df_fuente, csv_fuente)
    _validar_columnas(df_destino, csv_destino)
    _validar_scian_completo(df_fuente, csv_fuente)

    mapa_fuente = _mapear_por_generico(df_fuente, csv_fuente)
    mapa_destino = _mapear_por_generico(df_destino, csv_destino)
    _validar_genericos_coinciden(mapa_fuente, mapa_destino, csv_fuente, csv_destino)

    _confirmar_sobrescritura(csv_fuente, csv_destino, len(df_destino))

    original = df_destino.copy()
    claves = df_destino["generico"].map(normalizar_texto)
    for col in _COLUMNAS_SCIAN:
        df_destino[col] = claves.map(lambda clave: mapa_fuente[clave][col])

    cambios_por_columna = {col: (original[col] != df_destino[col]) for col in _COLUMNAS_SCIAN}
    celdas_actualizadas = int(sum(serie.sum() for serie in cambios_por_columna.values()))
    cambios = {
        generico: any(cambios_por_columna[col][i] for col in _COLUMNAS_SCIAN)
        for i, generico in enumerate(df_destino["generico"])
    }

    guardar_csv(df_destino, csv_destino, _VERSION_DESTINO)

    return ResultadoSincronizacion(
        df=df_destino, cambios=cambios, celdas_actualizadas=celdas_actualizadas
    )


def _leer_csv(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str).fillna("")


def _validar_columnas(df: pd.DataFrame, ruta: Path) -> None:
    faltantes = {"generico", *_COLUMNAS_SCIAN} - set(df.columns)
    if faltantes:
        faltantes_txt = ", ".join(sorted(faltantes))
        raise ValueError(f"El CSV no tiene las columnas requeridas ({faltantes_txt}): {ruta}")


def _validar_scian_completo(df_fuente: pd.DataFrame, csv_fuente: Path) -> None:
    faltantes = df_fuente[
        (df_fuente["SCIAN sector"].str.strip() == "") | (df_fuente["SCIAN rama"].str.strip() == "")
    ]
    if not faltantes.empty:
        raise ValueError(
            "El CSV fuente (asumido 2013) no tiene SCIAN completo para todos los genericos. "
            "Primero genera 2013 con --xlsx y --pdf juntos. "
            f"Faltan {len(faltantes)} fila(s) en {csv_fuente}."
        )


def _mapear_por_generico(df: pd.DataFrame, ruta: Path) -> dict[str, dict[str, str]]:
    claves = df["generico"].map(normalizar_texto)
    duplicadas = claves[claves.duplicated()].unique().tolist()
    if duplicadas:
        ejemplos = ", ".join(duplicadas[:5])
        raise ValueError(f"Hay genericos duplicados tras normalizar en {ruta}: {ejemplos}")

    mapa: dict[str, dict[str, str]] = {}
    for clave, (_, row) in zip(claves, df.iterrows()):
        mapa[clave] = {str(col): str(valor) for col, valor in row.items()}
    return mapa


def _validar_genericos_coinciden(
    mapa_fuente: dict[str, dict[str, str]],
    mapa_destino: dict[str, dict[str, str]],
    csv_fuente: Path,
    csv_destino: Path,
) -> None:
    claves_fuente = set(mapa_fuente)
    claves_destino = set(mapa_destino)
    solo_fuente = sorted(claves_fuente - claves_destino)
    solo_destino = sorted(claves_destino - claves_fuente)
    if not solo_fuente and not solo_destino:
        return

    detalles: list[str] = []
    if solo_fuente:
        ejemplos = ", ".join(mapa_fuente[c]["generico"] for c in solo_fuente[:5])
        detalles.append(f"solo en fuente ({csv_fuente}): {ejemplos}")
    if solo_destino:
        ejemplos = ", ".join(mapa_destino[c]["generico"] for c in solo_destino[:5])
        detalles.append(f"solo en destino ({csv_destino}): {ejemplos}")
    raise ValueError("Los genericos de fuente y destino no coinciden; " + " | ".join(detalles))


def _confirmar_sobrescritura(csv_fuente: Path, csv_destino: Path, total_genericos: int) -> None:
    mensaje = (
        "\nConfirmacion requerida\n"
        "Se copiaran las clasificaciones SCIAN sector y SCIAN rama de 2013 a 2010.\n"
        "Se sobrescribira el contenido actual de esas dos columnas en el CSV destino.\n"
        f"Se asume:\n- fuente = 2013: {csv_fuente}\n- destino = 2010: {csv_destino}\n"
        f"Total de genericos a sincronizar: {total_genericos}\n"
        "¿Continuar? [s/N]: "
    )

    try:
        respuesta = input(mensaje).strip().lower()
    except EOFError as exc:
        raise RuntimeError(
            "La sincronizacion requiere confirmacion explicita por stdin. "
            "Ejecuta el comando manualmente y responde la confirmacion."
        ) from exc
    if respuesta not in {"s", "si", "sí", "y", "yes"}:
        raise RuntimeError("Sincronizacion cancelada por el usuario.")
