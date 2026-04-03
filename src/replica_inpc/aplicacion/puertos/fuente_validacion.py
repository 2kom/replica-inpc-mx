from __future__ import annotations

from typing import Protocol

from replica_inpc.dominio.periodos import Periodo


class FuenteValidacion(Protocol):
    """Contrato para obtener valores oficiales usados en la validación.

    Implementado actualmente por `_FuenteValidacionNula`.

    La fuente devuelve un valor por periodo solicitado y puede señalar que la
    validación no está disponible lanzando un error de validación.

    Ver: docs/diseño.md §7.1.3, §11.6
    """

    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]:
        """Devuelve un valor oficial por periodo y `None` donde no hay dato."""
        ...
