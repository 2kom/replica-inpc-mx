from typing import Literal

import pandas as pd

from canasta_inpc.esquema import COLUMNAS_BASE, FUENTES_POSIBLES, VersionCanasta

Preferencia = Literal["pdf", "csv"]

# columnas que se comparan fila por fila cuando ambas fuentes las traen (grupo A);
# el resto de columnas con ambas fuentes se comparan agrupando por par unico (grupo B)
_COLUMNAS_FILA = {"generico", "ponderador", "encadenamiento"}
_COLUMNAS_NUMERICAS = {"ponderador", "encadenamiento"}


def match_dfs(
    df_xlsx: pd.DataFrame,
    df_pdf: pd.DataFrame,
    version: VersionCanasta,
    preferir: Preferencia | None = None,
) -> pd.DataFrame:
    """Cruza extracciones xlsx y pdf en un df maestro, resolviendo discrepancias.

    `preferir` salta las preguntas interactivas y resuelve automatico ("pdf" o
    "csv", el valor viene tal cual del flag `--preferir` del CLI, "csv" =
    valor extraido del xlsx); sin `preferir`, discrepancia real = pregunta en
    consola, Enter = pdf.

    Ver: tools/uso_generar_canasta.md §Diseño futuro: PDF y sincronización.
    """
    # paso 0: df maestro vacio, mismo indice que las fuentes ya alineadas (paso 1)
    # paso 1: alinear ambos df por `generico`, orden alfabetico; se asume mismo
    # largo y correspondencia 1 a 1 tras ordenar (genericos son el mismo texto
    # en teoria entre xlsx y pdf, discrepancias de nombre se resuelven como
    # cualquier otra discrepancia de la columna `generico`, no como fila
    # faltante)
    df_xlsx = df_xlsx.sort_values(by="generico").reset_index(drop=True)
    df_pdf = df_pdf.sort_values(by="generico").reset_index(drop=True)

    fuentes = FUENTES_POSIBLES[version]
    df_maestro = pd.DataFrame(index=df_xlsx.index)

    # paso 2: avanzar columna por columna, en el orden final de COLUMNAS_BASE
    # (asi el df maestro ya sale con las columnas en orden, sin reindex extra)
    for columna in COLUMNAS_BASE:
        origenes = fuentes[columna]

        # paso 3: segun de donde puede venir esta columna en esta version --
        # FUENTES_POSIBLES ya responde "cuantas fuentes hay que cruzar", no
        # hay que re-derivarlo
        if "xlsx" in origenes and "pdf" in origenes:
            # ambas fuentes traen la columna: hay que comparar (grupo A o B)
            if columna in _COLUMNAS_FILA:
                # grupo A: generico/ponderador/encadenamiento -- fila por fila,
                # discrepancia real se resuelve una por una
                df_maestro[columna] = _resolucion_fila(
                    df_xlsx[columna],
                    df_pdf[columna],
                    numerica=columna in _COLUMNAS_NUMERICAS,
                    preferir=preferir,
                )
            else:
                # grupo B: columnas categoricas -- discrepancias se agrupan
                # por par unico (valor_xlsx, valor_pdf), se resuelve una vez
                # por par, no una vez por fila
                df_maestro[columna] = _resolucion_categoria(
                    df_xlsx[columna], df_pdf[columna], preferir=preferir
                )
        elif "xlsx" in origenes:
            # grupo C: solo el xlsx trae esta columna en esta version -- se
            # copia directo, no hay nada que cruzar
            df_maestro[columna] = df_xlsx[columna]
        elif "pdf" in origenes:
            # grupo C: solo el pdf la trae -- copia directo
            df_maestro[columna] = df_pdf[columna]
        else:
            # grupo D: ninguna de las dos fuentes la trae (o solo "sync", que
            # no participa de este cruce xlsx+pdf) -- columna vacia
            df_maestro[columna] = ""

    # paso 4: df maestro queda armado y ordenado; quien llama lo pasa a
    # guardar_csv (que ya hace su propio reindex/fill contra COLUMNAS_BASE)
    return df_maestro


def _resolucion_fila(
    col_xlsx: pd.Series, col_pdf: pd.Series, numerica: bool, preferir: Preferencia | None
) -> pd.Series:
    """Compara fila por fila; discrepancia real se resuelve a mano, una por una (Enter = pdf).

    Para columnas numericas (3.1 del procedimiento): una discrepancia dentro
    de la tolerancia de redondeo (la fuente de menor precision cabe en la de
    mayor precision) no cuenta como discrepancia real -- se resuelve sola,
    quedandose con el valor de mayor precision, sin preguntar ni consultar
    `preferir`.
    """
    resultado = pd.Series(index=col_xlsx.index, dtype=object)

    for i in col_xlsx.index:
        valor_xlsx = col_xlsx[i]
        valor_pdf = col_pdf[i]

        # 3.2 (aplica igual a filas no numericas): iguales, no hay nada que resolver
        if valor_xlsx == valor_pdf:
            resultado[i] = valor_pdf
            continue

        # 3.1: numerica dentro de tolerancia de redondeo -- se resuelve sola
        if numerica and _coinciden_por_redondeo(str(valor_xlsx), str(valor_pdf)):
            resultado[i] = _mas_preciso(str(valor_xlsx), str(valor_pdf))
            continue

        # discrepancia real: se pregunta esta fila puntual (o se resuelve con
        # `preferir` sin preguntar)
        print(f"Discrepancia en la fila {i} (columna '{col_xlsx.name}'):")
        resultado[i] = _resolver(valor_xlsx, valor_pdf, preferir)

    return resultado


def _resolucion_categoria(
    col_xlsx: pd.Series, col_pdf: pd.Series, preferir: Preferencia | None
) -> pd.Series:
    """Compara columna categorica; discrepancias se agrupan por par unico (xlsx, pdf).

    Se pregunta (o se resuelve con `preferir`) una sola vez por cada par
    distinto de valores encontrados, y la eleccion se aplica a todas las
    filas que comparten ese par.
    """
    # 3.2: filas iguales pasan derecho, da igual de cual fuente
    difieren = col_xlsx != col_pdf
    resultado = col_pdf.copy()

    # discrepancias agrupadas por par unico (valor_xlsx, valor_pdf) -- si 5
    # genericos comparten el mismo par, es una sola pregunta para los 5, no 5
    # preguntas
    pares = {(x, p) for x, p in zip(col_xlsx[difieren], col_pdf[difieren])}
    elecciones = {}
    for valor_xlsx, valor_pdf in sorted(pares):
        print(f"Discrepancia de categoria (columna '{col_xlsx.name}'):")
        elecciones[(valor_xlsx, valor_pdf)] = _resolver(valor_xlsx, valor_pdf, preferir)

    for i in col_xlsx[difieren].index:
        resultado[i] = elecciones[(col_xlsx[i], col_pdf[i])]

    return resultado


def _resolver(valor_xlsx: object, valor_pdf: object, preferir: Preferencia | None) -> object:
    """Resuelve una discrepancia puntual: automatico si viene `preferir`, si no, pregunta en consola."""
    if preferir == "pdf":
        return valor_pdf
    if preferir == "csv":
        return valor_xlsx
    return _preguntar(valor_xlsx, valor_pdf)


def _preguntar(valor_xlsx: object, valor_pdf: object) -> object:
    """Imprime ambos valores y pregunta con cual quedarse; Enter u otra respuesta no reconocida = pdf."""
    print(f"  xlsx: {valor_xlsx}")
    print(f"  pdf:  {valor_pdf}")
    eleccion = input("con cual quedarse (Enter = pdf): ").strip().lower()
    return valor_xlsx if eleccion in ("xlsx", "x") else valor_pdf


def _decimales(valor: str) -> int:
    """Cantidad de decimales de un numero en texto (0 si no trae punto)."""
    return len(valor.split(".")[-1]) if "." in valor else 0


def _coinciden_por_redondeo(valor_xlsx: str, valor_pdf: str) -> bool:
    """True si ambos valores coinciden al redondear al numero de decimales de la fuente menos precisa."""
    precision = min(_decimales(valor_xlsx), _decimales(valor_pdf))
    return round(float(valor_xlsx), precision) == round(float(valor_pdf), precision)


def _mas_preciso(valor_xlsx: str, valor_pdf: str) -> str:
    """Devuelve el valor con mas decimales entre los dos."""
    return valor_xlsx if _decimales(valor_xlsx) >= _decimales(valor_pdf) else valor_pdf
