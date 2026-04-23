from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.calculo._subindices import grupos_por_clasificacion
from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.errores import ErrorCalculo
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    RANGOS_VALIDOS,
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
        traslape = RANGOS_VALIDOS[version][0]
        if traslape not in df_serie.columns:
            raise ErrorCalculo(
                f"PeriodoQuincenal de traslape {traslape} no está en la serie "
                "y falta encadenamiento en canasta"
            )
        f_k_serie: pd.Series = df_serie[traslape] / 100
        f_k = enc_raw.astype(float)
        f_k = f_k.where(~necesita_fallback, f_k_serie)
    else:
        f_k = enc_raw.astype(float)

    return f_k


def _calcular_df(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    indice: str,
    tipo: str,
    version: VersionCanasta,
    f_h_override: float | None = None,
) -> pd.DataFrame:
    f_k = _obtener_f_k(df_canasta, df_serie, version)
    ponderadores = df_canasta["ponderador"].astype(float)

    periodos_null = df_serie.isnull().any(axis=0)

    df_raw = df_serie.divide(f_k, axis=0)
    resultado_raw = df_raw.multiply(ponderadores, axis=0).sum().divide(ponderadores.sum())
    f_h: float = (
        f_h_override
        if f_h_override is not None
        else float((ponderadores * f_k).sum() / ponderadores.sum())
    )
    resultado = resultado_raw * f_h

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
        df.loc[periodos_null_idx, "estado_calculo"] = "null_por_faltantes"
        df.loc[periodos_null_idx, "indice_replicado"] = None
        df.loc[periodos_null_idx, "motivo_error"] = "faltantes en serie"
    return df


class LaspeyresEncadenado(CalculadorBase):
    def __init__(self, f_h_por_indice: dict[str, float] | None = None) -> None:
        self._f_h = f_h_por_indice or {}

    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        tipo: str,
    ) -> ResultadoCalculo:

        if tipo in INDICE_POR_TIPO:
            indice = INDICE_POR_TIPO[tipo]
            df = _calcular_df(
                canasta.df, serie.df, indice, tipo, canasta.version, self._f_h.get(indice)
            )
            return ResultadoCalculo(df, id_corrida)

        assert tipo in COLUMNAS_CLASIFICACION
        dfs = [
            _calcular_df(df_c, df_s, cat, tipo, canasta.version, self._f_h.get(cat))
            for cat, df_c, df_s in grupos_por_clasificacion(canasta, serie, tipo)
        ]
        return ResultadoCalculo(pd.concat(dfs), id_corrida)
