from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.variaciones import (
    variacion_acumulada_anual,
    variacion_desde,
    variacion_periodica,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo

# Tabla de lags esperada, independiente de LAG_QUINCENAL/LAG_MENSUAL (docs/diseño.md
# §5.11) — deliberadamente NO importada de _temporal.py: si el productor cambia un lag
# por error, este oráculo no debe moverse con él.
_LAGS_QUINCENAL_ESPERADOS = {
    "quincenal": 1,
    "mensual": 2,
    "bimestral": 4,
    "trimestral": 6,
    "cuatrimestral": 8,
    "semestral": 12,
    "anual": 24,
}
_LAGS_MENSUAL_ESPERADOS = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "cuatrimestral": 4,
    "semestral": 6,
    "anual": 12,
}

# -- helpers -------------------------------------------------------------------


def _indice(
    data: dict[str, list[tuple[object, float | None]]],
    *,
    tipo: str = "INPC",
    version: int = 2018,
    estados: dict[tuple[object, str], str] | None = None,
    reporte: pd.DataFrame | None = None,
) -> ResultadoIndice:
    rows = []
    for indice, pares in data.items():
        for periodo, valor in pares:
            est = "ok" if valor is not None else "sin_datos"
            if estados and (periodo, indice) in estados:
                est = estados[(periodo, indice)]
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if valor is None else float(valor),
                    "estado_calculo": est,
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = [ManifestCalculo(version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
    return ResultadoIndice(
        df,
        manifiesto,
        reporte if reporte is not None else pd.DataFrame(),
        pd.DataFrame(),
    )


_Q1 = PeriodoQuincenal(2024, 1, 1)
_Q2 = PeriodoQuincenal(2024, 1, 2)
_Q3 = PeriodoQuincenal(2024, 2, 1)
_Q4 = PeriodoQuincenal(2024, 2, 2)


def _indice_quincenal() -> ResultadoIndice:
    return _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0), (_Q3, 106.0), (_Q4, 109.0)]})


# -- variacion_periodica -------------------------------------------------------


def test_periodica_retorna_resultado_variacion() -> None:
    r = variacion_periodica(_indice_quincenal(), "quincenal")
    assert isinstance(r, ResultadoVariacion)


def test_periodica_clase_embebe_frecuencia() -> None:
    r = variacion_periodica(_indice_quincenal(), "quincenal")
    assert (r.resultado.largo["clase_variacion"] == "periodica_quincenal").all()
    assert r.manifiesto.clase == "periodica_quincenal"


def test_periodica_valores_en_pp() -> None:
    r = variacion_periodica(_indice_quincenal(), "quincenal")
    assert r.df["variacion_pp"].tolist() == pytest.approx(
        [3.0, 106 / 103 * 100 - 100, 109 / 106 * 100 - 100]
    )


def test_periodica_primer_periodo_sin_base_ausente() -> None:
    r = variacion_periodica(_indice_quincenal(), "quincenal")
    assert _Q1 not in r.df.index.get_level_values("periodo")
    assert len(r.df) == 3


def test_periodica_frecuencia_invalida_falla() -> None:
    with pytest.raises(InvarianteViolado):
        variacion_periodica(_indice_quincenal(), "decenal")  # type: ignore[arg-type]


def test_periodica_quincenal_sobre_mensual_falla() -> None:
    mensual = _indice(
        {"INPC": [(PeriodoMensual(2024, 1), 100.0), (PeriodoMensual(2024, 2), 101.0)]}
    )
    with pytest.raises(InvarianteViolado):
        variacion_periodica(mensual, "quincenal")


def test_periodica_sin_filas_computables_falla() -> None:
    solo_uno = _indice({"INPC": [(_Q1, 100.0)]})
    with pytest.raises(InvarianteViolado):
        variacion_periodica(solo_uno, "quincenal")


def test_periodica_estado_parcial_propagado() -> None:
    indice = _indice(
        {"INPC": [(_Q1, 100.0), (_Q2, 103.0)]},
        estados={(_Q2, "INPC"): "parcial"},
    )
    r = variacion_periodica(indice, "quincenal")
    assert r.resultado.largo.loc[(_Q2, "INPC"), "estado_calculo"] == "parcial"  # type: ignore[index]


def test_periodica_fuente_sin_datos_ausente_y_en_reporte() -> None:
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0), (_Q3, None), (_Q4, 109.0)]})
    r = variacion_periodica(indice, "quincenal")
    assert (_Q3, "INPC") not in r.df.index
    assert (_Q3, "INPC") in r.reporte.index
    assert r.reporte.loc[(_Q3, "INPC"), "estado_calculo"] == "sin_datos"  # type: ignore[index]


def test_periodica_base_cero_falla() -> None:
    indice = _indice({"INPC": [(_Q1, 0.0), (_Q2, 103.0)]})
    with pytest.raises(InvarianteViolado):
        variacion_periodica(indice, "quincenal")


def test_periodica_base_no_finita_falla() -> None:
    indice = _indice({"INPC": [(_Q1, float("inf")), (_Q2, 103.0)]})
    with pytest.raises(InvarianteViolado):
        variacion_periodica(indice, "quincenal")


def test_periodica_overflow_en_variacion_falla() -> None:
    # Ambos extremos finitos; el cociente 1e308/1e-308 desborda a inf.
    indice = _indice({"INPC": [(_Q1, 1e-308), (_Q2, 1e308)]})
    with pytest.raises(InvarianteViolado):
        variacion_periodica(indice, "quincenal")


def test_periodica_numerador_cero_acepta_menos_cien() -> None:
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 0.0)]})
    r = variacion_periodica(indice, "quincenal")
    assert r.df.loc[(_Q2, "INPC"), "variacion_pp"] == pytest.approx(-100.0)  # type: ignore[index]


def test_periodica_manifiesto_y_diagnostico() -> None:
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0), (_Q3, None), (_Q4, 109.0)]})
    r = variacion_periodica(indice, "quincenal")
    assert r.manifiesto.versiones == [2018]
    assert len(r.diagnostico) == 3
    assert r.indices_parciales is None


def _avanzar_quincenas(base: PeriodoQuincenal, pasos: int) -> PeriodoQuincenal:
    """Avanza `pasos` quincenas desde `base`, quincena por quincena.

    Implementación propia (loop, no aritmética de ordinal), deliberadamente
    independiente de `restar_quincenas` de producción: si fixture y lookup
    comparten la misma función, un bug de desplazamiento en esa función se
    cancela entre ambos lados y el test queda ciego a él.
    """
    año, mes, quincena = base.año, base.mes, base.quincena
    for _ in range(pasos):
        if quincena == 1:
            quincena = 2
        else:
            quincena = 1
            mes, año = (1, año + 1) if mes == 12 else (mes + 1, año)
    return PeriodoQuincenal(año, mes, quincena)


def _serie_quincenal_n(n: int) -> ResultadoIndice:
    periodos = [_avanzar_quincenas(_Q1, i) for i in range(n)]
    valores = [100.0 + 3.0 * i for i in range(n)]
    return _indice({"INPC": list(zip(periodos, valores))})


@pytest.mark.parametrize(("frecuencia", "lag"), sorted(_LAGS_QUINCENAL_ESPERADOS.items()))
def test_periodica_todas_las_frecuencias_quincenales(frecuencia: str, lag: int) -> None:
    n = lag + 2
    r = variacion_periodica(_serie_quincenal_n(n), frecuencia)  # type: ignore[arg-type]
    assert (r.resultado.largo["clase_variacion"] == f"periodica_{frecuencia}").all()
    ultimo = _avanzar_quincenas(_Q1, n - 1)
    val_t = 100.0 + 3.0 * (n - 1)
    val_base = 100.0 + 3.0 * (n - 1 - lag)
    esperado = (val_t / val_base - 1.0) * 100.0
    assert r.df.loc[(ultimo, "INPC"), "variacion_pp"] == pytest.approx(esperado)  # type: ignore[index]


def _avanzar_meses(base: PeriodoMensual, pasos: int) -> PeriodoMensual:
    """Avanza `pasos` meses desde `base`, mes por mes — misma razón que `_avanzar_quincenas`."""
    año, mes = base.año, base.mes
    for _ in range(pasos):
        mes, año = (1, año + 1) if mes == 12 else (mes + 1, año)
    return PeriodoMensual(año, mes)


def _serie_mensual_n(n: int, base: PeriodoMensual) -> ResultadoIndice:
    periodos = [_avanzar_meses(base, i) for i in range(n)]
    valores = [100.0 + 3.0 * i for i in range(n)]
    return _indice({"INPC": list(zip(periodos, valores))})


@pytest.mark.parametrize(("frecuencia", "lag"), sorted(_LAGS_MENSUAL_ESPERADOS.items()))
def test_periodica_todas_las_frecuencias_mensuales(frecuencia: str, lag: int) -> None:
    n = lag + 2
    base = PeriodoMensual(2020, 1)
    r = variacion_periodica(_serie_mensual_n(n, base), frecuencia)  # type: ignore[arg-type]
    assert (r.resultado.largo["clase_variacion"] == f"periodica_{frecuencia}").all()
    ultimo = _avanzar_meses(base, n - 1)
    val_t = 100.0 + 3.0 * (n - 1)
    val_base = 100.0 + 3.0 * (n - 1 - lag)
    esperado = (val_t / val_base - 1.0) * 100.0
    assert r.df.loc[(ultimo, "INPC"), "variacion_pp"] == pytest.approx(esperado)  # type: ignore[index]


# -- variacion_acumulada_anual -------------------------------------------------


def test_acumulada_base_diciembre_anio_anterior() -> None:
    indice = _indice(
        {"INPC": [(PeriodoQuincenal(2023, 12, 2), 100.0), (PeriodoQuincenal(2024, 12, 2), 110.0)]}
    )
    r = variacion_acumulada_anual(indice)
    assert (r.resultado.largo["clase_variacion"] == "acumulada_anual").all()
    assert r.df.loc[(PeriodoQuincenal(2024, 12, 2), "INPC"), "variacion_pp"] == pytest.approx(  # type: ignore[index]
        10.0
    )
    assert len(r.df) == 1


def test_acumulada_base_diciembre_mensual() -> None:
    indice = _indice(
        {"INPC": [(PeriodoMensual(2023, 12), 100.0), (PeriodoMensual(2024, 12), 108.0)]}
    )
    r = variacion_acumulada_anual(indice)
    assert r.df.loc[(PeriodoMensual(2024, 12), "INPC"), "variacion_pp"] == pytest.approx(  # type: ignore[index]
        8.0
    )


def test_acumulada_periodo_ordinario_enero() -> None:
    indice = _indice(
        {
            "INPC": [
                (PeriodoQuincenal(2023, 12, 2), 100.0),
                (PeriodoQuincenal(2024, 1, 1), 101.0),
                (PeriodoQuincenal(2024, 1, 2), 102.0),
            ]
        }
    )
    r = variacion_acumulada_anual(indice)
    assert r.df.loc[(PeriodoQuincenal(2024, 1, 1), "INPC"), "variacion_pp"] == pytest.approx(  # type: ignore[index]
        1.0
    )
    assert r.df.loc[(PeriodoQuincenal(2024, 1, 2), "INPC"), "variacion_pp"] == pytest.approx(  # type: ignore[index]
        2.0
    )


# -- variacion_desde -----------------------------------------------------------


def _indice_dos() -> ResultadoIndice:
    return _indice({"A": [(_Q1, 100.0), (_Q2, 110.0)], "B": [(_Q1, 100.0), (_Q2, 90.0)]})


def test_desde_una_fila_por_indice() -> None:
    r = variacion_desde(_indice_dos(), _Q1, _Q2)
    assert len(r.df) == 2
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}


def test_desde_valores_correctos() -> None:
    r = variacion_desde(_indice_dos(), _Q1, _Q2)
    assert r.df.loc[(_Q2, "A"), "variacion_pp"] == pytest.approx(10.0)  # type: ignore[index]
    assert r.df.loc[(_Q2, "B"), "variacion_pp"] == pytest.approx(-10.0)  # type: ignore[index]


def test_desde_indices_parciales_vacio_si_exacto() -> None:
    r = variacion_desde(_indice_dos(), _Q1, _Q2)
    assert r.indices_parciales is not None
    assert r.indices_parciales.empty
    assert list(r.indices_parciales.columns) == ["periodo_desde_real", "periodo_hasta_real"]


def test_desde_incluir_parciales_ajusta_periodo() -> None:
    indice = _indice(
        {
            "A": [(_Q1, 100.0), (_Q2, 95.0), (_Q3, 110.0)],
            "B": [(_Q1, None), (_Q2, 95.0), (_Q3, 90.0)],
        }
    )
    r = variacion_desde(indice, _Q1, _Q3, incluir_parciales=True)
    assert len(r.df) == 2
    assert r.indices_parciales.loc["B", "periodo_desde_real"] == _Q2  # type: ignore[union-attr]
    assert r.df.loc[(_Q3, "B"), "variacion_pp"] == pytest.approx(  # type: ignore[index]
        90 / 95 * 100 - 100
    )


def test_desde_sin_parciales_excluye_indice() -> None:
    indice = _indice(
        {
            "A": [(_Q1, 100.0), (_Q3, 110.0)],
            "B": [(_Q1, None), (_Q3, 90.0)],
        }
    )
    r = variacion_desde(indice, _Q1, _Q3, incluir_parciales=False)
    assert set(r.df.index.get_level_values("indice")) == {"A"}
    assert len(r.diagnostico) == 1


def test_desde_sin_parciales_excluye_indice_con_estado_parcial() -> None:
    indice = _indice(
        {"A": [(_Q1, 100.0), (_Q2, 110.0)], "B": [(_Q1, 100.0), (_Q2, 90.0)]},
        estados={(_Q2, "A"): "parcial"},
    )
    r_con = variacion_desde(indice, _Q1, _Q2, incluir_parciales=True)
    assert set(r_con.df.index.get_level_values("indice")) == {"A", "B"}
    r_sin = variacion_desde(indice, _Q1, _Q2, incluir_parciales=False)
    assert set(r_sin.df.index.get_level_values("indice")) == {"B"}


def test_desde_hasta_anterior_a_desde_falla() -> None:
    with pytest.raises(InvarianteViolado):
        variacion_desde(_indice_dos(), _Q2, _Q1)


def test_desde_periodo_inexistente_falla() -> None:
    with pytest.raises(InvarianteViolado):
        variacion_desde(_indice_dos(), PeriodoQuincenal(2099, 1, 1), _Q2)


def test_desde_base_cero_falla() -> None:
    indice = _indice({"A": [(_Q1, 0.0), (_Q2, 110.0)]})
    with pytest.raises(InvarianteViolado):
        variacion_desde(indice, _Q1, _Q2)


def test_desde_extremo_no_finito_falla() -> None:
    indice = _indice({"A": [(_Q1, 100.0), (_Q2, float("inf"))]})
    with pytest.raises(InvarianteViolado):
        variacion_desde(indice, _Q1, _Q2)


def test_desde_overflow_en_variacion_falla() -> None:
    # Ambos extremos finitos; el cociente 1e308/1e-308 desborda a inf.
    indice = _indice({"A": [(_Q1, 1e-308), (_Q2, 1e308)]})
    with pytest.raises(InvarianteViolado):
        variacion_desde(indice, _Q1, _Q2)


def test_desde_numerador_cero_acepta_menos_cien() -> None:
    indice = _indice({"A": [(_Q1, 100.0), (_Q2, 0.0)]})
    r = variacion_desde(indice, _Q1, _Q2)
    assert r.df.loc[(_Q2, "A"), "variacion_pp"] == pytest.approx(-100.0)  # type: ignore[index]


def test_desde_hasta_none_usa_ultimo_periodo() -> None:
    r = variacion_desde(_indice_dos(), _Q1)
    assert set(r.df.index.get_level_values("periodo")) == {_Q2}


def test_desde_incluir_parciales_ajusta_periodo_hasta() -> None:
    indice = _indice(
        {
            "A": [(_Q1, 100.0), (_Q2, 105.0), (_Q3, 110.0)],
            "B": [(_Q1, 100.0), (_Q2, 105.0), (_Q3, None)],
        }
    )
    r = variacion_desde(indice, _Q1, _Q3, incluir_parciales=True)
    assert r.indices_parciales.loc["B", "periodo_hasta_real"] == _Q2  # type: ignore[union-attr]
    assert r.df.loc[(_Q2, "B"), "variacion_pp"] == pytest.approx(5.0)  # type: ignore[index]


def test_desde_reporte_usa_periodos_efectivos_no_los_solicitados() -> None:
    # "B" cae por ambos lados (falta en _Q1/_Q4 -> desde_real=_Q2, hasta_real=_Q3).
    # version/cobertura llevan un valor centinela en los periodos NOMINALES
    # (_Q1/_Q4, version=2010) distinto de los reales (_Q2=2013, _Q3=2018) para
    # que, si _construir_fila_reporte alguna vez vuelve a leer el periodo
    # pedido en vez del resuelto, el assert lo note. 2010/2013/2018 son
    # VersionCanasta válidas (no un centinela fuera de rango como 9999).
    filas = [
        {
            "periodo": _Q1,
            "indice": "B",
            "version": 2010,
            "tipo": "INPC",
            "indice_replicado": float("nan"),
            "estado_calculo": "sin_datos",
        },
        {
            "periodo": _Q2,
            "indice": "B",
            "version": 2013,
            "tipo": "INPC",
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
        },
        {
            "periodo": _Q3,
            "indice": "B",
            "version": 2018,
            "tipo": "INPC",
            "indice_replicado": 120.0,
            "estado_calculo": "ok",
        },
        {
            "periodo": _Q4,
            "indice": "B",
            "version": 2010,
            "tipo": "INPC",
            "indice_replicado": float("nan"),
            "estado_calculo": "sin_datos",
        },
    ]
    df = pd.DataFrame(filas).set_index(["periodo", "indice"])
    reporte_fuente = pd.DataFrame(
        {"cobertura_genericos_pct": [999.0, 40.0, 80.0, 999.0]},
        index=pd.MultiIndex.from_tuples(
            [(_Q1, "B"), (_Q2, "B"), (_Q3, "B"), (_Q4, "B")], names=["periodo", "indice"]
        ),
    )
    manifiesto = [
        ManifestCalculo(2010, "INPC", "LaspeyresDirecto"),
        ManifestCalculo(2013, "INPC", "LaspeyresDirecto"),
        ManifestCalculo(2018, "INPC", "LaspeyresDirecto"),
    ]
    indice = ResultadoIndice(df, manifiesto, reporte_fuente, pd.DataFrame())

    r = variacion_desde(indice, _Q1, _Q4, incluir_parciales=True)

    assert r.indices_parciales.loc["B", "periodo_desde_real"] == _Q2  # type: ignore[union-attr]
    assert r.indices_parciales.loc["B", "periodo_hasta_real"] == _Q3  # type: ignore[union-attr]

    fila_reporte: pd.Series = r.reporte.loc[(_Q3, "B")]  # type: ignore[index,assignment]
    assert fila_reporte["periodo_lag"] == _Q2
    assert fila_reporte["indice_t"] == pytest.approx(120.0)
    assert fila_reporte["indice_lag"] == pytest.approx(100.0)
    assert fila_reporte["version_t"] == 2018
    assert fila_reporte["version_lag"] == 2013
    assert fila_reporte["cobertura_pct_t"] == pytest.approx(80.0)
    assert fila_reporte["cobertura_pct_lag"] == pytest.approx(40.0)


def test_desde_ningun_indice_computable_falla() -> None:
    indice = _indice({"A": [(_Q1, None), (_Q2, None)]})
    with pytest.raises(InvarianteViolado):
        variacion_desde(indice, _Q1, _Q2, incluir_parciales=False)


# -- cobertura -----------------------------------------------------------------


def test_reporte_propaga_cobertura_del_fuente() -> None:
    reporte = pd.DataFrame(
        {"cobertura_genericos_pct": [88.0, 90.0]},
        index=pd.MultiIndex.from_tuples(
            [(_Q1, "INPC"), (_Q2, "INPC")], names=["periodo", "indice"]
        ),
    )
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0)]}, reporte=reporte)
    r = variacion_periodica(indice, "quincenal")
    assert r.reporte.loc[(_Q2, "INPC"), "cobertura_pct_t"] == pytest.approx(  # type: ignore[index]
        90.0
    )
    assert r.reporte.loc[(_Q2, "INPC"), "cobertura_pct_lag"] == pytest.approx(  # type: ignore[index]
        88.0
    )
