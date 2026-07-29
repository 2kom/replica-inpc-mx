from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoQuincenal

VersionCanasta = Literal[2010, 2013, 2018, 2024]

TIPO_INPC: str = "INPC"

# Las columnas que vienen por defecto en la canasta ya sea con la flag --xlsx
# o con la flag --pdf, son: generico, ponderador, COG, CCIF division,
# CCIF grupo, CCIF clase, inflacion componente, inflacion subcomponente,
# inflacion agrupacion, SCIAN sector, SCIAN rama, durabilidad, canasta basica,
# canasta consumo minimo; ahora pueden venir o no con informacion, pero esas
# columnas ya vienen en el archivo csv que luego se convierte en la canasta.
# LectorCanastaCsv las renombra a mayúsculas al cargar (ver
# infraestructura/csv/lector_canasta_csv.py) — CanastaCanonica y todo lo que
# sigue en el dominio solo ve el nombre en mayúsculas.

COLUMNAS_CLASIFICACION: frozenset[str] = frozenset(
    {
        "COG",
        "CCIF DIVISION",
        "CCIF GRUPO",
        "CCIF CLASE",
        "INFLACION COMPONENTE",
        "INFLACION SUBCOMPONENTE",
        "INFLACION AGRUPACION",
        "SCIAN SECTOR",
        "SCIAN RAMA",
        "DURABILIDAD",
        "CANASTA BASICA",
        "CANASTA CONSUMO MINIMO",
    }
)

INDICES_VALIDABLES: frozenset[str] = frozenset(
    {TIPO_INPC, "INFLACION COMPONENTE", "INFLACION SUBCOMPONENTE"}
)

RANGOS_CANASTAS: dict[VersionCanasta, tuple[PeriodoQuincenal, PeriodoQuincenal | None]] = {
    2010: (PeriodoQuincenal(2010, 12, 2), PeriodoQuincenal(2013, 3, 2)),
    2013: (PeriodoQuincenal(2013, 3, 2), PeriodoQuincenal(2018, 7, 2)),
    2018: (PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2024, 7, 2)),
    2024: (PeriodoQuincenal(2024, 7, 2), None),
}


@dataclass
class ManifestCalculo:
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    ruta_canasta: Path | None = None
    ruta_series: Path | None = None
    fecha: datetime = field(default_factory=datetime.now)


@dataclass
class ManifestDerivado:
    versiones: list[VersionCanasta]
    tipo: str
    clase: str
    descripcion: str
    fecha: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.clase:
            raise InvarianteViolado("ManifestDerivado.clase no puede estar vacío")
