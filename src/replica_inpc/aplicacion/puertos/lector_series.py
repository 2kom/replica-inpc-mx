from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.serie import SerieNormalizada


class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
