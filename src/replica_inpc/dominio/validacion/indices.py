"""`validar_indices` — compara un `ResultadoIndice` contra series INEGI."""

from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import ValidacionIndice
from replica_inpc.dominio.tipos import TIPOS_CON_VALIDACION
from replica_inpc.dominio.validacion._comun import clasificar, contar, rollup_global

_COLS_DIAGNOSTICO = [
    "id_corrida",
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
    fuente: FuenteValidacion,
    tolerancia: float = 0.0009,
) -> ValidacionIndice:
    """Compara los índices replicados contra los publicados por INEGI."""
    invalidos = {m.tipo for m in resultado.manifiesto} - TIPOS_CON_VALIDACION
    if invalidos:
        raise InvarianteViolado(
            f"validar_indices: tipo(s) {sorted(invalidos)} fuera de "
            f"TIPOS_CON_VALIDACION."
        )

    largo = resultado.resultado.largo
    periodos = list(dict.fromkeys(largo.index.get_level_values("periodo")))
    inegi = fuente.obtener_indices(periodos)

    estados: list[str] = []
    valores_inegi: list[float] = []
    errores: list[float] = []
    for (periodo, indice), fila in largo.iterrows():  # type: ignore[misc]
        estado, valor_inegi, error = clasificar(
            fila["indice_replicado"],
            inegi.get(indice),  # type: ignore[has-type]
            periodo,  # type: ignore[has-type]
            fila["estado_calculo"],
            tolerancia,
            admite_sin_calculo=True,
        )
        estados.append(estado)
        valores_inegi.append(valor_inegi)
        errores.append(error)

    largo_val = largo.copy()
    largo_val["indice_inegi"] = valores_inegi
    largo_val["error_absoluto"] = errores
    largo_val["estado_validacion"] = estados

    reporte = resultado.reporte.copy()
    reporte["indice_replicado"] = largo["indice_replicado"].reindex(reporte.index)
    for col in ("indice_inegi", "error_absoluto", "estado_validacion"):
        reporte[col] = largo_val[col].reindex(reporte.index)

    diagnostico = _construir_diagnostico(largo_val, resultado)
    resumen = _construir_resumen(largo_val, resultado)
    return ValidacionIndice(resultado, largo_val, resumen, reporte, diagnostico)


def _construir_diagnostico(
    largo_val: pd.DataFrame, resultado: ResultadoIndice
) -> pd.DataFrame:
    id_por_unidad = {
        (m.version, m.tipo): m.id_corrida for m in resultado.manifiesto
    }
    filas = largo_val[largo_val["estado_validacion"] != "ok"].reset_index()
    if filas.empty:
        return pd.DataFrame(columns=_COLS_DIAGNOSTICO)
    filas["id_corrida"] = [
        id_por_unidad.get((version, tipo), "")
        for version, tipo in zip(filas["version"], filas["tipo"])
    ]
    return filas[_COLS_DIAGNOSTICO].reset_index(drop=True)


def _construir_resumen(
    largo_val: pd.DataFrame, resultado: ResultadoIndice
) -> pd.DataFrame:
    base = resultado.resumen
    filas = []
    for id_corrida, fila in base.iterrows():
        mascara = (largo_val["version"] == fila["version"]) & (
            largo_val["tipo"] == fila["tipo"]
        )
        sub = largo_val[mascara]
        conteos = contar(sub["estado_validacion"])
        comparables = conteos["n_comparables"]
        error_max = (
            float(sub["error_absoluto"].max()) if comparables > 0 else float("nan")
        )
        filas.append(
            {
                "id_corrida": id_corrida,
                "version": fila["version"],
                "tipo": fila["tipo"],
                "estado_calculo": fila["estado_calculo"],
                "periodo_inicio": fila["periodo_inicio"],
                "periodo_fin": fila["periodo_fin"],
                **conteos,
                "error_absoluto_max": error_max,
                "estado_validacion_global": rollup_global(sub["estado_validacion"]),
            }
        )
    return pd.DataFrame(filas).set_index("id_corrida")
