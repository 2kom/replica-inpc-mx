"""Consulta directa de series publicadas por INEGI (sin comparación).

Devuelven `pd.DataFrame` indexado por `periodo` listo para inspeccionar.
Ver: docs/diseño.md §6.8
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import pandas as pd

from replica_inpc.api import config
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

_FRECUENCIA_A_TIPO_VARIACION: dict[str, Literal["periodica", "interanual", "acumulada_anual"]] = {
    "mensual": "periodica",
    "quincenal": "periodica",
    "anual": "interanual",
    "acumulada_anual": "acumulada_anual",
}


def _a_dataframe(series: Mapping[str, Mapping[Any, float | None]]) -> pd.DataFrame:
    df = pd.DataFrame(series)
    df.index.name = "periodo"
    df.sort_index(inplace=True)
    return df


def consultar_indice(
    tipo: str,
    periodicidad: Literal["mensual", "quincenal"] = "mensual",
) -> pd.DataFrame:
    """Devuelve el histórico de índices publicados por INEGI para `tipo`.

    Requiere token INEGI configurado (`rep.set_token(...)` o `INEGI_TOKEN`).
    Ver: docs/diseño.md §6.8.
    """
    if periodicidad not in ("mensual", "quincenal"):
        raise ErrorConfiguracion(
            f"periodicidad '{periodicidad}' inválida; usa 'mensual' o 'quincenal'."
        )
    fuente = FuenteValidacionApi(config.get_token(), tipo, timeout=config.timeout_api)
    return _a_dataframe(fuente.historico_indices(periodicidad))


def consultar_variacion(
    tipo: str,
    periodicidad: Literal["mensual", "quincenal"] = "mensual",
    frecuencia: Literal["mensual", "quincenal", "anual", "acumulada_anual"] = "mensual",
) -> pd.DataFrame:
    """Devuelve el histórico de variaciones publicadas por INEGI para `tipo`.

    `frecuencia` selecciona la clase: `"mensual"` / `"quincenal"` = vs periodo
    anterior; `"anual"` = vs mismo periodo año anterior; `"acumulada_anual"` =
    vs diciembre año anterior. Ver tabla de mapeo en docs/diseño.md §6.8.
    """
    if periodicidad not in ("mensual", "quincenal"):
        raise ErrorConfiguracion(
            f"periodicidad '{periodicidad}' inválida; usa 'mensual' o 'quincenal'."
        )
    if frecuencia not in _FRECUENCIA_A_TIPO_VARIACION:
        raise ErrorConfiguracion(
            f"frecuencia '{frecuencia}' inválida; usa {list(_FRECUENCIA_A_TIPO_VARIACION)}."
        )
    if frecuencia == "mensual" and periodicidad != "mensual":
        raise ErrorConfiguracion("frecuencia='mensual' requiere periodicidad='mensual'.")
    if frecuencia == "quincenal" and periodicidad != "quincenal":
        raise ErrorConfiguracion("frecuencia='quincenal' requiere periodicidad='quincenal'.")
    tipo_variacion = _FRECUENCIA_A_TIPO_VARIACION[frecuencia]
    fuente = FuenteValidacionApi(config.get_token(), tipo, timeout=config.timeout_api)
    return _a_dataframe(fuente.historico_variaciones(periodicidad, tipo_variacion))


def consultar_incidencia(
    tipo: str,
) -> pd.DataFrame:
    """Devuelve el histórico de incidencias publicadas por INEGI para `tipo`.

    INEGI solo publica incidencias mensuales de tipo `"periodica"`.
    Ver: docs/diseño.md §6.8.
    """
    fuente = FuenteValidacionApi(config.get_token(), tipo, timeout=config.timeout_api)
    return _a_dataframe(fuente.historico_incidencias("periodica"))
