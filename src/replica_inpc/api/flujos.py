"""Flujos orquestados completos (modo automático)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from replica_inpc.api._periodos import parsear_periodo
from replica_inpc.aplicacion.casos_uso.calcular_historia import CalcularHistoria
from replica_inpc.dominio.errores import ErrorConfiguracion, PeriodoNoInterpretable
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv


def calcular_historia(
    insumos: list[tuple[VersionCanasta, str, str]],
    tipo: str = "inpc",
    referencia: str = "2Q Jul 2018",
    periodicidad: Literal["quincenal", "mensual"] = "mensual",
) -> ResultadoIndice:
    """Calcula el índice histórico empalmado, rebased y en la periodicidad dada.

    Orquesta carga → cálculo por versión → empalme por pares vecinos →
    conversión de frecuencia → rebase. Para control granular, usar las
    funciones manuales de `insumos` e `indices`.

    `referencia` debe estar en formato quincenal (`"NQ Mmm AAAA"`). Los
    cálculos internos son siempre quincenales; cuando `periodicidad="mensual"`
    la conversión a periodo mensual ocurre automáticamente.
    """
    try:
        periodo_referencia = parsear_periodo(referencia)
    except PeriodoNoInterpretable as exc:
        raise ErrorConfiguracion(
            f"referencia '{referencia}' no es un periodo interpretable."
        ) from exc
    if not isinstance(periodo_referencia, PeriodoQuincenal):
        raise ErrorConfiguracion(
            f"referencia '{referencia}' debe estar en formato quincenal "
            f"(\"NQ Mmm AAAA\", por ejemplo \"2Q Jul 2018\"); "
            f"los calculos internos son siempre quincenales."
        )

    insumos_path: list[tuple[VersionCanasta, Path, Path]] = [
        (version, Path(ruta_canasta), Path(ruta_series))
        for version, ruta_canasta, ruta_series in insumos
    ]
    caso = CalcularHistoria(LectorCanastaCsv(), LectorSeriesCsv())
    return caso.ejecutar(insumos_path, tipo, periodo_referencia, periodicidad)
