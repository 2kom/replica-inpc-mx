from __future__ import annotations

from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import (
    LaspeyresEncadenadoT1,
    LaspeyresEncadenadoT2,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica


def para_canasta(
    canasta: CanastaCanonica,
    referencia_empalme_por_indice: dict[str, float] | None = None,
) -> CalculadorBase:
    if canasta.version in (2010, 2018):
        return LaspeyresDirecto(referencia_empalme_por_indice)
    if canasta.version == 2013:
        return LaspeyresEncadenadoT1(referencia_empalme_por_indice)
    if canasta.version == 2024:
        return LaspeyresEncadenadoT2(referencia_empalme_por_indice)
    raise InvarianteViolado(f"version {canasta.version} no tiene calculador asociado")
