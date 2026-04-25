from __future__ import annotations

from typing import Literal

import requests  # type: ignore

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_INDICADORES_QUINCENALES: dict[str, dict[str, str]] = {
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

_INDICADORES_MENSUALES: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910392",
    },
    "inflacion componente": {
        "subyacente": "910393",
        "no subyacente": "910396",
    },
    "inflacion subcomponente": {
        "mercancias": "910394",
        "servicios": "910395",
        "agropecuarios": "910397",
        "energeticos y tarifas autorizadas por el gobierno": "910398",
    },
}

_VARIACIONES_PERIODICA_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910399",
    },
    "inflacion componente": {
        "subyacente": "910400",
        "no subyacente": "910403",
    },
    "inflacion subcomponente": {
        "mercancias": "910401",
        "servicios": "910402",
        "agropecuarios": "910404",
        "energeticos y tarifas autorizadas por el gobierno": "910405",
    },
}

_VARIACIONES_INTERANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910406",
    },
    "inflacion componente": {
        "subyacente": "910407",
        "no subyacente": "910410",
    },
    "inflacion subcomponente": {
        "mercancias": "910408",
        "servicios": "910409",
        "agropecuarios": "910411",
        "energeticos y tarifas autorizadas por el gobierno": "910412",
    },
}

_VARIACIONES_ACUMULADA_ANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910413",
    },
    "inflacion componente": {
        "subyacente": "910414",
        "no subyacente": "910417",
    },
    "inflacion subcomponente": {
        "mercancias": "910415",
        "servicios": "910416",
        "agropecuarios": "910418",
        "energeticos y tarifas autorizadas por el gobierno": "910419",
    },
}

_VARIACIONES_POR_TIPO: dict[str, dict[str, dict[str, str]]] = {
    "periodica": _VARIACIONES_PERIODICA_MENSUAL,
    "interanual": _VARIACIONES_INTERANUAL_MENSUAL,
    "acumulada_anual": _VARIACIONES_ACUMULADA_ANUAL_MENSUAL,
}

_URL = (
    "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
    "/INDICATOR/{indicador}/es/00/false/BIE-BISE/2.0/{token}?type=json"
)

_Periodo = PeriodoQuincenal | PeriodoMensual


class FuenteValidacionApi:
    """Adaptador que obtiene índices publicados por el INEGI vía su API.

    Ver: docs/diseño.md §8.6
    """

    _cache: dict[str, dict[_Periodo, float | None]] = {}

    def __init__(self, token: str, tipo: str) -> None:
        if tipo not in _INDICADORES_QUINCENALES:
            raise ErrorConfiguracion(
                f"tipo '{tipo}' no tiene indicador INEGI disponible. "
                f"Tipos soportados: {list(_INDICADORES_QUINCENALES)}"
            )
        self._token = token
        self._tipo = tipo

    def obtener(self, periodos: list[_Periodo]) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve el valor publicado por el INEGI por índice y por periodo.

        Detecta automáticamente si los periodos son mensuales o quincenales y
        usa el indicador correspondiente. Usa cache de clase — la primera llamada
        descarga el histórico completo; las siguientes lo reutilizan sin hacer
        requests adicionales.
        """
        es_mensual = periodos and isinstance(periodos[0], PeriodoMensual)
        if es_mensual and self._tipo not in _INDICADORES_MENSUALES:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicador mensual INEGI disponible. "
                f"Tipos con indicador mensual: {list(_INDICADORES_MENSUALES)}"
            )
        indicadores = (
            _INDICADORES_MENSUALES[self._tipo]
            if es_mensual
            else _INDICADORES_QUINCENALES[self._tipo]
        )
        resultado: dict[str, dict[_Periodo, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            resultado[nombre] = {p: historico.get(p) for p in periodos}
        return resultado

    def obtener_variaciones(
        self,
        periodos: list[PeriodoMensual],
        tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    ) -> dict[str, dict[PeriodoMensual, float | None]]:
        """Devuelve series de variación mensual publicadas por INEGI.

        Reutiliza el mismo cache de clase que `obtener()`.
        """
        if tipo_variacion not in _VARIACIONES_POR_TIPO:
            raise ErrorConfiguracion(
                f"tipo_variacion '{tipo_variacion}' no válido. "
                f"Valores soportados: {list(_VARIACIONES_POR_TIPO)}"
            )
        indicadores_tipo = _VARIACIONES_POR_TIPO[tipo_variacion]
        if self._tipo not in indicadores_tipo:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicadores de variación '{tipo_variacion}'. "
                f"Tipos soportados: {list(indicadores_tipo)}"
            )
        indicadores = indicadores_tipo[self._tipo]
        resultado: dict[str, dict[PeriodoMensual, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            resultado[nombre] = {p: historico.get(p) for p in periodos}
        return resultado

    def _fetch(self, indicador: str) -> dict[_Periodo, float | None]:
        url = _URL.format(indicador=indicador, token=self._token)
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise FuenteNoDisponible(f"No se pudo conectar a la API del INEGI: {exc}") from exc

        try:
            data = resp.json()
            series = data["Series"]
            if not series:
                raise RespuestaInvalida("La API devolvió 'Series' vacío.")
            observations = series[0]["OBSERVATIONS"]
        except (KeyError, IndexError, ValueError) as exc:
            raise RespuestaInvalida(f"Respuesta del INEGI con formato inesperado: {exc}") from exc

        resultado: dict[_Periodo, float | None] = {}
        for obs in observations:
            try:
                partes = obs["TIME_PERIOD"].split("/")
                if len(partes) == 3:
                    periodo: _Periodo = PeriodoQuincenal(
                        int(partes[0]), int(partes[1]), int(partes[2])
                    )
                elif len(partes) == 2:
                    periodo = PeriodoMensual(int(partes[0]), int(partes[1]))
                else:
                    raise ValueError(f"TIME_PERIOD con {len(partes)} partes")
                raw = obs["OBS_VALUE"]
                valor = None if raw is None else float(raw)
                resultado[periodo] = valor
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise RespuestaInvalida(
                    f"Observación con formato inesperado: {obs!r} — {exc}"
                ) from exc

        return resultado
