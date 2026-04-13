from __future__ import annotations

import requests

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import Periodo

INDICADORES_INEGI: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910420",
    },
    "inflacion componente": {
        "subyacente": "910421",
        "no subyacente": "910424",
    },
    "inflacion subcomponente": {
        "mercancias": "910422",
        "servicios": "910423",
        "agropecuarios": "910425",
        "energeticos y tarifas autorizadas por el gobierno": "910426",
    },
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
        self._indicadores = INDICADORES_INEGI[tipo]

    def obtener(
        self, periodos: list[Periodo]
    ) -> dict[str, dict[Periodo, float | None]]:
        """Devuelve el valor publicado por el INEGI por índice y por periodo.

        Usa cache de clase — la primera llamada descarga el histórico completo;
        las siguientes lo reutilizan sin hacer requests adicionales.
        """
        resultado = {}
        for nombre, indicador in self._indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            resultado[nombre] = {p: historico.get(p) for p in periodos}
        return resultado

    def _fetch(self, indicador: str) -> dict[Periodo, float | None]:
        url = _URL.format(indicador=indicador, token=self._token)
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
