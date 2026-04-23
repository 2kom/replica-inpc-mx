import pytest
import pandas as pd

from replica_inpc.dominio.conversion import a_mensual
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_Q1 = PeriodoQuincenal(2024, 1, 1)
_Q2 = PeriodoQuincenal(2024, 1, 2)
_Q3 = PeriodoQuincenal(2024, 2, 1)
_Q4 = PeriodoQuincenal(2024, 2, 2)


def _resultado(*periodos_estados: tuple, version: int = 2024, id_corrida: str = "abc") -> ResultadoCalculo:
    """Crea un ResultadoCalculo quincenal. periodos_estados = (periodo, estado, valor, motivo)."""
    filas = []
    for periodo, estado, valor, motivo in periodos_estados:
        filas.append({
            "periodo": periodo, "indice": "INPC",
            "version": version, "tipo": "inpc",
            "indice_replicado": valor,
            "estado_calculo": estado,
            "motivo_error": motivo,
        })
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    return ResultadoCalculo(df, id_corrida)


def test_ambas_quincenas_ok():
    r = _resultado((_Q1, "ok", 100.0, None), (_Q2, "ok", 102.0, None))
    rm = a_mensual(r)
    assert rm.df["estado_calculo"].iloc[0] == "ok"
    assert rm.df["indice_replicado"].iloc[0] == pytest.approx(101.0)
    assert isinstance(rm.df.index.get_level_values("periodo")[0], PeriodoMensual)


def test_solo_1q_semi_ok():
    r = _resultado((_Q1, "ok", 100.0, None))
    rm = a_mensual(r)
    assert rm.df["estado_calculo"].iloc[0] == "semi_ok"
    assert rm.df["indice_replicado"].iloc[0] == pytest.approx(100.0)


def test_solo_2q_semi_ok():
    r = _resultado((_Q2, "ok", 102.0, None))
    rm = a_mensual(r)
    assert rm.df["estado_calculo"].iloc[0] == "semi_ok"
    assert rm.df["indice_replicado"].iloc[0] == pytest.approx(102.0)


def test_ambas_nan_null_por_faltantes():
    r = _resultado(
        (_Q1, "null_por_faltantes", None, "faltantes"),
        (_Q2, "null_por_faltantes", None, "faltantes"),
    )
    rm = a_mensual(r)
    assert rm.df["estado_calculo"].iloc[0] == "null_por_faltantes"
    assert pd.isna(rm.df["indice_replicado"].iloc[0])


def test_quincena_fallida():
    r = _resultado(
        (_Q1, "ok", 100.0, None),
        (_Q2, "fallida", None, "error de calculo"),
    )
    rm = a_mensual(r)
    assert rm.df["estado_calculo"].iloc[0] == "fallida"
    assert pd.isna(rm.df["indice_replicado"].iloc[0])
    assert rm.df["motivo_error"].iloc[0] == "error de calculo"


def test_id_corrida_preservado():
    r = _resultado((_Q1, "ok", 100.0, None), id_corrida="mi-corrida")
    rm = a_mensual(r)
    assert rm.id_corrida == "mi-corrida"


def test_version_de_2q():
    r = _resultado(
        (_Q1, "ok", 100.0, None),
        (_Q2, "ok", 102.0, None),
    )
    r.df.loc[(slice(None), "INPC"), "version"] = [2018, 2024]
    rm = a_mensual(r)
    assert rm.df["version"].iloc[0] == 2024


def test_multiples_meses():
    r = _resultado(
        (_Q1, "ok", 100.0, None),
        (_Q2, "ok", 102.0, None),
        (_Q3, "ok", 104.0, None),
        (_Q4, "ok", 106.0, None),
    )
    rm = a_mensual(r)
    assert len(rm.df) == 2
    periodos = list(rm.df.index.get_level_values("periodo"))
    assert periodos[0] == PeriodoMensual(2024, 1)
    assert periodos[1] == PeriodoMensual(2024, 2)


def test_input_mensual_invalido():
    idx = pd.MultiIndex.from_tuples(
        [(PeriodoMensual(2024, 1), "INPC")], names=["periodo", "indice"]
    )
    df = pd.DataFrame(
        {"version": 2024, "tipo": "inpc", "indice_replicado": 100.0,
         "estado_calculo": "ok", "motivo_error": None},
        index=idx,
    )
    r = ResultadoCalculo(df, "abc")
    with pytest.raises(InvarianteViolado, match="quincenal"):
        a_mensual(r)
