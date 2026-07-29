from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta


def _rellenar_dato_serie_faltante(
    df_serie: pd.DataFrame,
    version: VersionCanasta,
    tipo: str,
) -> tuple[pd.DataFrame, pd.DataFrame, set[object]]:
    """Rellena NaN vía bfill→ffill por fila; documenta cada relleno con su periodo fuente."""
    columnas_diagnostico = [
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
    mascara_faltante = df_serie.isna()
    if not mascara_faltante.any(axis=None):
        return df_serie, pd.DataFrame(columns=columnas_diagnostico), set()

    df_serie_rellenada = df_serie.bfill(axis=1).ffill(axis=1).infer_objects(copy=False)
    mascara_rellenada = mascara_faltante & df_serie_rellenada.notna()
    periodos_rellenados: set[object] = set(
        df_serie_rellenada.columns[mascara_rellenada.any(axis=0)]
    )

    # Ubica el periodo fuente de cada relleno propagando la ETIQUETA de columna
    # (en vez del dato) con el mismo bfill→ffill: evita re-escanear columnas por
    # celda rellenada (antes O(genéricos × rellenos × periodos), ahora vectorizado.
    etiquetas_columna = pd.DataFrame(
        np.tile(df_serie.columns.to_numpy(), (len(df_serie.index), 1)),
        index=df_serie.index,
        columns=df_serie.columns,
    ).where(df_serie.notna())
    periodo_fuente_adelante = etiquetas_columna.bfill(axis=1)
    periodo_fuente_atras = etiquetas_columna.ffill(axis=1)
    periodo_fuente = periodo_fuente_adelante.where(
        periodo_fuente_adelante.notna(), periodo_fuente_atras
    )

    celdas_rellenadas = cast("pd.Series[bool]", mascara_rellenada.stack())
    celdas_rellenadas = celdas_rellenadas[celdas_rellenadas]
    if celdas_rellenadas.empty:
        return df_serie_rellenada, pd.DataFrame(columns=columnas_diagnostico), periodos_rellenados

    fuentes = periodo_fuente.stack().reindex(celdas_rellenadas.index)
    diagnostico = pd.DataFrame(
        {
            "version": version,
            "tipo": tipo,
            "periodo": celdas_rellenadas.index.get_level_values(1),
            "generico": celdas_rellenadas.index.get_level_values(0),
            "nivel_faltante": "periodo",
            "tipo_faltante": "rellenado",
            "detalle": "NaN sustituido con valor de " + fuentes.astype(str),
        },
        columns=columnas_diagnostico,
    )

    return df_serie_rellenada, diagnostico, periodos_rellenados


def _recortar_series_fecha(df_serie: pd.DataFrame, version: VersionCanasta) -> pd.DataFrame:
    """Recorta las columnas de periodo de la serie al rango vigente de la versión de canasta."""
    periodo_inicio, periodo_fin = RANGOS_CANASTAS[version]
    columnas_en_rango = [
        periodo
        for periodo in df_serie.columns
        if isinstance(periodo, PeriodoQuincenal)
        and periodo >= periodo_inicio
        and (periodo_fin is None or periodo <= periodo_fin)
    ]
    return df_serie[columnas_en_rango]


class CalculadorBase(ABC):
    """Contrato abstracto para estrategias de cálculo del dominio.

    Implementaciones: `LaspeyresDirecto`, `LaspeyresEncadenadoT1`,
    `LaspeyresEncadenadoT2`. La selección concreta vive en
    `estrategia.para_canasta`.
    """

    @abstractmethod
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        tipo: str,
    ) -> ResultadoIndice:
        """Calcula `ResultadoIndice` para una canasta y serie dadas."""


def _construir_reporte(
    df_calculo: pd.DataFrame,
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    version: VersionCanasta,
) -> pd.DataFrame:
    """Construye reporte de cobertura por (periodo, indice) para un subgrupo.

    Para subíndices clasificados, `df_canasta` y `df_serie` deben ser los del
    subgrupo (no la canasta entera) — `genericos_esperados` y
    `ponderador_esperado` se derivan de su tamaño.
    """
    ponderadores = df_canasta["ponderador"].astype(float)
    genericos_esperados = int(len(df_canasta))
    ponderador_esperado = float(ponderadores.sum())

    cubierto = df_serie.notna()
    pond_cubierto_por_periodo = cubierto.multiply(ponderadores, axis=0).sum()
    con_indice_por_periodo = cubierto.sum().astype(int)

    periodos = df_calculo.index.get_level_values("periodo")
    con_idx = con_indice_por_periodo.reindex(periodos).to_numpy()
    pond_cub = pond_cubierto_por_periodo.reindex(periodos).to_numpy()
    cobertura_pct = (100.0 * con_idx / genericos_esperados) if genericos_esperados else 0.0

    return pd.DataFrame(
        {
            "version": version,
            "estado_calculo": df_calculo["estado_calculo"].to_numpy(),
            "motivo_error": df_calculo["motivo_error"].to_numpy(),
            "genericos_esperados": genericos_esperados,
            "genericos_con_indice": con_idx,
            "genericos_sin_indice": genericos_esperados - con_idx,
            "cobertura_genericos_pct": cobertura_pct,
            "ponderador_esperado": ponderador_esperado,
            "ponderador_cubierto": pond_cub,
        },
        index=df_calculo.index,
    )


def _construir_diagnostico(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    version: VersionCanasta,
    tipo: str,
) -> pd.DataFrame:
    """Lista (periodo, generico) faltantes con schema DiagnosticoFaltantes.

    Para subíndices clasificados, `df_canasta` y `df_serie` deben ser los del
    subgrupo. Una fila por celda NaN. Solo considera genéricos presentes en
    `df_canasta.index` (los del subgrupo).
    """
    _ = df_canasta
    columnas_diagnostico = [
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
    mascara_faltante = df_serie.isna()
    # nonzero() en un solo paso: evita escanear la máscara dos veces (antes: una
    # para detectar si hay NaN con .any(), otra para ubicarlos con .nonzero())
    genericos_idx, periodos_idx = mascara_faltante.to_numpy().nonzero()
    if genericos_idx.size == 0:
        return pd.DataFrame(columns=columnas_diagnostico)

    genericos_faltantes = mascara_faltante.index[genericos_idx]
    periodos_faltantes = mascara_faltante.columns[periodos_idx]

    return pd.DataFrame(
        {
            "version": version,
            "tipo": tipo,
            "periodo": periodos_faltantes,
            "generico": genericos_faltantes,
            "nivel_faltante": "periodo",
            "tipo_faltante": "indice",
            "detalle": "valor NaN en serie publicada",
        },
        columns=columnas_diagnostico,
    )
