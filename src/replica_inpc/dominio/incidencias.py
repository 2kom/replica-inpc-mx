from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import COLUMNAS_CLASIFICACION

_LAG_MENSUAL: dict[str, int] = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "cuatrimestral": 4,
    "semestral": 6,
    "anual": 12,
}

_LAG_QUINCENAL: dict[str, int] = {
    "quincenal": 1,
    "mensual": 2,
    "bimestral": 4,
    "trimestral": 6,
    "cuatrimestral": 8,
    "semestral": 12,
    "anual": 24,
}


def _restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    return PeriodoQuincenal(ordinal // 24, (ordinal % 24) // 2 + 1, ordinal % 2 + 1)


def _restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    return PeriodoMensual(ordinal // 12, ordinal % 12 + 1)


def _es_mensual(df: pd.DataFrame) -> bool:
    return isinstance(df.index.get_level_values("periodo")[0], PeriodoMensual)


def _validar_entradas(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: dict[int, CanastaCanonica],
    frecuencia: str | None = None,
) -> None:
    tipo_inpc = str(inpc.df["tipo"].iloc[0])
    if tipo_inpc != "inpc":
        raise ErrorConfiguracion(
            f"El primer argumento debe ser un resultado de tipo 'inpc', se recibió '{tipo_inpc}'."
        )
    tipo_clas = str(clasificacion.df["tipo"].iloc[0])
    if tipo_clas not in COLUMNAS_CLASIFICACION:
        raise ErrorConfiguracion(
            f"El tipo de clasificación '{tipo_clas}' no es válido. "
            f"Tipos soportados: {sorted(COLUMNAS_CLASIFICACION)}"
        )
    clas_vers = set(int(v) for v in clasificacion.df["version"].unique())
    faltantes = clas_vers - set(canastas.keys())
    if faltantes:
        raise ErrorConfiguracion(
            f"Falta canasta para versión(es) {sorted(faltantes)}. "
            "Proporciona una canasta por cada versión presente en el resultado."
        )
    if frecuencia is not None:
        mensual = _es_mensual(inpc.df)
        lag_map = _LAG_MENSUAL if mensual else _LAG_QUINCENAL
        if frecuencia not in lag_map:
            tipo_p = "mensual" if mensual else "quincenal"
            raise ErrorConfiguracion(
                f"Frecuencia '{frecuencia}' no reconocida para periodos {tipo_p}. "
                f"Frecuencias válidas: {sorted(lag_map)}"
            )


def _construir_resultado(
    df_clas: pd.DataFrame,
    df_inpc: pd.DataFrame,
    canastas: dict[int, CanastaCanonica],
    base_por_periodo: dict[PeriodoQuincenal | PeriodoMensual, PeriodoQuincenal | PeriodoMensual],
    tipo_clas: str,
    frecuencia: str,
    clase_incidencia: str,
) -> ResultadoIncidencia:
    pond_por_version: dict[int, pd.Series] = {}
    for v, c in canastas.items():
        ponds = c.df["ponderador"].astype(float)
        pond_por_version[v] = ponds.groupby(c.df[tipo_clas]).sum()

    semiok_clas = frozenset(
        df_clas[df_clas["estado_calculo"] == "semi_ok"].index.get_level_values("periodo")
    )
    semiok_inpc = frozenset(
        df_inpc[df_inpc["estado_calculo"] == "semi_ok"].index.get_level_values("periodo")
    )
    semiok_base = semiok_clas | semiok_inpc

    periodos = df_clas.index.get_level_values("periodo")
    indices_clas = df_clas.index.get_level_values("indice")
    valores_t = df_clas["indice_replicado"]

    base_periodos_list = [base_por_periodo[p] for p in periodos]
    base_idx = pd.MultiIndex.from_arrays(
        [base_periodos_list, indices_clas], names=["periodo", "indice"]
    )
    base_clas = valores_t.reindex(base_idx)
    base_clas.index = df_clas.index

    version_por_periodo = (
        df_clas.reset_index().groupby("periodo")["version"].first().astype(int).to_dict()
    )
    pond_serie = pd.Series(
        [
            float(pond_por_version[version_por_periodo[p]].get(c, float("nan")))
            for p, c in zip(periodos, indices_clas)
        ],
        index=df_clas.index,
        dtype=float,
    )

    inpc_base_por_periodo: dict[PeriodoQuincenal | PeriodoMensual, float] = {}
    for p, base_p in base_por_periodo.items():
        try:
            inpc_base_por_periodo[p] = float(df_inpc.at[(base_p, "INPC"), "indice_replicado"])  # type: ignore[union-attr]
        except KeyError:
            inpc_base_por_periodo[p] = float("nan")
    inpc_base_serie = pd.Series(
        [inpc_base_por_periodo.get(p, float("nan")) for p in periodos],
        index=df_clas.index,
        dtype=float,
    )

    # inc_i = w_i * (I_t^i - I_base^i) / INPC_base  →  Σ inc_i = var_INPC en pp
    incidencia_pp = (valores_t - base_clas) * pond_serie / inpc_base_serie

    # Drop rows where current value exists but incidencia is NaN (base missing)
    mask_drop = valores_t.notna() & incidencia_pp.isna()
    df_clas_f = df_clas[~mask_drop]
    incidencia_pp = incidencia_pp[~mask_drop]
    periodos_f = df_clas_f.index.get_level_values("periodo")

    if incidencia_pp.empty or incidencia_pp.notna().sum() == 0:
        mensual = isinstance(periodos[0], PeriodoMensual)
        unidad = "meses" if mensual else "quincenas"
        raise InvarianteViolado(
            f"Sin periodos con base disponible para clase '{clase_incidencia}'. "
            f"Se requieren datos suficientes ({unidad})."
        )

    estado_calculo = pd.Series(
        [
            float("nan")
            if pd.isna(pp)
            else ("semi_ok" if base_por_periodo[p] in semiok_base else "ok")
            for p, pp in zip(periodos_f, incidencia_pp)
        ],
        index=df_clas_f.index,
    )

    df_result = pd.DataFrame(
        {
            "incidencia_pp": incidencia_pp,
            "tipo": tipo_clas,
            "frecuencia": frecuencia,
            "clase_incidencia": clase_incidencia,
            "estado_calculo": estado_calculo,
        },
        index=df_clas_f.index,
    ).sort_index()

    semiok_resultado = frozenset(
        df_result[df_result["estado_calculo"] == "semi_ok"].index.get_level_values("periodo")
    )

    return ResultadoIncidencia(
        df_result,
        clase_incidencia=clase_incidencia,  # type: ignore[arg-type]
        periodos_semiok=semiok_resultado,
    )


def incidencia_periodica(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: dict[int, CanastaCanonica],
    frecuencia: str,
) -> ResultadoIncidencia:
    _validar_entradas(inpc, clasificacion, canastas, frecuencia)

    df_clas = clasificacion.df
    df_inpc = inpc.df
    tipo_clas = str(df_clas["tipo"].iloc[0])
    mensual = _es_mensual(df_clas)

    if mensual:
        lag = _LAG_MENSUAL[frecuencia]
        restar = _restar_meses
    else:
        lag = _LAG_QUINCENAL[frecuencia]
        restar = _restar_quincenas  # type: ignore[assignment]

    periodos_uniq = df_clas.index.get_level_values("periodo").unique()
    base_por_periodo: dict[PeriodoQuincenal | PeriodoMensual, PeriodoQuincenal | PeriodoMensual] = {
        p: restar(p, lag)
        for p in periodos_uniq  # type: ignore[arg-type]
    }

    return _construir_resultado(
        df_clas, df_inpc, canastas, base_por_periodo, tipo_clas, frecuencia, "periodica"
    )


def incidencia_acumulada_anual(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: dict[int, CanastaCanonica],
) -> ResultadoIncidencia:
    _validar_entradas(inpc, clasificacion, canastas)

    df_clas = clasificacion.df
    df_inpc = inpc.df
    tipo_clas = str(df_clas["tipo"].iloc[0])
    mensual = _es_mensual(df_clas)

    periodos_uniq = df_clas.index.get_level_values("periodo").unique()
    base_por_periodo: dict[PeriodoQuincenal | PeriodoMensual, PeriodoQuincenal | PeriodoMensual]
    if mensual:
        base_por_periodo = {p: PeriodoMensual(p.año - 1, 12) for p in periodos_uniq}
    else:
        base_por_periodo = {p: PeriodoQuincenal(p.año - 1, 12, 2) for p in periodos_uniq}

    return _construir_resultado(
        df_clas,
        df_inpc,
        canastas,
        base_por_periodo,
        tipo_clas,
        "acumulada_anual",
        "acumulada_anual",
    )


def incidencia_desde(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: dict[int, CanastaCanonica],
    desde: PeriodoQuincenal | PeriodoMensual,
    hasta: PeriodoQuincenal | PeriodoMensual,
) -> ResultadoIncidencia:
    _validar_entradas(inpc, clasificacion, canastas)

    df_clas = clasificacion.df
    df_inpc = inpc.df
    tipo_clas = str(df_clas["tipo"].iloc[0])

    periodos_todos = df_clas.index.get_level_values("periodo")
    mask = (periodos_todos >= desde) & (periodos_todos <= hasta)  # type: ignore[operator]
    df_clas_rango = df_clas[mask]

    if df_clas_rango.empty:
        raise InvarianteViolado(f"Sin datos en el rango [{desde}, {hasta}].")

    periodos_rango = df_clas_rango.index.get_level_values("periodo").unique()
    base_por_periodo = {p: desde for p in periodos_rango}  # type: ignore[misc]

    frecuencia = f"desde {desde} hasta {hasta}"
    return _construir_resultado(
        df_clas_rango, df_inpc, canastas, base_por_periodo, tipo_clas, frecuencia, "desde"
    )
