from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from replica_inpc.dominio.calculo._subindices import grupos_por_clasificacion
from replica_inpc.dominio.calculo.base import (
    CalculadorBase,
    _construir_diagnostico,
    _construir_reporte,
    _recortar_al_rango,
    _rellenar_faltantes,
)
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    RANGOS_VALIDOS,
    ManifestUnidad,
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
        f_k_serie: pd.Series = df_serie[cast(Any, traslape)] / 100
        f_k = enc_raw.astype(float)
        f_k = f_k.where(~necesita_fallback, f_k_serie)
    else:
        f_k = enc_raw.astype(float)

    return f_k


def _i_tramo_y_metadata(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    version: VersionCanasta,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calcula i_tramo y devuelve también f_k, ponderadores, periodos_null."""
    f_k = _obtener_f_k(df_canasta, df_serie, version)
    ponderadores = df_canasta["ponderador"].astype(float)
    periodos_null = df_serie.isnull().any(axis=0)
    df_base = df_serie.divide(f_k, axis=0)
    i_tramo = df_base.multiply(ponderadores, axis=0).sum().divide(ponderadores.sum())
    return i_tramo, f_k, ponderadores, periodos_null


def _construir_df_resultado(
    resultado: pd.Series,
    indice: str,
    tipo: str,
    version: VersionCanasta,
    periodos_null: pd.Series,
    periodos_rellenados: set[object] | None = None,
) -> pd.DataFrame:
    if periodos_rellenados is None:
        periodos_rellenados = set()
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


def _calcular_df_t1(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    indice: str,
    tipo: str,
    referencia_empalme: float | None,
    periodos_rellenados: set[object] | None = None,
) -> pd.DataFrame:
    """T1 — v2013: factor_h = ref / i_tramo[traslape] | 1.0."""
    version: VersionCanasta = 2013
    i_tramo, _f_k, _pond, periodos_null = _i_tramo_y_metadata(df_canasta, df_serie, version)
    traslape = RANGOS_VALIDOS[version][0]
    if traslape not in i_tramo.index:
        raise ErrorCalculo(f"PeriodoQuincenal de traslape {traslape} no está en la serie.")
    if referencia_empalme is not None:
        factor_h = referencia_empalme / float(i_tramo[cast(Any, traslape)])
    else:
        factor_h = 1.0
    resultado = i_tramo * factor_h
    return _construir_df_resultado(
        resultado, indice, tipo, version, periodos_null, periodos_rellenados
    )


def _calcular_df_t2(
    df_canasta: pd.DataFrame,
    df_serie: pd.DataFrame,
    indice: str,
    tipo: str,
    referencia_empalme: float | None,
    periodos_rellenados: set[object] | None = None,
) -> pd.DataFrame:
    """T2 — v2024: factor_h = ref / 100 | sum(pond * f_k) / sum(pond)."""
    version: VersionCanasta = 2024
    i_tramo, f_k, ponderadores, periodos_null = _i_tramo_y_metadata(df_canasta, df_serie, version)
    traslape = RANGOS_VALIDOS[version][0]
    if traslape not in i_tramo.index:
        raise ErrorCalculo(f"PeriodoQuincenal de traslape {traslape} no está en la serie.")
    if referencia_empalme is not None:
        factor_h = referencia_empalme / 100
    else:
        factor_h = float((ponderadores * f_k).sum() / ponderadores.sum())
    resultado = i_tramo * factor_h
    return _construir_df_resultado(
        resultado, indice, tipo, version, periodos_null, periodos_rellenados
    )


class _LaspeyresEncadenadoBase(CalculadorBase):
    _VERSION_ESPERADA: VersionCanasta
    _CALCULADOR_NOMBRE: Literal["LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]

    def __init__(self, referencia_empalme_por_indice: dict[str, float] | None = None) -> None:
        self._referencia_empalme = referencia_empalme_por_indice or {}

    def _calcular_df_para(
        self,
        df_canasta: pd.DataFrame,
        df_serie: pd.DataFrame,
        indice: str,
        tipo: str,
        referencia_empalme: float | None,
        periodos_rellenados: set[object] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

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
        if canasta.version != self._VERSION_ESPERADA:
            raise InvarianteViolado(
                f"{self._CALCULADOR_NOMBRE} requiere canasta.version="
                f"{self._VERSION_ESPERADA}; recibió {canasta.version}"
            )
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
            df_calc = self._calcular_df_para(
                canasta.df,
                df_s,
                indice,
                tipo,
                self._referencia_empalme.get(indice),
                periodos_rel,
            )
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
                df_calc_g = self._calcular_df_para(
                    df_c,
                    df_s,
                    cat,
                    tipo,
                    self._referencia_empalme.get(cat),
                    periodos_rel,
                )
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
            calculador=self._CALCULADOR_NOMBRE,
            ruta_canasta=ruta_canasta,
            ruta_series=ruta_series,
            fecha=fecha if fecha is not None else datetime.now(),
        )
        return ResultadoIndice(df_calc, [manifiesto], df_reporte, df_diag)


class LaspeyresEncadenadoT1(_LaspeyresEncadenadoBase):
    _VERSION_ESPERADA = 2013
    _CALCULADOR_NOMBRE = "LaspeyresEncadenadoT1"

    def _calcular_df_para(
        self,
        df_canasta: pd.DataFrame,
        df_serie: pd.DataFrame,
        indice: str,
        tipo: str,
        referencia_empalme: float | None,
        periodos_rellenados: set[object] | None = None,
    ) -> pd.DataFrame:
        return _calcular_df_t1(
            df_canasta, df_serie, indice, tipo, referencia_empalme, periodos_rellenados
        )


class LaspeyresEncadenadoT2(_LaspeyresEncadenadoBase):
    _VERSION_ESPERADA = 2024
    _CALCULADOR_NOMBRE = "LaspeyresEncadenadoT2"

    def _calcular_df_para(
        self,
        df_canasta: pd.DataFrame,
        df_serie: pd.DataFrame,
        indice: str,
        tipo: str,
        referencia_empalme: float | None,
        periodos_rellenados: set[object] | None = None,
    ) -> pd.DataFrame:
        return _calcular_df_t2(
            df_canasta, df_serie, indice, tipo, referencia_empalme, periodos_rellenados
        )
