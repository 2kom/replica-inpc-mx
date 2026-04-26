from pathlib import Path

from replica_inpc.dominio.incidencias import (
    incidencia_acumulada_anual as _incidencia_acumulada_anual,
)
from replica_inpc.dominio.incidencias import (
    incidencia_desde as _incidencia_desde,
)
from replica_inpc.dominio.incidencias import (
    incidencia_periodica as _incidencia_periodica,
)
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv


def _cargar_canastas(
    canastas: list[tuple[Path | str, VersionCanasta]],
) -> dict[int, object]:
    lector = LectorCanastaCsv()
    return {int(v): lector.leer(Path(ruta), v) for ruta, v in canastas}


def incidencia_periodica(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: list[tuple[Path | str, VersionCanasta]],
    frecuencia: str,
) -> ResultadoIncidencia:
    return _incidencia_periodica(inpc, clasificacion, _cargar_canastas(canastas), frecuencia)  # type: ignore[arg-type]


def incidencia_acumulada_anual(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: list[tuple[Path | str, VersionCanasta]],
) -> ResultadoIncidencia:
    return _incidencia_acumulada_anual(inpc, clasificacion, _cargar_canastas(canastas))  # type: ignore[arg-type]


def incidencia_desde(
    inpc: ResultadoCalculo,
    clasificacion: ResultadoCalculo,
    canastas: list[tuple[Path | str, VersionCanasta]],
    desde: PeriodoQuincenal | PeriodoMensual,
    hasta: PeriodoQuincenal | PeriodoMensual,
) -> ResultadoIncidencia:
    return _incidencia_desde(inpc, clasificacion, _cargar_canastas(canastas), desde, hasta)  # type: ignore[arg-type]
