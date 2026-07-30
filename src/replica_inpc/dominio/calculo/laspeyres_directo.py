from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import numpy as np
import pandas as pd

from replica_inpc.dominio.calculo.base import (
    CalculadorBase,
    _construir_diagnostico,
    _recortar_series_fecha,
    _rellenar_dato_serie_faltante,
)
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    RANGOS_CANASTAS,
    TIPO_INPC,
    ManifestCalculo,
)


class LaspeyresDirecto(CalculadorBase):
    def __init__(self, referencia_empalme_por_indice: dict[str, float] | None = None) -> None:
        self._referencia_empalme = referencia_empalme_por_indice or {}

    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        tipo: str,
    ) -> ResultadoIndice:

        fecha = datetime.now()
        ruta_canasta = canasta.df.attrs.get("origen")
        ruta_serie = serie.df.attrs.get("origen")

        if tipo != TIPO_INPC and tipo not in COLUMNAS_CLASIFICACION:
            raise InvarianteViolado(
                f"tipo='{tipo}' no es '{TIPO_INPC}' ni está en COLUMNAS_CLASIFICACION"
            )
        if tipo in COLUMNAS_CLASIFICACION and canasta.df[tipo].dropna().empty:
            raise InvarianteViolado(
                f"La canasta versión {canasta.version} no tiene datos en '{tipo}'. "
                "Revisa tools/canasta_inpc/esquema.py::FUENTES_POSIBLES para qué "
                "clasificaciones aplican a cada versión (docs/diseño.md §5.4)."
            )

        # tipo==TIPO_INPC: c = 1 solo grupo constante (I_INS/INPC). Clasificación:
        # c = categoría (dropna excluye genéricos sin valor en esa columna).
        if tipo == TIPO_INPC:
            categoria_por_generico = pd.Series(TIPO_INPC, index=canasta.df.index)
        else:
            categoria_por_generico = canasta.df[tipo].dropna()
        genericos_del_grupo = categoria_por_generico.index

        serie_recortada = _recortar_series_fecha(serie.df.loc[genericos_del_grupo], canasta.version)
        serie_rellenada, df_diagnostico_relleno, _ = _rellenar_dato_serie_faltante(
            serie_recortada, canasta.version, tipo
        )
        ponderador = canasta.df.loc[genericos_del_grupo, "ponderador"].astype(float)

        serie_ponderada = serie_rellenada.multiply(ponderador, axis=0)
        suma_ponderada_por_grupo = serie_ponderada.groupby(categoria_por_generico).sum()
        ponderador_total_por_grupo = ponderador.groupby(categoria_por_generico).sum()
        indice_por_grupo = suma_ponderada_por_grupo.divide(ponderador_total_por_grupo, axis=0)
        indice_incidencia_por_grupo = indice_por_grupo.copy()  # antes del rebase (r_c)

        # self._referencia_empalme (R_c) está keyed por grupo — para INPC la única
        # key posible es TIPO_INPC; para clasificación, una key por categoría.
        if self._referencia_empalme:
            traslape = RANGOS_CANASTAS[canasta.version][0]
            if traslape not in indice_por_grupo.columns:
                raise ErrorCalculo(f"PeriodoQuincenal de traslape {traslape} no está en la serie.")
            grupos_con_referencia = [
                g for g in indice_por_grupo.index if g in self._referencia_empalme
            ]
            if grupos_con_referencia:
                referencia_rebase = pd.Series(
                    {g: self._referencia_empalme[g] for g in grupos_con_referencia}
                )
                factor_rebase = referencia_rebase / indice_por_grupo.loc[
                    grupos_con_referencia, cast(Any, traslape)
                ].astype(float)
                indice_por_grupo.loc[grupos_con_referencia] = indice_por_grupo.loc[
                    grupos_con_referencia
                ].multiply(factor_rebase, axis=0)

        # NaN irrellenable → sin_datos; celda imputada → rellenado
        hay_faltante = serie_rellenada.isna().groupby(categoria_por_generico).any()
        hubo_relleno = (
            (serie_recortada.isna() & serie_rellenada.notna()).groupby(categoria_por_generico).any()
        )

        indice_apilado = indice_por_grupo.T.stack()
        indice_apilado.index = indice_apilado.index.set_names(["periodo", "indice"])
        idx = indice_apilado.index

        faltante_alineado = hay_faltante.T.stack().reindex(idx).fillna(False)
        relleno_alineado = hubo_relleno.T.stack().reindex(idx).fillna(False)

        faltante_bool = faltante_alineado.to_numpy(dtype=bool)
        relleno_bool = relleno_alineado.to_numpy(dtype=bool)
        estado_calculo_arr = np.where(
            faltante_bool, "sin_datos", np.where(relleno_bool & ~faltante_bool, "rellenado", "ok")
        )
        motivo_error_arr = np.where(faltante_bool, "faltantes en serie", None)  # type: ignore[call-overload]

        df_indice_resultado = pd.DataFrame(
            {
                "version": canasta.version,
                "tipo": tipo,
                "indice_replicado": indice_apilado.where(~faltante_bool).values,
                "indice_incidencia": (
                    indice_incidencia_por_grupo.T.stack().reindex(idx).where(~faltante_bool).values
                ),
                "estado_calculo": estado_calculo_arr,
                "motivo_error": motivo_error_arr,
            },
            index=idx,
        )

        cubierto = serie_rellenada.notna()
        con_indice_por_grupo = cubierto.groupby(categoria_por_generico).sum()
        ponderador_cubierto_por_grupo = (
            cubierto.multiply(ponderador, axis=0).groupby(categoria_por_generico).sum()
        )
        genericos_esperados_por_grupo = categoria_por_generico.groupby(
            categoria_por_generico
        ).size()
        ponderador_esperado_por_grupo = ponderador.groupby(categoria_por_generico).sum()

        con_indice_flat = con_indice_por_grupo.T.stack().reindex(idx).to_numpy()
        ponderador_cubierto_flat = ponderador_cubierto_por_grupo.T.stack().reindex(idx).to_numpy()
        grupos_col = idx.get_level_values("indice")
        genericos_esperados_flat = genericos_esperados_por_grupo.reindex(grupos_col).to_numpy()
        ponderador_esperado_flat = ponderador_esperado_por_grupo.reindex(grupos_col).to_numpy()

        df_reporte = pd.DataFrame(
            {
                "version": canasta.version,
                "estado_calculo": estado_calculo_arr,
                "motivo_error": motivo_error_arr,
                "genericos_esperados": genericos_esperados_flat,
                "genericos_con_indice": con_indice_flat,
                "genericos_sin_indice": genericos_esperados_flat - con_indice_flat,
                "cobertura_genericos_pct": 100.0 * con_indice_flat / genericos_esperados_flat,
                "ponderador_esperado": ponderador_esperado_flat,
                "ponderador_cubierto": ponderador_cubierto_flat,
            },
            index=idx,
        )

        df_diagnostico = pd.concat(
            [
                _construir_diagnostico(canasta.df, serie_rellenada, canasta.version, tipo),
                df_diagnostico_relleno,
            ],
            ignore_index=True,
        )

        manifiesto = ManifestCalculo(
            version=canasta.version,
            tipo=tipo,
            calculador="LaspeyresDirecto",
            ruta_canasta=ruta_canasta,
            ruta_series=ruta_serie,
            fecha=fecha,
        )
        return ResultadoIndice(df_indice_resultado, [manifiesto], df_reporte, df_diagnostico)
