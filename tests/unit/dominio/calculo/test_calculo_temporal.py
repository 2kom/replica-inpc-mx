from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo._temporal import (
    LAG_MENSUAL,
    LAG_QUINCENAL,
    es_mensual,
    resolver_extremo,
    restar_meses,
    restar_quincenas,
)
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

# --------------------------------------------------------------------------- helpers


def _avanzar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    """Avance por loop, sin aritmética ordinal — referencia independiente.

    Reimplementa el desplazamiento con otro mecanismo A PROPÓSITO: un test que
    calculara el esperado con la misma fórmula ordinal que el código pasaría
    aunque esa fórmula estuviera mal. Ya pasó una vez en este proyecto —
    mutar `restar_quincenas` para duplicar el desplazamiento dejaba la suite
    en verde (ver la auditoría de `variaciones.py`).
    """
    año, mes, quincena = periodo.año, periodo.mes, periodo.quincena
    for _ in range(n):
        if quincena == 2:
            quincena = 1
            mes = mes + 1 if mes < 12 else 1
            año = año if mes != 1 else año + 1
        else:
            quincena = 2
    return PeriodoQuincenal(año, mes, quincena)


def _avanzar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    """Ídem `_avanzar_quincenas`, por loop y sin ordinal."""
    año, mes = periodo.año, periodo.mes
    for _ in range(n):
        mes = mes + 1 if mes < 12 else 1
        año = año if mes != 1 else año + 1
    return PeriodoMensual(año, mes)


_QUINCENAS = [
    PeriodoQuincenal(a, m, q) for a in (2010, 2018, 2024) for m in range(1, 13) for q in (1, 2)
]
_MESES = [PeriodoMensual(a, m) for a in (2010, 2018, 2024) for m in range(1, 13)]


# --------------------------------------------------------------------------- restar_quincenas


@pytest.mark.parametrize("n", [1, 2, 4, 6, 8, 12, 24, 25])
def test_restar_quincenas_es_inverso_de_avanzar(n: int) -> None:
    for periodo in _QUINCENAS:
        assert _avanzar_quincenas(restar_quincenas(periodo, n), n) == periodo


def test_restar_quincenas_cruza_el_cambio_de_año() -> None:
    assert restar_quincenas(PeriodoQuincenal(2018, 1, 1), 1) == PeriodoQuincenal(2017, 12, 2)


def test_restar_quincenas_un_año_cae_en_el_mismo_periodo() -> None:
    # 24 quincenas es el lag anual: tiene que caer en el mismo mes y quincena.
    for periodo in _QUINCENAS:
        anterior = restar_quincenas(periodo, LAG_QUINCENAL["anual"])
        assert (anterior.mes, anterior.quincena) == (periodo.mes, periodo.quincena)
        assert anterior.año == periodo.año - 1


def test_restar_quincenas_cero_no_mueve() -> None:
    periodo = PeriodoQuincenal(2018, 6, 2)
    assert restar_quincenas(periodo, 0) == periodo


# --------------------------------------------------------------------------- restar_meses


@pytest.mark.parametrize("n", [1, 2, 3, 4, 6, 12, 13])
def test_restar_meses_es_inverso_de_avanzar(n: int) -> None:
    for periodo in _MESES:
        assert _avanzar_meses(restar_meses(periodo, n), n) == periodo


def test_restar_meses_cruza_el_cambio_de_año() -> None:
    assert restar_meses(PeriodoMensual(2018, 1), 1) == PeriodoMensual(2017, 12)


def test_restar_meses_un_año_cae_en_el_mismo_mes() -> None:
    for periodo in _MESES:
        anterior = restar_meses(periodo, LAG_MENSUAL["anual"])
        assert anterior.mes == periodo.mes
        assert anterior.año == periodo.año - 1


def test_restar_meses_cero_no_mueve() -> None:
    periodo = PeriodoMensual(2018, 6)
    assert restar_meses(periodo, 0) == periodo


# --------------------------------------------------------------------------- tablas de lag


def test_lag_quincenal_es_el_doble_del_mensual() -> None:
    # Una quincena es media mensualidad: si las tablas se desincronizan, una
    # variación "anual" mediría tramos distintos según la periodicidad.
    for frecuencia, meses in LAG_MENSUAL.items():
        assert LAG_QUINCENAL[frecuencia] == meses * 2, frecuencia


def test_solo_la_tabla_quincenal_admite_frecuencia_quincenal() -> None:
    # No existe "variación quincenal" sobre datos mensuales; los llamadores se
    # apoyan en esta ausencia para rechazar la combinación.
    assert "quincenal" in LAG_QUINCENAL
    assert "quincenal" not in LAG_MENSUAL


# --------------------------------------------------------------------------- es_mensual


def _df(periodos: list[PeriodoQuincenal | PeriodoMensual]) -> pd.DataFrame:
    return pd.DataFrame(
        {"v": range(len(periodos))},
        index=pd.MultiIndex.from_arrays(
            [periodos, ["INPC"] * len(periodos)], names=["periodo", "indice"]
        ),
    )


def test_es_mensual_reconoce_periodos_mensuales() -> None:
    assert es_mensual(_df([PeriodoMensual(2018, 1), PeriodoMensual(2018, 2)])) is True


def test_es_mensual_reconoce_periodos_quincenales() -> None:
    assert es_mensual(_df([PeriodoQuincenal(2018, 1, 1), PeriodoQuincenal(2018, 1, 2)])) is False


# --------------------------------------------------------------------------- resolver_extremo


_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)
_P3 = PeriodoQuincenal(2018, 2, 1)
_AUSENTE = PeriodoQuincenal(2018, 3, 1)


@pytest.mark.parametrize("primero", [True, False])
def test_resolver_extremo_devuelve_el_exacto_si_tiene_dato(primero: bool) -> None:
    assert resolver_extremo(_P2, [_P1, _P2, _P3], incluir_parciales=True, primero=primero) == _P2


def test_resolver_extremo_sin_parciales_no_sustituye() -> None:
    assert resolver_extremo(_AUSENTE, [_P1, _P2], incluir_parciales=False, primero=True) is None


def test_resolver_extremo_sin_validos_no_es_computable() -> None:
    assert resolver_extremo(_AUSENTE, [], incluir_parciales=True, primero=True) is None


def test_resolver_extremo_sustituye_por_el_mas_temprano() -> None:
    assert resolver_extremo(_AUSENTE, [_P1, _P2, _P3], incluir_parciales=True, primero=True) == _P1


def test_resolver_extremo_sustituye_por_el_mas_tardio() -> None:
    assert resolver_extremo(_AUSENTE, [_P1, _P2, _P3], incluir_parciales=True, primero=False) == _P3


@pytest.mark.parametrize("primero", [True, False])
def test_resolver_extremo_no_depende_del_orden_de_validos(primero: bool) -> None:
    # Tomar validos[0]/validos[-1] daba el extremo equivocado con una lista
    # desordenada, y sin fallar: devolvia un periodo real, solo que el otro.
    ordenado = [_P1, _P2, _P3]
    desordenado = [_P3, _P1, _P2]
    esperado = resolver_extremo(_AUSENTE, ordenado, incluir_parciales=True, primero=primero)
    assert (
        resolver_extremo(_AUSENTE, desordenado, incluir_parciales=True, primero=primero) == esperado
    )


def test_resolver_extremo_funciona_con_periodos_mensuales() -> None:
    meses = [PeriodoMensual(2018, 3), PeriodoMensual(2018, 1)]
    ausente = PeriodoMensual(2018, 9)
    assert resolver_extremo(ausente, meses, incluir_parciales=True, primero=True) == PeriodoMensual(
        2018, 1
    )
