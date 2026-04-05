"""Cruce de genéricos xlsx/pdf, verificación de ponderadores."""

import pandas as pd

from canasta_inpc.config import PRECISION_DECIMALES, columnas_pdf


def cruzar_genericos(
    df_xlsx: pd.DataFrame,
    df_pdf: pd.DataFrame,
    version: int,
) -> tuple[pd.DataFrame, list[dict]]:
    """Cruza genéricos del xlsx con los del pdf por nombre normalizado.

    Devuelve (df_combinado, diferencias) donde diferencias es una lista
    de dicts que describen: genéricos sin match, ponderadores distintos,
    y columnas enriquecidas o en conflicto.
    """
    diferencias: list[dict] = []
    cols_pdf = columnas_pdf(version)
    precision = PRECISION_DECIMALES[version]

    pdf_idx = df_pdf.set_index("generico")

    df = df_xlsx.copy()
    for col in cols_pdf:
        if col not in df.columns:
            df[col] = ""

    # Columnas compartidas: no vacías en ambas fuentes (para verificación cruzada)
    cols_compartidas = _columnas_compartidas(df, pdf_idx)

    for idx, row in df.iterrows():
        gen = row["generico"]

        if gen not in pdf_idx.index:
            diferencias.append({"generico": gen, "motivo": "no encontrado en pdf"})
            continue

        fila_pdf = pdf_idx.loc[gen]

        # Verificar ponderador
        ponderador_ok = True
        if "ponderador" in pdf_idx.columns:
            ponderador_ok = _verificar_ponderador(gen, row["ponderador"], fila_pdf["ponderador"], precision, diferencias)

        # Enriquecer columnas PDF (solo las que son fuente pdf)
        for col in cols_pdf:
            if col not in pdf_idx.columns:
                continue

            valor_pdf = str(fila_pdf[col]).strip()
            valor_csv = str(row[col]).strip()

            if not valor_pdf:
                continue

            if not valor_csv:
                # Vacío en csv, llenar desde pdf
                df.at[idx, col] = valor_pdf
                diferencias.append({
                    "generico": gen,
                    "columna": col,
                    "csv": "",
                    "pdf": valor_pdf,
                    "elegido": "pdf",
                })
            elif valor_csv == valor_pdf:
                # Ya tenía el mismo valor
                diferencias.append({
                    "generico": gen,
                    "columna": col,
                    "csv": valor_csv,
                    "pdf": valor_pdf,
                    "ya_existia": True,
                    "elegido": "pdf",
                })
            else:
                # Conflicto: valores distintos, requiere resolución
                diferencias.append({
                    "generico": gen,
                    "columna": col,
                    "csv": valor_csv,
                    "pdf": valor_pdf,
                })

        # Verificar clasificaciones compartidas (solo si ponderador coincide)
        if ponderador_ok:
            for col in cols_compartidas:
                valor_csv = str(row[col]).strip()
                valor_pdf = str(fila_pdf[col]).strip()

                if valor_csv and valor_pdf and valor_csv != valor_pdf:
                    diferencias.append({
                        "generico": gen,
                        "columna": col,
                        "csv": valor_csv,
                        "pdf": valor_pdf,
                    })

    # Genéricos en pdf que no están en xlsx
    gen_xlsx = set(df["generico"])
    for gen in sorted(set(pdf_idx.index) - gen_xlsx):
        diferencias.append({"generico": gen, "motivo": "en pdf pero no en xlsx"})

    return df, diferencias


def _columnas_compartidas(df_xlsx: pd.DataFrame, pdf_idx: pd.DataFrame) -> list[str]:
    """Columnas de clasificación con datos en ambas fuentes."""
    skip = {"generico", "ponderador", "encadenamiento", "canasta basica", "canasta consumo minimo"}
    cols_xlsx = {
        col for col in df_xlsx.columns
        if col not in skip and df_xlsx[col].astype(str).str.strip().ne("").any()
    }
    cols_pdf = {
        col for col in pdf_idx.columns
        if col not in skip and pdf_idx[col].astype(str).str.strip().ne("").any()
    }
    return sorted(cols_xlsx & cols_pdf)


def _verificar_ponderador(
    generico: str,
    pond_xlsx: object,
    pond_pdf: object,
    precision: int,
    diferencias: list[dict],
) -> bool:
    """Compara ponderadores redondeados a la precisión visible del PDF.

    Devuelve True si coinciden (o no se puede comparar).
    """
    try:
        val_xlsx = round(float(pond_xlsx), precision)
        val_pdf = round(float(pond_pdf), precision)
    except (ValueError, TypeError):
        return True

    if val_xlsx != val_pdf:
        diferencias.append({
            "generico": generico,
            "csv": str(pond_xlsx),
            "pdf": str(pond_pdf),
            "decimales": precision,
        })
        return False
    return True
