import pandas as pd

from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada


class LaspeyresDirecto(CalculadorBase):
    def calcular(
        self, canasta: CanastaCanonica, serie: SerieNormalizada
    ) -> ResultadoCalculo:

        # Hacemos una suma ponderada de los precios de la serie utilizando los ponderadores de la canasta
        ponderadores = canasta.df["ponderador"].astype(float)
        resultado = (serie.df.multiply(ponderadores, axis=0).sum()).divide(100)

        version_canasta = canasta.version

        df_resultado = pd.DataFrame(
            {
                "version": version_canasta,
                "inpc_replicado": resultado,
                "estado_calculo": "ok",
                "motivo_error": None,
            },
            index=resultado.index,
        )

        return ResultadoCalculo(df_resultado, "")
