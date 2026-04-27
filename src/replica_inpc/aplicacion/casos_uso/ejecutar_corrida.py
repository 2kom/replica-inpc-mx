from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd

from replica_inpc.aplicacion.puertos.almacen_artefactos import AlmacenArtefactos
from replica_inpc.aplicacion.puertos.escritor_resultados import EscritorResultados
from replica_inpc.aplicacion.puertos.fuente_validacion import FuenteValidacion
from replica_inpc.aplicacion.puertos.lector_canasta import LectorCanasta
from replica_inpc.aplicacion.puertos.lector_series import LectorSeries
from replica_inpc.aplicacion.puertos.repositorio_corridas import RepositorioCorridas
from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.correspondencia import alinear_genericos
from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    ErrorValidacion,
    PeriodosInsuficientes,
)
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    RANGOS_VALIDOS,
    ManifestCorrida,
    ResultadoCorrida,
    VersionCanasta,
)
from replica_inpc.dominio.validar_inpc import validar


def _rellenar_faltantes(
    serie: SerieNormalizada,
) -> tuple[SerieNormalizada, dict[tuple[str, PeriodoQuincenal], PeriodoQuincenal]]:
    periodos: list[PeriodoQuincenal] = sorted(
        cast(PeriodoQuincenal, c) for c in serie.df.columns if isinstance(c, PeriodoQuincenal)
    )
    df_original = serie.df[periodos]
    df_relleno = df_original.bfill(axis=1).ffill(axis=1)

    imputados: dict[tuple[str, PeriodoQuincenal], PeriodoQuincenal] = {}
    nans = df_original.isna() & df_relleno.notna()
    nans_stack = nans.stack()
    for generico, periodo in nans_stack[nans_stack].index:  # type: ignore[index]
        idx = periodos.index(periodo)
        fuente: PeriodoQuincenal | None = None
        for i in range(idx + 1, len(periodos)):
            if not pd.isna(df_original.at[generico, periodos[i]]):
                fuente = periodos[i]
                break
        if fuente is None:
            for i in range(idx - 1, -1, -1):
                if not pd.isna(df_original.at[generico, periodos[i]]):
                    fuente = periodos[i]
                    break
        if fuente is not None:
            imputados[(str(generico), periodo)] = fuente

    return SerieNormalizada(df_relleno, serie.mapeo), imputados


def _referencia_empalme_desde_resultado(
    resultado_ref: ResultadoCalculo, traslape: PeriodoQuincenal
) -> dict[str, float]:
    df = resultado_ref.df
    mask = (df.index.get_level_values("periodo") == traslape) & (df["estado_calculo"] == "ok")
    if not mask.any():
        return {}
    referencia_empalme: dict[str, float] = {}
    for key, val in df.loc[mask, "indice_replicado"].items():
        if val is not None and not pd.isna(val):
            referencia_empalme[str(key[1])] = float(val)  # type: ignore[index]
    return referencia_empalme


class EjecutarCorrida:
    def __init__(
        self,
        lector_canasta: LectorCanasta,
        lector_series: LectorSeries,
        fuente_validacion: FuenteValidacion,
        repositorio: RepositorioCorridas | None = None,
        almacen: AlmacenArtefactos | None = None,
        escritor: EscritorResultados | None = None,
        ruta_salida: Path | None = None,
    ) -> None:
        self._lector_canasta = lector_canasta
        self._lector_series = lector_series
        self._fuente_validacion = fuente_validacion
        self._repositorio = repositorio
        self._almacen = almacen
        self._escritor = escritor
        self._ruta_salida = ruta_salida

    def ejecutar(
        self,
        ruta_canasta: Path,
        ruta_series: Path,
        version: VersionCanasta,
        tipo: str = "inpc",
        persistir: bool = False,
        resultado_referencia: ResultadoCalculo | None = None,
    ) -> ResultadoCorrida:

        if tipo not in INDICE_POR_TIPO and tipo not in COLUMNAS_CLASIFICACION:
            raise ErrorConfiguracion(
                f"tipo '{tipo}' no es válido. Valores aceptados: "
                f"{sorted(INDICE_POR_TIPO)} + {sorted(COLUMNAS_CLASIFICACION)}"
            )

        if persistir and any(
            p is None
            for p in (
                self._repositorio,
                self._almacen,
                self._escritor,
                self._ruta_salida,
            )
        ):
            raise ErrorConfiguracion(
                "persistir=True requiere repositorio, almacen, escritor y ruta_salida"
            )

        fecha_hora_ejecucion = datetime.now()
        id_corrida = str(uuid.uuid4())
        manifiesto = ManifestCorrida(
            id_corrida, version, ruta_canasta, ruta_series, fecha_hora_ejecucion
        )

        canasta = self._lector_canasta.leer(ruta_canasta, version)
        serie = self._lector_series.leer(ruta_series)

        inicio, fin = RANGOS_VALIDOS[version]
        cols = [
            p
            for p in serie.df.columns
            if isinstance(p, PeriodoQuincenal) and p >= inicio and (fin is None or p <= fin)
        ]
        if not cols:
            raise PeriodosInsuficientes(
                f"No hay periodos validos para canasta {version}, valida para {inicio} - {fin}, "
                f"pero se encontraron: {serie.df.columns}"
            )

        serie = SerieNormalizada(serie.df[cols], serie.mapeo)
        serie = alinear_genericos(canasta, serie)
        serie, imputados = _rellenar_faltantes(serie)

        referencia_empalme_por_indice: dict[str, float] = {}
        if resultado_referencia is not None:
            if canasta.df["encadenamiento"].isna().all():
                print(
                    f"[replica_inpc] Advertencia: resultado_referencia fue proporcionado "
                    f"pero la canasta {version} no usa encadenamiento (columna "
                    f"'encadenamiento' vacía). El parámetro se ignora y no tiene "
                    f"efecto en el cálculo. resultado_referencia solo aplica para "
                    f"canastas 2013 y 2024."
                )
            else:
                traslape = RANGOS_VALIDOS[version][0]
                referencia_empalme_por_indice = _referencia_empalme_desde_resultado(
                    resultado_referencia, traslape
                )

        resultado = para_canasta(canasta, referencia_empalme_por_indice).calcular(
            canasta, serie, id_corrida, tipo
        )

        try:
            periodos_unicos = resultado.df.index.get_level_values("periodo").unique().tolist()
            inegi = self._fuente_validacion.obtener(periodos_unicos)
        except ErrorValidacion:
            inegi = {}

        resumen, reporte, diagnostico = validar(
            resultado, inegi, canasta, serie, id_corrida, imputados
        )

        if persistir:
            self._repositorio.guardar(manifiesto)  # type: ignore[union-attr]
            self._almacen.guardar(id_corrida, "resultado", resultado.df)  # type: ignore[union-attr]
            self._almacen.guardar(id_corrida, "resumen", resumen.df)  # type: ignore[union-attr]
            self._almacen.guardar(id_corrida, "reporte", reporte.df)  # type: ignore[union-attr]
            self._almacen.guardar(id_corrida, "diagnostico", diagnostico.df)  # type: ignore[union-attr]
            self._escritor.escribir_reporte(  # type: ignore[union-attr]
                reporte,
                self._ruta_salida / f"reporte_{id_corrida}.csv",  # type: ignore[operator]
            )
            self._escritor.escribir_diagnostico(  # type: ignore[union-attr]
                diagnostico,
                self._ruta_salida / f"diagnostico_{id_corrida}.csv",  # type: ignore[operator]
            )

        return ResultadoCorrida(
            manifest=manifiesto,
            resultado=resultado,
            resumen=resumen,
            reporte=reporte,
            diagnostico=diagnostico,
        )
