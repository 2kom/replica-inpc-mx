from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.calculo._subindices import grupos_por_clasificacion
from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import COLUMNAS_CLASIFICACION, INDICE_POR_TIPO


def _calcular_df(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    indice: str,
    tipo: str,
    version: int,
) -> pd.DataFrame:
    periodos_null = df_serie.isnull().any(axis=0)
    ponderadores = df_canasta["ponderador"].astype(float)
    resultado = df_serie.multiply(ponderadores, axis=0).sum().divide(ponderadores.sum())

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


class LaspeyresDirecto(CalculadorBase):
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        tipo: str,
    ) -> ResultadoCalculo:

        if tipo in INDICE_POR_TIPO:
            df = _calcular_df(canasta.df, serie.df, INDICE_POR_TIPO[tipo], tipo, canasta.version)
            return ResultadoCalculo(df, id_corrida)

        assert tipo in COLUMNAS_CLASIFICACION
        dfs = [
            _calcular_df(df_c, df_s, cat, tipo, canasta.version)
            for cat, df_c, df_s in grupos_por_clasificacion(canasta, serie, tipo)
        ]
        return ResultadoCalculo(pd.concat(dfs), id_corrida)
