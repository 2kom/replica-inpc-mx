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
from replica_inpc.dominio.tipos import ManifestUnidad

# -- helpers -------------------------------------------------------------------


def _indice(
    data: dict[str, list[tuple[object, float | None]]],
    *,
    tipo: str = "inpc",
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
    manifiesto = [ManifestUnidad("c1", version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
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
    mensual = _indice({"INPC": [(PeriodoMensual(2024, 1), 100.0), (PeriodoMensual(2024, 2), 101.0)]})
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
    assert r.resultado.largo.loc[(_Q2, "INPC"), "estado_calculo"] == "parcial"


def test_periodica_fuente_sin_datos_ausente_y_en_reporte() -> None:
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0), (_Q3, None), (_Q4, 109.0)]})
    r = variacion_periodica(indice, "quincenal")
    assert (_Q3, "INPC") not in r.df.index
    assert (_Q3, "INPC") in r.reporte.index
    assert r.reporte.loc[(_Q3, "INPC"), "estado_calculo"] == "sin_datos"


def test_periodica_manifiesto_y_diagnostico() -> None:
    indice = _indice({"INPC": [(_Q1, 100.0), (_Q2, 103.0), (_Q3, None), (_Q4, 109.0)]})
    r = variacion_periodica(indice, "quincenal")
    assert r.manifiesto.id_corrida == ["c1"]
    assert r.manifiesto.inpc_ids is None
    assert len(r.diagnostico) == 3
    assert r.indices_parciales is None


# -- variacion_acumulada_anual -------------------------------------------------


def test_acumulada_base_diciembre_anio_anterior() -> None:
    indice = _indice(
        {"INPC": [(PeriodoQuincenal(2023, 12, 2), 100.0), (PeriodoQuincenal(2024, 12, 2), 110.0)]}
    )
    r = variacion_acumulada_anual(indice)
    assert (r.resultado.largo["clase_variacion"] == "acumulada_anual").all()
    assert r.df.loc[(PeriodoQuincenal(2024, 12, 2), "INPC"), "variacion_pp"] == pytest.approx(10.0)
    assert len(r.df) == 1


# -- variacion_desde -----------------------------------------------------------


def _indice_dos() -> ResultadoIndice:
    return _indice({"A": [(_Q1, 100.0), (_Q2, 110.0)], "B": [(_Q1, 100.0), (_Q2, 90.0)]})


def test_desde_una_fila_por_indice() -> None:
    r = variacion_desde(_indice_dos(), _Q1, _Q2)
    assert len(r.df) == 2
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}


def test_desde_valores_correctos() -> None:
    r = variacion_desde(_indice_dos(), _Q1, _Q2)
    assert r.df.loc[(_Q2, "A"), "variacion_pp"] == pytest.approx(10.0)
    assert r.df.loc[(_Q2, "B"), "variacion_pp"] == pytest.approx(-10.0)


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
    assert r.indices_parciales.loc["B", "periodo_desde_real"] == _Q2
    assert r.df.loc[(_Q3, "B"), "variacion_pp"] == pytest.approx(90 / 95 * 100 - 100)


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
    assert r.reporte.loc[(_Q2, "INPC"), "cobertura_pct_t"] == pytest.approx(90.0)
    assert r.reporte.loc[(_Q2, "INPC"), "cobertura_pct_lag"] == pytest.approx(88.0)
