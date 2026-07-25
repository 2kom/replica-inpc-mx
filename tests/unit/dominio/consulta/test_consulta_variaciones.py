from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.consulta.variaciones import (
    inflacion_acumulada,
    inflacion_en,
    inflacion_maxima,
    inflacion_minima,
    inflacion_promedio,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.tipos import ManifestDerivado

_M1 = PeriodoMensual(2024, 1)
_M2 = PeriodoMensual(2024, 2)
_M3 = PeriodoMensual(2024, 3)
_M9 = PeriodoMensual(2099, 9)

# -- helpers -------------------------------------------------------------------


def _rv(
    data: dict[str, list[tuple[PeriodoMensual, float]]],
    *,
    tipo: str = "inpc",
    clase: str = "periodica_mensual",
) -> ResultadoVariacion:
    rows = []
    for indice, pares in data.items():
        for periodo, valor in pares:
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "tipo": tipo,
                    "clase_variacion": clase,
                    "variacion_pp": float(valor),
                    "estado_calculo": "ok",
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = ManifestDerivado(
        id_corrida=["c1"], tipo=tipo, clase=clase, descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    return ResultadoVariacion(df, manifiesto, pd.DataFrame(), pd.DataFrame())


def _rv_multi() -> ResultadoVariacion:
    return _rv(
        {
            "INPC": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)],
            "Alimentos": [(_M1, 5.0), (_M2, -1.0), (_M3, 4.0)],
        }
    )


# -- inflacion_en --------------------------------------------------------------


def test_en_devuelve_dataframe_con_categorias() -> None:
    df = inflacion_en(_rv_multi(), _M2)
    assert list(df.columns) == ["variacion_pp"]
    assert set(df.index) == {"INPC", "Alimentos"}
    assert df.loc["INPC", "variacion_pp"] == pytest.approx(3.0)


def test_en_periodo_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        inflacion_en(_rv_multi(), _M9)


def test_en_no_muta_resultado() -> None:
    r = _rv_multi()
    df = inflacion_en(r, _M2)
    df.loc["INPC", "variacion_pp"] = 999.0
    assert r.df.loc[(_M2, "INPC"), "variacion_pp"] == pytest.approx(3.0)


# -- inflacion_acumulada -------------------------------------------------------


def test_acumulada_suma_el_rango() -> None:
    r = _rv({"INPC": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert inflacion_acumulada(r, _M1, _M3, indice="INPC") == pytest.approx(6.0)


def test_acumulada_hasta_none_usa_ultimo() -> None:
    r = _rv({"INPC": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert inflacion_acumulada(r, _M2, indice="INPC") == pytest.approx(5.0)


def test_acumulada_indice_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        inflacion_acumulada(_rv_multi(), _M1, _M3, indice="Inexistente")


def test_acumulada_desde_posterior_a_hasta_falla() -> None:
    with pytest.raises(InvarianteViolado):
        inflacion_acumulada(_rv_multi(), _M3, _M1, indice="INPC")


def test_acumulada_rango_vacio_falla() -> None:
    # 'Alimentos' existe globalmente y _M2/_M3 existen globalmente,
    # pero 'Alimentos' no tiene filas dentro de [_M2, _M3].
    r = _rv(
        {
            "INPC": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)],
            "Alimentos": [(_M1, 5.0)],
        }
    )
    with pytest.raises(InvarianteViolado):
        inflacion_acumulada(r, _M2, _M3, indice="Alimentos")


# -- inflacion_promedio --------------------------------------------------------


def test_promedio_simple_es_media_aritmetica() -> None:
    r = _rv({"INPC": [(_M1, 1.0), (_M2, 3.0), (_M3, 2.0)]})
    assert inflacion_promedio(r, indice="INPC", metodo="simple") == pytest.approx(2.0)


def test_promedio_tcac_formula_congelada() -> None:
    # Dos variaciones de 10 pp; factor = 1.1 * 1.1 = 1.21; ppy=12, n=2.
    # tcac = (1.21 ** 6 - 1) * 100 = 213.8428376721
    r = _rv({"INPC": [(_M1, 10.0), (_M2, 10.0)]})
    assert inflacion_promedio(r, indice="INPC", metodo="tcac") == pytest.approx(
        213.8428376721
    )


def test_promedio_metodo_invalido_falla() -> None:
    r = _rv({"INPC": [(_M1, 1.0), (_M2, 3.0)]})
    with pytest.raises(InvarianteViolado):
        inflacion_promedio(r, indice="INPC", metodo="geometrico")  # type: ignore[arg-type]


# -- inflacion_maxima / inflacion_minima ---------------------------------------


def test_maxima_global() -> None:
    periodo, indice, valor = inflacion_maxima(_rv_multi())
    assert (periodo, indice, valor) == (_M1, "Alimentos", pytest.approx(5.0))


def test_minima_global() -> None:
    periodo, indice, valor = inflacion_minima(_rv_multi())
    assert (periodo, indice, valor) == (_M2, "Alimentos", pytest.approx(-1.0))


def test_maxima_con_indice() -> None:
    periodo, indice, valor = inflacion_maxima(_rv_multi(), indice="INPC")
    assert (periodo, indice, valor) == (_M2, "INPC", pytest.approx(3.0))


def test_maxima_con_rango() -> None:
    periodo, indice, valor = inflacion_maxima(_rv_multi(), desde=_M2, hasta=_M3)
    assert (periodo, indice, valor) == (_M3, "Alimentos", pytest.approx(4.0))


def test_maxima_indice_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        inflacion_maxima(_rv_multi(), indice="Inexistente")
