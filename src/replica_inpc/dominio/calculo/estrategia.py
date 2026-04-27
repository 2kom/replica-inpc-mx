from __future__ import annotations

from replica_inpc.dominio.calculo.base import CalculadorBase
from replica_inpc.dominio.calculo.encadenado import LaspeyresEncadenado
from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica


def para_canasta(
    canasta: CanastaCanonica,
    referencia_empalme_por_indice: dict[str, float] | None = None,
) -> CalculadorBase:

    if canasta.df["encadenamiento"].isna().all():
        return LaspeyresDirecto()
    return LaspeyresEncadenado(referencia_empalme_por_indice)
