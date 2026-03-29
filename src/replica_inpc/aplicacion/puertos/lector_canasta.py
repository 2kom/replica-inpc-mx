from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.tipos import VersionCanasta


class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
