from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal, periodo_desde_str

_LAG_QUINCENAL: dict[str, int] = {
    "quincenal": 1,
    "mensual": 2,
    "bimestral": 4,
    "trimestral": 6,
    "cuatrimestral": 8,
    "semestral": 12,
    "anual": 24,
}

_LAG_MENSUAL: dict[str, int] = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "cuatrimestral": 4,
    "semestral": 6,
    "anual": 12,
}


def _restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    if not isinstance(periodo, PeriodoQuincenal):
        raise InvarianteViolado(
            f"_restar_quincenas requiere PeriodoQuincenal, se recibió {type(periodo).__name__}."
        )
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    año = ordinal // 24
    mes = (ordinal % 24) // 2 + 1
    quincena = (ordinal % 24) % 2 + 1
    return PeriodoQuincenal(año, mes, quincena)


def _restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    año = ordinal // 12
    mes = ordinal % 12 + 1
    return PeriodoMensual(año, mes)


def _es_mensual(df: pd.DataFrame) -> bool:
    return isinstance(df.index.get_level_values("periodo")[0], PeriodoMensual)


def _tipo_unico(df: pd.DataFrame) -> str:
    tipos = df["tipo"].unique()
    if len(tipos) != 1:
        raise InvarianteViolado(f"El DataFrame contiene tipos {tipos} y se esperaba un único tipo.")
    return str(tipos[0])


def _drop_keep(df_var: pd.DataFrame, valores_t: pd.Series) -> pd.DataFrame:
    mask_drop = valores_t.notna() & df_var["variacion"].isna()
    return df_var[~mask_drop]


def variacion_periodica(
    resultado: ResultadoCalculo,
    frecuencia: Literal[
        "quincenal", "mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual"
    ],
) -> ResultadoVariacion:

    df = resultado.df
    tipo = _tipo_unico(df)
    mensual = _es_mensual(df)

    if mensual:
        if frecuencia == "quincenal":
            print(
                "[replica_inpc] Advertencia: frecuencia 'quincenal' no aplica a datos mensuales. "
                "Se usará 'mensual'."
            )
            frecuencia = "mensual"
        lag = _LAG_MENSUAL[frecuencia]
        restar = _restar_meses
    else:
        lag = _LAG_QUINCENAL[frecuencia]
        restar = _restar_quincenas  # type: ignore[assignment]

    periodos = df.index.get_level_values("periodo")
    indices = df.index.get_level_values("indice")
    valores = df["indice_replicado"]

    base_periodos = [restar(p, lag) for p in periodos]
    base_idx = pd.MultiIndex.from_arrays([base_periodos, indices], names=["periodo", "indice"])
    base_valores = valores.reindex(base_idx)
    base_valores.index = df.index

    variacion = valores / base_valores - 1
    df_var = pd.DataFrame({"variacion": variacion}, index=df.index)
    df_var = _drop_keep(df_var, valores)

    if df_var.empty:
        unidad = "meses" if mensual else "quincenas"
        raise InvarianteViolado(
            f"Sin periodos con base para frecuencia '{frecuencia}'. "
            f"Se requieren >= {lag} {unidad} de datos."
        )

    return ResultadoVariacion(df_var.sort_index(), tipo=tipo, descripcion=frecuencia)


def variacion_desde(
    resultado: ResultadoCalculo,
    desde: str,
    hasta: str | None = None,
    incluir_parciales: bool = False,
) -> ResultadoVariacion:
    df = resultado.df
    tipo = _tipo_unico(df)
    mensual = _es_mensual(df)

    desde_p = periodo_desde_str(desde)
    hasta_p = periodo_desde_str(hasta) if hasta is not None else None

    if mensual and not isinstance(desde_p, PeriodoMensual):
        raise InvarianteViolado(
            f"'desde' debe ser periodo mensual cuando el resultado es mensual. "
            f"Se recibió '{desde_p}' (quincenal)."
        )
    if not mensual and not isinstance(desde_p, PeriodoQuincenal):
        raise InvarianteViolado(
            f"'desde' debe ser periodo quincenal cuando el resultado es quincenal. "
            f"Se recibió '{desde_p}' (mensual)."
        )
    if hasta_p is not None:
        if mensual and not isinstance(hasta_p, PeriodoMensual):
            raise InvarianteViolado(
                f"'hasta' debe ser periodo mensual cuando el resultado es mensual. "
                f"Se recibió '{hasta_p}' (quincenal)."
            )
        if not mensual and not isinstance(hasta_p, PeriodoQuincenal):
            raise InvarianteViolado(
                f"'hasta' debe ser periodo quincenal cuando el resultado es quincenal. "
                f"Se recibió '{hasta_p}' (mensual)."
            )

    restar = _restar_meses if mensual else _restar_quincenas  # type: ignore[assignment]

    periodos_todos = df.index.get_level_values("periodo")
    hasta_efectivo = hasta_p if hasta_p is not None else max(periodos_todos)

    if hasta_efectivo < desde_p:  # type: ignore[operator]
        raise InvarianteViolado("'hasta' debe ser posterior a 'desde'")

    base_periodo = restar(desde_p, 1)  # type: ignore[arg-type]
    mask_rango = (periodos_todos >= desde_p) & (periodos_todos <= hasta_efectivo)
    df_rango = df[mask_rango]
    valores = df["indice_replicado"]

    if not incluir_parciales:
        try:
            slice_base = df.xs(base_periodo, level="periodo")["indice_replicado"]
            indices_validos = set(slice_base[slice_base.notna()].index)
        except KeyError:
            indices_validos = set()

        if not indices_validos:
            periodos_set = set(periodos_todos)
            if base_periodo not in periodos_set:
                min_desde = next(
                    (p for p in sorted(periodos_set) if restar(p, 1) in periodos_set),
                    None,
                )
                raise InvarianteViolado(
                    f"No hay datos en '{base_periodo}' (base de '{desde_p}'). "
                    + (
                        f"'desde' mínimo válido: '{min_desde}'."
                        if min_desde
                        else "Sin periodos con base disponible."
                    )
                )
            raise InvarianteViolado(
                f"Ningún índice tiene dato en el rango [{desde_p}, {hasta_efectivo}]. Usa incluir_parciales=True."
            )

        indice_lvl = df_rango.index.get_level_values("indice")
        df_filtrado = df_rango[indice_lvl.isin(indices_validos)]

        valores_t = df_filtrado["indice_replicado"]
        indice_lvl_f = df_filtrado.index.get_level_values("indice")
        base_idx = pd.MultiIndex.from_arrays(
            [[base_periodo] * len(df_filtrado), indice_lvl_f],
            names=["periodo", "indice"],
        )
        base_valores = valores.reindex(base_idx)
        base_valores.index = df_filtrado.index

        variacion = valores_t / base_valores - 1
        df_var = pd.DataFrame({"variacion": variacion}, index=df_filtrado.index)
        df_var = _drop_keep(df_var, valores_t)

        if df_var.empty:
            raise InvarianteViolado(
                f"Ningún índice tiene dato en el rango [{desde_p}, {hasta_efectivo}]. Usa incluir_parciales=True."
            )

        return ResultadoVariacion(
            df_var.sort_index(),
            tipo=tipo,
            descripcion=f"desde {desde_p} hasta {hasta_efectivo}",
        )

    else:
        if df_rango.empty:
            raise InvarianteViolado(
                f"Sin datos en el rango desde {desde_p} hasta {hasta_efectivo}."
            )

        valid_en_rango = df_rango[df_rango["indice_replicado"].notna()]
        if valid_en_rango.empty:
            raise InvarianteViolado(
                f"Sin datos en el rango desde {desde_p} hasta {hasta_efectivo}."
            )

        try:
            slice_base = df.xs(base_periodo, level="periodo")["indice_replicado"]
            indices_en_base = set(slice_base[slice_base.notna()].index)
        except KeyError:
            indices_en_base = set()

        first_valid_por_indice: pd.Series = (
            valid_en_rango.reset_index().groupby("indice")["periodo"].min()
        )

        base_por_indice: pd.Series = pd.Series(
            {
                indice: (base_periodo if indice in indices_en_base else t0)
                for indice, t0 in first_valid_por_indice.items()
            }
        )

        base_tuples = list(zip(base_por_indice.values, base_por_indice.index))
        base_mi = pd.MultiIndex.from_tuples(base_tuples, names=["periodo", "indice"])
        base_vals = valores.reindex(base_mi).droplevel("periodo")

        indice_lvl = df_rango.index.get_level_values("indice")
        base_val_per_row = pd.Series(
            [base_vals.get(i, float("nan")) for i in indice_lvl],
            index=df_rango.index,
        )

        valores_t = df_rango["indice_replicado"]
        variacion = valores_t / base_val_per_row - 1
        df_var = pd.DataFrame({"variacion": variacion}, index=df_rango.index)
        df_var = _drop_keep(df_var, valores_t)

        if df_var.empty:
            raise InvarianteViolado(
                f"Sin datos en el rango desde {desde_p} hasta {hasta_efectivo}."
            )

        indices_parciales = {
            str(indice): periodo
            for indice, periodo in base_por_indice.items()
            if periodo != base_periodo
        }

        return ResultadoVariacion(
            df_var.sort_index(),
            tipo=tipo,
            descripcion=f"desde {desde_p} hasta {hasta_efectivo}",
            indices_parciales=indices_parciales if indices_parciales else None,
        )


def variacion_acumulada_anual(
    resultado: ResultadoCalculo,
) -> ResultadoVariacion:
    df = resultado.df
    tipo = _tipo_unico(df)
    mensual = _es_mensual(df)

    periodos = df.index.get_level_values("periodo")
    indices = df.index.get_level_values("indice")
    valores = df["indice_replicado"]

    base_periodos: list[PeriodoMensual | PeriodoQuincenal]
    if mensual:
        base_periodos = [PeriodoMensual(p.año - 1, 12) for p in periodos]
    else:
        base_periodos = [PeriodoQuincenal(p.año - 1, 12, 2) for p in periodos]

    base_idx = pd.MultiIndex.from_arrays([base_periodos, indices], names=["periodo", "indice"])
    base_valores = valores.reindex(base_idx)
    base_valores.index = df.index

    variacion = valores / base_valores - 1
    df_var = pd.DataFrame({"variacion": variacion}, index=df.index)
    df_var = _drop_keep(df_var, valores)

    if df_var.empty:
        raise InvarianteViolado(
            "Sin periodos con base anual disponible. Se requiere  >= 1 año de datos."
        )

    return ResultadoVariacion(df_var.sort_index(), tipo=tipo, descripcion="acumulada_anual")
