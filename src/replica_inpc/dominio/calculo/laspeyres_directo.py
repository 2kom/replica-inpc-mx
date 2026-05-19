from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from replica_inpc.dominio.calculo._subindices import grupos_por_clasificacion
from replica_inpc.dominio.calculo.base import (
    CalculadorBase,
    _construir_diagnostico,
    _construir_reporte,
    _recortar_al_rango,
    _rellenar_faltantes,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
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
) -> pd.DataFrame:
    if periodos_rellenados is None:
        periodos_rellenados = set()
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
            df_calc = _calcular_df(canasta.df, df_s, indice, tipo, canasta.version, periodos_rel)
            df_reporte = _construir_reporte(df_calc, canasta.df, df_s, canasta.version)
            df_diag = pd.concat(
                [
                    _construir_diagnostico(canasta.df, df_s, id_corrida, canasta.version, tipo),
                    df_corr_relleno,
                ],
                ignore_index=True,
            )
        else:
            dfs_calc: list[pd.DataFrame] = []
            dfs_reporte: list[pd.DataFrame] = []
            dfs_diag: list[pd.DataFrame] = []
            for cat, df_c, df_s_all in grupos_por_clasificacion(canasta, serie, tipo):
                df_s_raw = _recortar_al_rango(df_s_all, canasta.version)
                df_s, df_corr_relleno, periodos_rel = _rellenar_faltantes(
                    df_s_raw, id_corrida, canasta.version, tipo
                )
                df_calc_g = _calcular_df(df_c, df_s, cat, tipo, canasta.version, periodos_rel)
                dfs_calc.append(df_calc_g)
                dfs_reporte.append(_construir_reporte(df_calc_g, df_c, df_s, canasta.version))
                dfs_diag.append(
                    pd.concat(
                        [
                            _construir_diagnostico(df_c, df_s, id_corrida, canasta.version, tipo),
                            df_corr_relleno,
                        ],
                        ignore_index=True,
                    )
                )
            df_calc = pd.concat(dfs_calc)
            df_reporte = pd.concat(dfs_reporte)
            df_diag = pd.concat(dfs_diag, ignore_index=True)

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
