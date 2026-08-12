from __future__ import annotations

import math
import warnings

import pandas as pd

from replica_inpc.dominio.correspondencia_canastas import (
    _ORDEN_VERSIONES,
    _aplicar_renombre,
    _construir_mapa_renombre,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta

_ESTADOS_CON_VALOR = frozenset({"ok", "parcial", "rellenado"})

# Juntas de canasta: (periodo_quincenal_enlace, version_old, version_new). El enlace es el
# límite inferior del tramo nuevo; el tramo viejo lo posee en el empalme.
_JUNTAS_FRONTERA: list[tuple[PeriodoQuincenal, VersionCanasta, VersionCanasta]] = [
    (RANGOS_CANASTAS[v_new][0], v_old, v_new)
    for v_old, v_new in zip(_ORDEN_VERSIONES, _ORDEN_VERSIONES[1:])
]


def _construir_frontera(df: pd.DataFrame) -> pd.DataFrame | None:
    """Extrae anclas de junta de un df quincenal empalmado.

    Por cada junta `e` presente y que separe dos versiones presentes, guarda los valores
    del tramo viejo en `e` (que el empalme le asigna al tramo anterior). Devuelve `None`
    si no hay junta activa (resultado de un solo tramo o sin enlace).

    `indice_replicado_old` es el visible del tramo viejo en `e`, siempre por índice: para
    el INPC es `INPC_visible(e)`; para clasificación es `I_K_visible(e)` de cada categoría.
    Lo que la frontera de clasificación **no** guarda es `INPC_visible(e)` — ese vive solo
    en la del INPC, porque `rebasar(clasificacion)` no conoce `k_INPC` (ver
    docs/diseño §11.29). El motor de incidencias necesita `I_K_visible(e)` para derivar el
    ancla del lado nuevo de la junta sin suponer que vale 100.
    """
    tiene_inc = "indice_incidencia" in df.columns
    periodos = set(df.index.get_level_values("periodo"))
    versiones = {int(v) for v in df["version"].unique()}
    filas: list[dict[str, object]] = []
    for e, v_old, v_new in _JUNTAS_FRONTERA:
        if e not in periodos or v_old not in versiones or v_new not in versiones:
            continue
        sub = df[df.index.get_level_values("periodo") == e]
        indices = sub.index.get_level_values("indice")
        reps = sub["indice_replicado"].to_numpy()
        incs = sub["indice_incidencia"].to_numpy() if tiene_inc else reps
        versions = sub["version"].to_numpy()
        for ind, rep, inc, ver in zip(indices, reps, incs, versions):
            filas.append(
                {
                    "periodo": e,
                    "indice": ind,
                    "version_old": int(ver),
                    "version_new": int(v_new),
                    "indice_incidencia_old": inc,
                    "indice_replicado_old": float(rep) if pd.notna(rep) else float("nan"),
                }
            )
    if not filas:
        return None
    return pd.DataFrame(filas).set_index(["periodo", "indice"])


_COLS_REPORTE_STRUCT = ("genericos_esperados", "ponderador_esperado")
_COLS_REPORTE_MIN = ("genericos_con_indice", "cobertura_genericos_pct", "ponderador_cubierto")
_COLS_REPORTE_MAX = ("genericos_sin_indice",)
# reindex/fillna sobre columnas con NaN en un lado (mes con 1 sola quincena) las
# sube a float64 aunque el resultado final nunca tenga NaN real — se restauran a
# int explícito, únicas columnas de docs/diseño.md §5.7/§5.10 tipadas `int`.
_COLS_REPORTE_INT = (
    "version",
    "genericos_esperados",
    "genericos_con_indice",
    "genericos_sin_indice",
)


def _validar_topologia(ordenados: list[ResultadoIndice]) -> list[object]:
    """Valida topología PATH y devuelve lista de periodos frontera entre pares consecutivos."""
    conjuntos = [set(r._df_resultado.index.get_level_values("periodo")) for r in ordenados]
    fronteras: list[object] = []
    for i in range(len(ordenados) - 1):
        compartidos = conjuntos[i] & conjuntos[i + 1]
        if len(compartidos) == 0:
            raise InvarianteViolado(
                f"empalmar: par consecutivo [{i}, {i + 1}] no comparte ningún periodo — "
                "no hay frontera válida para empalmar."
            )
        if len(compartidos) > 1:
            raise InvarianteViolado(
                f"empalmar: par consecutivo [{i}, {i + 1}] comparte {len(compartidos)} periodos "
                f"({sorted(map(str, compartidos))}); se requiere exactamente 1 (topología PATH)."
            )
        fronteras.append(next(iter(compartidos)))
        for j in range(i + 2, len(ordenados)):
            no_consecutivos = conjuntos[i] & conjuntos[j]
            if no_consecutivos:
                raise InvarianteViolado(
                    f"empalmar: par no-consecutivo [{i}, {j}] comparte periodos "
                    f"({sorted(map(str, no_consecutivos))}); topología debe ser PATH lineal."
                )
    return fronteras


def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: VersionCanasta | None = None,
) -> ResultadoIndice:
    """Concatena tramos del mismo `tipo` en un único `ResultadoIndice`.

    Normaliza nomenclatura de categorías entre versiones. En la frontera entre
    tramos consecutivos, el tramo anterior posee (frontera, indice) si ese
    indice existe en él; si no, el tramo posterior lo aporta.
    """
    if len(resultados) < 2:
        raise InvarianteViolado("empalmar requiere al menos 2 ResultadoIndice.")

    tipos = {m.tipo for r in resultados for m in r.manifiesto}
    if len(tipos) != 1:
        raise InvarianteViolado(
            f"empalmar requiere mismo 'tipo' entre todos los inputs; recibió {sorted(tipos)}"
        )

    tipos_periodo = {
        type(p) for r in resultados for p in r._df_resultado.index.get_level_values("periodo")
    }
    if len(tipos_periodo) > 1:
        raise InvarianteViolado(
            "empalmar requiere que todos los inputs tengan la misma periodicidad "
            "(quincenales o mensuales); no se pueden mezclar."
        )
    primer_periodo = resultados[0]._df_resultado.index.get_level_values("periodo")[0]
    if not isinstance(primer_periodo, PeriodoQuincenal):
        warnings.warn(
            "empalmar recibió ResultadoIndice mensuales. El mes frontera puede perder "
            "una quincena. Usa a_mensual(empalmar([r1, r2])) en su lugar.",
            UserWarning,
            stacklevel=2,
        )

    ordenados = sorted(
        resultados,
        key=lambda r: r._df_resultado.index.get_level_values("periodo").min(),
    )

    fronteras = _validar_topologia(ordenados)

    for i, frontera in enumerate(fronteras):
        ref_i = ordenados[i].periodo_referencia
        if ref_i is not None and ref_i != frontera:
            msg = (
                f"empalmar: tramo {i} tiene periodo_referencia={ref_i} "
                f"pero la frontera con el siguiente tramo es {frontera}; "
                "la juntura puede ser discontinua — usa rebasar() antes o forzar=True."
            )
            if not forzar:
                raise InvarianteViolado(msg)
            warnings.warn(msg, UserWarning, stacklevel=2)

    if version_nombres is None:
        vc = max(int(v) for r in ordenados for v in r._df_resultado["version"].unique())
    else:
        vc = int(version_nombres)

    vers_labels = {max(m.version for m in r.manifiesto) for r in ordenados}
    vers_en_orden = sorted(v for v in vers_labels if v in _ORDEN_VERSIONES)
    if version_nombres is not None and vers_en_orden:
        if vc < min(vers_en_orden) or vc > max(vers_en_orden):
            raise InvarianteViolado(
                f"empalmar: version_nombres={vc} fuera del rango de versiones de los inputs "
                f"[{min(vers_en_orden)}, {max(vers_en_orden)}]."
            )

    tipo_unico = next(iter(tipos))

    dfs_indice: list[pd.DataFrame] = []
    dfs_reporte: list[pd.DataFrame] = []
    dfs_diag: list[pd.DataFrame] = []

    for r in ordenados:
        version_origen = max(m.version for m in r.manifiesto)
        mapa = _construir_mapa_renombre(tipo_unico, version_origen, vc)

        df_completo = _aplicar_renombre(r._df_resultado, tipo_unico, version_origen, mapa)
        reporte = _aplicar_renombre(r.reporte, tipo_unico, version_origen, mapa)
        # El renombre puede colapsar dos variantes del mismo índice cuando el
        # catálogo 2010→2013 está incompleto y acc acumula ambas formas. Se
        # preserva la primera aparición (orden cronológico = tramo anterior
        # prevalece), coherente con el contrato de empalmar.
        if df_completo.index.duplicated().any():
            df_completo = df_completo[~df_completo.index.duplicated(keep="first")]
        if reporte.index.duplicated().any():
            reporte = reporte[~reporte.index.duplicated(keep="first")]

        dfs_indice.append(df_completo)
        dfs_reporte.append(reporte)
        dfs_diag.append(r.diagnostico)

    # Propiedad de la frontera: el tramo anterior posee (periodo, indice) si tiene esa
    # fila exacta (keep="first", tramos concatenados en orden cronológico); el posterior
    # la aporta solo si el anterior no la tiene ahí. `_validar_topologia` garantiza que
    # duplicados de índice solo ocurren en el periodo de frontera entre tramos consecutivos
    # — nunca en un periodo normal, porque la topología PATH ya lo prohíbe.
    df_combinado = pd.concat(dfs_indice)
    df_combinado = df_combinado[~df_combinado.index.duplicated(keep="first")]
    df_combinado.sort_index(level="periodo", sort_remaining=False, inplace=True)

    reporte_combinado = pd.concat(dfs_reporte)
    reporte_combinado = reporte_combinado[~reporte_combinado.index.duplicated(keep="first")]
    reporte_combinado.sort_index(level="periodo", sort_remaining=False, inplace=True)

    diag_combinado = pd.concat(dfs_diag, ignore_index=True)
    manifiesto_combinado = [m for r in ordenados for m in r.manifiesto]

    refs_explicitas = [r.periodo_referencia for r in ordenados if r.periodo_referencia is not None]
    periodo_referencia_out = refs_explicitas[-1] if refs_explicitas else None

    # Propagar/renombrar `_frontera` si algún tramo la trae (caso secundario: el flujo
    # canónico es a_mensual(empalmar(...)), donde aún es None). Se renombra con el mismo
    # mapa RENOMBRES_INDICES que el resto del resultado para que empate con `df_emitir`.
    fronteras_df: list[pd.DataFrame] = []
    for r in ordenados:
        fr = r._frontera
        if fr is None:
            continue
        version_origen = max(m.version for m in r.manifiesto)
        mapa = _construir_mapa_renombre(tipo_unico, version_origen, vc)
        fronteras_df.append(_aplicar_renombre(fr, tipo_unico, version_origen, mapa))
    frontera_out: pd.DataFrame | None = None
    if fronteras_df:
        frontera_out = pd.concat(fronteras_df)
        frontera_out = frontera_out[~frontera_out.index.duplicated(keep="first")]

    return ResultadoIndice(
        df_combinado,
        manifiesto_combinado,
        reporte_combinado,
        diag_combinado,
        periodo_referencia=periodo_referencia_out,
        frontera=frontera_out,
    )


def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual,
    valor_base: float = 100.0,
) -> ResultadoIndice:
    """Reexpresa cada índice a una nueva referencia usando el valor replicado propio.

    Endógeno: el denominador es el valor replicado del propio resultado en
    `periodo_referencia`. Un índice sin dato válido ahí queda sin rebasar
    (`UserWarning`); si NINGÚN índice tiene dato en `periodo_referencia` (periodo
    inexistente, o periodicidad de `periodo_referencia` distinta a la del
    resultado), la operación entera falla en vez de devolver un resultado sin
    reescalar con `periodo_referencia` seteado.

    Raises:
        InvarianteViolado: si `periodo_referencia` no tiene dato para ningún
            índice; si la base de algún índice es NaN o exactamente 0 (`inf`
            o negativo NO se validan — el dato ya está garantizado finito y
            positivo aguas arriba, en `dominio/calculo/`); o si `valor_base`
            no es finito y positivo (parámetro de usuario, sin garantía
            previa — a diferencia de la base, sí es límite de sistema).

    Ver: docs/diseño.md §5.10
    """
    if not (math.isfinite(valor_base) and valor_base > 0):
        raise InvarianteViolado(f"rebasar: valor_base={valor_base} debe ser finito y positivo.")

    df = resultado._df_resultado.copy()
    indices_unicos = df.index.get_level_values("indice").unique()
    indices_sin_referencia: list[str] = []

    # Aislar, por índice, la fila en el periodo de referencia (el futuro denominador).
    mask_periodo_referencia = df.index.get_level_values("periodo") == periodo_referencia
    df_en_referencia = df[mask_periodo_referencia].copy()
    df_en_referencia.index = df_en_referencia.index.droplevel("periodo")

    factores_por_indice: dict[object, float] = {}
    for indice in indices_unicos:
        if indice not in df_en_referencia.index:
            indices_sin_referencia.append(str(indice))
            continue
        fila_referencia: pd.Series = df_en_referencia.loc[indice]
        estado_en_referencia = fila_referencia["estado_calculo"]
        if estado_en_referencia not in _ESTADOS_CON_VALOR:
            raise InvarianteViolado(
                f"El valor base de '{indice}' en {periodo_referencia} no está disponible "
                f"(estado_calculo='{estado_en_referencia}')."
            )
        valor_en_referencia_raw = fila_referencia["indice_replicado"]
        if pd.isna(valor_en_referencia_raw):
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es NaN; "
                f"estado_calculo='{estado_en_referencia}' es inconsistente."
            )
        valor_en_referencia = float(valor_en_referencia_raw)
        if valor_en_referencia == 0:
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es 0; no rebasable."
            )
        factores_por_indice[indice] = valor_base / valor_en_referencia

    if not factores_por_indice:
        raise InvarianteViolado(
            f"rebasar: ningún índice tiene dato en {periodo_referencia}; no se puede "
            "rebasar (periodo inexistente en el resultado, o periodicidad de "
            "periodo_referencia distinta a la del resultado)."
        )

    # Solo se reescalan filas cuyo estado ya trae un valor confiable (`sin_datos`/
    # `fallida` quedan como NaN, intactas); índices sin referencia (huérfanos) no
    # tienen entrada en `factores_por_indice`, así que `factor_por_fila` les da NaN
    # y `mask_aplicar_factor` los excluye — quedan en su escala original.
    mask_estado_rebasable = df["estado_calculo"].isin(_ESTADOS_CON_VALOR)
    indice_por_fila = df.index.get_level_values("indice")
    factor_por_fila = pd.Series(
        indice_por_fila.map(factores_por_indice),
        index=df.index,
        dtype=float,
    )
    mask_aplicar_factor = mask_estado_rebasable & factor_por_fila.notna()
    df.loc[mask_aplicar_factor, "indice_replicado"] = (
        df.loc[mask_aplicar_factor, "indice_replicado"].astype(float).to_numpy()
        * factor_por_fila.loc[mask_aplicar_factor].to_numpy()
    )

    if indices_sin_referencia:
        warnings.warn(
            f"rebasar: {len(indices_sin_referencia)} índice(s) sin dato en {periodo_referencia} "
            f"quedan sin rebasar (base original): {indices_sin_referencia}",
            UserWarning,
            stacklevel=2,
        )

    # Reescalar la frontera: el campo visible (`indice_replicado_old`) se multiplica por el
    # mismo factor por índice, solo para índices con factor calculado — los huérfanos quedan
    # intactos (mismo criterio que `indice_replicado`, nunca se pisan con NaN).
    # `indice_incidencia_old` queda intacto (es de-encadenado, invariante al rebase). El
    # reescalado por índice aplica igual al INPC y a cada categoría: en la frontera de
    # clasificación cada `I_K_visible(e)` recibe su propio `k_K`.
    frontera_out = resultado._frontera
    if frontera_out is not None:
        frontera_out = frontera_out.copy()
        indices_frontera = frontera_out.index.get_level_values("indice")
        mask_frontera_con_factor = indices_frontera.isin(factores_por_indice)
        factores_frontera = (
            indices_frontera[mask_frontera_con_factor].map(factores_por_indice).astype(float)
        )
        frontera_out.loc[mask_frontera_con_factor, "indice_replicado_old"] = (
            frontera_out.loc[mask_frontera_con_factor, "indice_replicado_old"]
            .astype(float)
            .to_numpy()
            * factores_frontera.to_numpy()
        )

    return ResultadoIndice(
        df,
        resultado.manifiesto,
        resultado.reporte,
        resultado.diagnostico,
        periodo_referencia=periodo_referencia,
        frontera=frontera_out,
    )


def _reporte_a_mensual(df_result: pd.DataFrame, reporte_q: pd.DataFrame) -> pd.DataFrame:
    """Construye reporte con índice PeriodoMensual a partir del reporte quincenal.

    version/estado_calculo/motivo_error vienen de df_result (ya agregados).
    Columnas de cobertura: peor caso entre Q1 y Q2 del mismo mes.
    """
    rq = reporte_q.reset_index()
    periodos = rq["periodo"]
    rq["_año"] = [p.año for p in periodos]
    rq["_mes"] = [p.mes for p in periodos]
    rq["_quincena"] = [p.quincena for p in periodos]
    rq = rq.drop(columns="periodo").set_index(["_año", "_mes", "indice"])

    q1 = rq[rq["_quincena"] == 1].drop(columns="_quincena")
    q2 = rq[rq["_quincena"] == 2].drop(columns="_quincena")
    all_groups = q1.index.union(q2.index)
    q1_r = q1.reindex(all_groups)
    q2_r = q2.reindex(all_groups)

    años = all_groups.get_level_values("_año")
    meses = all_groups.get_level_values("_mes")
    idx_vals = all_groups.get_level_values("indice")
    periodos_m = [PeriodoMensual(int(a), int(m)) for a, m in zip(años, meses)]
    m_idx = pd.MultiIndex.from_arrays([periodos_m, idx_vals], names=["periodo", "indice"])

    cols_result = [
        c for c in ("version", "estado_calculo", "motivo_error") if c in reporte_q.columns
    ]
    df_rep = df_result[cols_result].reindex(m_idx)

    for col in _COLS_REPORTE_STRUCT:
        if col in reporte_q.columns:
            df_rep[col] = q2_r[col].fillna(q1_r[col]).values

    for col in _COLS_REPORTE_MIN:
        if col in reporte_q.columns:
            df_rep[col] = pd.concat([q1_r[col], q2_r[col]], axis=1).min(axis=1).values

    for col in _COLS_REPORTE_MAX:
        if col in reporte_q.columns:
            df_rep[col] = pd.concat([q1_r[col], q2_r[col]], axis=1).max(axis=1).values

    for col in _COLS_REPORTE_INT:
        if col in df_rep.columns:
            df_rep[col] = df_rep[col].astype(int)

    return df_rep[list(reporte_q.columns)]


def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
    """Convierte un ResultadoIndice quincenal a periodos mensuales.

    Promedio simple 1Q+2Q por `(año, mes, indice)`; si solo una quincena está
    disponible, usa su valor solo y marca `parcial`. También agrega `.reporte`
    (peor caso de cobertura entre 1Q/2Q), filtra `.manifiesto` a las versiones
    con al menos una fila tras la agregación (conserva la lista original si
    todas quedarían huérfanas), propaga `.periodo_referencia` **sin convertir**
    (promediar no mueve la base, y no se garantiza que el mes que contiene a la
    quincena base valga 100: es el promedio de sus dos quincenas; para anclar un
    mes en 100, rebasar el resultado ya mensual), y crea `._frontera` para
    preservar las anclas de junta de canasta que el promedio destruiría. `.diagnostico` se propaga sin tocar (queda indexado por
    quincena, a diferencia de `.reporte`/`.resultado`).

    Precedencia de `motivo_error` entre dos quincenas con el mismo estado
    irregular: para `sin_datos`, prioriza 2Q (mismo criterio que
    version/tipo); para `fallida`, prioriza la quincena que realmente falló
    (1Q si ambas fallaron) — asimetría intencional, no un descuido.

    Args:
        resultado: `ResultadoIndice` con periodos `PeriodoQuincenal`.

    Raises:
        InvarianteViolado: si `resultado` no es quincenal.

    Ver: docs/diseño.md §5.10
    """
    df = resultado._df_resultado
    periodos = df.index.get_level_values("periodo")

    if not all(isinstance(p, PeriodoQuincenal) for p in periodos):
        raise InvarianteViolado("a_mensual requiere un ResultadoIndice quincenal")

    df_flat = df.copy()
    df_flat["_año"] = [p.año for p in periodos]
    df_flat["_mes"] = [p.mes for p in periodos]
    df_flat["_quincena"] = [p.quincena for p in periodos]
    df_flat["_indice"] = df.index.get_level_values("indice")
    df_flat = df_flat.reset_index(drop=True).set_index(["_año", "_mes", "_indice"])

    q1 = df_flat[df_flat["_quincena"] == 1]
    q2 = df_flat[df_flat["_quincena"] == 2]

    all_groups = q1.index.union(q2.index)
    q1_r = q1.reindex(all_groups)
    q2_r = q2.reindex(all_groups)

    # reindex sube "version" a float64 cuando un mes tiene una sola quincena
    # (NaN del lado ausente) — se restaura int explícito, el resultado nunca
    # tiene NaN real porque all_groups garantiza al menos un lado presente.
    version = q2_r["version"].fillna(q1_r["version"]).astype(int)
    tipo = q2_r["tipo"].fillna(q1_r["tipo"])

    v1 = q1_r["indice_replicado"]
    v2 = q2_r["indice_replicado"]
    v1_ok = v1.notna()
    v2_ok = v2.notna()
    both_ok = v1_ok & v2_ok
    one_ok = v1_ok ^ v2_ok

    fallida_q1 = (q1_r["estado_calculo"] == "fallida").fillna(False)
    fallida_q2 = (q2_r["estado_calculo"] == "fallida").fillna(False)
    any_fallida = fallida_q1 | fallida_q2
    null_mask = ~any_fallida & ~both_ok & ~one_ok

    rellenado_q1 = (q1_r["estado_calculo"] == "rellenado").fillna(False)
    rellenado_q2 = (q2_r["estado_calculo"] == "rellenado").fillna(False)
    any_rellenado = rellenado_q1 | rellenado_q2

    estado_calculo = pd.Series("sin_datos", index=all_groups, dtype=object)
    estado_calculo[any_fallida] = "fallida"
    estado_calculo[~any_fallida & both_ok] = "ok"
    estado_calculo[~any_fallida & both_ok & any_rellenado] = "rellenado"
    estado_calculo[~any_fallida & one_ok] = "parcial"

    val_avg = (v1 + v2) / 2
    val_one = v1.fillna(v2)
    indice_replicado = pd.Series(float("nan"), index=all_groups)
    indice_replicado[~any_fallida & both_ok] = val_avg[~any_fallida & both_ok]
    indice_replicado[~any_fallida & one_ok] = val_one[~any_fallida & one_ok]

    # indice_incidencia: mismo promedio simple que indice_replicado, mismas mascaras.
    # Fallback resuelto una sola vez (resultados sin la columna usan indice_replicado).
    col_inc = "indice_incidencia" if "indice_incidencia" in q1_r.columns else "indice_replicado"
    j1 = q1_r[col_inc]
    j2 = q2_r[col_inc]
    val_avg_inc = (j1 + j2) / 2
    val_one_inc = j1.fillna(j2)
    indice_incidencia = pd.Series(float("nan"), index=all_groups)
    indice_incidencia[~any_fallida & both_ok] = val_avg_inc[~any_fallida & both_ok]
    indice_incidencia[~any_fallida & one_ok] = val_one_inc[~any_fallida & one_ok]

    motivo_q1 = q1_r["motivo_error"]
    motivo_q2 = q2_r["motivo_error"]
    motivo_fallida_s = motivo_q1.where(fallida_q1, motivo_q2)
    motivo_faltante_s = motivo_q2.where(motivo_q2.notna(), motivo_q1)
    motivo_error = pd.Series(None, index=all_groups, dtype=object)
    motivo_error[any_fallida] = motivo_fallida_s[any_fallida]
    motivo_error[null_mask] = motivo_faltante_s[null_mask]

    años = all_groups.get_level_values("_año")
    meses = all_groups.get_level_values("_mes")
    indices = all_groups.get_level_values("_indice")
    periodos_mensuales = [PeriodoMensual(int(a), int(m)) for a, m in zip(años, meses)]

    df_result = pd.DataFrame(
        {
            "version": version.values,
            "tipo": tipo.values,
            "indice_replicado": indice_replicado.values,
            "indice_incidencia": indice_incidencia.values,
            "estado_calculo": estado_calculo.values,
            "motivo_error": motivo_error.values,
        },
        index=pd.MultiIndex.from_arrays([periodos_mensuales, indices], names=["periodo", "indice"]),
    )

    df_result.sort_index(level="periodo", sort_remaining=False, inplace=True)

    # ResultadoIndice exige fila por cada manifiesto. Tras a_mensual, una version
    # puede perder todas sus filas (ej: q1=2018, q2=2024 → mensual hereda 2024 por
    # preferencia 2Q). Se descartan manifiestos huérfanos; si todos quedarían
    # huérfanos, se preserva la lista original como fallback de provenance.
    pares_presentes = set(zip(df_result["version"], df_result["tipo"]))
    manifiesto_filtrado = [
        m for m in resultado.manifiesto if (m.version, m.tipo) in pares_presentes
    ]
    if not manifiesto_filtrado:
        manifiesto_filtrado = resultado.manifiesto

    # `periodo_referencia` se propaga SIN convertir: promediar 1Q y 2Q no mueve la
    # base. El mes que contiene a la quincena base es el promedio de esa quincena
    # con la otra, así que no hay garantía de que valga 100 — coincide solo si la
    # otra quincena también vale 100, o si el mes aporta una sola quincena al
    # tramo. Convertirlo a `PeriodoMensual` afirmaba justo lo que el campo
    # promete y no podía sostener. Para obtener un mes anclado en 100, `rebasar`
    # acepta un `ResultadoIndice` ya mensual con un `PeriodoMensual`.
    return ResultadoIndice(
        df_result,
        manifiesto_filtrado,
        _reporte_a_mensual(df_result, resultado.reporte),
        resultado.diagnostico,
        periodo_referencia=resultado.periodo_referencia,
        frontera=_construir_frontera(df),
    )
