import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado, PeriodoNoInterpretable
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal, periodo_desde_str

# --- Compartidos (validan ambos tipos al mismo tiempo) ---


@pytest.mark.parametrize(
    "cls,args",
    [
        (PeriodoQuincenal, (2018, 13, 1)),  # cota superior
        (PeriodoMensual, (2024, 13)),
        (PeriodoQuincenal, (2018, 0, 1)),  # cota inferior
        (PeriodoMensual, (2024, 0)),
        (PeriodoQuincenal, (2018, -1, 1)),  # negativo
        (PeriodoMensual, (2024, -1)),
    ],
)
def test_mes_invalido(cls, args):
    with pytest.raises(InvarianteViolado):
        cls(*args)


@pytest.mark.parametrize(
    "cls,args",
    [
        (PeriodoQuincenal, (-2018, 1, 1)),  # negativo
        (PeriodoMensual, (-1, 1)),
        (PeriodoQuincenal, (0, 1, 1)),  # cota exacta
        (PeriodoMensual, (0, 1)),
    ],
)
def test_año_invalido(cls, args):
    with pytest.raises(InvarianteViolado):
        cls(*args)


@pytest.mark.parametrize(
    "fn",
    [
        lambda: PeriodoQuincenal.desde_str("formato incorrecto"),  # conteo de palabras
        lambda: PeriodoMensual.desde_str("formato incorrecto x"),
        lambda: PeriodoQuincenal.desde_str("1Q Xyz 2024"),  # mes fuera de catálogo
        lambda: PeriodoMensual.desde_str("Xyz 2024"),
        lambda: PeriodoQuincenal.desde_str("1Q Ene abcd"),  # año no numérico
        lambda: PeriodoMensual.desde_str("Ene abcd"),
    ],
)
def test_desde_str_invalido(fn):
    with pytest.raises(PeriodoNoInterpretable):
        fn()


def test_mensual_cross_type_no_compara():
    p_m = PeriodoMensual(2024, 7)
    p_q = PeriodoQuincenal(2024, 7, 1)
    with pytest.raises(TypeError):
        p_m < p_q  # type: ignore[operator]


def test_quincenal_cross_type_no_compara():
    p_q = PeriodoQuincenal(2024, 7, 1)
    p_m = PeriodoMensual(2024, 7)
    with pytest.raises(TypeError):
        p_q < p_m  # type: ignore[operator]


def test_cross_type_no_son_iguales():
    p_q = PeriodoQuincenal(2024, 7, 1)
    p_m = PeriodoMensual(2024, 7)
    assert p_q != p_m
    assert not (p_q == p_m)


def test_periodo_desde_str_invalido():
    with pytest.raises(PeriodoNoInterpretable):
        periodo_desde_str("formato totalmente incorrecto aqui")


# --- PeriodoQuincenal ---


def test_construccion_valida():
    # test de construccion valida de un periodo
    p = PeriodoQuincenal(2018, 1, 1)
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


@pytest.mark.parametrize("quincena", [0, 3, -1])
def test_quincena_invalida(quincena):
    with pytest.raises(InvarianteViolado):
        PeriodoQuincenal(2018, 1, quincena)


def test_desde_str_valido():
    # test de construccion desde string valido
    p = PeriodoQuincenal.desde_str("1Q Ene 2018")
    assert p.año == 2018
    assert p.mes == 1
    assert p.quincena == 1


def test_desde_str_quincena_invalida_lanza_periodo_no_interpretable():
    # la InvarianteViolado del __init__ queda envuelta por el except generico de
    # desde_str: misma violacion, excepcion distinta segun la ruta de entrada
    with pytest.raises(PeriodoNoInterpretable):
        PeriodoQuincenal.desde_str("3Q Ene 2024")


def test_str():
    assert str(PeriodoQuincenal(2024, 1, 1)) == "1Q Ene 2024"
    assert str(PeriodoQuincenal(2024, 7, 2)) == "2Q Jul 2024"


def test_repr():
    assert repr(PeriodoQuincenal(2024, 7, 2)) == "PeriodoQuincenal(2024, 7, 2)"


def test_eq():
    p1 = PeriodoQuincenal(2018, 1, 1)
    p2 = PeriodoQuincenal(2018, 1, 1)
    p3 = PeriodoQuincenal(2018, 1, 2)
    assert p1 == p2
    assert p1 != p3
    assert p1 != "no es un periodo"


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


def test_periodo_desde_str_quincenal():
    p = periodo_desde_str("1Q Ene 2024")
    assert isinstance(p, PeriodoQuincenal)
    assert p.año == 2024
    assert p.mes == 1
    assert p.quincena == 1


# --- PeriodoMensual ---


def test_mensual_construccion_valida():
    p = PeriodoMensual(2024, 7)
    assert p.año == 2024
    assert p.mes == 7


def test_mensual_str():
    assert str(PeriodoMensual(2024, 1)) == "Ene 2024"
    assert str(PeriodoMensual(2024, 12)) == "Dic 2024"


def test_mensual_repr():
    assert repr(PeriodoMensual(2024, 7)) == "PeriodoMensual(2024, 7)"


def test_mensual_eq():
    p1 = PeriodoMensual(2024, 7)
    p2 = PeriodoMensual(2024, 7)
    p3 = PeriodoMensual(2024, 8)
    assert p1 == p2
    assert p1 != p3
    assert p1 != "no es un periodo"


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


def test_mensual_to_timestamp():
    assert PeriodoMensual(2024, 1).to_timestamp() == pd.Timestamp(2024, 1, 31)
    assert PeriodoMensual(2024, 2).to_timestamp() == pd.Timestamp(2024, 2, 29)  # bisiesto
    assert PeriodoMensual(2023, 2).to_timestamp() == pd.Timestamp(2023, 2, 28)


def test_mensual_desde_str():
    p = PeriodoMensual.desde_str("Jul 2024")
    assert p.año == 2024
    assert p.mes == 7


def test_periodo_desde_str_mensual():
    p = periodo_desde_str("Jul 2024")
    assert isinstance(p, PeriodoMensual)
    assert p.año == 2024
    assert p.mes == 7
