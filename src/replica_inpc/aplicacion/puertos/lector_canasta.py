from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.tipos import VersionCanasta


class LectorCanasta(Protocol):
    """Contrato para cargar una `CanastaCanonica` desde una fuente externa.

    Implementado por `LectorCanastaCsv`.

    El adaptador recibe la versión explícitamente para validar e interpretar el
    archivo de entrada antes de construir la canasta canónica.

    Ver: docs/diseño.md §7.1.1, §8.1
    """

    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica:
        """Lee la canasta indicada y la devuelve en formato canónico."""
        ...
