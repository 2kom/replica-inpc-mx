import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import pandas as pd

from canasta_inpc.esquema import COLUMNAS_BASE, FUENTES_POSIBLES, VersionCanasta

Preferencia = Literal["pdf", "xlsx"]
Origen = Literal["xlsx", "pdf", "ambas", "mixto"]
Metodo = Literal["igual", "redondeo", "preferido", "interactiva", "directo"]


@dataclass(frozen=True)
class Resolucion:
    """Como se resolvio un campo (fila) o una categoria (par unico xlsx/pdf) al cruzar fuentes.

    `genericos` es 1 elemento en columnas fila (`ponderador`/`encadenamiento`)
    y N en columnas categoricas (todos los genericos que comparten el mismo
    par `valor_xlsx`/`valor_pdf`, o el mismo valor unico en columnas de una
    sola fuente). `valor_xlsx`/`valor_pdf` son `None` cuando esa fuente no
    trae la columna en esta version (`metodo="directo"`). `origen="mixto"`
    marca el hibrido CCIF (`_reconstruir_hibrido_ccif`): `valor_final` no es identico a
    `valor_xlsx` NI a `valor_pdf`.
    """

    columna: str
    genericos: tuple[str, ...]
    valor_xlsx: str | None
    valor_pdf: str | None
    valor_final: str
    origen: Origen
    metodo: Metodo


@dataclass
class ResultadoMatch:
    """Df maestro del cruce xlsx+pdf, mas el detalle de como se resolvio cada campo/categoria."""

    df: pd.DataFrame
    resoluciones: tuple[Resolucion, ...]


# columnas que se comparan fila por fila cuando ambas fuentes las traen (grupo A);
# el resto de columnas con ambas fuentes se comparan agrupando por par unico (grupo B)
_COLUMNAS_FILA = {"generico", "ponderador", "encadenamiento"}
_COLUMNAS_NUMERICAS = {"ponderador", "encadenamiento"}

# CCIF division/grupo/clase es la unica familia donde xlsx y pdf difieren a
# proposito en el prefijo numerico (contrato: extraccion_xlsx.py SIEMPRE lo
# quita, extraccion_pdf.py SIEMPRE lo conserva, ver utilidades.py) -- sin
# ignorar el prefijo al comparar, CUALQUIER division/grupo/clase sin
# divergencia real de nombre dispara una pregunta espuria (confirmado
# corriendo la tool real contra 2018: decenas de prompts por solo el
# prefijo). El codigo puede ser jerarquico ("01", "01.1", "01.1.1"), a
# diferencia de `quitar_prefijo_numerico` que solo pela un nivel simple
_COLUMNAS_CCIF = {"CCIF division", "CCIF grupo", "CCIF clase"}
_PATRON_CODIGO_CCIF = re.compile(r"^\d+(\.\d+)*\s+")


def _sin_codigo_ccif(texto: str) -> str:
    return _PATRON_CODIGO_CCIF.sub("", texto, count=1)


def _codigo_ccif(texto: str) -> str:
    """Codigo inicial (con el espacio que lo separa del nombre), o "" si no trae."""
    m = _PATRON_CODIGO_CCIF.match(texto)
    return m[0] if m else ""


def match_dfs(
    df_xlsx: pd.DataFrame,
    df_pdf: pd.DataFrame,
    version: VersionCanasta,
    preferir: Preferencia | None = None,
) -> ResultadoMatch:
    """Cruza extracciones xlsx y pdf en un df maestro, resolviendo discrepancias.

    `preferir` salta las preguntas interactivas y resuelve automatico ("pdf" o
    "xlsx", el valor viene tal cual del flag `--preferir` del CLI, "xlsx" =
    valor extraido del xlsx); sin `preferir`, discrepancia real = pregunta en
    consola, Enter = pdf.

    Devuelve tambien `resoluciones`: una `Resolucion` por cada campo (grupo A,
    incluidas columnas de una sola fuente -- grupo C fila) o por cada categoria
    final (grupo B, incluidas categoricas de una sola fuente -- grupo C
    categoria). `registro.py` solo agrupa y serializa esto, no reconstruye
    nada comparando de nuevo `df_xlsx`/`df_pdf`/`df` despues.

    Ver: tools/uso_generar_canasta.md §Cruce `xlsx` + `pdf`.
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
    resoluciones: list[Resolucion] = []

    # paso 2: avanzar columna por columna, en el orden final de COLUMNAS_BASE
    # (asi el df maestro ya sale con las columnas en orden, sin reindex extra;
    # "generico" es la primera, entonces para el resto de columnas
    # `df_maestro["generico"]` ya trae el nombre final resuelto)
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
                genericos_ref = (
                    df_xlsx["generico"] if columna == "generico" else df_maestro["generico"]
                )
                valores, res = _resolver_fila(
                    df_xlsx[columna],
                    df_pdf[columna],
                    genericos_ref,
                    columna,
                    numerica=columna in _COLUMNAS_NUMERICAS,
                    preferir=preferir,
                )
                df_maestro[columna] = valores
                resoluciones.extend(res)
            else:
                # grupo B: columnas categoricas -- discrepancias se agrupan
                # por par unico (valor_xlsx, valor_pdf), se resuelve una vez
                # por par, no una vez por fila
                valores, res = _resolver_categoria(
                    df_xlsx[columna],
                    df_pdf[columna],
                    df_maestro["generico"],
                    preferir=preferir,
                    columna=columna,
                )
                df_maestro[columna] = valores
                resoluciones.extend(res)
        elif "xlsx" in origenes:
            # grupo C: solo el xlsx trae esta columna en esta version -- se
            # copia directo, no hay nada que cruzar
            df_maestro[columna] = df_xlsx[columna]
            resoluciones.extend(
                _resolver_directo(df_xlsx[columna], df_maestro["generico"], columna, "xlsx")
            )
        elif "pdf" in origenes:
            # grupo C: solo el pdf la trae -- copia directo
            df_maestro[columna] = df_pdf[columna]
            resoluciones.extend(
                _resolver_directo(df_pdf[columna], df_maestro["generico"], columna, "pdf")
            )
        else:
            # grupo D: ninguna de las dos fuentes la trae (o solo "sync", que
            # no participa de este cruce xlsx+pdf) -- columna vacia
            df_maestro[columna] = ""

    # paso 4: df maestro queda armado y ordenado; quien llama lo pasa a
    # guardar_csv (que ya hace su propio reindex/fill contra COLUMNAS_BASE)
    return ResultadoMatch(df=df_maestro, resoluciones=tuple(resoluciones))


def _resolver_fila(
    col_xlsx: pd.Series,
    col_pdf: pd.Series,
    genericos: pd.Series,
    columna: str,
    numerica: bool,
    preferir: Preferencia | None,
) -> tuple[pd.Series, tuple[Resolucion, ...]]:
    """Compara fila por fila; discrepancia real se resuelve a mano, una por una (Enter = pdf).

    Para columnas numericas (3.1 del procedimiento): una discrepancia dentro
    de la tolerancia de redondeo (la fuente de menor precision cabe en la de
    mayor precision) no cuenta como discrepancia real -- se resuelve sola,
    quedandose con el valor de mayor precision, sin preguntar ni consultar
    `preferir`.
    """
    resultado = pd.Series(index=col_xlsx.index, dtype=object)
    resoluciones: list[Resolucion] = []

    for i in col_xlsx.index:
        valor_xlsx = col_xlsx[i]
        valor_pdf = col_pdf[i]
        generico = genericos[i]

        # 3.2 (aplica igual a filas no numericas): iguales, no hay nada que resolver
        if valor_xlsx == valor_pdf:
            resultado[i] = valor_pdf
            resoluciones.append(
                Resolucion(columna, (generico,), valor_xlsx, valor_pdf, valor_pdf, "ambas", "igual")
            )
            continue

        # 3.1: numerica dentro de tolerancia de redondeo -- se resuelve sola
        if numerica and _coinciden_por_redondeo(str(valor_xlsx), str(valor_pdf)):
            valor, origen = _mas_preciso(str(valor_xlsx), str(valor_pdf))
            resultado[i] = valor
            resoluciones.append(
                Resolucion(columna, (generico,), valor_xlsx, valor_pdf, valor, origen, "redondeo")
            )
            continue

        # discrepancia real: se pregunta esta fila puntual (o se resuelve con
        # `preferir` sin preguntar)
        print(f"Discrepancia en la fila {i} (columna '{columna}'):")
        origen = _resolver(valor_xlsx, valor_pdf, preferir)
        valor = valor_xlsx if origen == "xlsx" else valor_pdf
        metodo: Metodo = "preferido" if preferir is not None else "interactiva"
        resultado[i] = valor
        resoluciones.append(
            Resolucion(columna, (generico,), valor_xlsx, valor_pdf, valor, origen, metodo)
        )

    return resultado, tuple(resoluciones)


def _resolver_categoria(
    col_xlsx: pd.Series,
    col_pdf: pd.Series,
    genericos: pd.Series,
    preferir: Preferencia | None,
    columna: str,
) -> tuple[pd.Series, tuple[Resolucion, ...]]:
    """Compara columna categorica; discrepancias se agrupan por par unico (xlsx, pdf).

    Se pregunta (o se resuelve con `preferir`) una sola vez por cada par
    distinto de valores encontrados, y la eleccion se aplica a todas las
    filas que comparten ese par. En `CCIF division`/`grupo`/`clase`, la
    comparacion ignora el prefijo numerico (`_COLUMNAS_CCIF`): xlsx nunca lo
    trae y pdf siempre si, esa diferencia por si sola no es una discrepancia
    real. Si SI hay discrepancia real de nombre en una columna CCIF y gana el
    nombre del xlsx, `_reconstruir_hibrido_ccif` repone el codigo (que solo el pdf trae)
    en vez de perderlo -- `origen="mixto"` en ese caso.
    """
    es_ccif = columna in _COLUMNAS_CCIF
    resultado = col_pdf.copy()
    resoluciones: list[Resolucion] = []

    # un solo bucle por par unico, cubre tanto pares iguales (metodo="igual",
    # sin preguntar) como discrepancias reales (metodo="preferido"/"interactiva")
    pares = {(x, p) for x, p in zip(col_xlsx, col_pdf)}
    for valor_xlsx, valor_pdf in sorted(pares):
        mascara = (col_xlsx == valor_xlsx) & (col_pdf == valor_pdf)
        genericos_grupo = tuple(genericos[mascara])

        clave_xlsx = _sin_codigo_ccif(valor_xlsx) if es_ccif else valor_xlsx
        clave_pdf = _sin_codigo_ccif(valor_pdf) if es_ccif else valor_pdf

        if clave_xlsx == clave_pdf:
            # 3.2: sin discrepancia real -- el valor final sigue siendo el
            # crudo de pdf (ya trae el prefijo correcto en CCIF); origen
            # "ambas" solo si el string crudo tambien era identico, si no
            # (CCIF con prefijo distinto) el codigo solo vino de pdf. Si
            # ademas el valor es vacio (ninguna fuente clasifico este par) no
            # hubo decision real que registrar, unico caso que se omite aqui
            origen: Origen = "ambas" if valor_xlsx == valor_pdf else "pdf"
            valor_final = valor_pdf
            resultado.loc[mascara] = valor_final
            if valor_final != "":
                resoluciones.append(
                    Resolucion(
                        columna,
                        genericos_grupo,
                        valor_xlsx,
                        valor_pdf,
                        valor_final,
                        origen,
                        "igual",
                    )
                )
            continue

        afectados = len(genericos_grupo)
        print(f"Discrepancia de categoria (columna '{columna}'), afecta a {afectados} generico(s):")
        origen_elegido = _resolver(valor_xlsx, valor_pdf, preferir)
        metodo: Metodo = "preferido" if preferir is not None else "interactiva"

        if es_ccif and origen_elegido == "xlsx":
            valor_final, origen_final = _reconstruir_hibrido_ccif(valor_xlsx, valor_pdf)
        else:
            valor_final = valor_xlsx if origen_elegido == "xlsx" else valor_pdf
            origen_final = origen_elegido

        resultado.loc[mascara] = valor_final
        # a diferencia del caso "igual" de arriba, aqui SI hubo una decision
        # real (clave_xlsx != clave_pdf) -- se conserva aunque el valor
        # elegido resulte vacio (ej. --preferir xlsx y xlsx no clasifico este
        # generico), para que la decision no desaparezca del registro
        resoluciones.append(
            Resolucion(
                columna, genericos_grupo, valor_xlsx, valor_pdf, valor_final, origen_final, metodo
            )
        )

    return resultado, tuple(resoluciones)


def _reconstruir_hibrido_ccif(valor_xlsx: str, valor_pdf: str) -> tuple[str, Origen]:
    """Repone el codigo CCIF (que xlsx nunca trae) sobre el nombre elegido del xlsx.

    Sin esto, si gana el nombre del xlsx en una discrepancia real, el codigo
    se pierde por completo (xlsx nunca lo trae). El codigo SIEMPRE sale del
    pdf, unica fuente que lo tiene; si por algun motivo el pdf no trae codigo
    (no deberia pasar, dado el contrato de extraccion), se usa el xlsx tal
    cual, sin fabricar un origen mixto que no aplica.

    Si el xlsx no clasifico este generico (`valor_xlsx == ""`), tampoco hay
    nombre que reponerle codigo -- devolver `f"{codigo} "` seria basura (un
    codigo suelto sin nombre, ni vacio de verdad ni un hibrido real). Se
    devuelve vacio tal cual, para que quede como decision real sin clasificar
    (`sin_clasificar` en `registro.py`), no como un valor hibrido inventado.
    """
    if not valor_xlsx:
        return "", "xlsx"
    codigo = _codigo_ccif(valor_pdf)
    if not codigo:
        return valor_xlsx, "xlsx"
    return f"{codigo}{valor_xlsx}", "mixto"


def _resolver_directo(
    col: pd.Series, genericos: pd.Series, columna: str, origen: Origen
) -> tuple[Resolucion, ...]:
    """`Resolucion` para columnas de una sola fuente (grupo C): sin comparacion, `metodo="directo"`.

    Una `Resolucion` por generico en columnas fila (`ponderador`/
    `encadenamiento`) -- incluidos los vacios: `registro.py` arma una entrada
    de `genericos_detalle` por CADA generico del df, un vacio omitido aqui
    causaria un `KeyError` alla al buscar metadata que nunca se genero. Una
    por valor unico (agrupando genericos) en columnas categoricas -- mismo
    criterio de agrupacion que `_resolver_categoria`, para que el resumen de
    `registro.py` sea igual de facil de leer; ahi si se omiten los vacios
    (`_conteo_genericos_categoria` tampoco cuenta "no clasificado" como
    categoria real).
    """
    if columna in _COLUMNAS_FILA:
        return tuple(
            Resolucion(
                columna,
                (genericos[i],),
                col[i] if origen == "xlsx" else None,
                col[i] if origen == "pdf" else None,
                col[i],
                origen,
                "directo",
            )
            for i in col.index
        )

    resoluciones = []
    for valor in sorted(v for v in col.unique() if v != ""):
        mascara = col == valor
        genericos_grupo = tuple(genericos[mascara])
        resoluciones.append(
            Resolucion(
                columna,
                genericos_grupo,
                valor if origen == "xlsx" else None,
                valor if origen == "pdf" else None,
                valor,
                origen,
                "directo",
            )
        )
    return tuple(resoluciones)


def _resolver(valor_xlsx: object, valor_pdf: object, preferir: Preferencia | None) -> Origen:
    """Resuelve una discrepancia puntual: automatico si viene `preferir`, si no, pregunta en consola."""
    if preferir == "pdf":
        return "pdf"
    if preferir == "xlsx":
        return "xlsx"
    return _preguntar(valor_xlsx, valor_pdf)


def _preguntar(valor_xlsx: object, valor_pdf: object) -> Origen:
    """Imprime ambos valores y pregunta con cual quedarse; Enter u otra respuesta no reconocida = pdf."""
    print(f"  xlsx: {valor_xlsx}")
    print(f"  pdf:  {valor_pdf}")
    eleccion = input("con cual quedarse (Enter = pdf): ").strip().lower()
    origen: Origen = "xlsx" if eleccion in ("xlsx", "x") else "pdf"
    print(f"  elegido: {origen}")
    return origen


def _decimales(valor: str) -> int:
    """Cantidad de decimales de un numero en texto.

    Via `Decimal` en vez de contar caracteres tras el punto -- un simple
    `split(".")` da 0 decimales para notacion cientifica ("1E-5" tiene 5
    decimales reales, no 0), fabricando una imprecision falsa al comparar
    contra `_mas_preciso`.
    """
    exponente = Decimal(valor).as_tuple().exponent
    return max(0, -exponente) if isinstance(exponente, int) else 0


def _coinciden_por_redondeo(valor_xlsx: str, valor_pdf: str) -> bool:
    """True si ambos valores coinciden al redondear al numero de decimales de la fuente menos precisa."""
    precision = min(_decimales(valor_xlsx), _decimales(valor_pdf))
    return round(float(valor_xlsx), precision) == round(float(valor_pdf), precision)


def _mas_preciso(valor_xlsx: str, valor_pdf: str) -> tuple[str, Origen]:
    """Devuelve el valor con mas decimales entre los dos, y de que fuente vino."""
    if _decimales(valor_xlsx) >= _decimales(valor_pdf):
        return valor_xlsx, "xlsx"
    return valor_pdf, "pdf"
