from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import Periodo

_LAG: dict[str, int] = {
    "quincenal": 1,
    "mensual": 2,
    "bimestral": 4,
    "trimestral": 6,
    "cuatrimestral": 8,
    "semestral": 12,
    "anual": 24,
}


def _restar_quincenas(periodo: Periodo, n: int) -> Periodo:
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    año = ordinal // 24
    mes = (ordinal % 24) // 2 + 1
    quincena = (ordinal % 24) % 2 + 1
    return Periodo(año, mes, quincena)


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
    lag = _LAG[frecuencia]

    periodos = df.index.get_level_values("periodo")
    indices = df.index.get_level_values("indice")
    valores = df["indice_replicado"]

    base_periodos = [_restar_quincenas(p, lag) for p in periodos]
    base_idx = pd.MultiIndex.from_arrays([base_periodos, indices], names=["periodo", "indice"])
    base_valores = valores.reindex(base_idx)
    base_valores.index = df.index

    variacion = valores / base_valores - 1
    df_var = pd.DataFrame({"variacion": variacion}, index=df.index)
    df_var = _drop_keep(df_var, valores)

    if df_var.empty:
        raise InvarianteViolado(
            f"Sin periodos con base para frecuencia '{frecuencia}'. Se requieren >= {lag} quincenas de datos."
        )

    return ResultadoVariacion(df_var.sort_index(), tipo=tipo, descripcion=frecuencia)


def variacion_desde(
    resultado: ResultadoCalculo,
    desde: Periodo,
    hasta: Periodo | None = None,
    incluir_parciales: bool = False,
) -> ResultadoVariacion:
    df = resultado.df
    tipo = _tipo_unico(df)

    periodos_todos = df.index.get_level_values("periodo")
    hasta_efectivo = hasta if hasta is not None else max(periodos_todos)

    if hasta_efectivo < desde:
        raise InvarianteViolado("'hasta' debe ser posterior a 'desde'")

    mask_rango = (periodos_todos >= desde) & (periodos_todos <= hasta_efectivo)
    df_rango = df[mask_rango]
    valores = df["indice_replicado"]

    if not incluir_parciales:
        try:
            slice_desde = df.xs(desde, level="periodo")["indice_replicado"]
            indices_validos = set(slice_desde[slice_desde.notna()].index)
        except KeyError:
            indices_validos = set()

        if not indices_validos:
            raise InvarianteViolado(
                f"Ningún índice tiene dato en el rango [{desde}, {hasta_efectivo}]. Usa incluir_parciales=True."
            )

        indice_lvl = df_rango.index.get_level_values("indice")
        df_filtrado = df_rango[indice_lvl.isin(indices_validos)]

        valores_t = df_filtrado["indice_replicado"]
        indice_lvl_f = df_filtrado.index.get_level_values("indice")
        base_idx = pd.MultiIndex.from_arrays(
            [[desde] * len(df_filtrado), indice_lvl_f],
            names=["periodo", "indice"],
        )
        base_valores = valores.reindex(base_idx)
        base_valores.index = df_filtrado.index

        variacion = valores_t / base_valores - 1
        df_var = pd.DataFrame({"variacion": variacion}, index=df_filtrado.index)
        df_var = _drop_keep(df_var, valores_t)

        if df_var.empty:
            raise InvarianteViolado(
                f"Ningún índice tiene dato en el rango [{desde}, {hasta_efectivo}]. Usa incluir_parciales=True."
            )

        return ResultadoVariacion(
            df_var.sort_index(),
            tipo=tipo,
            descripcion=f"desde {desde} hasta {hasta_efectivo}",
        )

    else:
        if df_rango.empty:
            raise InvarianteViolado(f"Sin datos en el rango desde {desde} hasta {hasta_efectivo}.")

        valid_en_rango = df_rango[df_rango["indice_replicado"].notna()]
        if valid_en_rango.empty:
            raise InvarianteViolado(f"Sin datos en el rango desde {desde} hasta {hasta_efectivo}.")

        base_por_indice: pd.Series = valid_en_rango.reset_index().groupby("indice")["periodo"].min()

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
            raise InvarianteViolado(f"Sin datos en el rango desde {desde} hasta {hasta_efectivo}.")

        indices_parciales = {
            str(indice): periodo for indice, periodo in base_por_indice.items() if periodo != desde
        }

        return ResultadoVariacion(
            df_var.sort_index(),
            tipo=tipo,
            descripcion=f"desde {desde} hasta {hasta_efectivo}",
            indices_parciales=indices_parciales if indices_parciales else None,
        )


def variacion_acumulada_anual(
    resultado: ResultadoCalculo,
) -> ResultadoVariacion:
    df = resultado.df
    tipo = _tipo_unico(df)

    periodos = df.index.get_level_values("periodo")
    indices = df.index.get_level_values("indice")
    valores = df["indice_replicado"]

    base_periodos = [Periodo(p.año - 1, 12, 2) for p in periodos]
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
