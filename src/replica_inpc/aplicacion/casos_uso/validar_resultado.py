"""Caso de uso que valida resultados replicados contra series publicadas por INEGI.

Orquesta el I/O que antes hacía el propio dominio: decide qué periodos consultar,
pide la serie al puerto una sola vez y le entrega a `dominio/validacion/` un mapa
ya resuelto. Los comparadores quedan puros — reciben datos, no un puerto.

Ver: docs/diseño.md §7, §11.8
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pandas as pd

from replica_inpc.aplicacion.puertos.fuente_validacion import FuenteValidacion
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import (
    ValidacionIncidencia,
    ValidacionIndice,
    ValidacionVariacion,
)
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import INDICES_VALIDABLES
from replica_inpc.dominio.validacion.incidencias import (
    resolver_tipo_incidencia_inegi,
    validar_incidencias,
)
from replica_inpc.dominio.validacion.indices import validar_indices
from replica_inpc.dominio.validacion.variaciones import (
    resolver_tipo_variacion_inegi,
    validar_variaciones,
)

_Periodo = PeriodoQuincenal | PeriodoMensual
CrearFuente = Callable[[str], FuenteValidacion]


def _verificar_tipo(tipo: str) -> None:
    """Rechaza un tipo que INEGI no publica, antes de construir la fuente."""
    if tipo not in INDICES_VALIDABLES:
        raise ErrorConfiguracion(
            f"tipo '{tipo}' no es comparable contra INEGI; "
            f"tipos válidos: {sorted(INDICES_VALIDABLES)}."
        )


def _periodos_del_reporte(reporte: pd.DataFrame, metodo: str) -> list[_Periodo]:
    """Periodos únicos del `.reporte` de un derivado, en orden de aparición.

    La comprobación de `.empty` va antes de `get_level_values`: los modelos
    aceptan un reporte vacío con `RangeIndex`, y ahí pedir el nivel `periodo`
    lanzaría un `KeyError` de pandas en vez de un error de dominio.
    """
    if reporte.empty:
        raise InvarianteViolado(
            f"{metodo} requiere al menos un periodo en resultado.reporte; "
            f"el reporte recibido está vacío."
        )
    return list(dict.fromkeys(reporte.index.get_level_values("periodo")))


#: Periodicidad que cada clase derivada declara. `None` = admite ambas, pero
#: homogéneas.
_PERIODICIDAD_POR_CLASE: dict[str, type | None] = {
    "periodica_quincenal": PeriodoQuincenal,
    "periodica_mensual": PeriodoMensual,
    "periodica_anual": None,
    "acumulada_anual": None,
}


def _verificar_periodicidad(periodos: list[_Periodo], clase: str | None, metodo: str) -> None:
    """Exige periodos homogéneos y coherentes con la clase declarada.

    El adaptador elige la serie oficial —mensual o quincenal— por
    `type(periodos[0])`. Sin esta guardia, un resultado incoherente pero
    construible se compararía contra la serie equivocada en silencio, y una
    lista mixta escaparía como `TypeError` de pandas en vez de como error de
    dominio.
    """
    tipos = {type(p) for p in periodos}
    if len(tipos) > 1:
        raise InvarianteViolado(
            f"{metodo}: los periodos deben ser todos de la misma periodicidad; "
            f"se recibió una mezcla de {sorted(t.__name__ for t in tipos)}."
        )
    esperado = _PERIODICIDAD_POR_CLASE.get(clase) if clase is not None else None
    if esperado is not None and not isinstance(periodos[0], esperado):
        raise InvarianteViolado(
            f"{metodo}: la clase '{clase}' declara periodos {esperado.__name__}, "
            f"pero se recibieron {type(periodos[0]).__name__}."
        )


class ValidarResultado:
    """Compara resultados replicados contra INEGI resolviendo el I/O por ellos.

    Args:
        crear_fuente: Fábrica que construye la `FuenteValidacion` para un tipo
            dado. Se recibe diferida, no ya construida, para que el rechazo de
            tipo o de clase ocurra antes de exigir credenciales o red — de otro
            modo una clase inválida sin token fallaría por token y no por clase.

    Implementado con `FuenteValidacionApi` desde `api/validaciones.py`.
    """

    def __init__(self, crear_fuente: CrearFuente) -> None:
        self._crear_fuente = crear_fuente

    def validar_indice(
        self, resultado: ResultadoIndice, tolerancia: float = 0.0009
    ) -> ValidacionIndice:
        """Valida un `ResultadoIndice` de un solo tipo."""
        tipos = {m.tipo for m in resultado.manifiesto}
        if len(tipos) > 1:
            raise ErrorConfiguracion(
                f"el resultado mezcla varios tipos {sorted(tipos)}; valida un solo tipo a la vez."
            )
        tipo = next(iter(tipos))
        _verificar_tipo(tipo)

        # Los índices salen del largo, no del reporte: en ResultadoIndice ambos
        # tienen el mismo MultiIndex, y `Resultado` ya prohíbe un largo vacío.
        largo = resultado.resultado.largo
        periodos = list(dict.fromkeys(largo.index.get_level_values("periodo")))
        _verificar_periodicidad(periodos, None, "validar_indice")

        inegi = self._crear_fuente(tipo).obtener_indices(periodos)
        return validar_indices(resultado, inegi, tolerancia)

    def validar_variacion(
        self, resultado: ResultadoVariacion, tolerancia_pp: float = 0.009
    ) -> ValidacionVariacion:
        """Valida un `ResultadoVariacion` de una clase que INEGI publique."""
        tipo = resultado.manifiesto.tipo
        _verificar_tipo(tipo)
        tipo_variacion = resolver_tipo_variacion_inegi(resultado.manifiesto.clase)

        periodos = _periodos_del_reporte(resultado.reporte, "validar_variacion")
        _verificar_periodicidad(periodos, resultado.manifiesto.clase, "validar_variacion")

        inegi = self._crear_fuente(tipo).obtener_variaciones(periodos, tipo_variacion)
        return validar_variaciones(resultado, inegi, tolerancia_pp)

    def validar_incidencia(
        self, resultado: ResultadoIncidencia, tolerancia_pp: float = 0.009
    ) -> ValidacionIncidencia:
        """Valida un `ResultadoIncidencia` de una clase que INEGI publique."""
        tipo = resultado.manifiesto.tipo
        _verificar_tipo(tipo)
        tipo_incidencia = resolver_tipo_incidencia_inegi(resultado.manifiesto.clase)

        periodos = _periodos_del_reporte(resultado.reporte, "validar_incidencia")
        _verificar_periodicidad(periodos, resultado.manifiesto.clase, "validar_incidencia")
        # El puerto solo acepta mensuales, y la guardia de arriba ya lo comprobó
        # en runtime: la única clase de incidencia que INEGI publica es
        # `periodica_mensual`, y `_PERIODICIDAD_POR_CLASE` la ata a PeriodoMensual.
        # Si algún día se admite una clase quincenal, hay que revisar este cast.
        mensuales = cast(list[PeriodoMensual], periodos)

        inegi = self._crear_fuente(tipo).obtener_incidencias(mensuales, tipo_incidencia)
        return validar_incidencias(resultado, inegi, tolerancia_pp)
