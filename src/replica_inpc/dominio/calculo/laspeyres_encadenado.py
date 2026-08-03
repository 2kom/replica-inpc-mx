from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.calculo.base import (
    CalculadorBase,
    _construir_diagnostico,
    _promedio_ponderado_por_grupo,
    _recortar_series_fecha,
    _rellenar_dato_serie_faltante,
)
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    RANGOS_CANASTAS,
    TIPO_INPC,
    ManifestCalculo,
    VersionCanasta,
)


def _obtener_f_k(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    version: VersionCanasta,
) -> pd.Series:
    enc_raw = df_canasta["encadenamiento"]
    necesita_fallback = enc_raw.isna()

    if necesita_fallback.any():
        traslape = RANGOS_CANASTAS[version][0]
        if traslape not in df_serie.columns:
            raise ErrorCalculo(
                f"PeriodoQuincenal de traslape {traslape} no está en la serie "
                "y falta encadenamiento en canasta"
            )
        f_k_serie: pd.Series = df_serie[cast(Any, traslape)] / 100
        f_k = enc_raw.astype(float)
        f_k = f_k.where(~necesita_fallback, f_k_serie)
    else:
        f_k = enc_raw.astype(float)

    return f_k


class _LaspeyresEncadenadoBase(CalculadorBase):
    _VERSION_ESPERADA: VersionCanasta
    _CALCULADOR_NOMBRE: Literal["LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]

    def __init__(self, referencia_empalme_por_indice: dict[str, float] | None = None) -> None:
        self._referencia_empalme = referencia_empalme_por_indice or {}

    def _factor_h_para_cats(
        self,
        i_tramo_mat: pd.DataFrame,
        f_k: pd.Series,
        cat_por_gen: pd.Series,
        pond: pd.Series,
    ) -> pd.Series:
        raise NotImplementedError

    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        tipo: str,
    ) -> ResultadoIndice:

        fecha = datetime.now()
        ruta_canasta = canasta.df.attrs.get("origen")
        ruta_serie = serie.df.attrs.get("origen")

        if canasta.version != self._VERSION_ESPERADA:
            raise InvarianteViolado(
                f"{self._CALCULADOR_NOMBRE} requiere canasta.version="
                f"{self._VERSION_ESPERADA}; recibió {canasta.version}"
            )
        if tipo != TIPO_INPC and tipo not in COLUMNAS_CLASIFICACION:
            raise InvarianteViolado(
                f"tipo='{tipo}' no es '{TIPO_INPC}' ni está en COLUMNAS_CLASIFICACION"
            )
        if tipo in COLUMNAS_CLASIFICACION and canasta.df[tipo].dropna().empty:
            raise InvarianteViolado(
                f"La canasta versión {canasta.version} no tiene datos en '{tipo}'. "
                "Revisa tools/canasta_inpc/esquema.py::FUENTES_POSIBLES para qué "
                "clasificaciones aplican a cada versión (docs/diseño.md §5.4)."
            )

        # tipo==TIPO_INPC: c = 1 solo grupo constante (INPC). Clasificación:
        # c = categoría (dropna excluye genéricos sin valor en esa columna).
        if tipo == TIPO_INPC:
            cat_por_gen = pd.Series(TIPO_INPC, index=canasta.df.index)
        else:
            cat_por_gen = canasta.df[tipo].dropna()
        gens = cat_por_gen.index

        df_s_raw = _recortar_series_fecha(serie.df.loc[gens], canasta.version)
        df_s, df_corr_relleno, _ = _rellenar_dato_serie_faltante(df_s_raw, canasta.version, tipo)
        pond = canasta.df.loc[gens, "ponderador"].astype(float)
        f_k = _obtener_f_k(canasta.df.loc[gens], df_s, canasta.version)

        # i_tramo por grupo: media ponderada de (serie / f_k), de-encadenada
        df_base = df_s.divide(f_k, axis=0)
        i_tramo_mat = _promedio_ponderado_por_grupo(df_base, pond, cat_por_gen)

        factor_h = self._factor_h_para_cats(i_tramo_mat, f_k, cat_por_gen, pond)
        resultado_mat = i_tramo_mat.multiply(factor_h, axis=0)

        has_null = df_s.isna().groupby(cat_por_gen).any()
        has_rel = (df_s_raw.isna() & df_s.notna()).groupby(cat_por_gen).any()

        df_stacked = resultado_mat.T.stack()
        df_stacked.index = df_stacked.index.set_names(["periodo", "indice"])
        idx = df_stacked.index

        null_flat = has_null.T.stack().reindex(idx).fillna(False)
        rel_flat = has_rel.T.stack().reindex(idx).fillna(False)

        null_bool = null_flat.to_numpy(dtype=bool)
        rel_bool = rel_flat.to_numpy(dtype=bool)
        estado_arr = np.where(
            null_bool,
            "sin_datos",
            np.where(rel_bool & ~null_bool, "rellenado", "ok"),
        )
        motivo_arr = np.where(null_bool, "faltantes en serie", None)  # type: ignore[call-overload]

        df_calc = pd.DataFrame(
            {
                "version": canasta.version,
                "tipo": tipo,
                "indice_replicado": df_stacked.where(~null_bool).values,
                "indice_incidencia": i_tramo_mat.T.stack().where(~null_bool).values,
                "estado_calculo": estado_arr,
                "motivo_error": motivo_arr,
            },
            index=idx,
        )

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
                _construir_diagnostico(df_s, canasta.version, tipo),
                df_corr_relleno,
            ],
            ignore_index=True,
        )

        manifiesto = ManifestCalculo(
            version=canasta.version,
            tipo=tipo,
            calculador=self._CALCULADOR_NOMBRE,
            ruta_canasta=ruta_canasta,
            ruta_series=ruta_serie,
            fecha=fecha,
        )
        return ResultadoIndice(df_calc, [manifiesto], df_reporte, df_diag)


class LaspeyresEncadenadoT1(_LaspeyresEncadenadoBase):
    _VERSION_ESPERADA = 2013
    _CALCULADOR_NOMBRE = "LaspeyresEncadenadoT1"

    def _factor_h_para_cats(
        self,
        i_tramo_mat: pd.DataFrame,
        f_k: pd.Series,
        cat_por_gen: pd.Series,
        pond: pd.Series,
    ) -> pd.Series:
        factor_h = pd.Series(1.0, index=i_tramo_mat.index)
        cats_ref = [c for c in i_tramo_mat.index if c in self._referencia_empalme]
        if cats_ref:
            traslape = RANGOS_CANASTAS[2013][0]
            if traslape not in i_tramo_mat.columns:
                raise ErrorCalculo(f"PeriodoQuincenal de traslape {traslape} no está en la serie.")
            denominador = i_tramo_mat.loc[cats_ref, cast(Any, traslape)].astype(float)
            refs_s = pd.Series({c: self._referencia_empalme[c] for c in cats_ref})
            grupos_invalidos = denominador[
                ~np.isfinite(denominador) | (denominador == 0) | ~np.isfinite(refs_s)
            ].index.tolist()
            if grupos_invalidos:
                raise ErrorCalculo(
                    f"No se puede encadenar {grupos_invalidos} en el periodo de traslape "
                    f"{traslape}: i_tramo o referencia de empalme no válidos (cero o no finito)."
                )
            factor_h.loc[cats_ref] = refs_s.to_numpy(dtype=float) / denominador.to_numpy()
        return factor_h


class LaspeyresEncadenadoT2(_LaspeyresEncadenadoBase):
    _VERSION_ESPERADA = 2024
    _CALCULADOR_NOMBRE = "LaspeyresEncadenadoT2"

    def _factor_h_para_cats(
        self,
        i_tramo_mat: pd.DataFrame,
        f_k: pd.Series,
        cat_por_gen: pd.Series,
        pond: pd.Series,
    ) -> pd.Series:
        _ = i_tramo_mat
        pond_fk_sum = (pond * f_k).groupby(cat_por_gen).sum()
        factor_h = pond_fk_sum / pond.groupby(cat_por_gen).sum()
        cats_ref = [c for c in factor_h.index if c in self._referencia_empalme]
        if cats_ref:
            refs_s = pd.Series({c: self._referencia_empalme[c] / 100 for c in cats_ref})
            factor_h.loc[cats_ref] = refs_s
        return factor_h
