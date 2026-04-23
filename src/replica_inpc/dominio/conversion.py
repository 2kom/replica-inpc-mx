from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal


def a_mensual(resultado: ResultadoCalculo) -> ResultadoCalculo:
    """Convierte un ResultadoCalculo quincenal a periodos mensuales.

    Promedia las dos quincenas de cada mes por promedio simple. Si solo hay
    una quincena disponible, usa ese valor con estado_calculo='semi_ok'.

    Args:
        resultado: ResultadoCalculo con todos los periodos PeriodoQuincenal.

    Returns:
        ResultadoCalculo con periodos PeriodoMensual y mismo id_corrida.

    Raises:
        InvarianteViolado: Si resultado ya es mensual.

    Ver: docs/diseño.md §5.13
    """
    df = resultado.df
    periodos = df.index.get_level_values("periodo")

    if not all(isinstance(p, PeriodoQuincenal) for p in periodos):
        raise InvarianteViolado("a_mensual requiere un ResultadoCalculo quincenal")

    df_work = df.copy()
    df_work["_año"] = [p.año for p in periodos]
    df_work["_mes"] = [p.mes for p in periodos]
    df_work["_quincena"] = [p.quincena for p in periodos]
    df_work["_indice"] = df.index.get_level_values("indice")

    filas: list[dict] = []
    for (año, mes, indice), grupo in df_work.groupby(["_año", "_mes", "_indice"], sort=False):
        q_rows = {int(row["_quincena"]): row for _, row in grupo.iterrows()}
        q1 = q_rows.get(1)
        q2 = q_rows.get(2)

        ref = q2 if q2 is not None else q1
        assert ref is not None  # groupby siempre produce al menos un row por grupo
        base = {
            "periodo": PeriodoMensual(int(año), int(mes)),  # type: ignore[arg-type]
            "indice": indice,
            "version": ref["version"],
            "tipo": ref["tipo"],
        }

        if any(row["estado_calculo"] == "fallida" for row in q_rows.values()):
            motivo = next(
                row["motivo_error"] for row in q_rows.values() if row["estado_calculo"] == "fallida"
            )
            filas.append(
                {
                    **base,
                    "indice_replicado": None,
                    "estado_calculo": "fallida",
                    "motivo_error": motivo,
                }
            )
            continue

        v1 = q1["indice_replicado"] if q1 is not None else None
        v2 = q2["indice_replicado"] if q2 is not None else None
        v1_ok = v1 is not None and pd.notna(v1)
        v2_ok = v2 is not None and pd.notna(v2)

        if v1_ok and v2_ok:
            assert v1 is not None and v2 is not None
            filas.append(
                {
                    **base,
                    "indice_replicado": (v1 + v2) / 2,
                    "estado_calculo": "ok",
                    "motivo_error": None,
                }
            )
        elif v1_ok or v2_ok:
            filas.append(
                {
                    **base,
                    "indice_replicado": v1 if v1_ok else v2,
                    "estado_calculo": "semi_ok",
                    "motivo_error": None,
                }
            )
        else:
            filas.append(
                {
                    **base,
                    "indice_replicado": None,
                    "estado_calculo": "null_por_faltantes",
                    "motivo_error": ref["motivo_error"],
                }
            )

    df_result = pd.DataFrame(filas)
    df_result.index = pd.MultiIndex.from_arrays(
        [df_result.pop("periodo"), df_result.pop("indice")],
        names=["periodo", "indice"],
    )
    df_result.sort_index(level="periodo", sort_remaining=False, inplace=True)

    return ResultadoCalculo(df_result, resultado.id_corrida)
