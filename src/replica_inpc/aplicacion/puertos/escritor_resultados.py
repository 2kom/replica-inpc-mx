from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
)


class EscritorResultados(Protocol):
    def escribir_reporte(
        self, reporte: ReporteDetalladoValidacion, ruta: Path
    ) -> None: ...

    def escribir_diagnostico(
        self, diagnostico: DiagnosticoFaltantes, ruta: Path
    ) -> None: ...
