from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Vista
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo


def _manifiesto(id_corrida: str = "abc", version: int = 2018, tipo: str = "inpc") -> ManifestCalculo:
    return ManifestCalculo(
        id_corrida=id_corrida,
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador="LaspeyresDirecto",
        ruta_canasta=Path("/tmp/c.csv"),
        ruta_series=Path("/tmp/s.csv"),
        fecha=datetime(2024, 1, 1),
    )


def _df_indice(
    estados: list[str] | None = None,
    version: int = 2018,
    tipo: str = "inpc",
    año: int = 2024,
) -> pd.DataFrame:
    estados = estados or ["ok", "ok"]
    n = len(estados)
    periodos = [PeriodoQuincenal(año, 1, q) for q in range(1, n + 1)]
    idx = pd.MultiIndex.from_tuples(
        [(p, "INPC") for p in periodos], names=["periodo", "indice"]
    )
    return pd.DataFrame(
        {
            "version": [version] * n,
            "tipo": [tipo] * n,
            "indice_replicado": [100.0 + i for i in range(n)],
            "estado_calculo": estados,
            "motivo_error": [None] * n,
        },
        index=idx,
    )


def _reporte_vacio() -> pd.DataFrame:
    return pd.DataFrame({"version": [], "estado_calculo": []})


def _diagnostico_vacio() -> pd.DataFrame:
    return pd.DataFrame({"id_corrida": [], "version": []})


def test_construccion_valida() -> None:
    r = ResultadoIndice(_df_indice(), [_manifiesto()], _reporte_vacio(), _diagnostico_vacio())
    assert r.df.shape == (2, 1)
    assert list(r.df.columns) == ["indice_replicado"]


def test_manifiesto_vacio_falla() -> None:
    with pytest.raises(InvarianteViolado):
        ResultadoIndice(_df_indice(), [], _reporte_vacio(), _diagnostico_vacio())


@pytest.mark.parametrize("falta", ["version", "tipo", "indice_replicado", "estado_calculo"])
def test_df_falta_columna_minima_falla(falta: str) -> None:
    df = _df_indice().drop(columns=[falta])
    with pytest.raises(InvarianteViolado):
        ResultadoIndice(df, [_manifiesto()], _reporte_vacio(), _diagnostico_vacio())


def test_estado_calculo_invalido_falla() -> None:
    df = _df_indice(estados=["ok", "indefinido"])
    with pytest.raises(InvarianteViolado):
        ResultadoIndice(df, [_manifiesto()], _reporte_vacio(), _diagnostico_vacio())


def test_manifiesto_sin_filas_en_df_falla() -> None:
    df = _df_indice(version=2018)
    huerfano = _manifiesto(id_corrida="orphan", version=2024)
    with pytest.raises(InvarianteViolado):
        ResultadoIndice(df, [huerfano], _reporte_vacio(), _diagnostico_vacio())


def test_resultado_retorna_vista() -> None:
    r = ResultadoIndice(_df_indice(), [_manifiesto()], _reporte_vacio(), _diagnostico_vacio())
    vista = r.resultado
    assert isinstance(vista, Vista)
    assert "version" in vista.largo.columns
    assert "estado_calculo" in vista.largo.columns


def test_reporte_y_diagnostico_propagados() -> None:
    rep = pd.DataFrame({"x": [1]})
    diag = pd.DataFrame({"y": [2]})
    r = ResultadoIndice(_df_indice(), [_manifiesto()], rep, diag)
    assert r.reporte is rep
    assert r.diagnostico is diag


def test_periodo_referencia_propagado() -> None:
    p = PeriodoQuincenal(2018, 7, 2)
    r = ResultadoIndice(
        _df_indice(), [_manifiesto()], _reporte_vacio(), _diagnostico_vacio(), periodo_referencia=p
    )
    assert r.periodo_referencia == p


def test_resumen_una_fila_por_manifiesto() -> None:
    m1 = _manifiesto(id_corrida="c1", version=2018)
    m2 = _manifiesto(id_corrida="c2", version=2024)
    df1 = _df_indice(version=2018, año=2018)
    df2 = _df_indice(version=2024, año=2024)
    df = pd.concat([df1, df2])
    r = ResultadoIndice(df, [m1, m2], _reporte_vacio(), _diagnostico_vacio())
    res = r.resumen
    assert list(res.index) == ["c1", "c2"]
    assert list(res.columns) == [
        "version",
        "tipo",
        "estado_calculo",
        "periodo_inicio",
        "periodo_fin",
        "fecha",
    ]
    assert list(res["fecha"]) == [datetime(2024, 1, 1), datetime(2024, 1, 1)]


def test_resumen_peor_estado_segun_severidad() -> None:
    r = ResultadoIndice(
        _df_indice(estados=["ok", "parcial"]),
        [_manifiesto()],
        _reporte_vacio(),
        _diagnostico_vacio(),
    )
    assert r.resumen.loc["abc", "estado_calculo"] == "parcial"


def test_resumen_estado_fallida_mas_severo_que_sin_datos() -> None:
    r = ResultadoIndice(
        _df_indice(estados=["sin_datos", "fallida"]),
        [_manifiesto()],
        _reporte_vacio(),
        _diagnostico_vacio(),
    )
    assert r.resumen.loc["abc", "estado_calculo"] == "fallida"
