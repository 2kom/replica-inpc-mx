from pathlib import Path

import pandas as pd

from canasta_inpc.config import COLUMNAS_FIJAS


def escribir_csv(df: pd.DataFrame, ruta: Path, version: int) -> None:
    """Escribe el CSV de 15 columnas fijas. Columnas sin datos quedan vacías."""
    salida = pd.DataFrame(columns=COLUMNAS_FIJAS)
    for col in COLUMNAS_FIJAS:
        if col in df.columns:
            salida[col] = df[col]
        else:
            salida[col] = ""
    salida.to_csv(ruta, index=False)
