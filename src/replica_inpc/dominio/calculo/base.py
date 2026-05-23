from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_VALIDOS, VersionCanasta


def _rellenar_faltantes(
    df_serie: pd.DataFrame,
    id_corrida: str,
    version: VersionCanasta,
    tipo: str,
) -> tuple[pd.DataFrame, pd.DataFrame, set[object]]:
    """Rellena NaN via bfill→ffill por fila. Retorna (df_rellenado, df_corr_relleno, periodos_rellenados)."""
    columnas = [
        "id_corrida",
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
    mask_antes = df_serie.isna()
    if not mask_antes.any(axis=None):
        return df_serie, pd.DataFrame(columns=columnas), set()

    df_rel = df_serie.bfill(axis=1).ffill(axis=1).infer_objects(copy=False)
    mask_rel = mask_antes & df_rel.notna()
    periodos_rellenados: set[object] = set(df_rel.columns[mask_rel.any(axis=0)])

    cols_list = list(df_serie.columns)
    filas = []
    for generico in mask_rel.index:
        for periodo in mask_rel.columns:
            if not mask_rel.at[generico, periodo]:
                continue
            idx = cols_list.index(periodo)
            fuente = None
            for j in range(idx + 1, len(cols_list)):
                if pd.notna(df_serie.at[generico, cols_list[j]]):
                    fuente = cols_list[j]
                    break
            if fuente is None:
                for j in range(idx - 1, -1, -1):
                    if pd.notna(df_serie.at[generico, cols_list[j]]):
                        fuente = cols_list[j]
                        break
            filas.append(
                {
                    "id_corrida": id_corrida,
                    "version": version,
                    "tipo": tipo,
                    "periodo": periodo,
                    "generico": generico,
                    "nivel_faltante": "periodo",
                    "tipo_faltante": "rellenado",
                    "detalle": f"NaN sustituido con valor de {fuente}",
                }
            )

    return df_rel, pd.DataFrame(filas, columns=columnas), periodos_rellenados


def _recortar_al_rango(df_serie: pd.DataFrame, version: VersionCanasta) -> pd.DataFrame:
    inicio, fin = RANGOS_VALIDOS[version]
    cols = [
        p
        for p in df_serie.columns
        if isinstance(p, PeriodoQuincenal) and p >= inicio and (fin is None or p <= fin)
    ]
    return df_serie[cols]


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
        id_corrida: str,
        tipo: str,
        ruta_canasta: Path | None = None,
        ruta_series: Path | None = None,
        fecha: datetime | None = None,
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

    filas = []
    for _key, fila in df_calculo.iterrows():
        periodo, indice = cast(tuple[Any, Any], _key)
        con_idx = int(con_indice_por_periodo[periodo])
        pond_cub = float(pond_cubierto_por_periodo[periodo])
        cobertura_pct = 100.0 * con_idx / genericos_esperados if genericos_esperados else 0.0
        filas.append(
            {
                "periodo": periodo,
                "indice": indice,
                "version": version,
                "estado_calculo": fila["estado_calculo"],
                "motivo_error": fila["motivo_error"],
                "genericos_esperados": genericos_esperados,
                "genericos_con_indice": con_idx,
                "genericos_sin_indice": genericos_esperados - con_idx,
                "cobertura_genericos_pct": cobertura_pct,
                "ponderador_esperado": ponderador_esperado,
                "ponderador_cubierto": pond_cub,
            }
        )
    return pd.DataFrame(filas).set_index(["periodo", "indice"])


def _construir_diagnostico(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    id_corrida: str,
    version: VersionCanasta,
    tipo: str,
) -> pd.DataFrame:
    """Lista (periodo, generico) faltantes con schema DiagnosticoFaltantes.

    Para subíndices clasificados, `df_canasta` y `df_serie` deben ser los del
    subgrupo. Una fila por celda NaN. Solo considera genéricos presentes en
    `df_canasta.index` (los del subgrupo).
    """
    _ = df_canasta
    filas = []
    mascara_faltante = df_serie.isna()
    for generico in mascara_faltante.index:
        for periodo in mascara_faltante.columns:
            if not mascara_faltante.at[generico, periodo]:
                continue
            filas.append(
                {
                    "id_corrida": id_corrida,
                    "version": version,
                    "tipo": tipo,
                    "periodo": periodo,
                    "generico": generico,
                    "nivel_faltante": "periodo",
                    "tipo_faltante": "indice",
                    "detalle": "valor NaN en serie publicada",
                }
            )
    columnas = [
        "id_corrida",
        "version",
        "tipo",
        "periodo",
        "generico",
        "nivel_faltante",
        "tipo_faltante",
        "detalle",
    ]
    if not filas:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(filas, columns=columnas)
