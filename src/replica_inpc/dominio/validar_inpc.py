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

_TOLERANCIAS: dict[int, float] = {2010: 0.0005, 2013: 0.0005, 2018: 0.0009, 2024: 0.005}


def validar(
    resultado: ResultadoCalculo,
    inegi: dict[str, dict[Periodo, float | None]],
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    id_corrida: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:

    tipo = resultado.df["tipo"].iloc[0]
    version = resultado.df["version"].iloc[0]
    con_validacion = tipo in TIPOS_CON_VALIDACION
    tolerancia = _TOLERANCIAS[version]
    ponderadores_full = canasta.df["ponderador"].astype(float)

    indices = resultado.df.index.get_level_values("indice").unique()
    periodos = resultado.df.index.get_level_values("periodo").unique()

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

        for periodo in periodos:
            estado_calculo = resultado.df.loc[(periodo, indice), "estado_calculo"]
            indice_replicado = resultado.df.loc[(periodo, indice), "indice_replicado"]
            motivo_error = resultado.df.loc[(periodo, indice), "motivo_error"]

            serie_col = serie.df[periodo]
            serie_grupo = serie_col[ponderadores.index]
            con_indice = serie_grupo.notna().sum()
            sin_indice = total_genericos_esperados - con_indice
            cobertura_genericos_pct = con_indice / total_genericos_esperados * 100
            ponderador_total_cubierto = ponderadores[serie_grupo.notna()].sum()

            if con_validacion:
                indice_inegi = float("nan")
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
        estados = set(
            df_reporte.loc[df_reporte["estado_calculo"] == "ok", "estado_validacion"]
        )

        if not estados:
            estado_validacion_global = "no_disponible"
        elif "diferencia_detectada" in estados:
            estado_validacion_global = "diferencia_detectada"
        elif estados == {"no_disponible"}:
            estado_validacion_global = "no_disponible"
        elif "no_disponible" in estados:
            estado_validacion_global = "ok_parcial"
        else:
            estado_validacion_global = "ok"

        resumen_base["error_absoluto_max"] = (
            df_reporte["error_absoluto"].max()
            if "error_absoluto" in df_reporte
            else float("nan")
        )
        resumen_base["error_relativo_max"] = (
            df_reporte["error_relativo"].max()
            if "error_relativo" in df_reporte
            else float("nan")
        )
        resumen_base["estado_validacion_global"] = estado_validacion_global

    df_resumen = pd.DataFrame(resumen_base, index=[id_corrida])

    return (
        ResumenValidacion(df_resumen),
        ReporteDetalladoValidacion(df_reporte, id_corrida),
        DiagnosticoFaltantes(df_diagnostico),
    )
