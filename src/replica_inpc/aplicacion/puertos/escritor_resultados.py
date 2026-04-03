from __future__ import annotations

from pathlib import Path
from typing import Protocol

from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
)


class EscritorResultados(Protocol):
    """Contrato para exportar artefactos de validación al usuario final.

    Implementado por `EscritorResultadosCsv`.

    Exporta el `ReporteDetalladoValidacion` y el `DiagnosticoFaltantes` en un
    formato consumible fuera del pipeline interno.

    Ver: docs/diseño.md §7.1.4, §8.5
    """

    def escribir_reporte(
        self, reporte: ReporteDetalladoValidacion, ruta: Path
    ) -> None:
        """Escribe el reporte detallado en la ruta de salida indicada."""
        ...

    def escribir_diagnostico(
        self, diagnostico: DiagnosticoFaltantes, ruta: Path
    ) -> None:
        """Escribe el diagnóstico de faltantes en la ruta de salida indicada."""
        ...
