from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

import replica_inpc as rep
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "inputs"
DATA_DIR_CANASTA = Path(__file__).parent.parent.parent / "data" / "tests" / "p_pdf"
_CANASTA_2018 = str(DATA_DIR_CANASTA / "ponderadores_2018.csv")
_SERIE_2018 = str(DATA_DIR / "series2018_horizontal_metadata.CSV")
_BASE = PeriodoQuincenal(2018, 7, 2)


@pytest.mark.requires_data
def test_calcular_historia_defaults_sin_argumentos_extra() -> None:
    # Defaults: referencia="2Q Jul 2018", periodicidad="mensual".
    # Julio 2018 vale 100 pero NO prueba nada sobre el orden rebase→mensualizar:
    # el tramo 2018 arranca en 2Q Jul 2018 (RANGOS_CANASTAS), así que julio tiene
    # una sola quincena y su "promedio" es esa quincena. Ver el test de agosto.
    resultado = rep.calcular_historia([(2018, _CANASTA_2018, _SERIE_2018)])

    assert isinstance(resultado, ResultadoIndice)
    largo = resultado.resultado.largo
    assert not largo.empty
    clave = cast(Any, (PeriodoMensual(2018, 7), "INPC"))
    assert largo.loc[clave, "indice_replicado"] == pytest.approx(100.0)
    assert resultado.periodo_referencia == _BASE


@pytest.mark.requires_data
def test_mensual_conserva_base_quincenal_y_el_mes_base_no_vale_100() -> None:
    # Agosto 2018 sí tiene sus dos quincenas, así que acá el orden sí se nota:
    # se rebasa en 2Q Ago (quincenal) y recién después se promedia, con lo que el
    # mes de agosto queda en el promedio de 1Q y 2Q — no en 100. La base sigue
    # siendo la quincena, y `periodo_referencia` debe decirlo.
    base_agosto = PeriodoQuincenal(2018, 8, 2)
    mensual = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="INPC",
        periodicidad="mensual",
        referencia="2Q Ago 2018",
    )
    quincenal = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="INPC",
        periodicidad="quincenal",
        referencia="2Q Ago 2018",
    )

    assert mensual.periodo_referencia == base_agosto
    assert quincenal.resultado.largo.loc[
        cast(Any, (base_agosto, "INPC")), "indice_replicado"
    ] == pytest.approx(100.0)

    # `.loc` se tipa como el `Scalar` amplio de pandas (incluye str, datetime,
    # complex), así que ni la suma ni `float()` pasan el type checker.
    valor_agosto = cast(
        float,
        mensual.resultado.largo.loc[
            cast(Any, (PeriodoMensual(2018, 8), "INPC")), "indice_replicado"
        ],
    )
    primera_quincena = cast(
        float,
        quincenal.resultado.largo.loc[
            cast(Any, (PeriodoQuincenal(2018, 8, 1), "INPC")), "indice_replicado"
        ],
    )
    assert valor_agosto != pytest.approx(100.0)
    assert valor_agosto == pytest.approx((primera_quincena + 100.0) / 2)


@pytest.mark.requires_data
def test_calcular_historia_2018_standalone_quincenal() -> None:
    resultado = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="INPC",
        referencia="2q jul 2018",
        periodicidad="quincenal",
    )

    assert isinstance(resultado, ResultadoIndice)
    largo = resultado.resultado.largo
    assert not largo.empty
    # rebased a 2Q Jul 2018 = 100 → el INPC en la base vale 100.
    clave = cast(Any, (_BASE, "INPC"))
    assert largo.loc[clave, "indice_replicado"] == pytest.approx(100.0)


@pytest.mark.requires_data
def test_calcular_historia_smoke_pipeline_completo() -> None:
    # Variación y consulta sobre el resultado del flujo orquestado.
    resultado = rep.calcular_historia(
        [(2018, _CANASTA_2018, _SERIE_2018)],
        tipo="INPC",
        referencia="2Q Jul 2018",
        periodicidad="quincenal",
    )
    variaciones = rep.variacion_periodica(resultado, frecuencia="quincenal")
    assert not variaciones.resultado.largo.empty
