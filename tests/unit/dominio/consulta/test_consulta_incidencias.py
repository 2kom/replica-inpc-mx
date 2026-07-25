from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.consulta.incidencias import (
    incidencia_acumulada,
    incidencia_en,
    incidencia_promedio,
    mayor_incidencia,
    menor_incidencia,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.tipos import ManifestDerivado

_M1 = PeriodoMensual(2024, 1)
_M2 = PeriodoMensual(2024, 2)
_M3 = PeriodoMensual(2024, 3)
_M9 = PeriodoMensual(2099, 9)

# -- helpers -------------------------------------------------------------------


def _ri(
    data: dict[str, list[tuple[PeriodoMensual, float]]],
    *,
    tipo: str = "inflacion componente",
    clase: str = "periodica_mensual",
) -> ResultadoIncidencia:
    rows = []
    for indice, pares in data.items():
        for periodo, valor in pares:
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "tipo": tipo,
                    "clase_incidencia": clase,
                    "incidencia_pp": float(valor),
                    "estado_calculo": "ok",
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = ManifestDerivado(
        id_corrida=["ci", "cc"], tipo=tipo, clase=clase, descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    return ResultadoIncidencia(df, manifiesto, pd.DataFrame(), pd.DataFrame())


def _ri_multi() -> ResultadoIncidencia:
    return _ri(
        {
            "subyacente": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)],
            "no subyacente": [(_M1, 5.0), (_M2, -1.0), (_M3, 4.0)],
        }
    )


# -- incidencia_en -------------------------------------------------------------


def test_en_devuelve_dataframe_con_categorias() -> None:
    df = incidencia_en(_ri_multi(), _M2)
    assert list(df.columns) == ["incidencia_pp"]
    assert set(df.index) == {"subyacente", "no subyacente"}
    assert df.loc["subyacente", "incidencia_pp"] == pytest.approx(3.0)


def test_en_periodo_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        incidencia_en(_ri_multi(), _M9)


def test_en_no_muta_resultado() -> None:
    r = _ri_multi()
    df = incidencia_en(r, _M2)
    df.loc["subyacente", "incidencia_pp"] = 999.0
    assert r.df.loc[(_M2, "subyacente"), "incidencia_pp"] == pytest.approx(3.0)


# -- incidencia_acumulada ------------------------------------------------------


def test_acumulada_suma_el_rango() -> None:
    r = _ri({"subyacente": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert incidencia_acumulada(r, _M1, _M3, indice="subyacente") == pytest.approx(6.0)


def test_acumulada_hasta_none_usa_ultimo() -> None:
    r = _ri({"subyacente": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert incidencia_acumulada(r, _M2, indice="subyacente") == pytest.approx(5.0)


def test_acumulada_indice_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        incidencia_acumulada(_ri_multi(), _M1, _M3, indice="inexistente")


def test_acumulada_desde_posterior_a_hasta_falla() -> None:
    with pytest.raises(InvarianteViolado):
        incidencia_acumulada(_ri_multi(), _M3, _M1, indice="subyacente")


def test_acumulada_rango_vacio_falla() -> None:
    # 'no subyacente' existe globalmente y _M2/_M3 existen globalmente,
    # pero 'no subyacente' no tiene filas dentro de [_M2, _M3].
    r = _ri(
        {
            "subyacente": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)],
            "no subyacente": [(_M1, 5.0)],
        }
    )
    with pytest.raises(InvarianteViolado):
        incidencia_acumulada(r, _M2, _M3, indice="no subyacente")


# -- incidencia_promedio -------------------------------------------------------


def test_promedio_es_media_aritmetica() -> None:
    r = _ri({"subyacente": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert incidencia_promedio(r, indice="subyacente") == pytest.approx(2.0)


# -- mayor_incidencia / menor_incidencia ---------------------------------------


def test_mayor_global() -> None:
    periodo, indice, valor = mayor_incidencia(_ri_multi())
    assert (periodo, indice, valor) == (_M1, "no subyacente", pytest.approx(5.0))


def test_menor_global() -> None:
    periodo, indice, valor = menor_incidencia(_ri_multi())
    assert (periodo, indice, valor) == (_M2, "no subyacente", pytest.approx(-1.0))


def test_mayor_con_indice() -> None:
    periodo, indice, valor = mayor_incidencia(_ri_multi(), indice="subyacente")
    assert (periodo, indice, valor) == (_M2, "subyacente", pytest.approx(3.0))


def test_mayor_con_rango() -> None:
    periodo, indice, valor = mayor_incidencia(_ri_multi(), desde=_M2, hasta=_M3)
    assert (periodo, indice, valor) == (_M3, "no subyacente", pytest.approx(4.0))


def test_mayor_indice_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        mayor_incidencia(_ri_multi(), indice="inexistente")
