"""`validar_variaciones` — compara un `ResultadoVariacion` contra series INEGI."""

from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.modelos.validacion import ValidacionVariacion
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.tipos import TIPOS_CON_VALIDACION
from replica_inpc.dominio.validacion._comun import clasificar, contar, rollup_global

# clase_variacion → tipo_variacion del puerto FuenteValidacion.
_MAPA_TIPO_VARIACION: dict[str, str] = {
    "periodica_quincenal": "periodica",
    "periodica_mensual": "periodica",
    "periodica_anual": "interanual",
    "acumulada_anual": "acumulada_anual",
}

_COLS_DIAGNOSTICO = [
    "tipo",
    "clase_variacion",
    "periodo",
    "indice",
    "version_t",
    "estado_validacion",
    "estado_calculo",
    "variacion_pp",
    "variacion_inegi_pp",
    "error_absoluto_pp",
]


def _tipo_variacion(clase: str) -> str:
    if clase not in _MAPA_TIPO_VARIACION:
        raise ErrorConfiguracion(
            f"clase_variacion '{clase}' no es comparable contra INEGI; "
            f"INEGI no publica esa variación."
        )
    return _MAPA_TIPO_VARIACION[clase]


def validar_variaciones(
    resultado: ResultadoVariacion,
    fuente: FuenteValidacion,
    tolerancia_pp: float = 0.009,
) -> ValidacionVariacion:
    """Compara las variaciones replicadas contra las publicadas por INEGI."""
    if resultado.manifiesto.tipo not in TIPOS_CON_VALIDACION:
        raise InvarianteViolado(
            f"validar_variaciones: tipo '{resultado.manifiesto.tipo}' fuera de "
            f"TIPOS_CON_VALIDACION."
        )
    tipo_variacion = _tipo_variacion(resultado.manifiesto.clase)

    largo = resultado.resultado.largo
    # El .reporte heredado incluye filas no computables ausentes del largo;
    # se clasifica sobre el reporte completo (admite_sin_calculo=True).
    reporte_base = resultado.reporte
    periodos = list(dict.fromkeys(reporte_base.index.get_level_values("periodo")))
    inegi = fuente.obtener_variaciones(periodos, tipo_variacion)  # type: ignore[arg-type]

    var_pp = largo["variacion_pp"].reindex(reporte_base.index)
    estados: list[str] = []
    valores_inegi: list[float] = []
    errores: list[float] = []
    for ((periodo, indice), fila), valor_rep in zip(
        reporte_base.iterrows(), var_pp.to_numpy()
    ):
        estado, valor_inegi, error = clasificar(
            valor_rep,
            inegi.get(indice),
            periodo,
            fila["estado_calculo"],
            tolerancia_pp,
            admite_sin_calculo=True,
        )
        estados.append(estado)
        valores_inegi.append(valor_inegi)
        errores.append(error)

    reporte = reporte_base.copy()
    reporte["variacion_pp"] = var_pp
    reporte["variacion_inegi_pp"] = valores_inegi
    reporte["error_absoluto_pp"] = errores
    reporte["estado_validacion"] = estados

    largo_val = largo.copy()
    for col in ("variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"):
        largo_val[col] = reporte[col].reindex(largo.index)

    diagnostico = _construir_diagnostico(reporte, resultado)
    resumen = _construir_resumen(largo_val, resultado)
    return ValidacionVariacion(resultado, largo_val, resumen, reporte, diagnostico)


def _construir_diagnostico(
    reporte: pd.DataFrame, resultado: ResultadoVariacion
) -> pd.DataFrame:
    filas = reporte[reporte["estado_validacion"] != "ok"].reset_index()
    if filas.empty:
        return pd.DataFrame(columns=_COLS_DIAGNOSTICO)
    filas["tipo"] = resultado.manifiesto.tipo
    filas["clase_variacion"] = resultado.manifiesto.clase
    return filas[_COLS_DIAGNOSTICO].reset_index(drop=True)


def _construir_resumen(
    largo_val: pd.DataFrame, resultado: ResultadoVariacion
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
        "clase_variacion": base["clase_variacion"],
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
