import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from canasta_inpc.esquema import COLUMNAS_BASE, FUENTES_POSIBLES
from canasta_inpc.match import Resolucion, ResultadoMatch

_COLUMNAS_NO_CLASIFICACION = {"generico", "ponderador", "encadenamiento"}


def escribir_registro_xlsx(df: pd.DataFrame, args: argparse.Namespace, ruta_csv: Path) -> None:
    """Genera el JSON de registro para una ejecucion solo-xlsx.

    Ver: tools/uso_generar_canasta.md §Registro JSON (modo solo `xlsx`).
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
        "clasificaciones": {
            col: _resumir_clasificacion_xlsx(df, col) for col in cols_clasificacion
        },
        "genericos_detalle": _construir_detalle_genericos_xlsx(df, tiene_enc),
    }

    ruta_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    _imprimir_resumen_xlsx(registro, ruta_csv, ruta_json)


def _resumir_clasificacion_xlsx(df: pd.DataFrame, col: str) -> dict:
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


def _imprimir_resumen_xlsx(registro: dict, ruta_csv: Path, ruta_json: Path) -> None:
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
    resultado: ResultadoMatch, args: argparse.Namespace, ruta_csv: Path
) -> None:
    """Genera el JSON de registro para una ejecucion xlsx + pdf.

    `resultado.resoluciones` ya viene resuelta de `match_dfs` -- aca solo se
    agrupa y serializa, sin reconstruir fuente/metodo (ver `Resolucion` en
    `match.py`).

    Ver: tools/uso_generar_canasta.md §Registro JSON (modo `xlsx` + `pdf`).
    """
    df = resultado.df
    ahora = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta_json = args.salida / f"pdf_{args.version}_{ahora}.json"

    cols_clasificacion = [
        c for c in COLUMNAS_BASE if c not in _COLUMNAS_NO_CLASIFICACION and c in df.columns
    ]
    # a diferencia de escribir_registro_xlsx, `df` (de match_dfs) SIEMPRE trae
    # las 15 columnas de COLUMNAS_BASE (grupo D las rellena con "" si ninguna
    # fuente las trae) -- "esta en df.columns" no sirve para detectar "esta
    # version no tiene encadenamiento en ninguna fuente" (ej. 2010/2018), hay
    # que preguntarle a FUENTES_POSIBLES
    tiene_enc = bool(FUENTES_POSIBLES[args.version]["encadenamiento"])

    registro: dict = {
        "tipo": "xlsx_pdf",
        "preferir": args.preferir,
        "xlsx": str(args.xlsx),
        "pdf": str(args.pdf),
        "csv": str(ruta_csv),
        "version": args.version,
        "genericos": len(df),
        "ponderadores": int((df["ponderador"] != "").sum()),
        "encadenamientos": int((df["encadenamiento"] != "").sum()) if tiene_enc else None,
        "clasificaciones": {
            col: _resumir_clasificacion_pdf(df, col, resultado.resoluciones)
            for col in cols_clasificacion
        },
        "genericos_detalle": _construir_detalle_genericos_pdf(
            df, tiene_enc, resultado.resoluciones
        ),
    }

    ruta_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    _imprimir_resumen_pdf(registro, ruta_csv, ruta_json)


def _agrupar_resoluciones_por_columna(
    resoluciones: tuple[Resolucion, ...],
) -> dict[str, list[Resolucion]]:
    agrupado: dict[str, list[Resolucion]] = {}
    for r in resoluciones:
        agrupado.setdefault(r.columna, []).append(r)
    return agrupado


def _serializar_campo(r: Resolucion) -> dict:
    return {"valor": r.valor_final, "origen": r.origen, "metodo": r.metodo}


def _construir_detalle_genericos_pdf(
    df: pd.DataFrame, tiene_enc: bool, resoluciones: tuple[Resolucion, ...]
) -> list[dict]:
    """Arma una entrada {generico, ponderador, [encadenamiento]} por fila, cruce xlsx+pdf.

    A diferencia de `_construir_detalle_genericos_xlsx`, `ponderador`/
    `encadenamiento` van anidados (`_serializar_campo`) con `valor`/`origen`/`metodo` --
    hubo (o pudo haber habido) comparacion entre 2 fuentes, no es un valor
    plano de una sola fuente.
    """
    por_columna = _agrupar_resoluciones_por_columna(resoluciones)
    meta_ponderador = {r.genericos[0]: r for r in por_columna.get("ponderador", [])}
    meta_encadenamiento = {r.genericos[0]: r for r in por_columna.get("encadenamiento", [])}

    detalle = []
    for _, row in df.iterrows():
        generico = row["generico"]
        entrada: dict = {
            "generico": generico,
            "ponderador": _serializar_campo(meta_ponderador[generico]),
        }
        if tiene_enc:
            entrada["encadenamiento"] = _serializar_campo(meta_encadenamiento[generico])
        detalle.append(entrada)
    return detalle


def _resumir_clasificacion_pdf(
    df: pd.DataFrame, col: str, resoluciones: tuple[Resolucion, ...]
) -> dict:
    """Resumen agregado por categoria de una columna de clasificacion, cruce xlsx+pdf.

    Distinto de `_resumir_clasificacion_xlsx`: la resolucion en columnas
    categoricas es por par unico, no por fila -- no hay un `origen`/`metodo`
    individual por generico que valga la pena listar, importa cuantos cayeron
    en cada metodo dentro de cada categoria final. `metodos["decision"]`
    junta `preferido`+`interactiva` (dato redundante con `args.preferir` a
    nivel de todo el registro). `origenes_igual`/`origenes_decision`/
    `origenes_directo` solo aparecen si el bucket correspondiente tuvo algo.

    `categorias["sin_clasificar"]` (si aparece) junta las decisiones reales
    que resolvieron hacia vacio (ej. `--preferir xlsx` y xlsx no clasifico
    ese generico) -- `_resolver_categoria` conserva esos eventos aunque
    `valor_final` sea `""`, para que la decision no desaparezca del
    registro; no cuenta para `genericos`/`categorias_unicas` (no es una
    categoria real, es metadata de una decision).
    """
    conteo = _conteo_genericos_categoria(df, col)
    eventos = [r for r in resoluciones if r.columna == col]

    categorias: dict[str, dict] = {}
    for cat, n in conteo.items():
        categorias[cat] = _resumir_metodos_categoria(eventos, cat, n)

    sin_clasificar = [r for r in eventos if r.valor_final == ""]
    if sin_clasificar:
        categorias["sin_clasificar"] = _resumir_metodos_categoria(
            sin_clasificar, "", sum(len(r.genericos) for r in sin_clasificar)
        )

    return {
        "genericos": sum(conteo.values()),
        "categorias_unicas": len(conteo),
        "categorias": categorias,
    }


def _resumir_metodos_categoria(eventos: list[Resolucion], cat: str, genericos: int) -> dict:
    """Desglosa por metodo/origen los eventos de una categoria (o de `sin_clasificar`)."""
    metodos: dict[str, int] = {}
    origenes_igual: dict[str, int] = {}
    origenes_decision: dict[str, int] = {}
    origenes_directo: dict[str, int] = {}
    for r in eventos:
        if r.valor_final != cat:
            continue
        metodo_clave = "decision" if r.metodo in ("preferido", "interactiva") else r.metodo
        metodos[metodo_clave] = metodos.get(metodo_clave, 0) + len(r.genericos)
        if r.metodo == "igual":
            origenes_igual[r.origen] = origenes_igual.get(r.origen, 0) + len(r.genericos)
        elif r.metodo in ("preferido", "interactiva"):
            origenes_decision[r.origen] = origenes_decision.get(r.origen, 0) + len(r.genericos)
        elif r.metodo == "directo":
            origenes_directo[r.origen] = origenes_directo.get(r.origen, 0) + len(r.genericos)

    entrada: dict = {"genericos": genericos, "metodos": metodos}
    if origenes_igual:
        entrada["origenes_igual"] = origenes_igual
    if origenes_decision:
        entrada["origenes_decision"] = origenes_decision
    if origenes_directo:
        entrada["origenes_directo"] = origenes_directo
    return entrada


def _imprimir_resumen_pdf(registro: dict, ruta_csv: Path, ruta_json: Path) -> None:
    """Imprime a stdout el mismo resumen que queda en el JSON, cruce xlsx+pdf."""
    print(f"\n  version {registro['version']}: {registro['genericos']} genericos extraidos")
    if registro["encadenamientos"] is not None:
        print(f"  encadenamientos: {registro['encadenamientos']}")
    for col, info in registro["clasificaciones"].items():
        print(f"  {col}: {info['genericos']} clasificados, {info['categorias_unicas']} categorias")
    print(f"\n  csv:      {ruta_csv}")
    print(f"  registro: {ruta_json}\n")
