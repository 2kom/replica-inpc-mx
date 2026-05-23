"""`validar_incidencias` — compara un `ResultadoIncidencia` contra series INEGI."""

from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.validacion import ValidacionIncidencia
from replica_inpc.dominio.tipos import TIPOS_CON_VALIDACION
from replica_inpc.dominio.validacion._comun import clasificar, contar, rollup_global

# clase_incidencia → tipo_incidencia del puerto FuenteValidacion.
_MAPA_TIPO_INCIDENCIA: dict[str, str] = {"periodica_mensual": "periodica"}

_COLS_DIAGNOSTICO = [
    "tipo",
    "clase_incidencia",
    "periodo",
    "indice",
    "version_t",
    "estado_validacion",
    "estado_calculo",
    "incidencia_pp",
    "incidencia_inegi_pp",
    "error_absoluto_pp",
]


def _tipo_incidencia(clase: str) -> str:
    if clase not in _MAPA_TIPO_INCIDENCIA:
        raise ErrorConfiguracion(
            f"clase_incidencia '{clase}' no es comparable contra INEGI; "
            f"INEGI solo publica incidencias periódicas mensuales."
        )
    return _MAPA_TIPO_INCIDENCIA[clase]


def validar_incidencias(
    resultado: ResultadoIncidencia,
    fuente: FuenteValidacion,
    tolerancia_pp: float = 0.009,
) -> ValidacionIncidencia:
    """Compara las incidencias replicadas contra las publicadas por INEGI."""
    if resultado.manifiesto.tipo not in TIPOS_CON_VALIDACION:
        raise InvarianteViolado(
            f"validar_incidencias: tipo '{resultado.manifiesto.tipo}' fuera de "
            f"TIPOS_CON_VALIDACION."
        )
    tipo_incidencia = _tipo_incidencia(resultado.manifiesto.clase)

    largo = resultado.resultado.largo
    # El .reporte heredado incluye filas no computables ausentes del largo;
    # se clasifica sobre el reporte completo (admite_sin_calculo=True).
    reporte_base = resultado.reporte
    periodos = list(dict.fromkeys(reporte_base.index.get_level_values("periodo")))
    inegi = fuente.obtener_incidencias(periodos, tipo_incidencia)  # type: ignore[arg-type]

    inc_pp = largo["incidencia_pp"].reindex(reporte_base.index)
    estados: list[str] = []
    valores_inegi: list[float] = []
    errores: list[float] = []
    for ((periodo, indice), fila), valor_rep in zip(  # type: ignore[misc]
        reporte_base.iterrows(), inc_pp.to_numpy()
    ):
        estado, valor_inegi, error = clasificar(
            valor_rep,
            inegi.get(indice),  # type: ignore[arg-type, has-type]
            periodo,  # type: ignore[has-type]
            fila["estado_calculo"],
            tolerancia_pp,
            admite_sin_calculo=True,
        )
        estados.append(estado)
        valores_inegi.append(valor_inegi)
        errores.append(error)

    reporte = reporte_base.copy()
    reporte["incidencia_pp"] = inc_pp
    reporte["incidencia_inegi_pp"] = valores_inegi
    reporte["error_absoluto_pp"] = errores
    reporte["estado_validacion"] = estados

    largo_val = largo.copy()
    for col in ("incidencia_inegi_pp", "error_absoluto_pp", "estado_validacion"):
        largo_val[col] = reporte[col].reindex(largo.index)

    diagnostico = _construir_diagnostico(reporte, resultado)
    resumen = _construir_resumen(largo_val, resultado)
    return ValidacionIncidencia(resultado, largo_val, resumen, reporte, diagnostico)


def _construir_diagnostico(
    reporte: pd.DataFrame, resultado: ResultadoIncidencia
) -> pd.DataFrame:
    filas = reporte[reporte["estado_validacion"] != "ok"].reset_index()
    if filas.empty:
        return pd.DataFrame(columns=_COLS_DIAGNOSTICO)
    filas["tipo"] = resultado.manifiesto.tipo
    filas["clase_incidencia"] = resultado.manifiesto.clase
    return filas[_COLS_DIAGNOSTICO].reset_index(drop=True)


def _construir_resumen(
    largo_val: pd.DataFrame, resultado: ResultadoIncidencia
) -> pd.DataFrame:
    base = resultado.resumen.iloc[0]
    conteos = contar(largo_val["estado_validacion"])
    error_max = (
        float(largo_val["error_absoluto_pp"].max())
        if conteos["n_comparables"] > 0
        else float("nan")
    )
    fila = {
        "tipo": base["tipo"],
        "clase_incidencia": base["clase_incidencia"],
        "descripcion": base["descripcion"],
        "estado_calculo": base["estado_calculo"],
        "periodo_inicio": base["periodo_inicio"],
        "periodo_fin": base["periodo_fin"],
        "n_comparables": conteos["n_comparables"],
        "n_fuera_rango_inegi": conteos["n_fuera_rango_inegi"],
        "n_no_disponibles": conteos["n_no_disponibles"],
        "n_diferencia_por_parcial": conteos["n_diferencia_por_parcial"],
        "error_absoluto_max_pp": error_max,
        "estado_validacion_global": rollup_global(largo_val["estado_validacion"]),
    }
    return pd.DataFrame([fila])
