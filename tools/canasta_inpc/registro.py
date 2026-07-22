import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from canasta_inpc.esquema import COLUMNAS_BASE

_COLUMNAS_NO_CLASIFICACION = {"generico", "ponderador", "encadenamiento"}


def escribir_registro_xlsx(df: pd.DataFrame, args: argparse.Namespace, ruta_csv: Path) -> None:
    """Genera el JSON de registro para una ejecucion solo-xlsx.

    Ver: tools/uso_generar_canasta.md §Registro JSON.
    """
    ahora = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta_json = args.salida / f"xlsx_{args.version}_{ahora}.json"

    # solo columnas reales del esquema -- una columna fuera de COLUMNAS_BASE
    # (typo de codigo, xlsx con hoja distinta) ya la descarta guardar_csv con
    # aviso; el registro no debe reportarla como si fuera una clasificacion real
    cols_clasificacion = [
        c for c in COLUMNAS_BASE if c not in _COLUMNAS_NO_CLASIFICACION and c in df.columns
    ]
    tiene_enc = "encadenamiento" in df.columns

    registro: dict = {
        "tipo": "xlsx",
        "xlsx": str(args.xlsx),
        "csv": str(ruta_csv),
        "version": args.version,
        "genericos": len(df),
        "ponderadores": int((df["ponderador"] != "").sum()),
        "encadenamientos": int((df["encadenamiento"] != "").sum()) if tiene_enc else None,
        "clasificaciones": {col: _resumir_clasificacion(df, col) for col in cols_clasificacion},
        "genericos_detalle": _construir_detalle_genericos_xlsx(df, tiene_enc),
    }

    ruta_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    _imprimir_resumen(registro, ruta_csv, ruta_json)


def _resumir_clasificacion(df: pd.DataFrame, col: str) -> dict:
    """Cuenta genericos clasificados y categorias unicas de una columna de clasificacion."""
    no_vacios = df[col][df[col] != ""]
    categorias = sorted(no_vacios.unique().tolist())
    return {
        "genericos_clasificados": len(no_vacios),
        "categorias_unicas": len(categorias),
        "categorias": _conteo_genericos_categoria(df, col),
    }


def _conteo_genericos_categoria(df: pd.DataFrame, col: str) -> dict[str, int]:
    """Cuenta cuantos genericos hay por categoria de una columna de clasificacion."""
    conteo: dict[str, int] = {}
    categorias = sorted(df[col][df[col] != ""].unique().tolist())
    for cat in categorias:
        conteo[cat] = int((df[col] == cat).sum())
    return conteo


def _construir_detalle_genericos_xlsx(df: pd.DataFrame, tiene_enc: bool) -> list[dict]:
    """Arma una entrada {generico, ponderador, [encadenamiento]} por fila."""
    detalle = []
    for _, row in df.iterrows():
        entrada: dict = {"generico": row["generico"], "ponderador": row["ponderador"]}
        if tiene_enc:
            entrada["encadenamiento"] = row["encadenamiento"]
        detalle.append(entrada)
    return detalle


def _imprimir_resumen(registro: dict, ruta_csv: Path, ruta_json: Path) -> None:
    """Imprime a stdout el mismo resumen que queda en el JSON."""
    print(f"\n  version {registro['version']}: {registro['genericos']} genericos extraidos")
    if registro["encadenamientos"] is not None:
        print(f"  encadenamientos: {registro['encadenamientos']}")
    for col, info in registro["clasificaciones"].items():
        print(
            f"  {col}: {info['genericos_clasificados']} clasificados, "
            f"{info['categorias_unicas']} categorias"
        )
    print(f"\n  csv:      {ruta_csv}")
    print(f"  registro: {ruta_json}\n")


def escribir_registro_pdf(
    df: pd.DataFrame, args: argparse.Namespace, ruta_csv: Path, decisiones: dict
) -> None:

    ahora = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta_json = args.salida / f"pdf_{args.version}_{ahora}.json"

    cols_clasificacion = [
        c for c in COLUMNAS_BASE if c not in _COLUMNAS_NO_CLASIFICACION and c in df.columns
    ]
    tiene_enc = "encadenamiento" in df.columns

    registro: dict = {
        "tipo": "xlsx + pdf" if args.preferir is None else f"xlsx + pdf (preferir {args.preferir})",
        "xlsx": str(args.xlsx),
        "pdf": str(args.pdf),
        "csv": str(ruta_csv),
        "version": args.version,
        "genericos": len(df),
        "ponderadores": int((df["ponderador"] != "").sum()),
        "encadenamientos": int((df["encadenamiento"] != "").sum()) if tiene_enc else None,
        "clasificaciones": {col: _resumir_clasificacion(df, col) for col in cols_clasificacion},
        "genericos_detalle": _construir_detalle_genericos_pdf(df, tiene_enc, decisiones),
    }


def _resumir_clasificacion_genericos_categoria_pdf(df: pd.DataFrame, col: str):
    pass


def _construir_detalle_genericos_pdf(
    df: pd.DataFrame, tiene_enc: bool, decisiones: dict
) -> list[dict]:

    return [{}]
