from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from replica_inpc.dominio.errores import InvarianteViolado
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
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime


@dataclass
class ManifestDerivado:
    id_corrida: list[str]
    tipo: str
    clase: str
    descripcion: str
    fecha: datetime
    inpc_ids: list[str] | None = None
    clasificacion_ids: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.clase:
            raise InvarianteViolado("ManifestDerivado.clase no puede estar vacío")
        if (self.inpc_ids is None) != (self.clasificacion_ids is None):
            raise InvarianteViolado(
                "inpc_ids y clasificacion_ids deben ambos ser None o ambos estar presentes"
            )
