from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
    ResumenValidacion,
)
from replica_inpc.dominio.periodos import PeriodoQuincenal

VersionCanasta = Literal[2010, 2013, 2018, 2024]

INDICE_POR_TIPO: dict[str, str] = {"inpc": "INPC"}

COLUMNAS_CLASIFICACION: frozenset[str] = frozenset(
    {
        "COG",
        "CCIF division",
        "CCIF grupo",
        "CCIF clase",
        "inflacion componente",
        "inflacion subcomponente",
        "inflacion agrupacion",
        "SCIAN sector",
        "SCIAN rama",
        "durabilidad",
        "canasta basica",
    }
)

TIPOS_CON_VALIDACION: frozenset[str] = frozenset(
    {"inpc", "inflacion componente", "inflacion subcomponente"}
)

RANGOS_VALIDOS: dict[VersionCanasta, tuple[PeriodoQuincenal, PeriodoQuincenal | None]] = {
    2010: (PeriodoQuincenal(2010, 12, 2), PeriodoQuincenal(2013, 3, 2)),
    2013: (PeriodoQuincenal(2013, 3, 2), PeriodoQuincenal(2018, 7, 2)),
    2018: (PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2024, 7, 2)),
    2024: (PeriodoQuincenal(2024, 7, 2), None),
}


@dataclass
class ManifestCorrida:
    id_corrida: str
    version: VersionCanasta
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime


@dataclass
class ResultadoCorrida:
    manifest: ManifestCorrida
    resultado: ResultadoCalculo
    resumen: ResumenValidacion
    reporte: ReporteDetalladoValidacion
    diagnostico: DiagnosticoFaltantes

    def _repr_html_(self) -> str:
        return (
            "<h3>Resumen</h3>"
            + self.resumen._repr_html_()
            + "<h3>Reporte</h3>"
            + self.reporte._repr_html_()
            + "<h3>Diagnóstico</h3>"
            + self.diagnostico._repr_html_()
            + "<h3>Resultado</h3>"
            + self.resultado._repr_html_()
        )
