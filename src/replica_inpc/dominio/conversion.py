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

    # Metadata: preferir q2, fallback q1
    version = q2_r["version"].fillna(q1_r["version"])
    tipo = q2_r["tipo"].fillna(q1_r["tipo"])

    # Valores e indicadores de disponibilidad
    v1 = q1_r["indice_replicado"]
    v2 = q2_r["indice_replicado"]
    v1_ok = v1.notna()
    v2_ok = v2.notna()
    both_ok = v1_ok & v2_ok
    one_ok = v1_ok ^ v2_ok

    # Estado
    fallida_q1 = (q1_r["estado_calculo"] == "fallida").fillna(False)
    fallida_q2 = (q2_r["estado_calculo"] == "fallida").fillna(False)
    any_fallida = fallida_q1 | fallida_q2
    null_mask = ~any_fallida & ~both_ok & ~one_ok

    estado_calculo = pd.Series("null_por_faltantes", index=all_groups, dtype=object)
    estado_calculo[any_fallida] = "fallida"
    estado_calculo[~any_fallida & both_ok] = "ok"
    estado_calculo[~any_fallida & one_ok] = "semi_ok"

    # Valor promediado
    val_avg = (v1 + v2) / 2
    val_one = v1.fillna(v2)
    indice_replicado = pd.Series(float("nan"), index=all_groups)
    indice_replicado[~any_fallida & both_ok] = val_avg[~any_fallida & both_ok]
    indice_replicado[~any_fallida & one_ok] = val_one[~any_fallida & one_ok]

    # Motivo error
    motivo_q1 = q1_r["motivo_error"]
    motivo_q2 = q2_r["motivo_error"]
    motivo_fallida_s = motivo_q1.where(fallida_q1, motivo_q2)
    motivo_faltante_s = motivo_q2.where(motivo_q2.notna(), motivo_q1)
    motivo_error = pd.Series(None, index=all_groups, dtype=object)
    motivo_error[any_fallida] = motivo_fallida_s[any_fallida]
    motivo_error[null_mask] = motivo_faltante_s[null_mask]

    # Construir índice de PeriodoMensual
    años = all_groups.get_level_values("_año")
    meses = all_groups.get_level_values("_mes")
    indices = all_groups.get_level_values("_indice")
    periodos_mensuales = [PeriodoMensual(int(a), int(m)) for a, m in zip(años, meses)]

    df_result = pd.DataFrame(
        {
            "version": version.values,
            "tipo": tipo.values,
            "indice_replicado": indice_replicado.values,
            "estado_calculo": estado_calculo.values,
            "motivo_error": motivo_error.values,
        },
        index=pd.MultiIndex.from_arrays([periodos_mensuales, indices], names=["periodo", "indice"]),
    )

    df_result.sort_index(level="periodo", sort_remaining=False, inplace=True)
    return ResultadoCalculo(df_result, resultado.id_corrida)
