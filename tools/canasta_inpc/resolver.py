"""Resolución de conflictos entre valores xlsx y pdf."""

import pandas as pd


def resolver_diferencias(
    df: pd.DataFrame,
    diferencias: list[dict],
    preferir: str | None,
) -> pd.DataFrame:
    """Resuelve diferencias sin resolver entre xlsx y pdf.

    Diferencias sin resolver son las que tienen 'columna' pero no 'elegido'.
    Si preferir es "pdf" o "csv", se elige automáticamente.
    Si es None, se pregunta al usuario por cada conflicto.
    """
    df = df.copy()

    for dif in diferencias:
        if "columna" not in dif or "elegido" in dif:
            continue

        gen = dif["generico"]
        col = dif["columna"]

        if preferir == "pdf":
            elegido = "pdf"
        elif preferir == "csv":
            elegido = "csv"
        else:
            elegido = _preguntar(gen, col, dif["csv"], dif["pdf"])

        dif["elegido"] = elegido

        if elegido == "pdf":
            mask = df["generico"] == gen
            df.loc[mask, col] = dif["pdf"]

    return df


def _preguntar(generico: str, columna: str, valor_csv: str, valor_pdf: str) -> str:
    """Pregunta al usuario qué valor elegir. Enter = pdf por defecto."""
    print(f"\n  Diferencia en '{columna}' para '{generico}':")
    print(f"    csv: {valor_csv!r}")
    print(f"    pdf: {valor_pdf!r}")
    respuesta = input("  Elegir [pdf]/csv: ").strip().lower()
    if respuesta == "csv":
        return "csv"
    return "pdf"
