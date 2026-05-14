"""Archivo parking de código v1 marcado para muerte en Fase 10.

NO IMPORTAR desde código v2 activo.

Aislamiento temporal de ManifestCorrida/ResultadoCorrida para liberar tipos.py
de dependencias v1. Después de Fase 2 (sobreescritura de modelos derivados),
los imports internos de este archivo dejarán de funcionar — es aceptable:
nada de la superficie v2 activa lo importa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
    ResumenValidacion,
)
from replica_inpc.dominio.tipos import VersionCanasta


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
