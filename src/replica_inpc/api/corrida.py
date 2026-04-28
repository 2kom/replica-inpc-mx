from __future__ import annotations

from pathlib import Path

from replica_inpc.aplicacion.casos_uso.ejecutar_corrida import EjecutarCorrida
from replica_inpc.aplicacion.puertos.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.conversion import rebasar
from replica_inpc.dominio.errores import ErrorConfiguracion, FuenteNoDisponible
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo, combinar
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

_P_BASE_2018 = PeriodoQuincenal(2018, 7, 2)


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

    def ejecutar_historico(
        self,
        canasta_2010: str | Path,
        series_2010: str | Path,
        canasta_2013: str | Path,
        series_2013: str | Path,
        canasta_2018: str | Path,
        series_2018: str | Path,
        canasta_2024: str | Path,
        series_2024: str | Path,
        tipo: str = "inpc",
    ) -> ResultadoCalculo:
        """Calcula el INPC (o subíndices) histórico desde 2Q Dic 2010 hasta hoy.

        Orquesta las cuatro canastas, empalma cada tramo contra el anterior y
        reexpresa el bloque 2010+2013 a la base `2Q Jul 2018 = 100`.

        El resultado combina:
        - 2010: Laspeyres directo (2Q Dic 2010 – 2Q Mar 2013)
        - 2013: Laspeyres con alineación por f_k, empalmado contra 2010
        - 2018: Laspeyres directo
        - 2024: Laspeyres encadenado, empalmado contra 2018

        El bloque 2010+2013 se rebasa endógenamente a `2Q Jul 2018 = 100`
        usando el valor replicado propio en ese periodo.

        Args:
            canasta_2010: Ruta al CSV de ponderadores 2010.
            series_2010:  Ruta al CSV de series BIE que cubre 2010–2013.
            canasta_2013: Ruta al CSV de ponderadores 2013.
            series_2013:  Ruta al CSV de series BIE que cubre 2013–2018.
            canasta_2018: Ruta al CSV de ponderadores 2018.
            series_2018:  Ruta al CSV de series BIE base 2018.
            canasta_2024: Ruta al CSV de ponderadores 2024.
            series_2024:  Ruta al CSV de series BIE base 2024.
            tipo:         Tipo de índice — "inpc" o cualquier columna de clasificación.

        Returns:
            ResultadoCalculo quincenal con todos los periodos desde 2Q Dic 2010.
        """
        r2010 = self.ejecutar(canasta_2010, series_2010, 2010, tipo, persistir=False).resultado
        r2013 = self.ejecutar(
            canasta_2013, series_2013, 2013, tipo, persistir=False, resultado_referencia=r2010
        ).resultado
        r2018 = self.ejecutar(canasta_2018, series_2018, 2018, tipo, persistir=False).resultado
        r2024 = self.ejecutar(
            canasta_2024, series_2024, 2024, tipo, persistir=False, resultado_referencia=r2018
        ).resultado

        tramo_viejo = combinar([r2010, r2013])
        tramo_rebased = rebasar(tramo_viejo, _P_BASE_2018)
        return combinar([tramo_rebased, r2018, r2024])
