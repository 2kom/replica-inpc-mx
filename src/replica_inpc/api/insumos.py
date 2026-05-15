"""IO de insumos: carga de canastas y series desde CSV."""

from __future__ import annotations

from pathlib import Path

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv

_VERSIONES_VALIDAS = (2010, 2013, 2018, 2024)


def _validar_version(version: int) -> None:
    if version not in _VERSIONES_VALIDAS:
        raise InvarianteViolado(
            f"version {version!r} inválida; usa una de {_VERSIONES_VALIDAS}."
        )


def cargar_canasta(ruta: str, version: VersionCanasta) -> CanastaCanonica:
    """Carga una canasta de ponderadores desde un CSV.

    `version` es obligatoria — 2010 y 2013 tienen genéricos idénticos y un
    auto-detect elegiría mal en silencio (ver api.md §D3).
    """
    _validar_version(version)
    return LectorCanastaCsv().leer(Path(ruta), version)


def cargar_serie(ruta: str, version: VersionCanasta) -> SerieNormalizada:
    """Carga una serie de índices desde un CSV.

    La serie es siempre quincenal; los datos mensuales se obtienen vía
    `a_mensual`, nunca cargando CSV mensuales. `version` se valida pero la
    lectura de la serie no depende de ella.
    """
    _validar_version(version)
    return LectorSeriesCsv().leer(Path(ruta))
