from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.calculo.base import (
    CalculadorBase,
    _construir_diagnostico,
    _construir_reporte,
    _recortar_al_rango,
    _rellenar_faltantes,
)
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    RANGOS_VALIDOS,
    ManifestUnidad,
    VersionCanasta,
)


def _calcular_df(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    indice: str,
    tipo: str,
    version: VersionCanasta,
    periodos_rellenados: set[object] | None = None,
    referencia_empalme: float | None = None,
) -> pd.DataFrame:
    if periodos_rellenados is None:
        periodos_rellenados = set()
    periodos_null = df_serie.isnull().any(axis=0)
    ponderadores = df_canasta["ponderador"].astype(float)
    resultado = df_serie.multiply(ponderadores, axis=0).sum().divide(ponderadores.sum())
    if referencia_empalme is not None:
        traslape = RANGOS_VALIDOS[version][0]
        if traslape not in resultado.index:
            raise ErrorCalculo(f"PeriodoQuincenal de traslape {traslape} no está en la serie.")
        factor_h = referencia_empalme / float(resultado[traslape])
        resultado = resultado * factor_h

    idx = pd.MultiIndex.from_tuples(
        [(p, indice) for p in resultado.index],
        names=["periodo", "indice"],
    )
    df = pd.DataFrame(
        {
            "version": version,
            "tipo": tipo,
            "indice_replicado": resultado.values,
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    periodos_null_idx = [(p, indice) for p in resultado.index[periodos_null]]
    if periodos_null_idx:
        df.loc[periodos_null_idx, "estado_calculo"] = "sin_datos"
        df.loc[periodos_null_idx, "indice_replicado"] = None
        df.loc[periodos_null_idx, "motivo_error"] = "faltantes en serie"
    periodos_null_set = {p for p, _ in periodos_null_idx}
    periodos_rel_idx = [
        (p, indice)
        for p in resultado.index
        if p in periodos_rellenados and p not in periodos_null_set
    ]
    if periodos_rel_idx:
        df.loc[periodos_rel_idx, "estado_calculo"] = "rellenado"
    return df


class LaspeyresDirecto(CalculadorBase):
    def __init__(self, referencia_empalme_por_indice: dict[str, float] | None = None) -> None:
        self._referencia_empalme = referencia_empalme_por_indice or {}

    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        tipo: str,
        ruta_canasta: Path | None = None,
        ruta_series: Path | None = None,
        fecha: datetime | None = None,
    ) -> ResultadoIndice:
        if tipo not in INDICE_POR_TIPO and tipo not in COLUMNAS_CLASIFICACION:
            raise InvarianteViolado(
                f"tipo='{tipo}' no está en INDICE_POR_TIPO ni en COLUMNAS_CLASIFICACION"
            )

        if tipo in INDICE_POR_TIPO:
            indice = INDICE_POR_TIPO[tipo]
            df_s_raw = _recortar_al_rango(serie.df, canasta.version)
            df_s, df_corr_relleno, periodos_rel = _rellenar_faltantes(
                df_s_raw, id_corrida, canasta.version, tipo
            )
            df_calc = _calcular_df(
                canasta.df,
                df_s,
                indice,
                tipo,
                canasta.version,
                periodos_rel,
                self._referencia_empalme.get(indice),
            )
            df_reporte = _construir_reporte(df_calc, canasta.df, df_s, canasta.version)
            df_diag = pd.concat(
                [
                    _construir_diagnostico(canasta.df, df_s, id_corrida, canasta.version, tipo),
                    df_corr_relleno,
                ],
                ignore_index=True,
            )
        else:
            # Vectorizado: un groupby reemplaza el loop por cada categoría SCIAN/CCIF.
            # El fill bfill→ffill opera por fila (genérico), independiente del grupo.
            cat_por_gen = canasta.df[tipo].dropna()
            gens = cat_por_gen.index

            df_s_raw = _recortar_al_rango(serie.df.loc[gens], canasta.version)
            df_s, df_corr_relleno, _ = _rellenar_faltantes(
                df_s_raw, id_corrida, canasta.version, tipo
            )
            pond = canasta.df.loc[gens, "ponderador"].astype(float)

            # Laspeyres: media ponderada por categoría
            weighted = df_s.multiply(pond, axis=0)
            pond_sum = weighted.groupby(cat_por_gen).sum()  # cat × periodo
            pond_total = pond.groupby(cat_por_gen).sum()  # cat
            resultado_mat = pond_sum.divide(pond_total, axis=0)  # cat × periodo

            # referencia_empalme por categoría (solo LaspeyresDirecto usado como T0 de encadenado)
            if self._referencia_empalme:
                traslape = RANGOS_VALIDOS[canasta.version][0]
                if traslape not in resultado_mat.columns:
                    raise ErrorCalculo(
                        f"PeriodoQuincenal de traslape {traslape} no está en la serie."
                    )
                cats_ref = [c for c in resultado_mat.index if c in self._referencia_empalme]
                if cats_ref:
                    refs_s = pd.Series({c: self._referencia_empalme[c] for c in cats_ref})
                    factor_h = refs_s / resultado_mat.loc[cats_ref, cast(Any, traslape)].astype(
                        float
                    )
                    resultado_mat.loc[cats_ref] = resultado_mat.loc[cats_ref].multiply(
                        factor_h, axis=0
                    )

            # Estado por (cat, periodo)
            has_null = df_s.isna().groupby(cat_por_gen).any()  # cat × bool
            has_rel = (df_s_raw.isna() & df_s.notna()).groupby(cat_por_gen).any()  # cat × bool

            # Reshape a MultiIndex (periodo, indice=cat)
            df_stacked = resultado_mat.T.stack()
            df_stacked.index = df_stacked.index.set_names(["periodo", "indice"])
            idx = df_stacked.index

            null_flat = has_null.T.stack().reindex(idx).fillna(False)
            rel_flat = has_rel.T.stack().reindex(idx).fillna(False)

            null_bool = null_flat.to_numpy(dtype=bool)
            rel_bool = rel_flat.to_numpy(dtype=bool)
            estado_arr = np.where(
                null_bool, "sin_datos", np.where(rel_bool & ~null_bool, "rellenado", "ok")
            )
            motivo_arr = np.where(null_bool, "faltantes en serie", None)  # type: ignore[call-overload]

            df_calc = pd.DataFrame(
                {
                    "version": canasta.version,
                    "tipo": tipo,
                    "indice_replicado": df_stacked.where(~null_bool).values,
                    "estado_calculo": estado_arr,
                    "motivo_error": motivo_arr,
                },
                index=idx,
            )

            # Reporte vectorizado para todos los grupos de una vez
            cubierto = df_s.notna()
            con_by_cat = cubierto.groupby(cat_por_gen).sum()
            pond_cub_by_cat = cubierto.multiply(pond, axis=0).groupby(cat_por_gen).sum()
            gen_esp_by_cat = cat_por_gen.groupby(cat_por_gen).size()
            pond_esp_by_cat = pond.groupby(cat_por_gen).sum()

            con_flat = con_by_cat.T.stack().reindex(idx).to_numpy()
            pond_cub_flat = pond_cub_by_cat.T.stack().reindex(idx).to_numpy()
            cats_col = idx.get_level_values("indice")
            gen_esp = gen_esp_by_cat.reindex(cats_col).to_numpy()
            pond_esp = pond_esp_by_cat.reindex(cats_col).to_numpy()

            df_reporte = pd.DataFrame(
                {
                    "version": canasta.version,
                    "estado_calculo": estado_arr,
                    "motivo_error": motivo_arr,
                    "genericos_esperados": gen_esp,
                    "genericos_con_indice": con_flat,
                    "genericos_sin_indice": gen_esp - con_flat,
                    "cobertura_genericos_pct": 100.0 * con_flat / gen_esp,
                    "ponderador_esperado": pond_esp,
                    "ponderador_cubierto": pond_cub_flat,
                },
                index=idx,
            )

            df_diag = pd.concat(
                [
                    _construir_diagnostico(canasta.df, df_s, id_corrida, canasta.version, tipo),
                    df_corr_relleno,
                ],
                ignore_index=True,
            )

        manifiesto = ManifestUnidad(
            id_corrida=id_corrida,
            version=canasta.version,
            tipo=tipo,
            calculador="LaspeyresDirecto",
            ruta_canasta=ruta_canasta,
            ruta_series=ruta_series,
            fecha=fecha if fecha is not None else datetime.now(),
        )
        return ResultadoIndice(df_calc, [manifiesto], df_reporte, df_diag)
