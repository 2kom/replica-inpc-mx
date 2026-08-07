"""Cálculo de incidencias a partir de `ResultadoIndice`.

Tres funciones producen `ResultadoIncidencia` combinando el INPC con un
resultado de clasificación (`COG`, `CCIF DIVISION`, etc.):

- `incidencia_periodica` — incidencia periodo a periodo por genérico.
- `incidencia_acumulada_anual` — enero..periodo vs diciembre del año anterior.
- `incidencia_desde` — incidencia total de un rango; una fila por genérico.

Corrige la escala de los índices antes de descomponer:

- Fix 1: los ponderadores son los de la canasta del periodo base.
- `indice_incidencia` (= i_tramo de-encadenado, columna interna de `ResultadoIndice`)
  se usa within-canasta (`version_t == version_base`): exacto e invariante al rebase.
- Cross-canasta (`version_t != version_base`): para tipos de clasificación estable
  (`_es_clasificacion_estable`) se descompone exacto por segmentos
  (`_calcular_incidencia_cross_encadenada`), derivando el ancla del lado nuevo de cada
  junta por continuidad del visible — exacto para las 3 juntas, T1 incluida; para tipos
  finos sin clasificación estable cae al `indice_replicado` visible (`cross_visible`,
  sin garantía).
  El método por fila se marca en `metodo_incidencia` — en `.reporte`/`.diagnostico`, NO en
  `.resultado.largo` (`Vista.largo` devuelve el `_df_resultado` entero). El cruce es además
  detectable por `version_t != version_lag`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.calculo._temporal import (
    LAG_MENSUAL,
    LAG_QUINCENAL,
    Frecuencia,
    es_mensual,
    resolver_extremo,
    restar_meses,
    restar_quincenas,
)
from replica_inpc.dominio.correspondencia_canastas import (
    _ORDEN_VERSIONES,
    RENOMBRES_GENERICOS,
    _componer_mapas,
    _construir_mapa_renombre,
    _renombrar_valor,
)
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    RANGOS_CANASTAS,
    TIPO_INPC,
    ManifestDerivado,
    MetodoIncidencia,
    VersionCanasta,
)

Periodo = PeriodoQuincenal | PeriodoMensual

_COLS_REPORTE = [
    "estado_calculo",
    "motivo_error",
    "metodo_incidencia",
    "periodo_lag",
    "indice_t",
    "indice_lag",
    "ponderador_t",
    "ponderador_lag",
    "version_t",
    "version_lag",
    "cobertura_pct_t",
    "cobertura_pct_lag",
]
_COLS_DIAGNOSTICO = [
    "versiones",
    "tipo",
    "clase_incidencia",
    "periodo",
    "indice",
    "estado_calculo",
    "motivo_error",
    "metodo_incidencia",
    "periodo_lag",
    "version_t",
    "version_lag",
]


def _verificar_periodo_referencia(inpc: ResultadoIndice, clasificacion: ResultadoIndice) -> None:
    if inpc.periodo_referencia != clasificacion.periodo_referencia:
        raise InvarianteViolado(
            f"'inpc' y 'clasificacion' deben compartir periodo_referencia; "
            f"se recibió {inpc.periodo_referencia!r} y "
            f"{clasificacion.periodo_referencia!r}."
        )


def _validar_entradas(
    df_inpc: pd.DataFrame,
    df_clas: pd.DataFrame,
    canastas: dict[int, CanastaCanonica],
) -> None:
    tipo_inpc = str(df_inpc["tipo"].iloc[0])
    if tipo_inpc != TIPO_INPC:
        raise ErrorConfiguracion(
            f"El primer argumento debe ser un resultado de tipo '{TIPO_INPC}', "
            f"se recibió '{tipo_inpc}'."
        )
    tipo_clas = str(df_clas["tipo"].iloc[0])
    if tipo_clas not in COLUMNAS_CLASIFICACION:
        raise ErrorConfiguracion(
            f"El tipo de clasificación '{tipo_clas}' no es válido. "
            f"Tipos soportados: {sorted(COLUMNAS_CLASIFICACION)}"
        )
    clas_vers = {int(v) for v in df_clas["version"].unique()}
    faltantes = clas_vers - set(canastas.keys())
    if faltantes:
        raise ErrorConfiguracion(
            f"Falta canasta para versión(es) {sorted(faltantes)}. "
            "Proporciona una canasta por cada versión presente en el resultado."
        )


def _obtener_lag_y_mensual(df_clas: pd.DataFrame, frecuencia: Frecuencia) -> tuple[int, bool]:
    """Valida `frecuencia` y devuelve `(lag, mensual)`."""
    mensual = es_mensual(df_clas)
    lag_map = LAG_MENSUAL if mensual else LAG_QUINCENAL
    if frecuencia not in lag_map:
        raise InvarianteViolado(
            f"Frecuencia '{frecuencia}' no aplica a periodos "
            f"{'mensuales' if mensual else 'quincenales'}. "
            f"Válidas: {sorted(lag_map)}."
        )
    return lag_map[frecuencia], mensual


def _construir_mapa_generico(version_origen: int, version_canonica: int) -> dict[str, str]:
    """Compone `RENOMBRES_GENERICOS` de `version_origen` a `version_canonica`.

    Análogo a `_construir_mapa_renombre` pero sobre genéricos (sin `tipo`).
    """
    orden: list[int] = list(_ORDEN_VERSIONES)
    if version_origen == version_canonica:
        return {}
    try:
        idx_o = orden.index(version_origen)
        idx_c = orden.index(version_canonica)
    except ValueError:
        return {}
    mapa: dict[str, str] = {}
    if idx_o < idx_c:
        for paso in range(idx_o, idx_c):
            mapa = _componer_mapas(mapa, dict(RENOMBRES_GENERICOS.get(orden[paso], {})))
    else:
        pasos_inv: list[dict[str, str]] = []
        for paso in range(idx_c, idx_o):
            fwd = dict(RENOMBRES_GENERICOS.get(orden[paso], {}))
            pasos_inv.append({v: k for k, v in fwd.items()})
        for m in reversed(pasos_inv):
            mapa = _componer_mapas(mapa, m)
    return mapa


def _es_clasificacion_estable(tipo: str, canastas: dict[int, CanastaCanonica]) -> bool:
    """`True` si `tipo` tiene clasificación estable entre las versiones de `canastas`.

    Clasificación estable = (a) el conjunto de categorías es idéntico entre versiones
    tras alinear nombres con `RENOMBRES_INDICES`, y (b) ningún genérico cambia de
    categoría tras alinear con `RENOMBRES_GENERICOS`. Solo lee; ante cualquier duda
    devuelve `False` (cae a `cross_visible`, sin regresión).
    """
    versiones = sorted(canastas)
    if len(versiones) < 2:
        return True
    vc = max(versiones)
    cat_sets: list[set[str]] = []
    gen_cat: list[dict[str, str]] = []
    for v in versiones:
        df = canastas[v].df
        if tipo not in df.columns:
            return False
        serie = df[tipo].dropna()
        mapa_cat = _construir_mapa_renombre(tipo, int(v), vc)
        mapa_gen = _construir_mapa_generico(int(v), vc)
        d: dict[str, str] = {}
        for gen_nat, cat_nat in serie.items():
            gen_c = mapa_gen.get(str(gen_nat), str(gen_nat))
            cat_c = _renombrar_valor(str(cat_nat), tipo, int(v), mapa_cat)
            d[gen_c] = cat_c
        gen_cat.append(d)
        cat_sets.append(set(d.values()))
    if any(cat_sets[0] != s for s in cat_sets[1:]):
        return False
    todos_gen = set().union(*(set(d) for d in gen_cat))
    for g in todos_gen:
        cats = {d[g] for d in gen_cat if g in d}
        if len(cats) > 1:
            return False
    return True


def _partir_en_segmentos(
    ver_b: int, ver_t: int, b: Periodo, t: Periodo
) -> list[tuple[int, Periodo, Periodo, bool, bool]]:
    """Parte `[b, t]` en segmentos por las juntas de canasta que atraviesa.

    Devuelve `(version_m, inicio_m, fin_m, inicio_es_junta_nueva, fin_es_junta_vieja)`.
    Las juntas son los límites inferiores de `RANGOS_CANASTAS` de las versiones más
    nuevas; son periodos QUINCENALES aun cuando `b`/`t` sean mensuales (el punto de
    enlace oculto). Lanza `InvarianteViolado` si `ver_b`/`ver_t` no forman un cruce
    hacia adelante (consistencia: una fila cross siempre debe producir ≥2 segmentos).
    """
    orden: list[int] = list(_ORDEN_VERSIONES)
    try:
        i = orden.index(int(ver_b))
        j = orden.index(int(ver_t))
    except ValueError as exc:
        raise InvarianteViolado(
            f"_partir_en_segmentos: versión desconocida (ver_b={ver_b}, ver_t={ver_t})."
        ) from exc
    if i >= j:
        raise InvarianteViolado(
            f"_partir_en_segmentos: fila cross sin cruce hacia adelante "
            f"(ver_b={ver_b}, ver_t={ver_t}); no hay junta entre ellas."
        )
    juntas = [RANGOS_CANASTAS[orden[k]][0] for k in range(i + 1, j + 1)]  # type: ignore[index]
    total = j - i + 1
    segmentos: list[tuple[int, Periodo, Periodo, bool, bool]] = []
    for m in range(1, total + 1):
        ver_m = orden[i + m - 1]
        inicio: Periodo = b if m == 1 else juntas[m - 2]
        fin: Periodo = t if m == total else juntas[m - 1]
        segmentos.append((ver_m, inicio, fin, m > 1, m < total))
    return segmentos


def _construir_lector_ancla(
    df: pd.DataFrame,
    frontera: pd.DataFrame | None,
    indice: str,
    columna: str,
    mensual: bool,
) -> Callable[[Periodo, bool], float | None]:
    """Devuelve `leer(periodo, es_junta_del_lado_viejo) -> valor` para un índice y columna.

    En mensual la quincena de enlace no existe en `df` — el promedio mensual la absorbió —
    así que el lado viejo de la junta se lee de `frontera`, en `<columna>_old`. En
    quincenal la fila de la junta sí está en `df` (el empalme se la asigna al tramo
    anterior) y ambos caminos coinciden. Devuelve `None` si falta la fila o el valor.
    """
    columna_old = f"{columna}_old"

    def leer(periodo: Periodo, junta_lado_viejo: bool) -> float | None:
        fuente, col = df, columna
        if junta_lado_viejo and mensual:
            if frontera is None:
                return None
            fuente, col = frontera, columna_old
        try:
            valor = float(fuente.at[(periodo, indice), col])  # type: ignore[arg-type]
        except KeyError:
            return None
        return None if pd.isna(valor) else valor

    return leer


def _verificar_operandos(
    valores: Mapping[str, float], divisores: frozenset[str], contexto: str
) -> None:
    """Exige finitud a todos los operandos y `!= 0` solo a los divisores.

    Mismo contrato que `variaciones.py`: un operando **ausente** no llega acá — el llamador
    lo trata antes como fila no computable. Esta guardia es para dato **presente pero
    inválido** (`±inf`, o cero en un denominador), que sin ella se propagaría como
    `inf`/`nan` hasta la salida pública con `estado_calculo = "ok"`.

    Raises:
        InvarianteViolado: Si algún operando es no finito, o si un divisor vale cero.
    """
    for nombre, valor in valores.items():
        if not np.isfinite(valor):
            raise InvarianteViolado(f"incidencias: {nombre} no finito ({valor}) en {contexto}.")
        if nombre in divisores and valor == 0:
            raise InvarianteViolado(f"incidencias: {nombre} = 0 (divisor) en {contexto}.")


def _calcular_incidencia_cross_encadenada(
    t: Periodo,
    indice: str,
    b: Periodo,
    ver_t: int,
    ver_b: int,
    mensual: bool,
    df_inpc: pd.DataFrame,
    df_clas: pd.DataFrame,
    inpc_frontera: pd.DataFrame | None,
    clas_frontera: pd.DataFrame | None,
    pond_por_version: dict[int, pd.Series],
) -> tuple[float | None, MetodoIncidencia]:
    """Incidencia cross-canasta exacta por encadenamiento de segmentos.

    ```text
    f_INPC^(m) = INPC_visible(fin_m) / J_INPC(fin_m)
    f_K^(m)    = I_K_visible(fin_m)  / J_K(fin_m)
    J_K(inicio_m) = I_K_visible(junta) / f_K^(m)   si el segmento empieza en junta
                  = J_K(b)                         en el primer segmento
    contribucion = Σ_m f_INPC^(m) · w_K · (J_K(fin_m) − J_K(inicio_m)) / INPC_visible(b)
    ```

    `J = indice_incidencia` (de-encadenado) en la escala interna de cada segmento. Los
    factores `f^(m)` se leen de un periodo **real** de la versión `m` — `fin_m`, que es `t`
    en el último segmento y la junta que cierra el segmento en los demás (esa fila
    pertenece al tramo viejo, o sea a la versión `m`). El ancla del lado nuevo de la junta
    **no se supone igual a 100**: se deriva por continuidad del visible, que el
    encadenamiento preserva. Eso hace exactas por igual las juntas T1 (2013, cuyo
    `i_tramo` no ancla en 100), directo (2018) y T2 (2024).

    Es una reagrupación algebraica de la forma con `S_m = INPC_visible(inicio_m)/
    INPC_visible(b)`: `S_m / J_INPC(inicio_m)` equivale a `f_INPC^(m) / INPC_visible(b)`.
    Con esta forma desaparece la división por `J_INPC(inicio_m)`.

    Returns:
        `(valor, estado)`. Con `valor=None` el llamador conserva el visible de Fase 1;
        único caso: `cross_sin_frontera` (falta un ancla, típicamente la de enlace mensual).

    Raises:
        InvarianteViolado: Si la fila cross no produce ≥2 segmentos, o si algún operando
            presente es no finito o un divisor vale cero.

    Ver: docs/diseño.md §11.29, data/glosario.md (símbolos `J_K`/`J_INPC`/`f_K^(m)`/
        `f_INPC^(m)`/ancla, sección "Notación matemática").
    """
    segmentos = _partir_en_segmentos(ver_b, ver_t, b, t)
    if len(segmentos) < 2:
        raise InvarianteViolado(
            f"_calcular_incidencia_cross_encadenada: fila cross ({t}, {indice}) sin junta."
        )
    contexto = f"({t}, {indice})"

    j_k = _construir_lector_ancla(df_clas, clas_frontera, indice, "indice_incidencia", mensual)
    i_k_visible = _construir_lector_ancla(
        df_clas, clas_frontera, indice, "indice_replicado", mensual
    )
    j_inpc = _construir_lector_ancla(df_inpc, inpc_frontera, "INPC", "indice_incidencia", mensual)
    inpc_visible = _construir_lector_ancla(
        df_inpc, inpc_frontera, "INPC", "indice_replicado", mensual
    )

    inpc_vis_b = inpc_visible(b, False)
    if inpc_vis_b is None:
        return None, "cross_sin_frontera"
    _verificar_operandos({"INPC_visible(b)": inpc_vis_b}, frozenset({"INPC_visible(b)"}), contexto)

    total = 0.0
    for ver_m, inicio, fin, inicio_junta_nueva, fin_junta_vieja in segmentos:
        w_k = _ponderador(pond_por_version, int(ver_m), indice)
        j_k_fin = j_k(fin, fin_junta_vieja)
        i_k_visible_fin = i_k_visible(fin, fin_junta_vieja)
        j_inpc_fin = j_inpc(fin, fin_junta_vieja)
        inpc_visible_fin = inpc_visible(fin, fin_junta_vieja)
        # El lado nuevo de la junta no sobrevive al empalme (la fila la posee el tramo
        # anterior), así que su J se deriva del visible, continuo en el enlace.
        ancla_inicio = i_k_visible(inicio, True) if inicio_junta_nueva else j_k(inicio, False)

        crudos = (w_k, j_k_fin, i_k_visible_fin, j_inpc_fin, inpc_visible_fin, ancla_inicio)
        if any(x is None or pd.isna(x) for x in crudos):
            return None, "cross_sin_frontera"
        _verificar_operandos(
            {
                "w_K": w_k,
                "J_K(fin_m)": cast(float, j_k_fin),
                "I_K_visible(fin_m)": cast(float, i_k_visible_fin),
                "J_INPC(fin_m)": cast(float, j_inpc_fin),
                "INPC_visible(fin_m)": cast(float, inpc_visible_fin),
                "ancla_inicio": cast(float, ancla_inicio),
            },
            frozenset({"J_K(fin_m)", "J_INPC(fin_m)"}),
            contexto,
        )

        f_inpc = cast(float, inpc_visible_fin) / cast(float, j_inpc_fin)
        f_k = cast(float, i_k_visible_fin) / cast(float, j_k_fin)
        _verificar_operandos(
            {"f_K^(m)": f_k, "f_INPC^(m)": f_inpc}, frozenset({"f_K^(m)"}), contexto
        )

        j_k_inicio = cast(float, ancla_inicio) / f_k if inicio_junta_nueva else ancla_inicio
        contribucion = f_inpc * w_k * (cast(float, j_k_fin) - cast(float, j_k_inicio)) / inpc_vis_b
        _verificar_operandos({"contribucion_m": contribucion}, frozenset(), contexto)
        total += contribucion
    _verificar_operandos({"total cross": total}, frozenset(), contexto)
    return total, "cross_segmentado"


def incidencia_periodica(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    frecuencia: Frecuencia,
) -> ResultadoIncidencia:
    """Incidencia de cada periodo contra N periodos anteriores."""
    _verificar_periodo_referencia(inpc, clasificacion)
    df_inpc = inpc._completo
    df_clas = clasificacion._completo
    _validar_entradas(df_inpc, df_clas, canastas)
    lag, mensual = _obtener_lag_y_mensual(df_clas, frecuencia)
    restar = restar_meses if mensual else restar_quincenas

    periodos = df_clas.index.get_level_values("periodo")
    base_periodos = [restar(p, lag) for p in periodos]  # type: ignore[arg-type]
    return _construir_resultado(
        df_clas,
        df_clas,
        canastas,
        base_periodos,
        f"periodica_{frecuencia}",
        "",
        inpc,
        clasificacion,
        None,
    )


def incidencia_acumulada_anual(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
) -> ResultadoIncidencia:
    """Incidencia de cada periodo contra diciembre del año anterior."""
    _verificar_periodo_referencia(inpc, clasificacion)
    df_inpc = inpc._completo
    df_clas = clasificacion._completo
    _validar_entradas(df_inpc, df_clas, canastas)
    mensual = es_mensual(df_clas)

    periodos = df_clas.index.get_level_values("periodo")
    if mensual:
        base_periodos: list[Periodo] = [PeriodoMensual(p.año - 1, 12) for p in periodos]
    else:
        base_periodos = [PeriodoQuincenal(p.año - 1, 12, 2) for p in periodos]
    return _construir_resultado(
        df_clas,
        df_clas,
        canastas,
        base_periodos,
        "acumulada_anual",
        "",
        inpc,
        clasificacion,
        None,
    )


def incidencia_desde(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    desde: Periodo | None = None,
    hasta: Periodo | None = None,
    incluir_parciales: bool = True,
) -> ResultadoIncidencia:
    """Incidencia total del rango `[desde, hasta]`; una fila por genérico.

    Con `incluir_parciales=True`, un genérico sin dato exacto en `desde`/`hasta`
    usa el primer/último periodo válido del rango; el periodo real usado se
    registra en `indices_parciales`.
    """
    _verificar_periodo_referencia(inpc, clasificacion)
    df_inpc = inpc._completo
    df_clas = clasificacion._completo
    _validar_entradas(df_inpc, df_clas, canastas)

    periodo_lvl = df_clas.index.get_level_values("periodo")
    periodos = sorted(set(periodo_lvl))
    if desde is not None and desde not in periodos:
        raise InvarianteViolado(f"El periodo 'desde' ({desde}) no existe en el resultado.")
    if hasta is not None and hasta not in periodos:
        raise InvarianteViolado(f"El periodo 'hasta' ({hasta}) no existe en el resultado.")
    desde_e: Periodo = desde if desde is not None else periodos[0]
    hasta_e: Periodo = hasta if hasta is not None else periodos[-1]
    if hasta_e < desde_e:  # type: ignore[operator]
        raise InvarianteViolado(f"'hasta' ({hasta_e}) no puede ser anterior a 'desde' ({desde_e}).")

    rango = [p for p in periodos if desde_e <= p <= hasta_e]
    df_lookup = df_clas[periodo_lvl.isin(rango)]
    valores = df_clas["indice_replicado"]
    genericos = sorted(set(df_clas.index.get_level_values("indice")))

    tuplas_emitir: list[tuple[Periodo, str]] = []
    base_periodos: list[Periodo] = []
    filas_parciales: list[dict[str, object]] = []
    for generico in genericos:
        validos = [p for p in rango if pd.notna(valores.get((p, generico)))]
        desde_real = resolver_extremo(desde_e, validos, incluir_parciales, primero=True)
        hasta_real = resolver_extremo(hasta_e, validos, incluir_parciales, primero=False)
        if desde_real is None or hasta_real is None:
            # No computable: se emite en los extremos exactos (valor NaN).
            tuplas_emitir.append((hasta_e, generico))
            base_periodos.append(desde_e)
            continue
        tuplas_emitir.append((hasta_real, generico))
        base_periodos.append(desde_real)
        if desde_real != desde_e or hasta_real != hasta_e:
            filas_parciales.append(
                {
                    "indice": generico,
                    "periodo_desde_real": desde_real,
                    "periodo_hasta_real": hasta_real,
                }
            )

    df_emitir = df_clas.loc[pd.MultiIndex.from_tuples(tuplas_emitir, names=["periodo", "indice"])]
    indices_parciales = pd.DataFrame(
        filas_parciales,
        columns=["indice", "periodo_desde_real", "periodo_hasta_real"],
    ).set_index("indice")

    return _construir_resultado(
        df_emitir,
        df_lookup,
        canastas,
        base_periodos,
        "desde",
        f"desde {desde_e} hasta {hasta_e}",
        inpc,
        clasificacion,
        indices_parciales,
        excluir_parciales=not incluir_parciales,
    )


def _columna_incidencia(df: pd.DataFrame) -> str:
    """Nombre de la columna de escala de-encadenada, con fallback al visible.

    `indice_incidencia` no existe en resultados construidos sin pasar por un
    `CalculadorBase` (ej. dobles de test que arman `ResultadoIndice` a mano); ahí se
    usa `indice_replicado` directo, sin escala within/cross que corregir.
    """
    return "indice_incidencia" if "indice_incidencia" in df.columns else "indice_replicado"


def _ponderador(pond_por_version: dict[int, pd.Series], version: int, categoria: str) -> float:
    """Ponderador de `categoria` en la canasta de `version`; `NaN` si falta cualquiera.

    `NaN` (nunca `KeyError`) es el contrato: una versión o categoría ausente hace la fila
    no computable — `_obtener_motivo_faltante` la explica en el reporte — no es un fallo
    de programación.
    """
    pond = pond_por_version.get(version)
    return float(pond.get(categoria, float("nan"))) if pond is not None else float("nan")


def _construir_resultado(
    df_emitir: pd.DataFrame,
    df_lookup: pd.DataFrame,
    canastas: dict[int, CanastaCanonica],
    base_periodos: list[Periodo],
    clase: str,
    descripcion: str,
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    indices_parciales: pd.DataFrame | None,
    excluir_parciales: bool = False,
) -> ResultadoIncidencia:
    """Núcleo del cálculo de incidencias (Fix 1 + selección por fila de la escala).

    `df_emitir` aporta las filas `(periodo, indice)` de salida; `df_lookup`
    aporta los valores de los periodos base. `base_periodos` da, por cada fila
    de `df_emitir` y en el mismo orden, el periodo base correspondiente.

    Con `excluir_parciales`, las filas con estado derivado `parcial` se
    descartan de `df_out` (siguen visibles en `reporte`).
    """
    # `inpc._completo` no llega como parámetro aparte: sería redundante, ya se pasa
    # `inpc` completo y los 3 llamadores lo derivan igual antes de llamar (lo necesitan
    # ahí mismo para `_validar_entradas`, previo a esta función).
    df_inpc = inpc._completo
    tipo_clas = str(df_emitir["tipo"].iloc[0])
    versiones_inpc: list[VersionCanasta] = [m.version for m in inpc.manifiesto]
    versiones_clas: list[VersionCanasta] = [m.version for m in clasificacion.manifiesto]

    # El resultado de clasificación ya viene normalizado al vocabulario canónico `vc` que usó
    # empalmar. Los ponderadores se indexan con el nombre NATIVO de cada canasta, así que se
    # renombran a `vc`. Sin esto, una categoría renombrada entre versiones (ej. "comunicaciones"
    # 2018 → "informacion y comunicacion" 2024) no se encontraría al buscar el ponderador base
    # cross-canasta y la fila caería como "sin ponderador".
    #
    # `vc` NO se infiere como max(version) — eso falla con empalmar(version_nombres custom). Se
    # infiere como la versión `v` cuyos nombres de índice (filas versión `v`) están todos en los
    # nombres nativos de canasta[v]: la canónica cumple por identidad, y una versión con
    # categorías renombradas no cumple (sus nombres ya están en otro vocabulario). Si varias
    # cumplen, no hay renombres entre ellas y el mapa queda vacío, así que da igual (max).
    completo_clas = clasificacion._completo
    nombres_por_version = {
        cast(int, v): set(sub.index.get_level_values("indice"))
        for v, sub in completo_clas.groupby("version")
    }
    candidatos_vc = [
        v
        for v, nombres in nombres_por_version.items()
        if v in canastas and nombres <= set(canastas[v].df[tipo_clas])
    ]
    vc = max(candidatos_vc) if candidatos_vc else cast(int, completo_clas["version"].max())
    pond_por_version: dict[int, pd.Series] = {}
    for v, c in canastas.items():
        ponds = c.df["ponderador"].astype(float).groupby(c.df[tipo_clas]).sum()
        mapa = _construir_mapa_renombre(tipo_clas, int(v), vc)
        renombres = {
            cast(str, x): _renombrar_valor(str(x), tipo_clas, int(v), mapa) for x in ponds.index
        }
        ponds = ponds.rename(index=renombres).groupby(level=0).sum()
        pond_por_version[v] = ponds
    indices_clas = df_emitir.index.get_level_values("indice")
    base_idx = pd.MultiIndex.from_arrays([base_periodos, indices_clas], names=["periodo", "indice"])

    # Versión POR FILA (periodo, indice), nunca por periodo: en una frontera de canasta
    # coexisten índices de versiones distintas, y groupby("periodo").first() los clasificaría
    # mal — etiqueta equivocada y, peor, el ponderador base se buscaría en la canasta
    # equivocada (una alta within-canasta caería como "sin ponderador"). ver_base hace
    # fallback a ver_t cuando el periodo base no existe en el lookup.
    ver_t_row = df_emitir["version"].to_numpy()
    ver_b_row = df_lookup["version"].reindex(base_idx).to_numpy()
    cross = pd.notna(ver_b_row) & (ver_t_row != ver_b_row)
    ver_base_arr = np.where(pd.notna(ver_b_row), ver_b_row, ver_t_row)
    ver_p_per_row = [int(v) for v in ver_t_row]
    ver_base_per_row = [int(v) for v in ver_base_arr]

    # Selección de la escala por fila. Within-canasta usa indice_incidencia (= i_tramo
    # de-encadenado, invariante al rebase); cross-canasta usa indice_replicado visible
    # (continuo) porque i_tramo es discontinuo en la junta.
    col_inc = _columna_incidencia(df_emitir)
    col_inc_lk = _columna_incidencia(df_lookup)
    col_inc_inpc = _columna_incidencia(df_inpc)

    valores_t = pd.Series(
        np.where(cross, df_emitir["indice_replicado"].to_numpy(), df_emitir[col_inc].to_numpy()),
        index=df_emitir.index,
    )
    base_rep = df_lookup["indice_replicado"].reindex(base_idx).to_numpy()
    base_inc = df_lookup[col_inc_lk].reindex(base_idx).to_numpy()
    base_clas = pd.Series(np.where(cross, base_rep, base_inc), index=df_emitir.index)

    # Fix 1: ponderadores de la canasta del periodo base.
    pond_serie = pd.Series(
        [
            _ponderador(pond_por_version, ver_base, c)
            for ver_base, c in zip(ver_base_per_row, indices_clas)
        ],
        index=df_emitir.index,
        dtype=float,
    )
    pond_t_serie = pd.Series(
        [_ponderador(pond_por_version, ver_p, c) for ver_p, c in zip(ver_p_per_row, indices_clas)],
        index=df_emitir.index,
        dtype=float,
    )

    inpc_rep_cache: dict[Periodo, float] = {}
    inpc_inc_cache: dict[Periodo, float] = {}
    inpc_estado_cache: dict[Periodo, object] = {}
    for bp in set(base_periodos):
        try:
            inpc_rep_cache[bp] = float(df_inpc.at[(bp, "INPC"), "indice_replicado"])  # type: ignore[arg-type]
            inpc_inc_cache[bp] = float(df_inpc.at[(bp, "INPC"), col_inc_inpc])  # type: ignore[arg-type]
            inpc_estado_cache[bp] = df_inpc.at[(bp, "INPC"), "estado_calculo"]
        except KeyError:
            inpc_rep_cache[bp] = float("nan")
            inpc_inc_cache[bp] = float("nan")
            inpc_estado_cache[bp] = None
    inpc_rep_arr = np.array([inpc_rep_cache[bp] for bp in base_periodos], dtype=float)
    inpc_inc_arr = np.array([inpc_inc_cache[bp] for bp in base_periodos], dtype=float)
    inpc_base_serie = pd.Series(np.where(cross, inpc_rep_arr, inpc_inc_arr), index=df_emitir.index)
    inpc_estado_base = pd.Series(
        [inpc_estado_cache[bp] for bp in base_periodos], index=df_emitir.index
    )

    # inc_i = w_base_i * (J_t - J_base) / J_INPC_base   (J por selección por fila)
    incidencia_pp = (valores_t - base_clas) * pond_serie / inpc_base_serie

    # Segunda pasada (Fase 2A): para filas cross de tipos con clasificación estable,
    # sobreescribir el valor visible (sin garantía) por la incidencia exacta encadenada
    # por segmentos. Las within quedan "within"; las cross sin clasificación estable
    # quedan "cross_visible".
    mensual_flag = es_mensual(df_emitir)
    metodo = np.where(cross, "cross_visible", "within").astype(object)
    if cross.any() and _es_clasificacion_estable(tipo_clas, canastas):
        inc_vals = incidencia_pp.to_numpy(dtype=float).copy()
        for pos in np.flatnonzero(cross):
            per_t, ind_k = df_emitir.index[pos]
            valor, estado = _calcular_incidencia_cross_encadenada(
                per_t,
                str(ind_k),
                base_periodos[pos],
                ver_p_per_row[pos],
                ver_base_per_row[pos],
                mensual_flag,
                df_inpc,
                clasificacion._completo,
                inpc._frontera,
                clasificacion._frontera,
                pond_por_version,
            )
            metodo[pos] = estado
            if valor is not None:
                inc_vals[pos] = valor
        incidencia_pp = pd.Series(inc_vals, index=df_emitir.index)

    # Guardia de los operandos de Fase 1, restringida a las filas cuyo valor final SÍ sale
    # de Fase 1. Una fila `cross_segmentado` puede traer un operando visible provisional
    # inválido que la fórmula exacta ya sustituyó — rechazarla ahí sería un falso positivo.
    # Mismo contrato que `variaciones.py`: un operando ausente deja la fila no computable
    # (sin excepción); finitud se exige a todos y `!= 0` solo al divisor.
    usa_fase1 = pd.Series(metodo != "cross_segmentado", index=df_emitir.index)
    computable_fase1 = (
        usa_fase1
        & valores_t.notna()
        & base_clas.notna()
        & pond_serie.notna()
        & inpc_base_serie.notna()
    )
    invalido = computable_fase1 & (
        ~np.isfinite(valores_t.astype(float))
        | ~np.isfinite(base_clas.astype(float))
        | ~np.isfinite(pond_serie.astype(float))
        | ~np.isfinite(inpc_base_serie.astype(float))
        | (inpc_base_serie == 0)
    )
    if invalido.any():
        raise InvarianteViolado(
            f"incidencias: operando no finito o INPC base = 0 (divisor) en "
            f"{int(invalido.sum())} fila(s) computable(s); "
            f"ejemplo {df_emitir.index[invalido][0]}."
        )

    estado_clas_base = pd.Series(
        df_lookup["estado_calculo"].reindex(base_idx).to_numpy(), index=df_emitir.index
    )
    computable = incidencia_pp.notna()
    # Guardia del resultado: sobre TODAS las filas computables y DESPUÉS de la
    # sobrescritura de Fase 2A. Cierra el overflow que pasa el gate de entrada (`1e308`
    # por un ponderador desborda al multiplicar) y que `notna()` no atrapa.
    resultado_invalido = computable & ~np.isfinite(incidencia_pp.astype(float))
    if resultado_invalido.any():
        raise InvarianteViolado(
            f"incidencias: incidencia_pp no finita (overflow) en "
            f"{int(resultado_invalido.sum())} fila(s) computable(s); "
            f"ejemplo {df_emitir.index[resultado_invalido][0]}."
        )
    derivado = pd.Series(
        [
            "parcial" if "parcial" in (et, eb, ie) else "ok"
            for et, eb, ie in zip(df_emitir["estado_calculo"], estado_clas_base, inpc_estado_base)
        ],
        index=df_emitir.index,
    )

    df_out = pd.DataFrame(
        {
            "tipo": tipo_clas,
            "clase_incidencia": clase,
            "incidencia_pp": incidencia_pp,
            "estado_calculo": derivado,
            "version_t": df_emitir["version"],
        },
        index=df_emitir.index,
    )[computable]
    if excluir_parciales:
        df_out = df_out[df_out["estado_calculo"] != "parcial"]
    df_out = df_out.sort_index()
    if df_out.empty:
        raise InvarianteViolado(
            f"Sin genéricos computables para clase '{clase}'. "
            "Se requieren datos suficientes en el periodo base."
        )

    reporte_df, diagnostico_df = _construir_reporte_diagnostico(
        df_emitir,
        clasificacion.reporte,
        valores_t,
        base_clas,
        pond_t_serie,
        pond_serie,
        base_idx,
        base_periodos,
        ver_p_per_row,
        ver_base_per_row,
        inpc_base_serie,
        derivado,
        computable,
        versiones_inpc + versiones_clas,
        tipo_clas,
        clase,
        metodo,
    )
    manifiesto = ManifestDerivado(
        versiones=versiones_inpc + versiones_clas,
        tipo=tipo_clas,
        clase=clase,
        descripcion=descripcion,
        fecha=datetime.now(),
    )
    return ResultadoIncidencia(df_out, manifiesto, reporte_df, diagnostico_df, indices_parciales)


def _obtener_motivo_faltante(
    valor_t: float, base_clas: float, inpc_base: float, pond: float
) -> str:
    if pd.isna(valor_t):
        return "sin valor de clasificación en t"
    if pd.isna(base_clas):
        return "sin valor de clasificación en periodo base"
    if pd.isna(inpc_base):
        return "sin INPC en periodo base"
    if pd.isna(pond):
        return "sin ponderador para el genérico en la canasta base"
    return "incidencia no computable"


def _construir_reporte_diagnostico(
    df_emitir: pd.DataFrame,
    reporte_fuente: pd.DataFrame,
    valores_t: pd.Series,
    base_clas: pd.Series,
    pond_t: pd.Series,
    pond_lag: pd.Series,
    base_idx: pd.MultiIndex,
    base_periodos: list[Periodo],
    ver_p_per_row: list[int],
    ver_base_per_row: list[int],
    inpc_base_serie: pd.Series,
    derivado: pd.Series,
    computable: pd.Series,
    versiones: list[VersionCanasta],
    tipo: str,
    clase: str,
    metodo: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye `reporte_df` (todas las filas) y `diagnostico_df` (no computables).

    `metodo` (alineado a `df_emitir`) es la columna `metodo_incidencia`: marcador
    interno del método por fila; se incluye en ambas salidas sin cambiar su semántica.
    """
    if "cobertura_genericos_pct" in reporte_fuente.columns:
        cobertura = reporte_fuente["cobertura_genericos_pct"]
        cob_t = cobertura.reindex(df_emitir.index)
        cob_lag = pd.Series(cobertura.reindex(base_idx).to_numpy(), index=df_emitir.index)
    else:
        cob_t = pd.Series(float("nan"), index=df_emitir.index)
        cob_lag = pd.Series(float("nan"), index=df_emitir.index)

    estados_rep: list[str] = []
    motivos: list[object] = []
    for ok, est, vt, vb, ib, pl in zip(
        computable, derivado, valores_t, base_clas, inpc_base_serie, pond_lag
    ):
        if ok:
            estados_rep.append(est)
            motivos.append(float("nan"))
        else:
            estados_rep.append("sin_datos")
            motivos.append(_obtener_motivo_faltante(vt, vb, ib, pl))

    reporte_df = pd.DataFrame(
        {
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
            "metodo_incidencia": metodo,
            "periodo_lag": pd.Series(base_periodos, index=df_emitir.index),
            "indice_t": valores_t.to_numpy(),
            "indice_lag": base_clas.to_numpy(),
            "ponderador_t": pond_t.to_numpy(),
            "ponderador_lag": pond_lag.to_numpy(),
            "version_t": ver_p_per_row,
            "version_lag": ver_base_per_row,
            "cobertura_pct_t": cob_t.to_numpy(),
            "cobertura_pct_lag": cob_lag.to_numpy(),
        },
        index=df_emitir.index,
        columns=_COLS_REPORTE,
    ).sort_index()

    no_computable = ~computable
    diagnostico_df = pd.DataFrame(
        {
            "versiones": ",".join(str(v) for v in versiones),
            "tipo": tipo,
            "clase_incidencia": clase,
            "periodo": df_emitir.index.get_level_values("periodo"),
            "indice": df_emitir.index.get_level_values("indice"),
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
            "metodo_incidencia": metodo,
            "periodo_lag": base_periodos,
            "version_t": ver_p_per_row,
            "version_lag": ver_base_per_row,
        },
        index=df_emitir.index,
        columns=_COLS_DIAGNOSTICO,
    )[no_computable].reset_index(drop=True)

    return reporte_df, diagnostico_df
