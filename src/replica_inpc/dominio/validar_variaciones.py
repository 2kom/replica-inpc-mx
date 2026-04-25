from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.modelos.validacion import ReporteValidacionVariaciones
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual

_TOLERANCIA_VARIACION_PP = 0.09

_LAG_POR_TIPO: dict[str, int] = {
    "periodica": 1,
    "interanual": 12,
}


def _restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    return PeriodoMensual(ordinal // 12, ordinal % 12 + 1)


def _base_periodo(
    periodo: PeriodoMensual,
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
) -> PeriodoMensual:
    if tipo_variacion == "acumulada_anual":
        return PeriodoMensual(periodo.año - 1, 12)
    return _restar_meses(periodo, _LAG_POR_TIPO[tipo_variacion])


def validar_variaciones(
    rv: ResultadoVariacion,
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    inegi: dict[str, dict[PeriodoMensual, float | None]],
) -> ReporteValidacionVariaciones:
    """Compara una variación mensual calculada contra series publicadas por el INEGI.

    Precondición: rv debe tener periodos PeriodoMensual.
    """
    periodos_semiok = rv.periodos_semiok
    filas: list[dict] = []

    for (periodo, indice), row in rv.df.iterrows():  # type: ignore[union-attr]
        variacion_rep = row["variacion"]
        base = _base_periodo(periodo, tipo_variacion)  # type: ignore[arg-type]

        if base in periodos_semiok:
            estado = "excluido_semi_ok"
            var_inegi = None
            error_pp = None
        else:
            var_inegi = inegi.get(indice, {}).get(periodo)  # type: ignore[arg-type]
            if var_inegi is None or pd.isna(variacion_rep):
                estado = "no_disponible"
                error_pp = None
            else:
                error_pp = abs(float(variacion_rep) * 100 - float(var_inegi))
                estado = "ok" if error_pp <= _TOLERANCIA_VARIACION_PP else "diferencia_detectada"

        filas.append(
            {
                "tipo_variacion": tipo_variacion,
                "periodo": periodo,
                "indice": indice,
                "variacion_replicada": float(variacion_rep) if not pd.isna(variacion_rep) else None,
                "variacion_inegi_pp": float(var_inegi) if var_inegi is not None else None,
                "error_absoluto_pp": error_pp,
                "estado_validacion": estado,
            }
        )

    df_rep = pd.DataFrame(filas).set_index(["tipo_variacion", "periodo", "indice"])
    return ReporteValidacionVariaciones(df_rep)
