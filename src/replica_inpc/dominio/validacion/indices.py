"""`validar_indices` — compara un `ResultadoIndice` contra series INEGI."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import ValidacionIndice
from replica_inpc.dominio.tipos import INDICES_VALIDABLES, VersionCanasta
from replica_inpc.dominio.validacion._comun import (
    PeriodoT,
    SeriesInegi,
    contar,
    rollup_global,
)

_COLS_DIAGNOSTICO = [
    "version",
    "tipo",
    "periodo",
    "indice",
    "estado_validacion",
    "estado_calculo",
    "indice_replicado",
    "indice_inegi",
    "error_absoluto",
]


def validar_indices(
    resultado: ResultadoIndice,
    inegi: SeriesInegi[PeriodoT],
    tolerancia: float = 0.0009,
) -> ValidacionIndice:
    """Compara los índices replicados contra los publicados por INEGI.

    Args:
        resultado: Índices replicados a validar.
        inegi: Series ya obtenidas de INEGI para los periodos de `resultado` —
            quien orquesta el I/O las resuelve antes de llamar (ver
            `aplicacion/casos_uso/validar_resultado.py`).
        tolerancia: Diferencia absoluta máxima para considerar una fila `ok`.
    """
    invalidos = {m.tipo for m in resultado.manifiesto} - INDICES_VALIDABLES
    if invalidos:
        raise InvarianteViolado(
            f"validar_indices: tipo(s) {sorted(invalidos)} fuera de INDICES_VALIDABLES."
        )

    largo = resultado.resultado.largo

    indices_lvl = largo.index.get_level_values("indice")
    periodos_lvl = largo.index.get_level_values("periodo")

    in_inegi = np.array(
        [idx in inegi and per in inegi[idx] for idx, per in zip(indices_lvl, periodos_lvl)],
        dtype=bool,
    )
    valor_inegi_arr = np.array(
        [
            (float(v) if (v := inegi[idx][per]) is not None else float("nan"))
            if in_inegi[i]
            else float("nan")
            for i, (idx, per) in enumerate(zip(indices_lvl, periodos_lvl))
        ],
        dtype=np.float64,
    )
    tiene_valor = in_inegi & ~np.isnan(valor_inegi_arr)

    replicado_arr = largo["indice_replicado"].to_numpy(dtype=float)
    estado_calc = largo["estado_calculo"].to_numpy()
    sin_calculo_mask = tiene_valor & np.isin(estado_calc, ["sin_datos", "fallida"])
    error_arr = np.abs(replicado_arr - valor_inegi_arr)

    estado_arr = np.where(
        ~in_inegi,
        "fuera_rango_inegi",
        np.where(
            ~tiene_valor,
            "no_disponible",
            np.where(
                sin_calculo_mask,
                "sin_calculo",
                np.where(
                    error_arr <= tolerancia,
                    "ok",
                    np.where(
                        estado_calc == "parcial",
                        "diferencia_por_parcial",
                        "diferencia_detectada",
                    ),
                ),
            ),
        ),
    )

    largo_val = largo.copy()
    largo_val["indice_inegi"] = np.where(tiene_valor, valor_inegi_arr, float("nan"))
    largo_val["error_absoluto"] = np.where(tiene_valor & ~sin_calculo_mask, error_arr, float("nan"))
    largo_val["estado_validacion"] = estado_arr

    reporte = resultado.reporte.copy()
    reporte["indice_replicado"] = largo["indice_replicado"].reindex(reporte.index)
    for col in ("indice_inegi", "error_absoluto", "estado_validacion"):
        reporte[col] = largo_val[col].reindex(reporte.index)

    diagnostico = _construir_diagnostico(largo_val)
    resumen = _construir_resumen(largo_val, resultado)
    return ValidacionIndice(resultado, largo_val, resumen, reporte, diagnostico)


def _construir_diagnostico(largo_val: pd.DataFrame) -> pd.DataFrame:
    filas = largo_val[largo_val["estado_validacion"] != "ok"].reset_index()
    if filas.empty:
        return pd.DataFrame(columns=_COLS_DIAGNOSTICO)
    return filas[_COLS_DIAGNOSTICO].reset_index(drop=True)


def _construir_resumen(largo_val: pd.DataFrame, resultado: ResultadoIndice) -> pd.DataFrame:
    base = resultado.resumen
    filas = []
    for idx, fila in base.iterrows():
        version_str, tipo = cast(str, idx).split(":", 1)
        version = cast(VersionCanasta, int(version_str))
        mascara = (largo_val["version"] == version) & (largo_val["tipo"] == tipo)
        sub = largo_val[mascara]
        conteos = contar(sub["estado_validacion"])
        comparables = conteos["n_comparables"]
        error_max = float(sub["error_absoluto"].max()) if comparables > 0 else float("nan")
        filas.append(
            {
                "version": version,
                "tipo": tipo,
                "estado_calculo": fila["estado_calculo"],
                "periodo_inicio": fila["periodo_inicio"],
                "periodo_fin": fila["periodo_fin"],
                **conteos,
                "error_absoluto_max": error_max,
                "estado_validacion_global": rollup_global(sub["estado_validacion"]),
            }
        )
    return pd.DataFrame(filas).set_index(["version", "tipo"])
