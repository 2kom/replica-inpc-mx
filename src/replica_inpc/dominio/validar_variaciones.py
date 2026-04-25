from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.modelos.validacion import ReporteValidacionVariaciones
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_TOLERANCIA_VARIACION_PP = 0.009

_LAG_POR_TIPO: dict[str, int] = {
    "periodica": 1,
    "interanual": 12,
}

_LAG_QUINCENAL: dict[str, int] = {
    "periodica": 1,
    "interanual": 24,
}


def _restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    return PeriodoMensual(ordinal // 12, ordinal % 12 + 1)


def _restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    o = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1) - n
    return PeriodoQuincenal(o // 24, (o % 24) // 2 + 1, o % 2 + 1)


def _base_periodo(
    periodo: PeriodoMensual | PeriodoQuincenal,
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
) -> PeriodoMensual | PeriodoQuincenal:
    if isinstance(periodo, PeriodoQuincenal):
        if tipo_variacion == "acumulada_anual":
            return PeriodoQuincenal(periodo.año - 1, 12, 2)
        return _restar_quincenas(periodo, _LAG_QUINCENAL[tipo_variacion])
    if tipo_variacion == "acumulada_anual":
        return PeriodoMensual(periodo.año - 1, 12)
    return _restar_meses(periodo, _LAG_POR_TIPO[tipo_variacion])


def validar_variaciones(
    rv: ResultadoVariacion,
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    inegi: dict[str, dict[PeriodoMensual | PeriodoQuincenal, float | None]],
) -> ReporteValidacionVariaciones:
    """Compara una variación calculada contra series publicadas por el INEGI.

    Soporta PeriodoMensual y PeriodoQuincenal. Ausencia de clave en inegi[indice]
    para un periodo dado indica fuera_de_rango_inegi (no publicado por INEGI aún).
    """
    periodos_semiok = rv.periodos_semiok
    filas: list[dict] = []

    for idx, row in rv.df.iterrows():  # type: ignore[union-attr]
        periodo: PeriodoMensual | PeriodoQuincenal
        indice: str
        periodo, indice = idx  # type: ignore[misc]
        variacion_rep = row["variacion"]
        base = _base_periodo(periodo, tipo_variacion)
        inegi_vals = inegi.get(indice, {})

        if base in periodos_semiok:
            estado = "excluido_semi_ok"
            var_inegi, error_pp = None, None
        elif periodo not in inegi_vals:
            estado = "fuera_de_rango_inegi"
            var_inegi, error_pp = None, None
        elif inegi_vals[periodo] is None or pd.isna(variacion_rep):
            estado = "no_disponible"
            var_inegi, error_pp = None, None
        else:
            var_inegi = inegi_vals[periodo]  # type: ignore[assignment]
            error_pp = abs(float(variacion_rep) * 100 - float(var_inegi))  # type: ignore[arg-type]
            estado = "ok" if error_pp <= _TOLERANCIA_VARIACION_PP else "diferencia_detectada"

        filas.append(
            {
                "tipo_variacion": tipo_variacion,
                "periodo": periodo,
                "indice": indice,
                "variacion_replicada_pp": float(variacion_rep) * 100
                if not pd.isna(variacion_rep)
                else None,
                "variacion_inegi_pp": float(var_inegi) if var_inegi is not None else None,
                "error_absoluto_pp": error_pp,
                "estado_validacion": estado,
            }
        )

    df_rep = pd.DataFrame(filas).set_index(["tipo_variacion", "periodo", "indice"])
    return ReporteValidacionVariaciones(df_rep)
