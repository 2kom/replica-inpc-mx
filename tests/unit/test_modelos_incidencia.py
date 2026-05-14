from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Vista
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestDerivado


def _manifiesto(
    tipo: str = "inpc",
    clase: str = "periodica_mensual",
    descripcion: str = "",
) -> ManifestDerivado:
    return ManifestDerivado(
        id_corrida=["c1", "c2"],
        tipo=tipo,
        clase=clase,
        descripcion=descripcion,
        fecha=datetime(2024, 1, 1),
        inpc_ids=["c1"],
        clasificacion_ids=["c2"],
    )


def _df_inc(
    estados: list[str] | None = None,
    clase: str = "periodica_mensual",
    tipo: str = "inpc",
) -> pd.DataFrame:
    estados = estados or ["ok", "ok"]
    n = len(estados)
    periodos = [PeriodoQuincenal(2024, m, 2) for m in range(1, n + 1)]
    idx = pd.MultiIndex.from_tuples(
        [(p, "INPC") for p in periodos], names=["periodo", "indice"]
    )
    return pd.DataFrame(
        {
            "tipo": [tipo] * n,
            "clase_incidencia": [clase] * n,
            "incidencia_pp": [0.3 + i * 0.1 for i in range(n)],
            "estado_calculo": estados,
            "version_t": [2024] * n,
        },
        index=idx,
    )


def _rep_vacio() -> pd.DataFrame:
    return pd.DataFrame({"estado_calculo": []})


def _diag_vacio() -> pd.DataFrame:
    return pd.DataFrame({"id_corrida": []})


# ---------- Construcción ----------

def test_construccion_valida_periodica() -> None:
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), _rep_vacio(), _diag_vacio())
    assert r.df.shape == (2, 1)


def test_construccion_valida_desde() -> None:
    df = _df_inc(clase="desde")
    ip = pd.DataFrame({"periodo_desde_real": []})
    r = ResultadoIncidencia(
        df, _manifiesto(clase="desde"), _rep_vacio(), _diag_vacio(), indices_parciales=ip
    )
    assert r.indices_parciales is ip


# ---------- Invariantes ----------

@pytest.mark.parametrize("falta", ["tipo", "clase_incidencia", "incidencia_pp", "estado_calculo"])
def test_df_falta_columna_minima_falla(falta: str) -> None:
    df = _df_inc().drop(columns=[falta])
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(), _rep_vacio(), _diag_vacio())


def test_clase_incidencia_heterogenea_falla() -> None:
    df = _df_inc()
    df.loc[df.index[1], "clase_incidencia"] = "periodica_anual"
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(), _rep_vacio(), _diag_vacio())


def test_clase_incidencia_fuera_catalogo_falla() -> None:
    df = _df_inc(clase="inventada")
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(clase="inventada"), _rep_vacio(), _diag_vacio())


def test_desde_sin_indices_parciales_falla() -> None:
    df = _df_inc(clase="desde")
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(clase="desde"), _rep_vacio(), _diag_vacio())


def test_periodica_con_indices_parciales_falla() -> None:
    df = _df_inc(clase="periodica_mensual")
    ip = pd.DataFrame({"x": []})
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(
            df, _manifiesto(clase="periodica_mensual"), _rep_vacio(), _diag_vacio(), indices_parciales=ip
        )


def test_manifiesto_clase_mismatch_falla() -> None:
    df = _df_inc(clase="periodica_mensual")
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(clase="periodica_anual"), _rep_vacio(), _diag_vacio())


def test_df_tipo_heterogeneo_falla() -> None:
    df = _df_inc()
    df.loc[df.index[1], "tipo"] = "inflacion componente"
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(), _rep_vacio(), _diag_vacio())


def test_manifiesto_tipo_mismatch_falla() -> None:
    df = _df_inc(tipo="inpc")
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(tipo="inflacion componente"), _rep_vacio(), _diag_vacio())


@pytest.mark.parametrize("estado_invalido", ["sin_datos", "fallida"])
def test_estado_calculo_invalido_falla(estado_invalido: str) -> None:
    df = _df_inc(estados=["ok", estado_invalido])
    with pytest.raises(InvarianteViolado):
        ResultadoIncidencia(df, _manifiesto(), _rep_vacio(), _diag_vacio())


# ---------- Properties ----------

def test_df_minimal_una_columna() -> None:
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), _rep_vacio(), _diag_vacio())
    assert list(r.df.columns) == ["incidencia_pp"]


def test_resultado_retorna_vista_con_largo_extendido() -> None:
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), _rep_vacio(), _diag_vacio())
    vista = r.resultado
    assert isinstance(vista, Vista)
    for col in ("tipo", "clase_incidencia", "incidencia_pp", "estado_calculo", "version_t"):
        assert col in vista.largo.columns


def test_reporte_y_diagnostico_propagados() -> None:
    rep = pd.DataFrame({"x": [1]})
    diag = pd.DataFrame({"y": [2]})
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), rep, diag)
    assert r.reporte is rep
    assert r.diagnostico is diag


def test_indices_parciales_propagado_con_clase_desde() -> None:
    ip = pd.DataFrame({"periodo_desde_real": [PeriodoQuincenal(2024, 1, 1)]})
    r = ResultadoIncidencia(
        _df_inc(clase="desde"),
        _manifiesto(clase="desde"),
        _rep_vacio(),
        _diag_vacio(),
        indices_parciales=ip,
    )
    assert r.indices_parciales is ip


def test_resumen_una_fila_con_cols_esperadas() -> None:
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), _rep_vacio(), _diag_vacio())
    res = r.resumen
    assert res.shape == (1, 6)
    assert list(res.columns) == [
        "tipo",
        "clase_incidencia",
        "descripcion",
        "estado_calculo",
        "periodo_inicio",
        "periodo_fin",
    ]


def test_resumen_valores_concretos() -> None:
    r = ResultadoIncidencia(
        _df_inc(), _manifiesto(descripcion="ene→feb 2024"), _rep_vacio(), _diag_vacio()
    )
    fila = r.resumen.loc[0]
    assert fila["tipo"] == "inpc"
    assert fila["clase_incidencia"] == "periodica_mensual"
    assert fila["descripcion"] == "ene→feb 2024"
    assert fila["estado_calculo"] == "ok"
    assert fila["periodo_inicio"] == PeriodoQuincenal(2024, 1, 2)
    assert fila["periodo_fin"] == PeriodoQuincenal(2024, 2, 2)


def test_resumen_mezcla_ok_parcial_devuelve_parcial() -> None:
    r = ResultadoIncidencia(
        _df_inc(estados=["ok", "parcial"]), _manifiesto(), _rep_vacio(), _diag_vacio()
    )
    assert r.resumen.loc[0, "estado_calculo"] == "parcial"


def test_manifiesto_propagado() -> None:
    m = _manifiesto(descripcion="x")
    r = ResultadoIncidencia(_df_inc(), m, _rep_vacio(), _diag_vacio())
    assert r.manifiesto is m


def test_repr_html_devuelve_string() -> None:
    r = ResultadoIncidencia(_df_inc(), _manifiesto(), _rep_vacio(), _diag_vacio())
    assert isinstance(r._repr_html_(), str)
