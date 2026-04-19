from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
    ResumenValidacion,
)
from replica_inpc.dominio.periodos import Periodo
from replica_inpc.dominio.tipos import COLUMNAS_CLASIFICACION, TIPOS_CON_VALIDACION

_TOLERANCIAS: dict[int, float] = {2010: 0.0005, 2013: 0.0005, 2018: 0.0009, 2024: 0.0009}


def validar(
    resultado: ResultadoCalculo,
    inegi: dict[str, dict[Periodo, float | None]],
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    id_corrida: str,
    imputados: dict[tuple[str, Periodo], Periodo] | None = None,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:

    tipo = resultado.df["tipo"].iloc[0]
    version = resultado.df["version"].iloc[0]
    con_validacion = tipo in TIPOS_CON_VALIDACION
    tolerancia = _TOLERANCIAS[version]
    ponderadores_full = canasta.df["ponderador"].astype(float)
    periodos_imputados = {p for _, p in imputados.keys()} if imputados else set()

    indices = resultado.df.index.get_level_values("indice").unique()
    periodos = resultado.df.index.get_level_values("periodo").unique()

    notna_df = ~serie.df.isna()
    res_lookup = resultado.df[["estado_calculo", "indice_replicado", "motivo_error"]].to_dict(
        "index"
    )

    filas_reporte = []
    for indice in indices:
        if tipo in COLUMNAS_CLASIFICACION:
            mascara = canasta.df[tipo] == indice
            ponderadores = ponderadores_full[mascara]
            total_genericos_esperados = int(mascara.sum())
        else:
            ponderadores = ponderadores_full
            total_genericos_esperados = len(canasta.df)

        ponderador_total_esperado = ponderadores.sum()
        inegi_indice = inegi.get(indice, {})

        notna_grupo = notna_df.loc[ponderadores.index]
        con_indice_serie = notna_grupo.sum()
        ponderador_cubierto_serie = notna_grupo.multiply(ponderadores, axis=0).sum()

        for periodo in periodos:
            row = res_lookup[(periodo, indice)]
            estado_calculo = row["estado_calculo"]
            indice_replicado = row["indice_replicado"]
            motivo_error = row["motivo_error"]

            con_indice = int(con_indice_serie[periodo])
            sin_indice = total_genericos_esperados - con_indice
            cobertura_genericos_pct = con_indice / total_genericos_esperados * 100
            ponderador_total_cubierto = float(ponderador_cubierto_serie[periodo])

            if con_validacion:
                indice_inegi: float | None = float("nan")
                error_absoluto = float("nan")
                error_relativo = float("nan")
                estado_validacion = "no_disponible"

                if inegi_indice and periodo in inegi_indice:
                    indice_inegi = inegi_indice[periodo]
                    if indice_inegi is not None and estado_calculo == "ok":
                        error_absoluto = abs(indice_replicado - indice_inegi)  # type: ignore[operator]
                        error_relativo = error_absoluto / abs(indice_inegi)

                        if error_absoluto <= tolerancia:
                            estado_validacion = "ok"
                        elif periodo in periodos_imputados:
                            estado_validacion = "diferencia_detectada_imputado"
                        else:
                            estado_validacion = "diferencia_detectada"

                filas_reporte.append(
                    {
                        "version": version,
                        "tipo": tipo,
                        "indice_replicado": indice_replicado,
                        "indice_inegi": indice_inegi,
                        "error_absoluto": error_absoluto,
                        "error_relativo": error_relativo,
                        "estado_calculo": estado_calculo,
                        "motivo_error": motivo_error,
                        "estado_validacion": estado_validacion,
                        "total_genericos_esperados": total_genericos_esperados,
                        "total_genericos_con_indice": con_indice,
                        "total_genericos_sin_indice": sin_indice,
                        "cobertura_genericos_pct": cobertura_genericos_pct,
                        "ponderador_total_esperado": ponderador_total_esperado,
                        "ponderador_total_cubierto": ponderador_total_cubierto,
                    }
                )
            else:
                filas_reporte.append(
                    {
                        "version": version,
                        "tipo": tipo,
                        "indice_replicado": indice_replicado,
                        "estado_calculo": estado_calculo,
                        "motivo_error": motivo_error,
                        "total_genericos_esperados": total_genericos_esperados,
                        "total_genericos_con_indice": con_indice,
                        "total_genericos_sin_indice": sin_indice,
                        "cobertura_genericos_pct": cobertura_genericos_pct,
                        "ponderador_total_esperado": ponderador_total_esperado,
                        "ponderador_total_cubierto": ponderador_total_cubierto,
                    }
                )

    index_reporte = pd.MultiIndex.from_tuples(
        [(p, ind) for ind in indices for p in periodos],
        names=["periodo", "indice"],
    )
    df_reporte = pd.DataFrame(filas_reporte, index=index_reporte)

    null_mask = serie.df.isna()
    null_counts = null_mask.sum(axis=1)
    total_periodos = len(serie.df.columns)
    null_stack = null_mask.stack()
    null_stack = null_stack[null_stack]  # type: ignore[index]

    if len(null_stack) > 0:
        genericos_arr = null_stack.index.get_level_values(0)
        periodos_arr = null_stack.index.get_level_values(1)
        counts = null_counts[genericos_arr].values
        nivel_arr = ["estructural" if c == total_periodos else "periodo" for c in counts]
        df_diagnostico = pd.DataFrame(
            {
                "id_corrida": id_corrida,
                "version": version,
                "tipo": tipo,
                "periodo": periodos_arr,
                "generico": genericos_arr,
                "nivel_faltante": nivel_arr,
                "tipo_faltante": "indice",
                "detalle": [
                    f"Sin dato de indice para generico {g} en {p}"
                    for g, p in zip(genericos_arr, periodos_arr)
                ],
            }
        )
    else:
        df_diagnostico = pd.DataFrame(
            columns=[
                "id_corrida",
                "version",
                "tipo",
                "periodo",
                "generico",
                "nivel_faltante",
                "tipo_faltante",
                "detalle",
            ]
        )

    if imputados:
        filas_imp = pd.DataFrame(
            [
                {
                    "id_corrida": id_corrida,
                    "version": version,
                    "tipo": tipo,
                    "periodo": periodo,
                    "generico": generico,
                    "nivel_faltante": "periodo",
                    "tipo_faltante": "indice_imputado",
                    "detalle": f"imputado desde {fuente}",
                }
                for (generico, periodo), fuente in imputados.items()
            ]
        )
        df_diagnostico = pd.concat([df_diagnostico, filas_imp], ignore_index=True)

    numero_null = (resultado.df["estado_calculo"] == "null_por_faltantes").sum()
    numero_total = len(resultado.df)

    if numero_null == 0:
        estado_corrida = "ok"
    elif numero_null == numero_total:
        estado_corrida = "fallida"
    else:
        estado_corrida = "ok_parcial"

    resumen_base: dict = {
        "version": version,
        "tipo": tipo,
        "periodo_inicio": min(periodos),
        "periodo_fin": max(periodos),
        "total_periodos_esperados": numero_total,
        "total_periodos_calculados": numero_total,
        "total_periodos_con_null": numero_null,
        "total_faltantes_indice": len(df_diagnostico),
        "total_faltantes_ponderador": 0,
        "estado_corrida": estado_corrida,
    }

    if con_validacion:
        estados = set(df_reporte.loc[df_reporte["estado_calculo"] == "ok", "estado_validacion"])

        if not estados:
            estado_validacion_global = "no_disponible"
        elif "diferencia_detectada" in estados:
            estado_validacion_global = "diferencia_detectada"
        elif estados == {"no_disponible"}:
            estado_validacion_global = "no_disponible"
        elif "no_disponible" in estados:
            estado_validacion_global = "ok_parcial"
        elif "diferencia_detectada_imputado" in estados and estados <= {
            "ok",
            "diferencia_detectada_imputado",
        }:
            estado_validacion_global = "ok_parcial"
        else:
            estado_validacion_global = "ok"

        resumen_base["error_absoluto_max"] = (
            df_reporte["error_absoluto"].max() if "error_absoluto" in df_reporte else float("nan")
        )
        resumen_base["error_relativo_max"] = (
            df_reporte["error_relativo"].max() if "error_relativo" in df_reporte else float("nan")
        )
        resumen_base["estado_validacion_global"] = estado_validacion_global

    df_resumen = pd.DataFrame(resumen_base, index=[id_corrida])

    return (
        ResumenValidacion(df_resumen),
        ReporteDetalladoValidacion(df_reporte, id_corrida),
        DiagnosticoFaltantes(df_diagnostico),
    )
