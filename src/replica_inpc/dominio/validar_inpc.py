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

_TOLERANCIAS: dict[int, float] = {2010: 0.0005, 2013: 0.0005, 2018: 0.0005, 2024: 0.005}


def validar(
    resultado: ResultadoCalculo,
    inegi: dict[Periodo, float | None],
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    id_corrida: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:

    indice = resultado.df.index.get_level_values("indice").unique()[0]
    tipo = resultado.df["tipo"].iloc[0]
    version = resultado.df["version"].iloc[0]
    tolerancia = _TOLERANCIAS[version]
    ponderadores = canasta.df["ponderador"].astype(float)
    total_genericos_esperados = len(canasta.df)
    ponderador_total_esperado = ponderadores.sum()

    periodos = resultado.df.index.get_level_values("periodo").unique()

    filas_reporte = []
    for periodo in periodos:
        estado_calculo = resultado.df.loc[(periodo, indice), "estado_calculo"]
        indice_replicado = resultado.df.loc[(periodo, indice), "indice_replicado"]
        motivo_error = resultado.df.loc[(periodo, indice), "motivo_error"]

        serie_col = serie.df[periodo]
        con_indice = serie_col.notna().sum()
        sin_indice = total_genericos_esperados - con_indice
        cobertura_genericos_pct = con_indice / total_genericos_esperados * 100
        ponderador_total_cubierto = ponderadores[serie_col.notna()].sum()

        indice_inegi = float("nan")
        error_absoluto = float("nan")
        error_relativo = float("nan")
        estado_validacion = "no_disponible"

        if inegi and periodo in inegi:
            indice_inegi = inegi[periodo]
            if indice_inegi is not None and estado_calculo == "ok":
                error_absoluto = abs(indice_replicado - indice_inegi)  # type: ignore[operator]
                error_relativo = error_absoluto / abs(indice_inegi)

                if error_absoluto <= tolerancia:
                    estado_validacion = "ok"
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

    index_reporte = pd.MultiIndex.from_tuples(
        [(p, indice) for p in periodos],
        names=["periodo", "indice"],
    )
    df_reporte = pd.DataFrame(filas_reporte, index=index_reporte)

    filas_diagnostico = []
    for generico in canasta.df.index:
        serie_generico = serie.df.loc[generico]
        periodos_null = [p for p in serie.df.columns if pd.isna(serie_generico[p])]

        if not periodos_null:
            continue

        nivel = (
            "estructural" if len(periodos_null) == len(serie.df.columns) else "periodo"
        )

        for p in periodos_null:
            filas_diagnostico.append(
                {
                    "id_corrida": id_corrida,
                    "version": version,
                    "tipo": tipo,
                    "periodo": p,
                    "generico": generico,
                    "nivel_faltante": nivel,
                    "tipo_faltante": "indice",
                    "detalle": f"Sin dato de indice para generico {generico} en {p}",
                }
            )

    if filas_diagnostico:
        df_diagnostico = pd.DataFrame(filas_diagnostico)
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

    numero_null = (resultado.df["estado_calculo"] == "null_por_faltantes").sum()
    numero_total = len(resultado.df)

    if numero_null == 0:
        estado_corrida = "ok"
    elif numero_null == numero_total:
        estado_corrida = "fallida"
    else:
        estado_corrida = "parcial"

    estados = set(df_reporte["estado_validacion"])

    if "diferencia_detectada" in estados:
        estado_validacion_global = "diferencia_detectada"
    elif estados == {"no_disponible"}:
        estado_validacion_global = "no_disponible"
    else:
        estado_validacion_global = "ok"

    df_resumen = pd.DataFrame(
        {
            "version": version,
            "tipo": tipo,
            "total_periodos_esperados": numero_total,
            "total_periodos_calculados": numero_total,
            "total_periodos_con_null": numero_null,
            "error_absoluto_max": df_reporte["error_absoluto"].max()
            if "error_absoluto" in df_reporte
            else float("nan"),
            "error_relativo_max": df_reporte["error_relativo"].max()
            if "error_relativo" in df_reporte
            else float("nan"),
            "total_faltantes_indice": len(df_diagnostico),
            "total_faltantes_ponderador": 0,
            "estado_validacion_global": estado_validacion_global,
            "estado_corrida": estado_corrida,
        },
        index=[id_corrida],
    )

    return (
        ResumenValidacion(df_resumen),
        ReporteDetalladoValidacion(df_reporte, id_corrida),
        DiagnosticoFaltantes(df_diagnostico),
    )
