"""Caso de uso que valida resultados replicados contra series publicadas por INEGI.

Orquesta el I/O que antes hacía el propio dominio: decide qué periodos consultar,
pide la serie al puerto una sola vez y le entrega a `dominio/validacion/` un mapa
ya resuelto. Los comparadores quedan puros — reciben datos, no un puerto.

Ver: docs/diseño.md §7, §11.9
"""

from __future__ import annotations

from collections.abc import Callable

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
from replica_inpc.dominio.tipos import INDICES_VALIDABLES
from replica_inpc.dominio.validacion._comun import Periodo
from replica_inpc.dominio.validacion.incidencias import (
    resolver_tipo_incidencia_inegi,
    validar_incidencias,
)
from replica_inpc.dominio.validacion.indices import validar_indices
from replica_inpc.dominio.validacion.variaciones import (
    resolver_tipo_variacion_inegi,
    validar_variaciones,
)

CrearFuente = Callable[[str], FuenteValidacion]


def _verificar_tipo(tipo: str) -> None:
    """Rechaza un tipo que INEGI no publica, antes de construir la fuente."""
    if tipo not in INDICES_VALIDABLES:
        raise ErrorConfiguracion(
            f"tipo '{tipo}' no es comparable contra INEGI; "
            f"tipos válidos: {sorted(INDICES_VALIDABLES)}."
        )


def _periodos_del_reporte(reporte: pd.DataFrame, metodo: str) -> list[Periodo]:
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

        inegi = self._crear_fuente(tipo).obtener_variaciones(periodos, tipo_variacion)  # type: ignore[arg-type]
        return validar_variaciones(resultado, inegi, tolerancia_pp)

    def validar_incidencia(
        self, resultado: ResultadoIncidencia, tolerancia_pp: float = 0.009
    ) -> ValidacionIncidencia:
        """Valida un `ResultadoIncidencia` de una clase que INEGI publique."""
        tipo = resultado.manifiesto.tipo
        _verificar_tipo(tipo)
        tipo_incidencia = resolver_tipo_incidencia_inegi(resultado.manifiesto.clase)

        periodos = _periodos_del_reporte(resultado.reporte, "validar_incidencia")

        inegi = self._crear_fuente(tipo).obtener_incidencias(periodos, tipo_incidencia)  # type: ignore[arg-type]
        return validar_incidencias(resultado, inegi, tolerancia_pp)
