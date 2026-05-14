from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

_periodos = [
    PeriodoQuincenal(2018, 7, 2),
    PeriodoQuincenal(2018, 8, 1),
    PeriodoQuincenal(2018, 8, 2),
    PeriodoQuincenal(2018, 9, 1),
]


def _canasta() -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": [None, None, None, None],
        },
        index=["arroz", "frijol", "leche", "huevo"],
    )
    return CanastaCanonica(df, 2018)


def _serie() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [100, 101, 102, 103],
            "frijol": [100, 102, 104, 106],
            "leche": [100, 103, 106, 109],
            "huevo": [100, 104, 108, 112],
        },
        index=_periodos,
    ).T
    return SerieNormalizada(df, {g: g.capitalize() for g in df.index})


def test_calcular_retorna_resultado_indice() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "inpc")
    assert isinstance(r, ResultadoIndice)


def test_valores_inpc_correctos() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "inpc")
    valores = r.df["indice_replicado"].tolist()
    assert valores == pytest.approx([100.0, 103.0, 106.0, 109.0])


def test_multiindex_periodo_indice() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "inpc")
    assert list(r.df.index.names) == ["periodo", "indice"]
    assert r.df.index.get_level_values("periodo").tolist() == _periodos
    assert (r.df.index.get_level_values("indice") == "INPC").all()


def test_manifiesto_calculador_y_version() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "inpc")
    assert len(r.manifiesto) == 1
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresDirecto"
    assert m.version == 2018
    assert m.tipo == "inpc"
    assert m.id_corrida == "c1"
    assert m.ruta_canasta is None
    assert m.ruta_series is None


def test_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "tipo_inventado")
