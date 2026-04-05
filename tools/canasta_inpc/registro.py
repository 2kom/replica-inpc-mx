import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from canasta_inpc.config import columnas_xlsx


def escribir_registro_xlsx(
    df: pd.DataFrame,
    args: argparse.Namespace,
    ruta_csv: Path,
) -> None:
    """Genera el JSON de registro para una ejecución solo-xlsx."""
    ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_json = args.salida / f"xlsx_{args.version}_{ahora}.json"

    cols_clasificacion = [
        c
        for c in columnas_xlsx(args.version)
        if c not in ("generico", "ponderador", "encadenamiento")
    ]

    tiene_enc = "encadenamiento" in df.columns
    n_enc = int(df["encadenamiento"].notna().sum()) if tiene_enc else None

    registro: dict = {
        "tipo": "xlsx",
        "xlsx": str(args.xlsx),
        "csv": str(ruta_csv),
        "version": args.version,
        "genericos": len(df),
        "ponderadores": int(df["ponderador"].notna().sum()),
        "encadenamientos": n_enc,
        "clasificaciones": {
            col: _resumen_clasificacion(df, col) for col in cols_clasificacion
        },
        "genericos_detalle": _detalle_genericos(df, tiene_enc),
    }

    ruta_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
    _imprimir_resumen(registro, ruta_csv, ruta_json)


def escribir_registro_pdf(
    df_xlsx: pd.DataFrame,
    df_pdf: pd.DataFrame,
    df_final: pd.DataFrame,
    diferencias: list[dict],
    args: argparse.Namespace,
    ruta_csv: Path,
) -> None:
    """Genera el JSON de registro para una ejecución xlsx+pdf."""
    ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_json = args.salida / f"pdf_{args.version}_{ahora}.json"

    cols_clasificacion = [
        c
        for c in df_final.columns
        if c not in ("generico", "ponderador", "encadenamiento")
        and df_final[c].astype(str).str.strip().ne("").any()
    ]

    from canasta_inpc.config import columnas_pdf

    cols_enriquecidas = columnas_pdf(args.version)

    # Columnas compartidas: clasificaciones con datos en ambas fuentes
    skip = {
        "generico",
        "ponderador",
        "encadenamiento",
        "canasta basica",
        "canasta consumo minimo",
    }
    cols_xlsx_no_vacias = {
        c
        for c in df_xlsx.columns
        if c not in skip and df_xlsx[c].astype(str).str.strip().ne("").any()
    }
    cols_pdf_no_vacias = {
        c
        for c in df_pdf.columns
        if c not in skip and df_pdf[c].astype(str).str.strip().ne("").any()
    }
    cols_compartidas = sorted(cols_xlsx_no_vacias & cols_pdf_no_vacias)

    registro: dict = {
        "tipo": "pdf",
        "xlsx": str(args.xlsx),
        "pdf": str(args.pdf),
        "csv": str(ruta_csv),
        "version": args.version,
        "genericos": len(df_final),
        "ponderadores": int(df_final["ponderador"].notna().sum()),
        "encadenamientos": (
            int(df_final["encadenamiento"].notna().sum())
            if "encadenamiento" in df_final.columns
            else None
        ),
        "clasificaciones": {
            col: _resumen_clasificacion(df_final, col) for col in cols_clasificacion
        },
        "columnas_enriquecidas": cols_enriquecidas,
        "columnas_compartidas": cols_compartidas,
        "enriquecimiento": _resumen_enriquecimiento(diferencias, cols_enriquecidas),
        "sin_match_pdf": [
            d for d in diferencias if d.get("motivo") == "no encontrado en pdf"
        ],
        "sin_match_xlsx": [
            d for d in diferencias if d.get("motivo") == "en pdf pero no en xlsx"
        ],
        "ponderador_no_coincide": [
            d for d in diferencias if "csv" in d and "pdf" in d and "decimales" in d
        ],
        "agregaciones": [
            {
                "generico": d["generico"],
                "clasificacion": d["columna"],
                "categoria": d["pdf"],
            }
            for d in diferencias
            if d.get("elegido") and not d.get("csv")
        ],
        "diferencias_resueltas": [
            d for d in diferencias if d.get("elegido") and d.get("csv")
        ],
        "validacion_conteo": _validacion_conteo(df_final, cols_enriquecidas),
    }

    ruta_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
    _imprimir_resumen_pdf(registro, ruta_csv, ruta_json)


def _detalle_genericos(df: pd.DataFrame, tiene_enc: bool) -> list[dict]:
    detalle = []
    for _, row in df.iterrows():
        entrada: dict = {"generico": row["generico"], "ponderador": row["ponderador"]}
        if tiene_enc:
            entrada["encadenamiento"] = row["encadenamiento"]
        detalle.append(entrada)
    return detalle


def _imprimir_resumen(registro: dict, ruta_csv: Path, ruta_json: Path) -> None:
    print(
        f"\n  version {registro['version']}: {registro['genericos']} genericos extraidos"
    )
    enc = registro["encadenamientos"]
    if enc is not None:
        print(f"  encadenamientos: {enc}")
    for col, info in registro["clasificaciones"].items():
        print(
            f"  {col}: {info['genericos_clasificados']} clasificados, {info['categorias_unicas']} categorias"
        )
    print(f"\n  csv:      {ruta_csv}")
    print(f"  registro: {ruta_json}\n")


def _imprimir_resumen_pdf(registro: dict, ruta_csv: Path, ruta_json: Path) -> None:
    total_agregadas = len(registro["agregaciones"])
    print(
        f"\n  version {registro['version']}: {registro['genericos']} genericos extraidos, {total_agregadas} categorias enriquecidas"
    )
    enc = registro["encadenamientos"]
    if enc is not None:
        print(f"  encadenamientos: {enc}")

    cols_enriquecidas = set(registro["columnas_enriquecidas"])
    cols_compartidas = set(registro["columnas_compartidas"])
    enriquecimiento = registro["enriquecimiento"]

    for col, info in registro["clasificaciones"].items():
        base = f"  {col}: {info['genericos_clasificados']} clasificados, {info['categorias_unicas']} categorias"
        if col in cols_enriquecidas:
            n = enriquecimiento[col]["agregados"]
            print(f"{base}, {n} categorias agregadas desde pdf")
        elif col in cols_compartidas:
            print(f"{base}, {info['genericos_clasificados']} comprobadas")
        else:
            print(base)

    # Warnings
    sin_pdf = registro["sin_match_pdf"]
    if sin_pdf:
        print(f"\n  WARNING: {len(sin_pdf)} generico(s) del xlsx sin match en pdf:")
        for d in sin_pdf:
            print(f"    - {d['generico']}")

    sin_xlsx = registro["sin_match_xlsx"]
    if sin_xlsx:
        print(f"\n  WARNING: {len(sin_xlsx)} generico(s) del pdf sin match en xlsx:")
        for d in sin_xlsx:
            print(f"    - {d['generico']}")

    pond = registro["ponderador_no_coincide"]
    if pond:
        print(f"\n  WARNING: {len(pond)} ponderador(es) no coinciden:")
        for d in pond:
            print(f"    - {d['generico']}: csv={d['csv']} pdf={d['pdf']}")

    val = registro["validacion_conteo"]
    if not val["ok"]:
        print(f"\n  WARNING: validacion de conteo fallo ({val['faltantes']} faltantes)")

    print(f"\n  csv:      {ruta_csv}")
    print(f"  registro: {ruta_json}\n")


def _resumen_clasificacion(df: pd.DataFrame, col: str) -> dict:
    valores = df[col].astype(str).str.strip()
    no_vacios = valores[valores != ""]
    categorias = sorted(no_vacios.unique().tolist())
    return {
        "genericos_clasificados": len(no_vacios),
        "categorias_unicas": len(categorias),
        "categorias": categorias,
    }


def _resumen_enriquecimiento(diferencias: list[dict], cols: list[str]) -> dict:
    resumen: dict = {}
    for col in cols:
        col_difs = [d for d in diferencias if d.get("columna") == col]
        resumen[col] = {
            "agregados": sum(1 for d in col_difs if d.get("elegido")),
            "ya_existian": sum(1 for d in col_difs if d.get("ya_existia", False)),
            "diferencias_nombre": sum(
                1 for d in col_difs if d.get("csv") and d.get("csv") != d.get("pdf")
            ),
        }
    return resumen


def _validacion_conteo(df: pd.DataFrame, cols: list[str]) -> dict:
    genericos = len(df)
    n_cols = len(cols)
    esperado = genericos * n_cols
    real = sum(
        df[col].astype(str).str.strip().ne("").sum()
        for col in cols
        if col in df.columns
    )
    return {
        "genericos": genericos,
        "columnas_enriquecidas": n_cols,
        "esperado": esperado,
        "real": int(real),
        "faltantes": esperado - int(real),
        "ok": esperado == int(real),
    }
