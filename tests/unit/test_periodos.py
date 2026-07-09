import operator

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


def test_periodo_desde_str_una_palabra_invalido():
    with pytest.raises(PeriodoNoInterpretable):
        periodo_desde_str("2024")


@pytest.mark.parametrize(
    "texto,cls_esperada,mes_esperado",
    [
        ("2q jul 2024", PeriodoQuincenal, 7),
        ("DIC 2024", PeriodoMensual, 12),
    ],
)
def test_periodo_desde_str_insensible_a_mayusculas(texto, cls_esperada, mes_esperado):
    p = periodo_desde_str(texto)
    assert isinstance(p, cls_esperada)
    assert p.mes == mes_esperado


@pytest.mark.parametrize("texto", ["3Q Ene 2024", "1Q Ene 0", "Ene 0"])
def test_periodo_desde_str_invariante_violado_propaga_limpio(texto):
    # el dispatcher no debe re-envolver InvarianteViolado en PeriodoNoInterpretable
    with pytest.raises(InvarianteViolado):
        periodo_desde_str(texto)


def test_periodo_desde_str_normaliza_espacios_extra():
    p = periodo_desde_str("  2q   jul   2018 ")
    assert p == PeriodoQuincenal(2018, 7, 2)


@pytest.mark.parametrize("op", [operator.le, operator.gt, operator.ge])
def test_cross_type_operadores_derivados_lanzan_typeerror(op):
    # <=, >, >= son derivados por total_ordering a partir de __lt__/__eq__
    p_q = PeriodoQuincenal(2024, 7, 1)
    p_m = PeriodoMensual(2024, 7)
    with pytest.raises(TypeError):
        op(p_q, p_m)


@pytest.mark.parametrize("p", [PeriodoQuincenal(2024, 7, 1), PeriodoMensual(2024, 7)])
def test_orden_contra_tipo_ajeno_lanza_typeerror(p):
    with pytest.raises(TypeError):
        p < 5  # type: ignore[operator]


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


@pytest.mark.parametrize("mes_str", ["jul", "JUL", "Jul", "jUL"])
def test_desde_str_insensible_a_mayusculas(mes_str):
    p = PeriodoQuincenal.desde_str(f"2Q {mes_str} 2024")
    assert p.mes == 7


@pytest.mark.parametrize("quincena_str", ["1q", "1Q", "2q", "2Q"])
def test_desde_str_quincena_insensible_a_mayusculas(quincena_str):
    p = PeriodoQuincenal.desde_str(f"{quincena_str} Ene 2024")
    assert p.quincena == int(quincena_str[0])


def test_desde_str_normaliza_espacios_extra():
    p = PeriodoQuincenal.desde_str("  2Q   Jul   2018 ")
    assert p == PeriodoQuincenal(2018, 7, 2)


@pytest.mark.parametrize(
    "texto",
    [
        "1XYZ Ene 2024",  # digito valido + basura en vez de "Q"
        "199 Ene 2024",  # digitos validos sin sufijo "Q"
        "QQ Ene 2024",  # sin digito
        "Q Ene 2024",  # solo la letra, sin digito
    ],
)
def test_desde_str_quincena_token_malformado_lanza_periodo_no_interpretable(texto):
    with pytest.raises(PeriodoNoInterpretable):
        PeriodoQuincenal.desde_str(texto)


def test_desde_str_quincena_multidigito_fuera_de_rango_lanza_invariante_violado():
    # "12Q": digito completo (12) se parsea, no se trunca a "1"; 12 esta fuera
    # de rango -> InvarianteViolado, no aceptado silenciosamente como quincena=1
    with pytest.raises(InvarianteViolado):
        PeriodoQuincenal.desde_str("12Q Ene 2024")


def test_desde_str_quincena_invalida_lanza_invariante_violado():
    # texto interpretable, valor fuera de rango: InvarianteViolado del __init__
    # sale sin envolver, misma excepcion que la ruta de construccion directa
    with pytest.raises(InvarianteViolado):
        PeriodoQuincenal.desde_str("3Q Ene 2024")


def test_desde_str_año_invalido_lanza_invariante_violado():
    with pytest.raises(InvarianteViolado):
        PeriodoQuincenal.desde_str("1Q Ene 0")


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


@pytest.mark.parametrize("mes_str", ["dic", "DIC", "Dic", "dIC"])
def test_mensual_desde_str_insensible_a_mayusculas(mes_str):
    p = PeriodoMensual.desde_str(f"{mes_str} 2024")
    assert p.mes == 12


def test_mensual_desde_str_normaliza_espacios_extra():
    p = PeriodoMensual.desde_str("  Jul   2018 ")
    assert p == PeriodoMensual(2018, 7)


def test_mensual_desde_str_año_invalido_lanza_invariante_violado():
    with pytest.raises(InvarianteViolado):
        PeriodoMensual.desde_str("Ene 0")


def test_periodo_desde_str_mensual():
    p = periodo_desde_str("Jul 2024")
    assert isinstance(p, PeriodoMensual)
    assert p.año == 2024
    assert p.mes == 7
