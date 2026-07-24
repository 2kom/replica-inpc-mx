"""Validación de resultados replicados contra series publicadas por INEGI."""

from __future__ import annotations

from replica_inpc.api import config
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import (
    ValidacionIncidencia,
    ValidacionIndice,
    ValidacionVariacion,
)
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.tipos import INDICES_VALIDABLES
from replica_inpc.dominio.validacion.incidencias import (
    _tipo_incidencia,
    validar_incidencias,
)
from replica_inpc.dominio.validacion.indices import validar_indices
from replica_inpc.dominio.validacion.variaciones import (
    _tipo_variacion,
    validar_variaciones,
)
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

__all__ = [
    "INDICES_VALIDABLES",
    "validar_incidencia",
    "validar_indice",
    "validar_variacion",
]


def _verificar_tipo(tipo: str) -> None:
    if tipo not in INDICES_VALIDABLES:
        raise ErrorConfiguracion(
            f"tipo '{tipo}' no es comparable contra INEGI; "
            f"tipos válidos: {sorted(INDICES_VALIDABLES)}."
        )


def _fuente(tipo: str) -> FuenteValidacionApi:
    return FuenteValidacionApi(config.get_token(), tipo, timeout=config.timeout_api)


def validar_indice(resultado: ResultadoIndice) -> ValidacionIndice:
    """Compara un `ResultadoIndice` contra los índices publicados por INEGI."""
    tipos = {m.tipo for m in resultado.manifiesto}
    if len(tipos) > 1:
        raise ErrorConfiguracion(
            f"el resultado mezcla varios tipos {sorted(tipos)}; valida un solo "
            f"tipo a la vez."
        )
    tipo = next(iter(tipos))
    _verificar_tipo(tipo)
    return validar_indices(resultado, _fuente(tipo), config.tolerancia_indice)


def validar_variacion(resultado: ResultadoVariacion) -> ValidacionVariacion:
    """Compara un `ResultadoVariacion` contra las variaciones publicadas por INEGI."""
    _verificar_tipo(resultado.manifiesto.tipo)
    _tipo_variacion(resultado.manifiesto.clase)  # clase no comparable → ErrorConfiguracion
    return validar_variaciones(
        resultado, _fuente(resultado.manifiesto.tipo), config.tolerancia_derivados
    )


def validar_incidencia(resultado: ResultadoIncidencia) -> ValidacionIncidencia:
    """Compara un `ResultadoIncidencia` contra las incidencias publicadas por INEGI."""
    _verificar_tipo(resultado.manifiesto.tipo)
    _tipo_incidencia(resultado.manifiesto.clase)  # clase no comparable → ErrorConfiguracion
    return validar_incidencias(
        resultado, _fuente(resultado.manifiesto.tipo), config.tolerancia_derivados
    )
