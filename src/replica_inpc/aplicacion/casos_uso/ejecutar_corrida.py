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
from replica_inpc.dominio.errores import ErrorValidacion
from replica_inpc.dominio.tipos import ManifestCorrida, ResultadoCorrida, VersionCanasta
from replica_inpc.dominio.validar_inpc import validar


class EjecutarCorrida:
    def __init__(
        self,
        lector_canasta: LectorCanasta,
        lector_series: LectorSeries,
        fuente_validacion: FuenteValidacion,
        repositorio: RepositorioCorridas,
        almacen: AlmacenArtefactos,
        escritor: EscritorResultados,
        ruta_salida: Path,
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
    ) -> ResultadoCorrida:

        # crear el manifiesto de la ejecucion
        fecha_hora_ejecucion = datetime.now()
        id_corrida = str(uuid.uuid4())
        manifiesto = ManifestCorrida(
            id_corrida, version, ruta_canasta, ruta_series, fecha_hora_ejecucion
        )

        canasta = self._lector_canasta.leer(ruta_canasta, version)
        serie = self._lector_series.leer(ruta_series)

        serie = alinear_genericos(canasta, serie)

        resultado = para_canasta(canasta).calcular(canasta, serie, id_corrida)

        try:
            inegi = self._fuente_validacion.obtener(list(resultado.df.index))
        except ErrorValidacion:
            inegi = {}

        resumen, reporte, diagnostico = validar(
            resultado, inegi, canasta, serie, id_corrida
        )

        self._repositorio.guardar(id_corrida, manifiesto)
        self._almacen.guardar(id_corrida, "canasta", canasta.df)
        self._almacen.guardar(id_corrida, "serie", serie.df)
        self._almacen.guardar(id_corrida, "resumen", resumen.df)
        self._almacen.guardar(id_corrida, "reporte", reporte.df)
        self._almacen.guardar(id_corrida, "diagnostico", diagnostico.df)

        self._escritor.escribir_reporte(
            reporte, self._ruta_salida / f"reporte_{id_corrida}.csv"
        )
        self._escritor.escribir_diagnostico(
            diagnostico, self._ruta_salida / f"diagnostico_{id_corrida}.csv"
        )

        return ResultadoCorrida(
            manifest=manifiesto,
            resultado=resultado,
            resumen=resumen,
            reporte=reporte,
            diagnostico=diagnostico,
        )
