from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada


class LaspeyresDirecto(CalculadorBase):
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        indice: str,
        tipo: str,
    ) -> ResultadoCalculo:

        periodos_null = serie.df.isnull().any(axis=0)

        ponderadores = canasta.df["ponderador"].astype(float)
        resultado = (serie.df.multiply(ponderadores, axis=0).sum()).divide(100)

        idx = pd.MultiIndex.from_tuples(
            [(p, indice) for p in resultado.index],
            names=["periodo", "indice"],
        )

        df_resultado = pd.DataFrame(
            {
                "version": canasta.version,
                "tipo": tipo,
                "indice_replicado": resultado.values,
                "estado_calculo": "ok",
                "motivo_error": None,
            },
            index=idx,
        )

        periodos_null_idx = [(p, indice) for p in resultado.index[periodos_null]]
        if periodos_null_idx:
            df_resultado.loc[periodos_null_idx, "estado_calculo"] = "null_por_faltantes"
            df_resultado.loc[periodos_null_idx, "indice_replicado"] = None
            df_resultado.loc[periodos_null_idx, "motivo_error"] = "faltantes en serie"

        return ResultadoCalculo(df_resultado, id_corrida)
