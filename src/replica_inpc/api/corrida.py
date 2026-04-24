from __future__ import annotations

from pathlib import Path

from replica_inpc.aplicacion.casos_uso.ejecutar_corrida import EjecutarCorrida
from replica_inpc.aplicacion.puertos.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.errores import ErrorConfiguracion, FuenteNoDisponible
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICE_POR_TIPO,
    ResultadoCorrida,
    VersionCanasta,
)
from replica_inpc.infraestructura.csv.escritor_resultados_csv import (
    EscritorResultadosCsv,
)
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv
from replica_inpc.infraestructura.filesystem.almacen_artefactos_fs import (
    AlmacenArtefactosFs,
)
from replica_inpc.infraestructura.filesystem.repositorio_corridas_fs import (
    RepositorioCorridasFs,
)
from replica_inpc.infraestructura.inegi.fuente_validacion_api import (
    _INDICADORES_QUINCENALES,
    FuenteValidacionApi,
)


class _FuenteValidacionNula:
    """Fuente nula — se usa cuando no hay token INEGI. Siempre señala no_disponible."""

    def obtener(
        self, periodos: list[PeriodoQuincenal | PeriodoMensual]
    ) -> dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]:  # noqa: ARG002
        raise FuenteNoDisponible("No se configuró token_inegi.")


class Corrida:
    """Punto de entrada principal para notebooks. Composition root del pipeline."""

    def __init__(
        self,
        ruta_datos: str | Path = "data/runs",
        ruta_salida: str | Path = "output",
        token_inegi: str | None = None,
    ) -> None:
        self._ruta_datos = Path(ruta_datos)
        self._ruta_salida = Path(ruta_salida)
        self._token_inegi = token_inegi

    def ejecutar(
        self,
        canasta: str | Path,
        series: str | Path,
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

        if persistir:
            self._ruta_datos.mkdir(parents=True, exist_ok=True)
            self._ruta_salida.mkdir(parents=True, exist_ok=True)

        fuente_validacion: FuenteValidacion
        if self._token_inegi and tipo in _INDICADORES_QUINCENALES:
            fuente_validacion = FuenteValidacionApi(self._token_inegi, tipo)
        else:
            fuente_validacion = _FuenteValidacionNula()

        if persistir:
            caso_uso = EjecutarCorrida(
                lector_canasta=LectorCanastaCsv(),
                lector_series=LectorSeriesCsv(),
                fuente_validacion=fuente_validacion,
                repositorio=RepositorioCorridasFs(self._ruta_datos),
                almacen=AlmacenArtefactosFs(self._ruta_datos),
                escritor=EscritorResultadosCsv(),
                ruta_salida=self._ruta_salida,
            )
        else:
            caso_uso = EjecutarCorrida(
                lector_canasta=LectorCanastaCsv(),
                lector_series=LectorSeriesCsv(),
                fuente_validacion=fuente_validacion,
            )

        return caso_uso.ejecutar(
            ruta_canasta=Path(canasta),
            ruta_series=Path(series),
            version=version,
            tipo=tipo,
            persistir=persistir,
            resultado_referencia=resultado_referencia,
        )
