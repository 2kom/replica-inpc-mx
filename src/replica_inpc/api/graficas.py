"""Graficación de resultados."""

from __future__ import annotations

from functools import singledispatch

from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.infraestructura.graficacion.graficador import (
    graficar_indice as _graficar_indice_plotnine,
)

__all__ = ["graficar"]


@singledispatch
def graficar(resultado: object, _comparacion: object | None = None) -> None:
    """Grafica un resultado y lo muestra; no devuelve nada.

    Args:
        resultado: Resultado a graficar. Soporta `ResultadoIndice` por
            ahora — el resto de tipos (`ResultadoVariacion`,
            `ResultadoIncidencia`, `Validacion*`) se suma a medida que se
            auditen esos módulos.
        comparacion: Un segundo `ResultadoIndice` opcional, para superponer
            en la misma gráfica (ej. INPC en negro + una clasificación).

    Raises:
        TypeError: Si `resultado` es de un tipo aún no soportado.
    """
    raise TypeError(f"graficar() no soporta el tipo {type(resultado).__name__!r} todavía.")


@graficar.register
def _graficar_indice(
    resultado: ResultadoIndice, comparacion: ResultadoIndice | None = None
) -> None:
    _graficar_indice_plotnine(resultado, comparacion)
