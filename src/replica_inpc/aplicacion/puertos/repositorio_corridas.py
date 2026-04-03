from __future__ import annotations

from typing import Protocol

from replica_inpc.dominio.tipos import ManifestCorrida


class RepositorioCorridas(Protocol):
    """Contrato para persistir y recuperar metadatos de corridas.

    Implementado por `RepositorioCorridasFs`.

    El repositorio registra la intención de la corrida vía `ManifestCorrida` y
    permite reconstruir historiales a partir de los `id_corrida` almacenados.

    Ver: docs/diseño.md §7.1.5, §8.3
    """

    def guardar(self, manifest: ManifestCorrida) -> None:
        """Guarda el `ManifestCorrida` asociado a una ejecución."""
        ...

    def obtener(self, id_corrida: str) -> ManifestCorrida:
        """Recupera el manifiesto registrado para un `id_corrida`."""
        ...

    def listar(self) -> list[str]:
        """Devuelve los identificadores de corrida registrados en el repositorio."""
        ...
