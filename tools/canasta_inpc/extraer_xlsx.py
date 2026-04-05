from pathlib import Path

import openpyxl
import pandas as pd

from canasta_inpc.config import LAYOUTS_XLSX, LayoutXlsx, columnas_xlsx

_SKIP = {"indice general", "total", "suma", "factor de encadenamiento"}


def extraer_xlsx(ruta: Path, version: int) -> pd.DataFrame:
    """Extrae genéricos, ponderadores y clasificaciones de un xlsx INEGI."""
    layout = LAYOUTS_XLSX[version]
    wb = openpyxl.load_workbook(ruta, data_only=True)

    df = _leer_hoja(wb[layout.hoja_cog], layout)
    df.rename(columns={"_grupo": "COG"}, inplace=True)

    if layout.hoja_ccif:
        df_ccif = _leer_hoja(wb[layout.hoja_ccif], layout)
        mapa_ccif = dict(zip(df_ccif["generico"], df_ccif["_grupo"]))
        df["CCIF division"] = df["generico"].map(mapa_ccif).fillna("")

    cols = columnas_xlsx(version)
    for col in cols:
        if col not in df.columns:
            df[col] = ""

    return df[cols]


def _leer_hoja(ws: object, layout: LayoutXlsx) -> pd.DataFrame:
    grupo_actual = ""
    filas: list[dict] = []
    cols_sep = layout.col_concepto_agg != layout.col_concepto_gen

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        ponderador = row[layout.col_ponderador - 1].value
        if not isinstance(ponderador, (int, float)):
            continue

        if cols_sep:
            concepto_agg = _str(row[layout.col_concepto_agg - 1].value)
            concepto_gen = _str(row[layout.col_concepto_gen - 1].value)

            if concepto_agg and not concepto_gen:
                if concepto_agg.lower() not in _SKIP:
                    grupo_actual = concepto_agg
                continue

            if not concepto_gen or concepto_gen.lower() in _SKIP:
                continue
            concepto = concepto_gen
        else:
            concepto = _str(row[layout.col_concepto_agg - 1].value)
            if not concepto or concepto.lower() in _SKIP:
                continue

            tiene_x = any(row[c - 1].value == "X" for c in layout.agrupaciones)
            if not tiene_x:
                grupo_actual = concepto
                continue

        comp, subcomp, agrup = _clasificar_inflacion(row, layout)

        fila: dict = {
            "generico": concepto,
            "ponderador": ponderador,
            "_grupo": grupo_actual,
            "inflacion componente": comp,
            "inflacion subcomponente": subcomp,
            "inflacion agrupacion": agrup,
        }

        if layout.col_encadenamiento:
            fila["encadenamiento"] = row[layout.col_encadenamiento - 1].value

        cb = row[layout.col_canasta_basica - 1].value
        fila["canasta basica"] = "X" if cb == "X" else ""

        if layout.col_canasta_consumo_minimo:
            ccm = row[layout.col_canasta_consumo_minimo - 1].value
            fila["canasta consumo minimo"] = "X" if ccm == "X" else ""

        filas.append(fila)

    return pd.DataFrame(filas)


def _clasificar_inflacion(row: tuple, layout: LayoutXlsx) -> tuple[str, str, str]:
    for col, (comp, subcomp, agrup) in layout.agrupaciones.items():
        if row[col - 1].value == "X":
            return comp, subcomp, agrup
    return "", "", ""


def _str(val: object) -> str:
    if val is None:
        return ""
    return str(val).strip()
