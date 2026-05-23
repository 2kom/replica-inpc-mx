from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

_periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]


def _canasta() -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": [None, None, None, None],
            "COG": ["alimentos", "alimentos", "servicios", "servicios"],
        },
        index=["arroz", "frijol", "leche", "huevo"],
    )
    return CanastaCanonica(df, 2018)


def _serie() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [100.0, 101.0],
            "frijol": [100.0, 102.0],
            "leche": [100.0, 103.0],
            "huevo": [100.0, 104.0],
        },
        index=_periodos,
    ).T
    return SerieNormalizada(df, {g: g.capitalize() for g in df.index})


def test_subindice_genera_indices_por_categoria() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    indices = sorted(r.df.index.get_level_values("indice").unique())
    assert indices == ["alimentos", "servicios"]


def test_subindice_valores_correctos_periodo_base_es_100() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    p0 = _periodos[0]
    assert r.df.at[(p0, "alimentos"), "indice_replicado"] == pytest.approx(100.0)
    assert r.df.at[(p0, "servicios"), "indice_replicado"] == pytest.approx(100.0)


def test_subindice_alimentos_post_periodo_es_promedio_ponderado() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    p1 = _periodos[1]
    # alimentos: (10*101 + 20*102) / (10+20)
    esperado = (10 * 101.0 + 20 * 102.0) / 30
    assert r.df.at[(p1, "alimentos"), "indice_replicado"] == pytest.approx(esperado)


def test_subindice_reporte_ponderador_esperado_es_del_subgrupo() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    p0 = _periodos[0]
    # ponderador_esperado de alimentos = 10 + 20 = 30
    assert r.reporte.at[(p0, "alimentos"), "ponderador_esperado"] == pytest.approx(30.0)
    # ponderador_esperado de servicios = 30 + 40 = 70
    assert r.reporte.at[(p0, "servicios"), "ponderador_esperado"] == pytest.approx(70.0)


def test_subindice_reporte_genericos_esperados_es_del_subgrupo() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    p0 = _periodos[0]
    assert r.reporte.at[(p0, "alimentos"), "genericos_esperados"] == 2
    assert r.reporte.at[(p0, "servicios"), "genericos_esperados"] == 2


def test_subindice_manifiesto_tipo_es_clasificacion() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "COG")
    assert r.manifiesto[0].tipo == "COG"
