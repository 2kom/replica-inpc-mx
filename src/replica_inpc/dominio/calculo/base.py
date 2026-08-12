from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.errores import ErrorCalculo
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta


def _validar_serie_cubre_grupo(
    genericos_del_grupo: pd.Index,
    serie: SerieNormalizada,
    version: VersionCanasta,
    tipo: str,
) -> None:
    """Rechaza una serie a la que le falte algún genérico del grupo que se va a calcular."""
    faltantes = sorted(str(g) for g in genericos_del_grupo.difference(serie.df.index))
    if not faltantes:
        return
    muestra = ", ".join(faltantes[:3])
    raise ErrorCalculo(
        f"la serie no tiene {len(faltantes)} de los {len(genericos_del_grupo)} genéricos "
        f"que '{tipo}' necesita de la canasta {version} (por ejemplo: {muestra}). Suele "
        f"significar que la canasta y la serie son de versiones distintas."
    )


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
    if not columnas_en_rango:
        raise ErrorCalculo(
            f"La serie no tiene ningún periodo dentro del rango vigente de la "
            f"canasta versión {version} ({periodo_inicio} - {periodo_fin or 'sin límite'}). "
            "Revisa que la serie y la canasta correspondan a la misma versión."
        )
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


def _laspeyres_por_grupo(
    numerador: pd.DataFrame,
    ponderador: pd.Series,
    cat_por_gen: pd.Series,
) -> pd.DataFrame:
    """Laspeyres por grupo: Σ(ponderador·numerador)/Σponderador, agrupado por `cat_por_gen`."""
    resultado = (
        numerador.multiply(ponderador, axis=0)
        .groupby(cat_por_gen)
        .sum()
        .divide(ponderador.groupby(cat_por_gen).sum(), axis=0)
    )
    valores = resultado.to_numpy(dtype=float)
    # numerador ya viene finito-o-NaN (SerieNormalizada lo garantiza), pero
    # ponderar puede desbordar a inf incluso con entradas finitas (ej. 1e308)
    if (~pd.isna(valores) & ~np.isfinite(valores)).any():
        raise ErrorCalculo(
            "El cálculo de Laspeyres por grupo produjo un valor no finito — "
            "posible desbordamiento al ponderar la serie."
        )
    return resultado


def _construir_diagnostico(
    df_serie: pd.DataFrame,
    version: VersionCanasta,
    tipo: str,
) -> pd.DataFrame:
    """Lista (periodo, generico) faltantes con schema DiagnosticoFaltantes.

    Para subíndices clasificados, `df_serie` debe ser el del subgrupo. Una
    fila por celda NaN.
    """
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
