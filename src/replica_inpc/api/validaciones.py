"""Validación de resultados replicados contra series publicadas por INEGI."""

from __future__ import annotations

from replica_inpc.aplicacion.casos_uso.validar_resultado import ValidarResultado
from replica_inpc.aplicacion.puertos.fuente_validacion import FuenteValidacion
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
    """Compara un `ResultadoIndice` contra los índices publicados por INEGI.

    Requiere token INEGI configurado. Tolerancia: `config.tolerancia_indice`
    (default `0.0009`). La frecuencia de la serie oficial a comparar se
    autodetecta por el tipo de periodo del resultado: `PeriodoQuincenal` →
    quincenal, `PeriodoMensual` → mensual.

    Raises:
        ErrorConfiguracion: `resultado.manifiesto` mezcla varios tipos, el
            tipo no está en `INDICES_VALIDABLES`, o no hay token configurado.
        FuenteNoDisponible: la API de INEGI no responde o devuelve error HTTP.
        RespuestaInvalida: la respuesta de INEGI tiene formato inesperado.
    """
    return _caso_uso().validar_indice(resultado, config.tolerancia_indice)


def validar_variacion(resultado: ResultadoVariacion) -> ValidacionVariacion:
    """Compara un `ResultadoVariacion` contra las variaciones publicadas por INEGI.

    Tolerancia: `config.tolerancia_derivados` (default `0.009` pp). Clases
    comparables: `"periodica_quincenal"`, `"periodica_mensual"`,
    `"periodica_anual"`, `"acumulada_anual"` — `"desde"` y cualquier otra
    clase no tienen contraparte oficial por esta vía.

    Raises:
        ErrorConfiguracion: `resultado.manifiesto.tipo` no está en
            `INDICES_VALIDABLES`, `manifiesto.clase` no es comparable, o no
            hay token configurado.
        FuenteNoDisponible: la API de INEGI no responde o devuelve error HTTP.
        RespuestaInvalida: la respuesta de INEGI tiene formato inesperado.
    """
    return _caso_uso().validar_variacion(resultado, config.tolerancia_derivados)


def validar_incidencia(resultado: ResultadoIncidencia) -> ValidacionIncidencia:
    """Compara un `ResultadoIncidencia` contra las incidencias publicadas por INEGI.

    Tolerancia: `config.tolerancia_derivados` (default `0.009` pp). La fuente
    BIE y el adaptador actual solo soportan incidencias periódicas mensuales
    — `resultado.manifiesto.clase` debe ser exactamente `"periodica_mensual"`,
    cualquier otra clase no tiene contraparte comparable por esta vía.

    Raises:
        ErrorConfiguracion: `resultado.manifiesto.tipo` no está en
            `INDICES_VALIDABLES`, `manifiesto.clase != "periodica_mensual"`,
            o no hay token configurado.
        FuenteNoDisponible: la API de INEGI no responde o devuelve error HTTP.
        RespuestaInvalida: la respuesta de INEGI tiene formato inesperado.
    """
    return _caso_uso().validar_incidencia(resultado, config.tolerancia_derivados)
