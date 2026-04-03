from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.serie import SerieNormalizada


class LectorSeries(Protocol):
    """Contrato para cargar y normalizar series de genéricos.

    Implementado por `LectorSeriesCsv`.

    El adaptador resuelve internamente encoding, orientación y metadatos para
    devolver una `SerieNormalizada` estable para el dominio.

    Ver: docs/diseño.md §7.1.2, §8.2
    """

    def leer(self, ruta: Path) -> SerieNormalizada:
        """Lee el archivo y devuelve la serie normalizada sin filtrar por versión."""
        ...
