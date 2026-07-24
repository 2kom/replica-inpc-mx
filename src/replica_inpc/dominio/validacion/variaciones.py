"""`validar_variaciones` — compara un `ResultadoVariacion` contra series INEGI."""

from __future__ import annotations

import numpy as np
import pandas as pd

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.modelos.validacion import ValidacionVariacion
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.tipos import INDICES_VALIDABLES
from replica_inpc.dominio.validacion._comun import contar, rollup_global

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
    if resultado.manifiesto.tipo not in INDICES_VALIDABLES:
        raise InvarianteViolado(
            f"validar_variaciones: tipo '{resultado.manifiesto.tipo}' fuera de "
            f"INDICES_VALIDABLES."
        )
    tipo_variacion = _tipo_variacion(resultado.manifiesto.clase)

    largo = resultado.resultado.largo
    # El .reporte heredado incluye filas no computables ausentes del largo;
    # se clasifica sobre el reporte completo (admite_sin_calculo=True).
    reporte_base = resultado.reporte
    periodos = list(dict.fromkeys(reporte_base.index.get_level_values("periodo")))
    inegi = fuente.obtener_variaciones(periodos, tipo_variacion)  # type: ignore[arg-type]

    var_pp = largo["variacion_pp"].reindex(reporte_base.index)

    indices_lvl = reporte_base.index.get_level_values("indice")
    periodos_lvl = reporte_base.index.get_level_values("periodo")

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

    replicado_arr = var_pp.to_numpy(dtype=float)
    estado_calc = reporte_base["estado_calculo"].to_numpy()
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
                    error_arr <= tolerancia_pp,
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

    reporte = reporte_base.copy()
    reporte["variacion_pp"] = var_pp
    reporte["variacion_inegi_pp"] = np.where(tiene_valor, valor_inegi_arr, float("nan"))
    reporte["error_absoluto_pp"] = np.where(
        tiene_valor & ~sin_calculo_mask, error_arr, float("nan")
    )
    reporte["estado_validacion"] = estado_arr

    largo_val = largo.copy()
    for col in ("variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"):
        largo_val[col] = reporte[col].reindex(largo.index)

    diagnostico = _construir_diagnostico(reporte, resultado)
    resumen = _construir_resumen(largo_val, resultado)
    return ValidacionVariacion(resultado, largo_val, resumen, reporte, diagnostico)


def _construir_diagnostico(reporte: pd.DataFrame, resultado: ResultadoVariacion) -> pd.DataFrame:
    filas = reporte[reporte["estado_validacion"] != "ok"].reset_index()
    if filas.empty:
        return pd.DataFrame(columns=_COLS_DIAGNOSTICO)
    filas["tipo"] = resultado.manifiesto.tipo
    filas["clase_variacion"] = resultado.manifiesto.clase
    return filas[_COLS_DIAGNOSTICO].reset_index(drop=True)


def _construir_resumen(largo_val: pd.DataFrame, resultado: ResultadoVariacion) -> pd.DataFrame:
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
