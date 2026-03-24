import pandas as pd
import pytest

from replica_inpc.dominio.periodos import Periodo


def test_construccion_valida():
    # test de construccion valida de un periodo
    p = Periodo(2018, 1, 1)
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


def test_quincena_invalida():
    # test de construccion con quincena invalida
    with pytest.raises(ValueError):
        Periodo(2018, 1, 3)


def test_mes_invalido():
    # test de construccion con mes invalido
    with pytest.raises(ValueError):
        Periodo(2018, 13, 1)


def test_año_invalido():
    # test de construccion con año invalido
    with pytest.raises(ValueError):
        Periodo(-2018, 1, 1)


def test_desde_str_valido():
    # test de construccion desde string valido
    p = Periodo.desde_str("1Q Ene 2018")
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


def test_str_invalido():
    # test de construccion desde string con formato invalido
    with pytest.raises(ValueError):
        Periodo.desde_str("formato incorrecto")


def test_orden():
    # test de orden entre periodos
    p1 = Periodo(2018, 1, 1)
    p2 = Periodo(2018, 1, 2)
    p3 = Periodo(2018, 2, 1)

    assert p1 < p2 < p3
    assert sorted([p3, p1, p2]) == [p1, p2, p3]


def test_hash():
    # test de hash de periodos
    p1 = Periodo(2018, 1, 1)
    p2 = Periodo(2018, 1, 1)

    assert hash(p1) == hash(p2)
    assert len({p1, p2}) == 1  # mismo elemento, no se duplica en el set


def test_to_timestamp():
    # test de conversion a timestamp
    assert Periodo(2018, 1, 1).to_timestamp() == pd.Timestamp(2018, 1, 1)
    assert Periodo(2018, 1, 2).to_timestamp() == pd.Timestamp(2018, 1, 16)
