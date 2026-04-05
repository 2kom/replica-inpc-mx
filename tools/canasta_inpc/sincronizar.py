import sys
from pathlib import Path

import pandas as pd

from canasta_inpc.escribir import escribir_csv
from canasta_inpc.normalizar import normalizar_celda

_COLUMNAS_SCIAN = ("SCIAN sector", "SCIAN rama")


def sincronizar_scian(csv_fuente: Path, csv_destino: Path) -> None:
    """Copia SCIAN 2013 -> 2010 por genérico normalizado.

    `csv_fuente` se asume como la salida 2013 y `csv_destino` como la salida 2010.
    Las columnas `SCIAN sector` y `SCIAN rama` del destino se sobrescriben con los
    valores de la fuente.
    """
    df_fuente = _leer_csv(csv_fuente)
    df_destino = _leer_csv(csv_destino)

    _validar_columnas(df_fuente, csv_fuente)
    _validar_columnas(df_destino, csv_destino)

    _validar_scian_fuente(df_fuente, csv_fuente)

    mapa_fuente = _mapear_por_generico(df_fuente, csv_fuente)
    mapa_destino = _mapear_por_generico(df_destino, csv_destino)
    _validar_genericos(mapa_fuente, mapa_destino, csv_fuente, csv_destino)

    _confirmar_sobrescritura(csv_fuente, csv_destino, len(df_destino))

    destino_original = df_destino.copy()
    claves = df_destino["generico"].map(normalizar_celda)
    for col in _COLUMNAS_SCIAN:
        df_destino[col] = claves.map(
            lambda clave: mapa_fuente[clave][col]
        )

    celdas_actualizadas = sum(
        int((destino_original[col] != df_destino[col]).sum())
        for col in _COLUMNAS_SCIAN
    )
    escribir_csv(df_destino, csv_destino, version=2010)

    print("\nSincronización completada")
    print(f"- Fuente asumida (2013): {csv_fuente}")
    print(f"- Destino asumido (2010): {csv_destino}")
    print(f"- Genéricos sincronizados: {len(df_destino)}")
    print(f"- Celdas SCIAN actualizadas: {celdas_actualizadas}")


def _leer_csv(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype=str).fillna("")
    return df


def _validar_columnas(df: pd.DataFrame, ruta: Path) -> None:
    faltantes = {"generico", *_COLUMNAS_SCIAN} - set(df.columns)
    if faltantes:
        faltantes_txt = ", ".join(sorted(faltantes))
        raise ValueError(f"El CSV no tiene las columnas requeridas ({faltantes_txt}): {ruta}")


def _validar_scian_fuente(df_fuente: pd.DataFrame, csv_fuente: Path) -> None:
    faltantes = df_fuente[
        (df_fuente["SCIAN sector"].astype(str).str.strip() == "")
        | (df_fuente["SCIAN rama"].astype(str).str.strip() == "")
    ]
    if not faltantes.empty:
        raise ValueError(
            "El CSV fuente (asumido 2013) no tiene SCIAN completo para todos los genéricos. "
            "Primero genera 2013 con --xlsx y --pdf juntos. "
            f"Faltan {len(faltantes)} fila(s) en {csv_fuente}."
        )


def _mapear_por_generico(df: pd.DataFrame, ruta: Path) -> dict[str, dict[str, str]]:
    claves = df["generico"].map(normalizar_celda)
    duplicadas = claves[claves.duplicated()].unique().tolist()
    if duplicadas:
        ejemplos = ", ".join(duplicadas[:5])
        raise ValueError(f"Hay genéricos duplicados tras normalizar en {ruta}: {ejemplos}")

    mapa: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        clave = normalizar_celda(row["generico"])
        mapa[clave] = row.to_dict()
    return mapa


def _validar_genericos(
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
    raise ValueError("Los genéricos de fuente y destino no coinciden; " + " | ".join(detalles))


def _confirmar_sobrescritura(csv_fuente: Path, csv_destino: Path, total_genericos: int) -> None:
    mensaje = (
        "\nConfirmación requerida\n"
        "Se copiarán las clasificaciones SCIAN sector y SCIAN rama de 2013 a 2010.\n"
        "Se sobrescribirá el contenido actual de esas dos columnas en el CSV destino.\n"
        f"Se asume:\n- fuente = 2013: {csv_fuente}\n- destino = 2010: {csv_destino}\n"
        f"Total de genéricos a sincronizar: {total_genericos}\n"
        "¿Continuar? [s/N]: "
    )

    try:
        respuesta = input(mensaje).strip().lower()
    except EOFError as exc:
        raise RuntimeError(
            "La sincronización requiere confirmación explícita por stdin. "
            "Ejecuta el comando manualmente y responde la confirmación."
        ) from exc
    if respuesta not in {"s", "si", "sí", "y", "yes"}:
        raise RuntimeError("Sincronización cancelada por el usuario.")
