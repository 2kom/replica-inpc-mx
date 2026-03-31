from __future__ import annotations

from typing import Protocol

from replica_inpc.dominio.tipos import ManifestCorrida


class RepositorioCorridas(Protocol):
    def guardar(self, manifest: ManifestCorrida) -> None: ...

    def obtener(self, id_corrida: str) -> ManifestCorrida: ...

    def listar(self) -> list[str]: ...
