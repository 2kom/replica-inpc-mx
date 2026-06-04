from __future__ import annotations

import warnings

import pandas as pd

from replica_inpc.dominio.correspondencia_canastas import RENOMBRES_INDICES
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_VALIDOS, VersionCanasta

_ESTADOS_CON_VALOR = frozenset({"ok", "parcial", "rellenado"})
_ORDEN_VERSIONES: tuple[VersionCanasta, ...] = (2010, 2013, 2018, 2024)

# Juntas de canasta: (periodo_quincenal_enlace, version_old, version_new). El enlace es el
# límite inferior del tramo nuevo; el tramo viejo lo posee en el empalme.
_JUNTAS_FRONTERA: list[tuple[PeriodoQuincenal, VersionCanasta, VersionCanasta]] = [
    (RANGOS_VALIDOS[v_new][0], v_old, v_new)
    for v_old, v_new in zip(_ORDEN_VERSIONES, _ORDEN_VERSIONES[1:])
]


def _construir_frontera(df: pd.DataFrame) -> pd.DataFrame | None:
    """Extrae anclas de junta de un df quincenal empalmado (Fase 2A).

    Por cada junta `e` presente y que separe dos versiones presentes, guarda los valores
    del tramo viejo en `e` (que el empalme le asigna al tramo anterior). Devuelve `None`
    si no hay junta activa (resultado de un solo tramo o sin enlace). Para el INPC guarda
    `indice_replicado_old` (= INPC_visible(e)); para clasificación lo deja NaN — no se
    guarda INPC_visible en la frontera de clasificación (ver docs/diseño §11.31).
    """
    es_inpc = str(df["tipo"].iloc[0]) == "inpc"
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
                    "indice_replicado_old": (
                        float(rep) if es_inpc and pd.notna(rep) else float("nan")
                    ),
                }
            )
    if not filas:
        return None
    return pd.DataFrame(filas).set_index(["periodo", "indice"])


_COLS_REPORTE_STRUCT = ("genericos_esperados", "ponderador_esperado")
_COLS_REPORTE_MIN = ("genericos_con_indice", "cobertura_genericos_pct", "ponderador_cubierto")
_COLS_REPORTE_MAX = ("genericos_sin_indice",)


def _componer_mapas(m1: dict[str, str], m2: dict[str, str]) -> dict[str, str]:
    resultado: dict[str, str] = {}
    for nombre in set(m1) | set(m2):
        v1 = m1.get(nombre, nombre)
        v2 = m2.get(v1, v1)
        if v2 != nombre:
            resultado[nombre] = v2
    return resultado


def _construir_mapa_renombre(
    tipo: str, version_origen: int, version_canonica: int
) -> dict[str, str]:
    if tipo not in RENOMBRES_INDICES or version_origen == version_canonica:
        return {}
    orden: list[int] = list(_ORDEN_VERSIONES)
    try:
        idx_o = orden.index(version_origen)
        idx_c = orden.index(version_canonica)
    except ValueError:
        return {}
    mapa: dict[str, str] = {}
    if idx_o < idx_c:
        for paso in range(idx_o, idx_c):
            mapa_paso = dict(RENOMBRES_INDICES[tipo].get(orden[paso], {}))
            mapa = _componer_mapas(mapa, mapa_paso)
    else:
        pasos_inv = []
        for paso in range(idx_c, idx_o):
            mapa_fwd = dict(RENOMBRES_INDICES[tipo].get(orden[paso], {}))
            pasos_inv.append({v: k for k, v in mapa_fwd.items()})
        for mapa_inv in reversed(pasos_inv):
            mapa = _componer_mapas(mapa, mapa_inv)
    return mapa


def _aplicar_renombre(df: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    if not mapa or df.empty:
        return df
    new_indice = df.index.get_level_values("indice").map(lambda x: mapa.get(x, x))
    new_periodo = df.index.get_level_values("periodo")
    df_nuevo = df.copy()
    df_nuevo.index = pd.MultiIndex.from_arrays(
        [new_periodo, new_indice], names=["periodo", "indice"]
    )
    return df_nuevo


def _validar_topologia(ordenados: list[ResultadoIndice]) -> list[object]:
    """Valida topología PATH y devuelve lista de periodos frontera entre pares consecutivos."""
    conjuntos = [set(r._df_completo.index.get_level_values("periodo")) for r in ordenados]
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

    tipos_periodo = {type(r._df_completo.index.get_level_values("periodo")[0]) for r in resultados}
    if len(tipos_periodo) > 1:
        raise InvarianteViolado(
            "empalmar requiere que todos los inputs tengan la misma periodicidad "
            "(quincenales o mensuales); no se pueden mezclar."
        )
    primer_periodo = resultados[0]._df_completo.index.get_level_values("periodo")[0]
    if not isinstance(primer_periodo, PeriodoQuincenal):
        warnings.warn(
            "empalmar recibió ResultadoIndice mensuales. El mes frontera puede perder "
            "una quincena. Usa a_mensual(empalmar([r1, r2])) en su lugar.",
            UserWarning,
            stacklevel=2,
        )

    ordenados = sorted(
        resultados,
        key=lambda r: r._df_completo.index.get_level_values("periodo").min(),
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
        vc = max(int(v) for r in ordenados for v in r._df_completo["version"].unique())
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

    indices_acumulados: set[object] = set()
    periodos_acumulados: set[object] = set()
    dfs_indice: list[pd.DataFrame] = []
    dfs_reporte: list[pd.DataFrame] = []
    dfs_diag: list[pd.DataFrame] = []

    for i, r in enumerate(ordenados):
        version_origen = max(m.version for m in r.manifiesto)
        mapa = _construir_mapa_renombre(tipo_unico, version_origen, vc)

        df_completo = _aplicar_renombre(r._df_completo, mapa)
        reporte = _aplicar_renombre(r.reporte, mapa)
        # El renombre puede colapsar dos variantes del mismo índice cuando el
        # catálogo 2010→2013 está incompleto y acc acumula ambas formas. Se
        # preserva la primera aparición (orden cronológico = tramo anterior
        # prevalece), coherente con el contrato de empalmar.
        if df_completo.index.duplicated().any():
            df_completo = df_completo[~df_completo.index.duplicated(keep="first")]
        if reporte.index.duplicated().any():
            reporte = reporte[~reporte.index.duplicated(keep="first")]
        periodos_propios = set(df_completo.index.get_level_values("periodo"))
        frontera = fronteras[i - 1] if i > 0 else None

        if frontera is not None:
            # Periodos normales: excluir los ya acumulados (excepto la frontera)
            periodos_normales = periodos_propios - periodos_acumulados - {frontera}
            # Frontera: solo índices que el acumulado no tiene (nombres canónicos)
            mask_frontera = df_completo.index.get_level_values("periodo") == frontera
            df_frontera_todos = df_completo[mask_frontera]
            indices_frontera_nuevos = ~df_frontera_todos.index.get_level_values("indice").isin(
                indices_acumulados
            )
            df_frontera_nuevos = df_frontera_todos[indices_frontera_nuevos]

            rep_frontera_todos = reporte[reporte.index.get_level_values("periodo") == frontera]
            rep_frontera_nuevos = rep_frontera_todos[
                ~rep_frontera_todos.index.get_level_values("indice").isin(indices_acumulados)
            ]

            mask_normales = df_completo.index.get_level_values("periodo").isin(periodos_normales)
            df_filtrado = pd.concat([df_completo[mask_normales], df_frontera_nuevos])
            rep_filtrado = pd.concat(
                [
                    reporte[reporte.index.get_level_values("periodo").isin(periodos_normales)],
                    rep_frontera_nuevos,
                ]
            )
        else:
            df_filtrado = df_completo
            rep_filtrado = reporte

        dfs_indice.append(df_filtrado)
        dfs_reporte.append(rep_filtrado)
        dfs_diag.append(r.diagnostico)

        periodos_acumulados |= periodos_propios
        indices_acumulados |= set(df_completo.index.get_level_values("indice"))

    df_combinado = pd.concat(dfs_indice)
    df_combinado.sort_index(level="periodo", sort_remaining=False, inplace=True)

    reporte_combinado = pd.concat(dfs_reporte)
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
        fronteras_df.append(_aplicar_renombre(fr, mapa))
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
    `periodo_referencia`.
    """
    df = resultado._df_completo.copy()
    indices_unicos = df.index.get_level_values("indice").unique()
    huerfanos: list[str] = []

    # Extraer fila base de cada índice en el periodo de referencia
    mask_ref = df.index.get_level_values("periodo") == periodo_referencia
    df_ref = df[mask_ref].copy()
    df_ref.index = df_ref.index.droplevel("periodo")

    factores: dict[object, float] = {}
    for indice in indices_unicos:
        if indice not in df_ref.index:
            huerfanos.append(str(indice))
            continue
        fila_base: pd.Series = df_ref.loc[indice]  # type: ignore[assignment]
        estado_base = fila_base["estado_calculo"]
        if estado_base not in _ESTADOS_CON_VALOR:
            raise InvarianteViolado(
                f"El valor base de '{indice}' en {periodo_referencia} no está disponible "
                f"(estado_calculo='{estado_base}')."
            )
        base_raw = fila_base["indice_replicado"]
        if pd.isna(base_raw):
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es NaN; "
                f"estado_calculo='{estado_base}' es inconsistente."
            )
        base = float(base_raw)  # type: ignore[arg-type]
        if base == 0:
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es 0; no rebasable."
            )
        factores[indice] = valor_base / base

    if factores:
        mask_valor = df["estado_calculo"].isin(_ESTADOS_CON_VALOR)
        indice_per_row = df.index.get_level_values("indice")
        factor_series = pd.Series(
            indice_per_row.map(factores),  # type: ignore[arg-type]
            index=df.index,
            dtype=float,
        )
        aplicar = mask_valor & factor_series.notna()
        df.loc[aplicar, "indice_replicado"] = (  # type: ignore[index]
            df.loc[aplicar, "indice_replicado"].astype(float).to_numpy()  # type: ignore[union-attr]
            * factor_series.loc[aplicar].to_numpy()
        )

    if huerfanos:
        warnings.warn(
            f"rebasar: {len(huerfanos)} índice(s) sin dato en {periodo_referencia} "
            f"quedan sin rebasar (base original): {huerfanos}",
            UserWarning,
            stacklevel=2,
        )

    # Reescalar la frontera: el campo visible (`indice_replicado_old` = INPC_visible(e))
    # se multiplica por el mismo factor `k` por índice; `indice_incidencia_old` queda
    # intacto (es de-encadenado, invariante al rebase). En la frontera de clasificación
    # `indice_replicado_old` es NaN, así que no se toca nada visible ahí.
    frontera_out = resultado._frontera
    if frontera_out is not None and factores:
        frontera_out = frontera_out.copy()
        ind_fr = frontera_out.index.get_level_values("indice")
        f_fr = pd.Series([factores.get(i, float("nan")) for i in ind_fr], index=frontera_out.index)
        frontera_out["indice_replicado_old"] = (
            frontera_out["indice_replicado_old"].astype(float) * f_fr
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

    return df_rep[list(reporte_q.columns)]


def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
    """Convierte un ResultadoIndice quincenal a periodos mensuales.

    Promedio simple 1Q+2Q. Si solo una quincena disponible → `parcial`.
    """
    df = resultado._df_completo
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

    version = q2_r["version"].fillna(q1_r["version"])
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

    ref = resultado.periodo_referencia
    if isinstance(ref, PeriodoQuincenal):
        ref = PeriodoMensual(ref.año, ref.mes)

    return ResultadoIndice(
        df_result,
        manifiesto_filtrado,
        _reporte_a_mensual(df_result, resultado.reporte),
        resultado.diagnostico,
        periodo_referencia=ref,
        frontera=_construir_frontera(df),
    )
