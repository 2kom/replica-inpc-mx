from __future__ import annotations

import requests

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import Periodo

INDICADORES_INEGI: dict[str, str] = {
    "inpc": "910420",
    # v2 — subyacente
    # "subyacente":            "910421",
    # "subyacente_mercancias": "910422",
    # "subyacente_servicios":  "910423",
    # v2 — no subyacente
    # "no_subyacente":                 "910424",
    # "no_subyacente_agropecuarios":   "910425",
    # "no_subyacente_energeticos":     "910426",
}

_URL = (
    "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
    "/INDICATOR/{indicador}/es/00/false/BIE-BISE/2.0/{token}?type=json"
)


class FuenteValidacionApi:
    """Adaptador que obtiene índices publicados por el INEGI vía su API.

    Ver: docs/diseño.md §8.6
    """

    _cache: dict[str, dict[Periodo, float | None]] = {}

    def __init__(self, token: str, tipo: str) -> None:
        if tipo not in INDICADORES_INEGI:
            raise ErrorConfiguracion(
                f"tipo '{tipo}' no tiene indicador INEGI disponible. "
                f"Tipos soportados: {list(INDICADORES_INEGI)}"
            )
        self._token = token
        self._indicador = INDICADORES_INEGI[tipo]

    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]:
        """Devuelve el valor publicado por el INEGI por periodo.

        Usa cache de clase — la primera llamada descarga el histórico completo;
        las siguientes lo reutilizan sin hacer requests adicionales.
        """
        if self._indicador not in self._cache:
            self._cache[self._indicador] = self._fetch()
        historico = self._cache[self._indicador]
        return {p: historico.get(p) for p in periodos}

    def _fetch(self) -> dict[Periodo, float | None]:
        url = _URL.format(indicador=self._indicador, token=self._token)
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise FuenteNoDisponible(
                f"No se pudo conectar a la API del INEGI: {exc}"
            ) from exc

        try:
            data = resp.json()
            series = data["Series"]
            if not series:
                raise RespuestaInvalida("La API devolvió 'Series' vacío.")
            observations = series[0]["OBSERVATIONS"]
        except (KeyError, IndexError, ValueError) as exc:
            raise RespuestaInvalida(
                f"Respuesta del INEGI con formato inesperado: {exc}"
            ) from exc

        resultado: dict[Periodo, float | None] = {}
        for obs in observations:
            try:
                partes = obs["TIME_PERIOD"].split("/")
                periodo = Periodo(int(partes[0]), int(partes[1]), int(partes[2]))
                raw = obs["OBS_VALUE"]
                valor = None if raw is None else float(raw)
                resultado[periodo] = valor
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise RespuestaInvalida(
                    f"Observación con formato inesperado: {obs!r} — {exc}"
                ) from exc

        return resultado
