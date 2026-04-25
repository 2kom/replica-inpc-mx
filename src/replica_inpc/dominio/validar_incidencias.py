from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.validacion import ReporteValidacionIncidencias
from replica_inpc.dominio.periodos import PeriodoMensual

# Verificación empírica pendiente antes de cerrar v1.2.5
_TOLERANCIA_INCIDENCIA_PP: float = 0.009


def validar_incidencias(
    ri: ResultadoIncidencia,
    tipo_incidencia: Literal["interanual"],
    inegi: dict[str, dict[PeriodoMensual, float | None]],
) -> ReporteValidacionIncidencias:
    """Compara incidencias calculadas contra series publicadas por el INEGI.

    Ausencia de clave en inegi[indice] para un periodo indica fuera_de_rango_inegi.
    """
    periodos_semiok = ri.periodos_semiok
    filas: list[dict] = []

    for idx, row in ri.df.iterrows():  # type: ignore[union-attr]
        periodo: PeriodoMensual
        indice: str
        periodo, indice = idx  # type: ignore[misc]
        incidencia_rep = row["incidencia_pp"]
        inegi_vals = inegi.get(indice, {})

        if periodo in periodos_semiok:
            estado = "excluido_semi_ok"
            inc_inegi, error_pp = None, None
        elif periodo not in inegi_vals:
            estado = "fuera_de_rango_inegi"
            inc_inegi, error_pp = None, None
        elif inegi_vals[periodo] is None or pd.isna(incidencia_rep):
            estado = "no_disponible"
            inc_inegi, error_pp = None, None
        else:
            inc_inegi = float(inegi_vals[periodo])  # type: ignore[arg-type]
            error_pp = abs(float(incidencia_rep) - inc_inegi)
            estado = "ok" if error_pp <= _TOLERANCIA_INCIDENCIA_PP else "diferencia_detectada"

        filas.append(
            {
                "tipo_incidencia": tipo_incidencia,
                "periodo": periodo,
                "indice": indice,
                "incidencia_replicada_pp": float(incidencia_rep)
                if not pd.isna(incidencia_rep)
                else None,
                "incidencia_inegi_pp": inc_inegi,
                "error_absoluto_pp": error_pp,
                "estado_validacion": estado,
            }
        )

    df_rep = pd.DataFrame(filas).set_index(["tipo_incidencia", "periodo", "indice"])
    return ReporteValidacionIncidencias(df_rep)
