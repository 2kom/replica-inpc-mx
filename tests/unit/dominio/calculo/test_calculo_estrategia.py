from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.calculo.laspeyres_encadenado import (
    LaspeyresEncadenadoT1,
    LaspeyresEncadenadoT2,
)
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.tipos import VersionCanasta


def _canasta(version: VersionCanasta, encadenamiento: list[str | None]) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": encadenamiento,
        },
        index=["a", "b", "c", "d"],
    )
    return CanastaCanonica(df, version)


@pytest.mark.parametrize(
    "version,encadenamiento,esperado",
    [
        (2010, [None, None, None, None], LaspeyresDirecto),
        (2018, [None, None, None, None], LaspeyresDirecto),
        (2013, ["1.2", "0.8", "1.1", "0.9"], LaspeyresEncadenadoT1),
        (2024, ["1.5", "1.4", "1.6", "1.3"], LaspeyresEncadenadoT2),
    ],
)
def test_dispatch_por_version(
    version: VersionCanasta, encadenamiento: list[str | None], esperado: type
) -> None:
    calc = para_canasta(_canasta(version, encadenamiento))
    assert isinstance(calc, esperado)


def test_dispatch_no_depende_de_encadenamiento_isna() -> None:
    canasta_2010_con_enc_inventado = _canasta(2010, ["1.1", "1.2", "1.3", "1.4"])
    assert isinstance(para_canasta(canasta_2010_con_enc_inventado), LaspeyresDirecto)
