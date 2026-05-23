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


def test_periodos_fuera_de_rango_2018_se_recortan() -> None:
    # Serie con periodos antes de 2Q Jul 2018 (inicio del rango válido de v2018)
    periodos_con_extra = [
        PeriodoQuincenal(2018, 1, 1),
        PeriodoQuincenal(2018, 7, 1),
        PeriodoQuincenal(2018, 7, 2),  # inicio válido
        PeriodoQuincenal(2018, 8, 1),
    ]
    df = pd.DataFrame(
        {
            "arroz": [99, 99, 100, 101],
            "frijol": [99, 99, 100, 102],
            "leche": [99, 99, 100, 103],
            "huevo": [99, 99, 100, 104],
        },
        index=periodos_con_extra,
    ).T
    serie_extra = SerieNormalizada(df, {g: g.capitalize() for g in df.index})

    r = LaspeyresDirecto().calcular(_canasta(), serie_extra, "c1", "inpc")

    periodos_resultado = r.df.index.get_level_values("periodo").tolist()
    assert PeriodoQuincenal(2018, 1, 1) not in periodos_resultado
    assert PeriodoQuincenal(2018, 7, 1) not in periodos_resultado
    assert PeriodoQuincenal(2018, 7, 2) in periodos_resultado
    assert PeriodoQuincenal(2018, 8, 1) in periodos_resultado


def test_nan_parcial_produce_estado_rellenado() -> None:
    # arroz sin dato en 2Q Aug 2018 — otros genéricos sí tienen dato
    periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1), PeriodoQuincenal(2018, 8, 2)]
    df = pd.DataFrame(
        {"arroz": [100.0, None, 102.0], "frijol": [100.0, 102.0, 104.0],
         "leche": [100.0, 103.0, 106.0], "huevo": [100.0, 104.0, 108.0]},
        index=periodos,
    ).T
    serie = SerieNormalizada(df, {g: g.capitalize() for g in df.index})

    r = LaspeyresDirecto().calcular(_canasta(), serie, "c1", "inpc")

    largo = r.resultado.largo
    estados = dict(zip(largo.index.get_level_values("periodo"), largo["estado_calculo"]))
    assert estados[PeriodoQuincenal(2018, 8, 1)] == "rellenado"
    assert estados[PeriodoQuincenal(2018, 7, 2)] == "ok"
    assert estados[PeriodoQuincenal(2018, 8, 2)] == "ok"
    assert r.df.loc[(PeriodoQuincenal(2018, 8, 1), "INPC"), "indice_replicado"] is not None


def test_nan_total_generico_produce_sin_datos() -> None:
    # arroz con NaN en TODOS los periodos — no hay valor adyacente con qué rellenar
    periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]
    df = pd.DataFrame(
        {"arroz": [None, None], "frijol": [100.0, 102.0],
         "leche": [100.0, 103.0], "huevo": [100.0, 104.0]},
        index=periodos,
    ).T
    serie = SerieNormalizada(df, {g: g.capitalize() for g in df.index})

    r = LaspeyresDirecto().calcular(_canasta(), serie, "c1", "inpc")

    # Ningún periodo queda "rellenado" — arroz all-NaN no puede rellenarse
    assert "rellenado" not in r.resultado.largo["estado_calculo"].values


def test_sin_nan_no_produce_estado_rellenado() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "c1", "inpc")
    largo = r.resultado.largo
    assert "rellenado" not in largo["estado_calculo"].values
    assert (largo["estado_calculo"] == "ok").all()
