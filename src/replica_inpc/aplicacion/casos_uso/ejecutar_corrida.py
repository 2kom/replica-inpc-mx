from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

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
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import Periodo
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    RANGOS_VALIDOS,
    ManifestCorrida,
    ResultadoCorrida,
    VersionCanasta,
)
from replica_inpc.dominio.validar_inpc import validar


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
            if isinstance(p, Periodo) and p >= inicio and (fin is None or p <= fin)
        ]
        if not cols:
            raise PeriodosInsuficientes(
                f"No hay periodos validos para canasta {version}, valida para {inicio} - {fin}, "
                f"pero se encontraron: {serie.df.columns}"
            )

        serie = SerieNormalizada(serie.df[cols], serie.mapeo)
        serie = alinear_genericos(canasta, serie)

        resultado = para_canasta(canasta).calcular(canasta, serie, id_corrida, tipo)

        try:
            periodos_unicos = resultado.df.index.get_level_values("periodo").unique().tolist()
            inegi = self._fuente_validacion.obtener(periodos_unicos)
        except ErrorValidacion:
            inegi = {}

        resumen, reporte, diagnostico = validar(resultado, inegi, canasta, serie, id_corrida)

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
