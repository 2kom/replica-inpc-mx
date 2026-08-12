"""Flujos orquestados completos (modo automático)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from replica_inpc.aplicacion.casos_uso.calcular_historia import CalcularHistoria
from replica_inpc.dominio.errores import ErrorConfiguracion, PeriodoNoInterpretable
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal, periodo_desde_str
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv


def calcular_historia(
    insumos: list[tuple[VersionCanasta, str, str]],
    tipo: str = "INPC",
    periodicidad: Literal["quincenal", "mensual"] = "mensual",
    referencia: str = "2Q Jul 2018",
) -> ResultadoIndice:
    """Calcula el índice histórico empalmado, rebasado y en la periodicidad dada.

    Orquesta carga → cálculo por versión → empalme por pares vecinos → rebase →
    conversión de frecuencia. Para control granular, usar las funciones manuales
    de `insumos` e `indices`.

    `referencia` debe estar en formato quincenal (`"NQ Mmm AAAA"`) porque la base
    del INPC siempre es una quincena: 2Q dic 2010 para las canastas 2010 y 2013,
    2Q jul 2018 para 2018 y 2024. Con `periodicidad="mensual"` la serie se
    promedia al final y la base sigue siendo esa quincena, que es la que reporta
    `periodo_referencia`. No se garantiza que el mes que contiene al ancla valga
    100: es el promedio de sus dos quincenas, y solo coincide con 100 si la otra
    quincena también vale 100 o si el mes tiene una sola quincena en el tramo. Si
    necesitas un mes anclado en 100 (por ejemplo para comparar contra un índice
    mensual), pide `periodicidad="mensual"` y rebasa después con `rebasar`.
    """
    tipo = tipo.upper()
    try:
        periodo_referencia = periodo_desde_str(referencia)
    except PeriodoNoInterpretable as exc:
        raise ErrorConfiguracion(
            f"referencia '{referencia}' no es un periodo interpretable."
        ) from exc
    if not isinstance(periodo_referencia, PeriodoQuincenal):
        raise ErrorConfiguracion(
            f"referencia '{referencia}' debe estar en formato quincenal "
            f'("NQ Mmm AAAA", por ejemplo "2Q Jul 2018"); '
            f"los calculos internos son siempre quincenales."
        )

    insumos_path: list[tuple[VersionCanasta, Path, Path]] = [
        (version, Path(ruta_canasta), Path(ruta_series))
        for version, ruta_canasta, ruta_series in insumos
    ]
    caso = CalcularHistoria(LectorCanastaCsv(), LectorSeriesCsv())
    return caso.ejecutar(insumos_path, tipo, periodicidad, periodo_referencia)
