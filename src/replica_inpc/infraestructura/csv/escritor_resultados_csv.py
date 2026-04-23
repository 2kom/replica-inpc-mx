from __future__ import annotations

from pathlib import Path

from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
)
from replica_inpc.dominio.periodos import PeriodoQuincenal


class EscritorResultadosCsv:
    def escribir_reporte(self, reporte: ReporteDetalladoValidacion, ruta: Path) -> None:
        df = reporte.df.reset_index()
        df["periodo"] = df["periodo"].apply(
            lambda v: str(v) if isinstance(v, PeriodoQuincenal) else v
        )
        df.to_csv(ruta, index=False)

    def escribir_diagnostico(self, diagnostico: DiagnosticoFaltantes, ruta: Path) -> None:
        df = diagnostico.df.copy()
        if "periodo" in df.columns and not df.empty:
            df["periodo"] = df["periodo"].apply(
                lambda v: str(v) if isinstance(v, PeriodoQuincenal) else v
            )
        df.to_csv(ruta, index=False)
