"""Validación de resultados replicados contra series publicadas por INEGI."""

from __future__ import annotations

from replica_inpc.aplicacion.casos_uso.validar_resultado import ValidarResultado
from replica_inpc.dominio.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import (
    ValidacionIncidencia,
    ValidacionIndice,
    ValidacionVariacion,
)
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.tipos import INDICES_VALIDABLES
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

from replica_inpc.api import config  # isort: skip

__all__ = [
    "INDICES_VALIDABLES",
    "validar_incidencia",
    "validar_indice",
    "validar_variacion",
]


def _crear_fuente(tipo: str) -> FuenteValidacion:
    """Fábrica del adaptador; el caso de uso la llama recién al necesitar datos."""
    return FuenteValidacionApi(config.get_token(), tipo, timeout=config.timeout_api)


def _caso_uso() -> ValidarResultado:
    return ValidarResultado(_crear_fuente)


def validar_indice(resultado: ResultadoIndice) -> ValidacionIndice:
    """Compara un `ResultadoIndice` contra los índices publicados por INEGI."""
    return _caso_uso().validar_indice(resultado, config.tolerancia_indice)


def validar_variacion(resultado: ResultadoVariacion) -> ValidacionVariacion:
    """Compara un `ResultadoVariacion` contra las variaciones publicadas por INEGI."""
    return _caso_uso().validar_variacion(resultado, config.tolerancia_derivados)


def validar_incidencia(resultado: ResultadoIncidencia) -> ValidacionIncidencia:
    """Compara un `ResultadoIncidencia` contra las incidencias publicadas por INEGI."""
    return _caso_uso().validar_incidencia(resultado, config.tolerancia_derivados)
