from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta


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
    inicio, fin = RANGOS_CANASTAS[version]
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
    mascara_faltante = df_serie.isna()
    if not mascara_faltante.any(axis=None):
        return pd.DataFrame(columns=columnas)

    # nonzero() sobre matriz booleana: índices (fila, col) donde hay NaN
    filas_idx, cols_idx = mascara_faltante.values.nonzero()
    genericos_f = mascara_faltante.index[filas_idx]
    periodos_f = mascara_faltante.columns[cols_idx]

    return pd.DataFrame(
        {
            "id_corrida": id_corrida,
            "version": version,
            "tipo": tipo,
            "periodo": periodos_f,
            "generico": genericos_f,
            "nivel_faltante": "periodo",
            "tipo_faltante": "indice",
            "detalle": "valor NaN en serie publicada",
        },
        columns=columnas,
    )
