"""Cálculo de incidencias a partir de `ResultadoIndice`.

Tres funciones producen `ResultadoIncidencia` combinando el INPC con un
resultado de clasificación (`COG`, `CCIF division`, etc.):

- `incidencia_periodica` — incidencia periodo a periodo por genérico.
- `incidencia_acumulada_anual` — enero..periodo vs diciembre del año anterior.
- `incidencia_desde` — incidencia total de un rango; una fila por genérico.

Conserva los dos arreglos del cálculo v1:

- Fix 1: los ponderadores son los de la canasta del periodo base.
- Fix 2: de-encadenamiento (÷ f_h) para versiones que usan
  `LaspeyresEncadenado` cuando base y `t` son de la misma canasta.
"""

from __future__ import annotations

from datetime import datetime

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
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import COLUMNAS_CLASIFICACION, ManifestDerivado

Periodo = PeriodoQuincenal | PeriodoMensual

_COLS_REPORTE = [
    "estado_calculo",
    "motivo_error",
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
    "id_corrida",
    "tipo",
    "clase_incidencia",
    "periodo",
    "indice",
    "estado_calculo",
    "motivo_error",
    "periodo_lag",
    "version_t",
    "version_lag",
]


def _verificar_periodo_referencia(
    inpc: ResultadoIndice, clasificacion: ResultadoIndice
) -> None:
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
    if tipo_inpc != "inpc":
        raise ErrorConfiguracion(
            f"El primer argumento debe ser un resultado de tipo 'inpc', "
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


def _lag_y_mensual(df_clas: pd.DataFrame, frecuencia: Frecuencia) -> tuple[int, bool]:
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


def incidencia_periodica(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
    frecuencia: Frecuencia,
) -> ResultadoIncidencia:
    """Incidencia de cada periodo contra N periodos anteriores."""
    _verificar_periodo_referencia(inpc, clasificacion)
    df_inpc = inpc.resultado.largo
    df_clas = clasificacion.resultado.largo
    _validar_entradas(df_inpc, df_clas, canastas)
    lag, mensual = _lag_y_mensual(df_clas, frecuencia)
    restar = restar_meses if mensual else restar_quincenas

    periodos = df_clas.index.get_level_values("periodo")
    base_periodos = [restar(p, lag) for p in periodos]  # type: ignore[arg-type]
    return _construir_resultado(
        df_clas, df_clas, df_inpc, canastas, base_periodos,
        f"periodica_{frecuencia}", "", inpc, clasificacion, None,
    )


def incidencia_acumulada_anual(
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    canastas: dict[int, CanastaCanonica],
) -> ResultadoIncidencia:
    """Incidencia de cada periodo contra diciembre del año anterior."""
    _verificar_periodo_referencia(inpc, clasificacion)
    df_inpc = inpc.resultado.largo
    df_clas = clasificacion.resultado.largo
    _validar_entradas(df_inpc, df_clas, canastas)
    mensual = es_mensual(df_clas)

    periodos = df_clas.index.get_level_values("periodo")
    if mensual:
        base_periodos: list[Periodo] = [PeriodoMensual(p.año - 1, 12) for p in periodos]
    else:
        base_periodos = [PeriodoQuincenal(p.año - 1, 12, 2) for p in periodos]
    return _construir_resultado(
        df_clas, df_clas, df_inpc, canastas, base_periodos,
        "acumulada_anual", "", inpc, clasificacion, None,
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
    df_inpc = inpc.resultado.largo
    df_clas = clasificacion.resultado.largo
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
        raise InvarianteViolado(
            f"'hasta' ({hasta_e}) no puede ser anterior a 'desde' ({desde_e})."
        )

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

    df_emitir = df_clas.loc[
        pd.MultiIndex.from_tuples(tuplas_emitir, names=["periodo", "indice"])
    ]
    indices_parciales = pd.DataFrame(
        filas_parciales,
        columns=["indice", "periodo_desde_real", "periodo_hasta_real"],
    ).set_index("indice")

    return _construir_resultado(
        df_emitir, df_lookup, df_inpc, canastas, base_periodos,
        "desde", f"desde {desde_e} hasta {hasta_e}", inpc, clasificacion,
        indices_parciales, excluir_parciales=not incluir_parciales,
    )


def _construir_resultado(
    df_emitir: pd.DataFrame,
    df_lookup: pd.DataFrame,
    df_inpc: pd.DataFrame,
    canastas: dict[int, CanastaCanonica],
    base_periodos: list[Periodo],
    clase: str,
    descripcion: str,
    inpc: ResultadoIndice,
    clasificacion: ResultadoIndice,
    indices_parciales: pd.DataFrame | None,
    excluir_parciales: bool = False,
) -> ResultadoIncidencia:
    """Núcleo del cálculo de incidencias (Fix 1 + Fix 2).

    `df_emitir` aporta las filas `(periodo, indice)` de salida; `df_lookup`
    aporta los valores de los periodos base. `base_periodos` da, por cada fila
    de `df_emitir` y en el mismo orden, el periodo base correspondiente.

    Con `excluir_parciales`, las filas con estado derivado `parcial` se
    descartan de `df_out` (siguen visibles en `reporte`).
    """
    tipo_clas = str(df_emitir["tipo"].iloc[0])
    ids_inpc = [m.id_corrida for m in inpc.manifiesto]
    ids_clas = [m.id_corrida for m in clasificacion.manifiesto]

    pond_por_version: dict[int, pd.Series] = {}
    for v, c in canastas.items():
        ponds = c.df["ponderador"].astype(float)
        pond_por_version[v] = ponds.groupby(c.df[tipo_clas]).sum()
    versiones_encadenadas = {
        int(v) for v, c in canastas.items() if not c.df["encadenamiento"].isna().all()
    }

    periodos = df_emitir.index.get_level_values("periodo")
    indices_clas = df_emitir.index.get_level_values("indice")
    valores_t = df_emitir["indice_replicado"]
    valores_lookup = df_lookup["indice_replicado"]

    base_idx = pd.MultiIndex.from_arrays(
        [base_periodos, indices_clas], names=["periodo", "indice"]
    )
    base_clas = pd.Series(
        valores_lookup.reindex(base_idx).to_numpy(), index=df_emitir.index
    )

    version_por_periodo = (
        df_lookup.reset_index().groupby("periodo")["version"].first().astype(int).to_dict()
    )
    ver_p_per_row = [version_por_periodo[p] for p in periodos]
    ver_base_per_row = [
        version_por_periodo.get(bp, vp)
        for bp, vp in zip(base_periodos, ver_p_per_row)
    ]

    # Fix 2: de-encadenamiento ÷ f_h para versiones encadenadas mismo-ver.
    same_encadenada = [
        ver_p == ver_base and ver_p in versiones_encadenadas
        for ver_p, ver_base in zip(ver_p_per_row, ver_base_per_row)
    ]
    if any(same_encadenada):
        traslape_por_version: dict[int, Periodo] = {
            ver: min(p for p, v in version_por_periodo.items() if v == ver)  # type: ignore[type-var, misc]
            for ver in versiones_encadenadas
            if ver in set(ver_p_per_row)
        }
        f_h_clas_map: dict[tuple[int, str], float] = {}
        f_h_inpc_map: dict[int, float] = {}
        for ver, traslape in traslape_por_version.items():
            for idx in df_lookup.index.get_level_values("indice").unique():
                try:
                    val = float(df_lookup.at[(traslape, idx), "indice_replicado"])  # type: ignore[arg-type]
                    if not pd.isna(val) and val != 0:
                        f_h_clas_map[(ver, str(idx))] = val / 100
                except KeyError:
                    pass
            try:
                val = float(df_inpc.at[(traslape, "INPC"), "indice_replicado"])  # type: ignore[arg-type]
                if not pd.isna(val) and val != 0:
                    f_h_inpc_map[ver] = val / 100
            except KeyError:
                pass
        f_h_i_series = pd.Series(
            [
                f_h_clas_map.get((ver_p, str(idx)), 1.0) if same else 1.0
                for ver_p, idx, same in zip(ver_p_per_row, indices_clas, same_encadenada)
            ],
            index=df_emitir.index,
            dtype=float,
        )
        f_h_inpc_series = pd.Series(
            [
                f_h_inpc_map.get(ver_p, 1.0) if same else 1.0
                for ver_p, same in zip(ver_p_per_row, same_encadenada)
            ],
            index=df_emitir.index,
            dtype=float,
        )
    else:
        f_h_i_series = pd.Series(1.0, index=df_emitir.index, dtype=float)
        f_h_inpc_series = pd.Series(1.0, index=df_emitir.index, dtype=float)

    # Fix 1: ponderadores de la canasta del periodo base.
    pond_serie = pd.Series(
        [
            float(pond_por_version[ver_base].get(c, float("nan")))
            for ver_base, c in zip(ver_base_per_row, indices_clas)
        ],
        index=df_emitir.index,
        dtype=float,
    )
    pond_t_serie = pd.Series(
        [
            float(pond_por_version[ver_p].get(c, float("nan")))
            for ver_p, c in zip(ver_p_per_row, indices_clas)
        ],
        index=df_emitir.index,
        dtype=float,
    )

    inpc_val_cache: dict[Periodo, float] = {}
    inpc_estado_cache: dict[Periodo, object] = {}
    for bp in set(base_periodos):
        try:
            inpc_val_cache[bp] = float(df_inpc.at[(bp, "INPC"), "indice_replicado"])  # type: ignore[arg-type]
            inpc_estado_cache[bp] = df_inpc.at[(bp, "INPC"), "estado_calculo"]
        except KeyError:
            inpc_val_cache[bp] = float("nan")
            inpc_estado_cache[bp] = None
    inpc_base_serie = pd.Series(
        [inpc_val_cache[bp] for bp in base_periodos], index=df_emitir.index, dtype=float
    )
    inpc_estado_base = pd.Series(
        [inpc_estado_cache[bp] for bp in base_periodos], index=df_emitir.index
    )

    # inc_i = w_i * (I_t/f_h_i - I_base/f_h_i) / (INPC_base/f_h_INPC)
    incidencia_pp = (
        (valores_t / f_h_i_series - base_clas / f_h_i_series)
        * pond_serie
        / (inpc_base_serie / f_h_inpc_series)
    )

    estado_clas_base = pd.Series(
        df_lookup["estado_calculo"].reindex(base_idx).to_numpy(), index=df_emitir.index
    )
    computable = incidencia_pp.notna()
    derivado = pd.Series(
        [
            "parcial" if "parcial" in (et, eb, ie) else "ok"
            for et, eb, ie in zip(
                df_emitir["estado_calculo"], estado_clas_base, inpc_estado_base
            )
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
        df_emitir, clasificacion.reporte, valores_t, base_clas,
        pond_t_serie, pond_serie, base_idx, base_periodos,
        ver_p_per_row, ver_base_per_row, inpc_base_serie,
        derivado, computable, ids_inpc + ids_clas, tipo_clas, clase,
    )
    manifiesto = ManifestDerivado(
        id_corrida=ids_inpc + ids_clas,
        tipo=tipo_clas,
        clase=clase,
        descripcion=descripcion,
        fecha=datetime.now(),
        inpc_ids=ids_inpc,
        clasificacion_ids=ids_clas,
    )
    return ResultadoIncidencia(
        df_out, manifiesto, reporte_df, diagnostico_df, indices_parciales
    )


def _motivo_faltante(
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
    ids: list[str],
    tipo: str,
    clase: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye `reporte_df` (todas las filas) y `diagnostico_df` (no computables)."""
    if "cobertura_genericos_pct" in reporte_fuente.columns:
        cobertura = reporte_fuente["cobertura_genericos_pct"]
        cob_t = cobertura.reindex(df_emitir.index)
        cob_lag = pd.Series(
            cobertura.reindex(base_idx).to_numpy(), index=df_emitir.index
        )
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
            motivos.append(_motivo_faltante(vt, vb, ib, pl))

    reporte_df = pd.DataFrame(
        {
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
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
            "id_corrida": ",".join(ids),
            "tipo": tipo,
            "clase_incidencia": clase,
            "periodo": df_emitir.index.get_level_values("periodo"),
            "indice": df_emitir.index.get_level_values("indice"),
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
            "periodo_lag": base_periodos,
            "version_t": ver_p_per_row,
            "version_lag": ver_base_per_row,
        },
        index=df_emitir.index,
        columns=_COLS_DIAGNOSTICO,
    )[no_computable].reset_index(drop=True)

    return reporte_df, diagnostico_df
