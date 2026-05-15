"""Cálculo y transformaciones de índices."""

from __future__ import annotations

from replica_inpc.api._periodos import parsear_periodo
from replica_inpc.aplicacion.casos_uso.calcular_historia import (
    _referencias_normalizadas,
)
from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.conversion import a_mensual as _a_mensual
from replica_inpc.dominio.conversion import empalmar as _empalmar
from replica_inpc.dominio.conversion import rebasar as _rebasar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import VersionCanasta

# Versiones cuyo calculador encadenado exige un resultado de referencia.
_VERSIONES_ENCADENADAS = (2013, 2024)


def calcular_indice(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    tipo: str,
    referencia: ResultadoIndice | None = None,
) -> ResultadoIndice:
    """Calcula el índice de un tramo de canasta.

    Las versiones encadenadas (2013, 2024) requieren `referencia` — el
    resultado del tramo anterior; las versiones base (2010, 2018) la ignoran.
    """
    if canasta.version in _VERSIONES_ENCADENADAS and referencia is None:
        raise InvarianteViolado(
            f"la versión {canasta.version} es encadenada y requiere `referencia` "
            f"(el ResultadoIndice del tramo anterior)."
        )

    referencias: dict[str, float] | None = None
    if referencia is not None:
        version_origen = max(m.version for m in referencia.manifiesto)
        referencias = _referencias_normalizadas(
            referencia, tipo, version_origen, canasta.version
        )

    return para_canasta(canasta, referencias).calcular(
        canasta, serie, f"{tipo}:{canasta.version}", tipo
    )


def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: VersionCanasta | None = None,
) -> ResultadoIndice:
    """Une tramos de índice del mismo tipo en orden cronológico."""
    return _empalmar(resultados, forzar=forzar, version_nombres=version_nombres)


def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: str,
    valor_referencia: float = 100.0,
) -> ResultadoIndice:
    """Reexpresa los índices a una nueva referencia."""
    return _rebasar(resultado, parsear_periodo(periodo_referencia), valor_referencia)


def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
    """Convierte un resultado quincenal a mensual (promedio simple de 1Q y 2Q)."""
    return _a_mensual(resultado)
