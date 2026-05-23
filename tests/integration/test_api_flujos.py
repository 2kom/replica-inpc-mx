from __future__ import annotations

from pathlib import Path

import pytest

import replica_inpc as rep
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "inputs"
_CANASTA_2018 = str(DATA_DIR / "ponderadores_2018.csv")
_SERIE_2018 = str(DATA_DIR / "series2018_horizontal_metadata.CSV")
_BASE = PeriodoQuincenal(2018, 7, 2)


@pytest.mark.requires_data
def test_calcular_historia_defaults_sin_argumentos_extra() -> None:
    # Defaults (referencia="Jul 2018", periodicidad="mensual") deben ser
    # consistentes entre sí: el rebase mensual exige una referencia mensual.
    resultado = rep.calcular_historia([(2018, _CANASTA_2018, _SERIE_2018)])

    assert isinstance(resultado, ResultadoIndice)
    largo = resultado.resultado.largo
    assert not largo.empty
    assert largo.loc[(PeriodoMensual(2018, 7), "INPC"), "indice_replicado"] == pytest.approx(
        100.0
    )


@pytest.mark.requires_data
def test_calcular_historia_2018_standalone_quincenal() -> None:
    resultado = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="inpc",
        referencia="2q jul 2018",
        periodicidad="quincenal",
    )

    assert isinstance(resultado, ResultadoIndice)
    largo = resultado.resultado.largo
    assert not largo.empty
    # rebased a 2Q Jul 2018 = 100 → el INPC en la base vale 100.
    assert largo.loc[(_BASE, "INPC"), "indice_replicado"] == pytest.approx(100.0)


def test_calcular_historia_referencia_invalida_lanza_error_configuracion() -> None:
    with pytest.raises(ErrorConfiguracion):
        rep.calcular_historia(
            [(2018, _CANASTA_2018, _SERIE_2018)],
            referencia="trimestre 3 de 2018",
        )


@pytest.mark.requires_data
def test_calcular_historia_smoke_pipeline_completo() -> None:
    # Variación y consulta sobre el resultado del flujo orquestado.
    resultado = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="inpc",
        referencia="2Q Jul 2018",
        periodicidad="quincenal",
    )
    variaciones = rep.variacion_periodica(resultado, frecuencia="quincenal")
    assert not variaciones.resultado.largo.empty
