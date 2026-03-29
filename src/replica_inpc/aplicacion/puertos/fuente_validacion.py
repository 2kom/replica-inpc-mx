from __future__ import annotations

from typing import Protocol

from replica_inpc.dominio.periodos import Periodo


class FuenteValidacion(Protocol):
    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]: ...
