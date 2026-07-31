import math

import pandas as pd
from mizani.breaks import breaks_extended

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_MAX_ETIQUETAS_EJE_X = 20
_N_ETIQUETAS_EJE_Y = 10
_VALOR_BASE = 100.0
_COLOR_INPC = "black"
_LINETYPE_PRINCIPAL = "solid"
_LINETYPE_COMPARACION = "dashed"
# INPC nunca aparece acá — tiene su propio color fijo (_COLOR_INPC).
_PALETA_OTROS_TIPOS = (
    "#2a78d6",  # azul
    "#eb6834",  # naranja
    "#1baf7a",  # aqua
    "#eda100",  # amarillo
    "#e87ba4",  # magenta
    "#008300",  # verde
    "#4a3aa7",  # violeta
    "#e34948",  # rojo
)
# Mismo tope que colores validados en _PALETA_OTROS_TIPOS -- pasado esto, no hay
# color distinguible que asignar, toca partir en varias imágenes.
_MAX_SERIES_POR_IMAGEN = len(_PALETA_OTROS_TIPOS)
_MAX_CARACTERES_LEYENDA = 34


def _titulo(datos: pd.DataFrame) -> str:

    tipos = list(pd.unique(datos["tipo"]))
    return " + ".join(tipos)


def _aplanar_resultado_indice(
    indice: ResultadoIndice, comparacion: ResultadoIndice | None = None
) -> pd.DataFrame:
    """Aplana `.resultado.largo` a un DataFrame único, una fila por `(periodo, indice)`.

    `empalmar()` ya unifica el nombre de `indice` cross-versión (vía
    `RENOMBRES_INDICES` en `dominio/conversion.py`), así que un mismo `indice`
    (ej. `"INPC"`, o una categoría de clasificación) ya es continuo en el
    tiempo pese a traer distinto `version` por tramo — no hace falta fusionar
    nada más. Agrega `periodo_ts` (timestamp del `periodo`) para el eje X.

    `comparacion`, si viene, se concatena marcando `linetype="dashed"`
    (`indice` queda `linetype="solid"`) — se distingue visualmente aunque
    comparta color (ej. INPC pasado como `comparacion` de una clasificación:
    se ve punteado incluso siendo el mismo negro que tendría solo).
    """
    resultados = [(indice, _LINETYPE_PRINCIPAL)]
    if comparacion is not None:
        resultados.append((comparacion, _LINETYPE_COMPARACION))

    partes = []
    for resultado, linetype in resultados:
        df = resultado.resultado.largo.reset_index()
        df["periodo_ts"] = pd.to_datetime(df["periodo"].map(lambda p: p.to_timestamp()))
        df["linetype"] = linetype
        partes.append(df)

    return pd.concat(partes, ignore_index=True) if len(partes) > 1 else partes[0]


def _recortar_tramo(
    datos: pd.DataFrame,
    desde: PeriodoQuincenal | PeriodoMensual | None,
    hasta: PeriodoQuincenal | PeriodoMensual | None,
) -> pd.DataFrame:
    """Recorta `datos` a `[desde, hasta]` sobre la columna `periodo`. `None` en un lado = sin límite ahí.

    Mismo criterio de rango que `dominio/consulta/_comun.py::serie_en_rango`,
    pero sin exigir que `desde`/`hasta` existan exacto en los datos — acá es
    un recorte visual (zoom), no una consulta puntual.
    """
    if desde is not None and hasta is not None and hasta < desde:  # type: ignore[operator]
        raise InvarianteViolado(f"'desde' ({desde}) no puede ser posterior a 'hasta' ({hasta}).")

    mascara = pd.Series(True, index=datos.index)
    if desde is not None:
        mascara &= datos["periodo"] >= desde
    if hasta is not None:
        mascara &= datos["periodo"] <= hasta

    filtrado = datos[mascara]
    if filtrado.empty:
        raise InvarianteViolado(f"Sin datos en el rango [{desde}, {hasta}].")
    return filtrado


def _particionar_series(
    datos: pd.DataFrame, capacidad: int = _MAX_SERIES_POR_IMAGEN
) -> list[pd.DataFrame]:
    """Parte `datos` en varios DataFrames si hay más de `capacidad` series (sin contar INPC).

    `INPC` nunca cuenta para el límite ni se reparte — se incluye COMPLETO en
    cada partición, así cada imagen resultante lo trae de referencia. El
    resto de categorías se reparte lo más parejo posible en el mínimo de
    particiones necesarias (`ceil(N / capacidad)`) — ej. 13 categorías con
    capacidad 8 da particiones de 7 y 6, no 8 y 5 (evita una segunda imagen
    casi vacía).
    """
    datos_inpc = datos[datos["indice"] == "INPC"]
    demas = [v for v in pd.unique(datos["indice"]) if v != "INPC"]

    if len(demas) <= capacidad:
        return [datos]

    n_particiones = math.ceil(len(demas) / capacidad)
    base, resto = divmod(len(demas), n_particiones)

    particiones = []
    inicio = 0
    for i in range(n_particiones):
        tamano = base + (1 if i < resto else 0)
        grupo = demas[inicio : inicio + tamano]
        inicio += tamano
        parte = datos[datos["indice"].isin(grupo)]
        if not datos_inpc.empty:
            parte = pd.concat([parte, datos_inpc], ignore_index=True)
        particiones.append(parte)
    return particiones


def _ordenar_series_dibujo(valores: pd.Series) -> pd.Categorical:
    """Categórico ordenado con `INPC` al final — se dibuja último, queda por encima del resto.

    `geom_line` agrupa y dibuja según el orden categórico de `indice`, no el
    orden de fila del DataFrame — sin esto, si `INPC` llega como `resultado`
    (primero en la concatenación) en vez de `comparacion`, su línea podría
    quedar tapada por otra que se dibuje después. `INPC` siempre arriba,
    sea cual sea el parámetro por el que haya entrado. Se aplica DESPUÉS de
    particionar (`_particionar_series`) para que las categorías del
    resultado reflejen solo lo presente en cada imagen, no el total original.
    """
    orden = [v for v in pd.unique(valores) if v != "INPC"]
    if "INPC" in set(valores):
        orden.append("INPC")
    return pd.Categorical(valores, categories=orden, ordered=True)


def _breaks_y_etiquetas_x(datos: pd.DataFrame) -> tuple[list[pd.Timestamp], list[str]]:
    """Elige un subconjunto de periodos reales para las marcas del eje X.

    Usa `str(periodo)` (`"1Q Ene 2024"` o `"Ene 2024"`) de los periodos que
    ya están en los datos — no reconstruye un periodo a partir de una fecha
    arbitraria elegida por el algoritmo de breaks. El primer y último break
    son siempre el primer y último periodo real de los datos.
    """
    pares = datos[["periodo", "periodo_ts"]].drop_duplicates().sort_values("periodo_ts")
    paso = max(1, len(pares) // _MAX_ETIQUETAS_EJE_X)
    seleccion = pares.iloc[::paso]
    extremos = pares.iloc[[0, -1]]
    combinado = (
        pd.concat([seleccion, extremos])
        .drop_duplicates(subset="periodo_ts")
        .sort_values("periodo_ts")
    )
    return list(combinado["periodo_ts"]), [str(p) for p in combinado["periodo"]]


def _breaks_y_etiqueta_y(
    datos: pd.DataFrame, resultado: ResultadoIndice
) -> tuple[list[float], str]:
    """Breaks del eje Y + su etiqueta — análogo a `_breaks_y_etiquetas_x` para el eje X.

    Breaks: automáticos + forzados, mínimo y máximo siempre son el primer y
    último break; ningún break automático ni la base (100) puede quedar por
    fuera de `[mínimo, máximo]`. Etiqueta: `"Indice"`, o `"Indice
    (periodo_referencia = 100)"` si el resultado fue rebasado.
    """
    minimo = float(datos["indice_replicado"].min())
    maximo = float(datos["indice_replicado"].max())
    extendidos = breaks_extended(n=_N_ETIQUETAS_EJE_Y)((minimo, maximo))
    intermedios = {b for b in extendidos.tolist() if minimo < b < maximo}
    if minimo < _VALOR_BASE < maximo:
        intermedios.add(_VALOR_BASE)
    breaks = sorted({minimo, maximo, *intermedios})

    if resultado.periodo_referencia is None:
        etiqueta = "Indice"
    else:
        etiqueta = f"Indice ({resultado.periodo_referencia} = 100)"

    return breaks, etiqueta


def _colores_y_etiquetas(series: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Color y etiqueta de leyenda por serie — mismas claves (`indice`), siempre se usan juntos.

    `series` son valores de `indice` (ej. `"INPC"`, o cada categoría de una
    clasificación como `"01 alimentos y bebidas no alcoholicas"`) — nunca
    `tipo`, que agrupa varias categorías bajo un solo valor y mezclaría sus
    líneas si se usara para color/agrupación.

    Color: INPC siempre negro; el resto toma color de paleta en el orden en
    que aparece. Etiqueta: nombre completo, o truncado a
    `_MAX_CARACTERES_LEYENDA` con `"..."` si no cabe — nombres largos de
    clasificación (SCIAN, CCIF, ej. "22 generacion transmision distribucion y
    comercializacion de energia electrica...") desbordaban el ancho de la
    leyenda y rompían el layout compacto. La etiqueta NO afecta color ni
    agrupación — ambos dicts quedan keyed por el nombre completo, para
    `scale_color_manual(values=colores, labels=etiquetas)`.
    """
    colores: dict[str, str] = {}
    etiquetas: dict[str, str] = {}
    i = 0
    for serie in series:
        if serie == "INPC":
            colores[serie] = _COLOR_INPC
        else:
            colores[serie] = _PALETA_OTROS_TIPOS[i % len(_PALETA_OTROS_TIPOS)]
            i += 1
        if len(serie) > _MAX_CARACTERES_LEYENDA:
            etiquetas[serie] = serie[: _MAX_CARACTERES_LEYENDA - 3] + "..."
        else:
            etiquetas[serie] = serie
    return colores, etiquetas


def _primero_y_ultimo_para_anotar(
    datos: pd.DataFrame, series: list[str]
) -> tuple[pd.Series, pd.Series] | None:
    """Primer y último punto a anotar con su valor, o `None` si no aplica.

    Solo con 1 sola serie (el mismo caso donde no hay leyenda) — con varias
    series, aunque `INPC` esté presente, no se anota nada: con N líneas
    cruzadas el numerito compite con la leyenda por espacio y no aporta.
    """
    if len(series) != 1:
        return None
    ordenado = datos.sort_values("periodo_ts")
    return ordenado.iloc[0], ordenado.iloc[-1]
