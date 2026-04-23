import pandas as pd
import pytest

from replica_inpc.dominio.errores import PeriodoNoInterpretable
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal, periodo_desde_str


def test_construccion_valida():
    # test de construccion valida de un periodo
    p = PeriodoQuincenal(2018, 1, 1)
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


def test_quincena_invalida():
    # test de construccion con quincena invalida
    with pytest.raises(ValueError):
        PeriodoQuincenal(2018, 1, 3)


def test_mes_invalido():
    # test de construccion con mes invalido
    with pytest.raises(ValueError):
        PeriodoQuincenal(2018, 13, 1)


def test_año_invalido():
    # test de construccion con año invalido
    with pytest.raises(ValueError):
        PeriodoQuincenal(-2018, 1, 1)


def test_desde_str_valido():
    # test de construccion desde string valido
    p = PeriodoQuincenal.desde_str("1Q Ene 2018")
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


def test_str_invalido():
    # test de construccion desde string con formato invalido
    with pytest.raises(PeriodoNoInterpretable):
        PeriodoQuincenal.desde_str("formato incorrecto")


def test_orden():
    # test de orden entre periodos
    p1 = PeriodoQuincenal(2018, 1, 1)
    p2 = PeriodoQuincenal(2018, 1, 2)
    p3 = PeriodoQuincenal(2018, 2, 1)

    assert p1 < p2 < p3
    assert sorted([p3, p1, p2]) == [p1, p2, p3]


def test_hash():
    # test de hash de periodos
    p1 = PeriodoQuincenal(2018, 1, 1)
    p2 = PeriodoQuincenal(2018, 1, 1)

    assert hash(p1) == hash(p2)
    assert len({p1, p2}) == 1  # mismo elemento, no se duplica en el set


def test_to_timestamp():
    assert PeriodoQuincenal(2018, 1, 1).to_timestamp() == pd.Timestamp(2018, 1, 15)
    assert PeriodoQuincenal(2018, 1, 2).to_timestamp() == pd.Timestamp(2018, 1, 31)
    assert PeriodoQuincenal(2024, 2, 2).to_timestamp() == pd.Timestamp(2024, 2, 29)  # bisiesto


# --- PeriodoMensual ---


def test_mensual_construccion_valida():
    p = PeriodoMensual(2024, 7)
    assert p.año == 2024
    assert p.mes == 7


def test_mensual_mes_invalido():
    with pytest.raises(ValueError):
        PeriodoMensual(2024, 13)


def test_mensual_año_invalido():
    with pytest.raises(ValueError):
        PeriodoMensual(-1, 1)


def test_mensual_str():
    assert str(PeriodoMensual(2024, 1)) == "Ene 2024"
    assert str(PeriodoMensual(2024, 12)) == "Dic 2024"


def test_mensual_repr():
    assert repr(PeriodoMensual(2024, 7)) == "PeriodoMensual(2024, 7)"


def test_mensual_hash():
    p1 = PeriodoMensual(2024, 7)
    p2 = PeriodoMensual(2024, 7)
    assert hash(p1) == hash(p2)
    assert len({p1, p2}) == 1


def test_mensual_orden():
    p1 = PeriodoMensual(2024, 1)
    p2 = PeriodoMensual(2024, 6)
    p3 = PeriodoMensual(2025, 1)
    assert p1 < p2 < p3
    assert sorted([p3, p1, p2]) == [p1, p2, p3]


def test_mensual_cross_type_no_compara():
    p_m = PeriodoMensual(2024, 7)
    p_q = PeriodoQuincenal(2024, 7, 1)
    with pytest.raises(TypeError):
        p_m < p_q  # type: ignore[operator]


def test_mensual_to_timestamp():
    assert PeriodoMensual(2024, 1).to_timestamp() == pd.Timestamp(2024, 1, 31)
    assert PeriodoMensual(2024, 2).to_timestamp() == pd.Timestamp(2024, 2, 29)  # bisiesto
    assert PeriodoMensual(2023, 2).to_timestamp() == pd.Timestamp(2023, 2, 28)


def test_mensual_desde_str():
    p = PeriodoMensual.desde_str("Jul 2024")
    assert p.año == 2024
    assert p.mes == 7


def test_mensual_desde_str_invalido():
    with pytest.raises(PeriodoNoInterpretable):
        PeriodoMensual.desde_str("formato incorrecto")


# --- periodo_desde_str ---


def test_periodo_desde_str_quincenal():
    p = periodo_desde_str("1Q Ene 2024")
    assert isinstance(p, PeriodoQuincenal)
    assert p.año == 2024
    assert p.mes == 1
    assert p.quincena == 1


def test_periodo_desde_str_mensual():
    p = periodo_desde_str("Jul 2024")
    assert isinstance(p, PeriodoMensual)
    assert p.año == 2024
    assert p.mes == 7


def test_periodo_desde_str_invalido():
    with pytest.raises(PeriodoNoInterpretable):
        periodo_desde_str("formato totalmente incorrecto aqui")
