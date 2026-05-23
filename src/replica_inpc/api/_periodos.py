"""Helper interno: parseo de periodos en la frontera de la API.

`api.md §Manejo de periodos` promete formatos insensibles a mayúsculas, pero el
factory de dominio `periodo_desde_str` espera el mes en formato `Title` (`"Ene"`,
`"Jul"`). La API normaliza aquí antes de delegar al dominio.
"""

from __future__ import annotations

from replica_inpc.dominio.periodos import (
    PeriodoMensual,
    PeriodoQuincenal,
    periodo_desde_str,
)

_Periodo = PeriodoQuincenal | PeriodoMensual


def parsear_periodo(texto: str) -> _Periodo:
    """Convierte un texto de periodo a `Periodo`, insensible a mayúsculas.

    Acepta `"NQ Mmm AAAA"` y `"Mmm AAAA"` en cualquier combinación de
    mayúsculas/minúsculas (`"2q jul 2018"`, `"DIC 2024"`, `"ene 2015"`).

    Raises:
        PeriodoNoInterpretable: Si el texto no corresponde a un formato válido.
    """
    normalizado = " ".join(parte.title() for parte in texto.split())
    return periodo_desde_str(normalizado)
