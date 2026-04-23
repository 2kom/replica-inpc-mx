import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_pq = PeriodoQuincenal(2024, 7, 2)
_pm = PeriodoMensual(2024, 7)


def _df_base(periodo, estado: str = "ok", indice_replicado: float | None = 100.0, motivo_error: str | None = None):
    idx = pd.MultiIndex.from_tuples([(periodo, "INPC")], names=["periodo", "indice"])
    return pd.DataFrame(
        {
            "version": 2024,
            "tipo": "inpc",
            "indice_replicado": indice_replicado,
            "estado_calculo": estado,
            "motivo_error": motivo_error,
        },
        index=idx,
    )


def test_construccion_quincenal_valida():
    r = ResultadoCalculo(_df_base(_pq), "abc")
    assert r.id_corrida == "abc"


def test_construccion_mensual_valida():
    r = ResultadoCalculo(_df_base(_pm), "abc")
    assert r.id_corrida == "abc"


def test_semi_ok_valido():
    df = _df_base(_pm, estado="semi_ok", indice_replicado=102.5)
    r = ResultadoCalculo(df, "abc")
    assert r.df["estado_calculo"].iloc[0] == "semi_ok"


def test_semi_ok_sin_valor_invalido():
    df = _df_base(_pm, estado="semi_ok", indice_replicado=None, motivo_error="solo 1q")
    with pytest.raises(InvarianteViolado, match="semi_ok"):
        ResultadoCalculo(df, "abc")


def test_tipo_homogeneo_mezcla_invalida():
    idx = pd.MultiIndex.from_tuples(
        [(_pq, "INPC"), (_pm, "INPC")], names=["periodo", "indice"]
    )
    df = pd.DataFrame(
        {
            "version": 2024,
            "tipo": "inpc",
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    with pytest.raises(InvarianteViolado, match="mismo tipo"):
        ResultadoCalculo(df, "abc")
