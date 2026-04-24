from __future__ import annotations

from typing import Protocol

from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_Periodo = PeriodoQuincenal | PeriodoMensual


class FuenteValidacion(Protocol):
    """Contrato para obtener valores oficiales usados en la validación.

    Implementado actualmente por `_FuenteValidacionNula`.

    La fuente devuelve un valor por periodo solicitado y puede señalar que la
    validación no está disponible lanzando un error de validación.

    Ver: docs/diseño.md §7.1.3, §11.6
    """

    def obtener(self, periodos: list[_Periodo]) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve un dict keyed por nombre de índice con valores por periodo.

        `None` por periodo cuando el INEGI no tiene dato para ese periodo.
        """
        ...
