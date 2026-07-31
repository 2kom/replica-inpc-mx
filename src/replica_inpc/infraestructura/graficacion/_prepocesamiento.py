import pandas as pd
from mizani.breaks import breaks_extended

from replica_inpc.dominio.modelos.indice import ResultadoIndice

_MAX_ETIQUETAS_EJE_X = 20
_N_ETIQUETAS_EJE_Y = 10
_VALOR_BASE = 100.0
_COLOR_INPC = "black"
# INPC nunca aparece acá — tiene su propio color fijo (_COLOR_INPC).
# 8 tonos validados con scripts/validate_palette.js del skill dataviz (banda de
# luminosidad, piso de croma, separación CVD, piso de visión normal, contraste):
# azul, naranja, aqua, amarillo, magenta, verde, violeta, rojo, en ese orden fijo
# (nunca reordenar — el orden es parte de lo validado). Solo garantiza distinción
# confiable par-a-par entre los primeros 3-4; pasado eso, hace falta etiqueta
# directa o separar en varias gráficas (ver _datos_para_anotar).
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


def _titulo(datos: pd.DataFrame) -> str:

    tipos = list(pd.unique(datos["tipo"]))
    return " + ".join(tipos)


def _aplanar_resultado_indice(indice: ResultadoIndice) -> pd.DataFrame:
    """Aplana `.resultado.largo` a un DataFrame único, una fila por `(periodo, indice)`.

    `empalmar()` ya unifica el nombre de `indice` cross-versión (vía
    `RENOMBRES_INDICES` en `dominio/conversion.py`), así que un mismo `indice`
    (ej. `"INPC"`, o una categoría de clasificación) ya es continuo en el
    tiempo pese a traer distinto `version` por tramo — no hace falta fusionar
    nada más. Agrega `periodo_ts` (timestamp del `periodo`) para el eje X.
    """
    df = indice.resultado.largo.reset_index()
    df["periodo_ts"] = pd.to_datetime(df["periodo"].map(lambda p: p.to_timestamp()))
    return df


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


def _colores_por_serie(series: list[str]) -> dict[str, str]:
    """INPC siempre negro; el resto toma color de paleta en el orden en que aparece.

    `series` son valores de `indice` (ej. `"INPC"`, o cada categoría de una
    clasificación como `"01 alimentos y bebidas no alcoholicas"`) — nunca
    `tipo`, que agrupa varias categorías bajo un solo valor y mezclaría sus
    líneas si se usara para color/agrupación.
    """
    colores: dict[str, str] = {}
    i = 0
    for serie in series:
        if serie == "INPC":
            colores[serie] = _COLOR_INPC
        else:
            colores[serie] = _PALETA_OTROS_TIPOS[i % len(_PALETA_OTROS_TIPOS)]
            i += 1
    return colores


def _primero_y_ultimo(datos: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Primer y último punto (por fecha) de `datos`, tal cual venga ya filtrado.

    No decide QUÉ filas anotar — eso lo resuelve `_datos_para_anotar` antes
    de llamar acá. Con `datos` sin filtrar (1 sola serie) da el extremo
    global; con `datos` ya acotado a `INPC` (ver `_datos_para_anotar`) da
    el extremo propio de esa serie.
    """
    ordenado = datos.sort_values("periodo_ts")
    return ordenado.iloc[0], ordenado.iloc[-1]


def _datos_para_anotar(datos: pd.DataFrame, series: list[str]) -> pd.DataFrame | None:
    """Subconjunto de `datos` a anotar con primer/último valor, o `None` si no aplica.

    Con 1 sola serie se anota esa serie completa (comportamiento original).
    Con varias series, solo si `INPC` está presente — la anotación se ancla
    a los puntos propios de `INPC` (nunca al extremo cronológico global, que
    podría caer en cualquier otra serie) porque `INPC` ya no aparece en la
    leyenda por color (siempre negro, identificable a simple vista) y
    necesita identificarse directo en el panel. Con varias series sin
    `INPC`, no se anota nada — evita una etiqueta ambigua de "cuál serie es
    esta" cuando hay N líneas cruzadas.
    """
    if len(series) == 1:
        return datos
    if "INPC" in series:
        return datos[datos["indice"] == "INPC"]
    return None
