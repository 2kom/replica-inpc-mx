from __future__ import annotations

import math
from typing import Literal, cast

import requests

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    InvarianteViolado,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_INDICADORES_QUINCENALES: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910420",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910421",
        "no subyacente": "910424",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910422",
        "servicios": "910423",
        "agropecuarios": "910425",
        "energeticos y tarifas autorizadas por el gobierno": "910426",
    },
}

_INDICADORES_MENSUALES: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910392",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910393",
        "no subyacente": "910396",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910394",
        "servicios": "910395",
        "agropecuarios": "910397",
        "energeticos y tarifas autorizadas por el gobierno": "910398",
    },
}

_VARIACIONES_PERIODICA_MENSUAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910399",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910400",
        "no subyacente": "910403",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910401",
        "servicios": "910402",
        "agropecuarios": "910404",
        "energeticos y tarifas autorizadas por el gobierno": "910405",
    },
}

_VARIACIONES_INTERANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910406",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910407",
        "no subyacente": "910410",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910408",
        "servicios": "910409",
        "agropecuarios": "910411",
        "energeticos y tarifas autorizadas por el gobierno": "910412",
    },
}

_VARIACIONES_ACUMULADA_ANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910413",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910414",
        "no subyacente": "910417",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910415",
        "servicios": "910416",
        "agropecuarios": "910418",
        "energeticos y tarifas autorizadas por el gobierno": "910419",
    },
}

_VARIACIONES_POR_TIPO_MENSUAL: dict[str, dict[str, dict[str, str]]] = {
    "periodica": _VARIACIONES_PERIODICA_MENSUAL,
    "interanual": _VARIACIONES_INTERANUAL_MENSUAL,
    "acumulada_anual": _VARIACIONES_ACUMULADA_ANUAL_MENSUAL,
}

_VARIACIONES_PERIODICA_QUINCENAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910427",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910428",
        "no subyacente": "910431",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910429",
        "servicios": "910430",
        "agropecuarios": "910432",
        "energeticos y tarifas autorizadas por el gobierno": "910433",
    },
}

_VARIACIONES_INTERANUAL_QUINCENAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910438",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910439",
        "no subyacente": "910442",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910440",
        "servicios": "910441",
        "agropecuarios": "910443",
        "energeticos y tarifas autorizadas por el gobierno": "910444",
    },
}

_VARIACIONES_ACUMULADA_ANUAL_QUINCENAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "910445",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "910446",
        "no subyacente": "910449",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "910447",
        "servicios": "910448",
        "agropecuarios": "910450",
        "energeticos y tarifas autorizadas por el gobierno": "910451",
    },
}

_INCIDENCIAS_PERIODICA_MENSUAL: dict[str, dict[str, str]] = {
    "INPC": {
        "INPC": "909281",
    },
    "INFLACION COMPONENTE": {
        "subyacente": "909282",
        "no subyacente": "909290",
    },
    "INFLACION SUBCOMPONENTE": {
        "mercancias": "909283",
        "servicios": "909286",
        "agropecuarios": "909291",
        "energeticos y tarifas autorizadas por el gobierno": "909294",
    },
}

_INCIDENCIAS_POR_TIPO: dict[str, dict[str, dict[str, str]]] = {
    "periodica": _INCIDENCIAS_PERIODICA_MENSUAL,
}

_VARIACIONES_POR_TIPO_QUINCENAL: dict[str, dict[str, dict[str, str]]] = {
    "periodica": _VARIACIONES_PERIODICA_QUINCENAL,
    "interanual": _VARIACIONES_INTERANUAL_QUINCENAL,
    "acumulada_anual": _VARIACIONES_ACUMULADA_ANUAL_QUINCENAL,
}

_URL = (
    "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
    "/INDICATOR/{indicador}/es/00/false/BIE-BISE/2.0/{token}?type=json"
)

_Periodo = PeriodoQuincenal | PeriodoMensual


def _rango_completo(historico: dict[_Periodo, float | None]) -> list[_Periodo]:
    """Genera todos los periodos entre min y max del histórico, inclusive.

    Periodos faltantes en `historico` dentro del rango se incluyen con `None`,
    haciendo visibles los gaps en el DataFrame resultante.
    """
    if not historico:
        return []
    min_p = min(historico)
    max_p = max(historico)
    if isinstance(min_p, PeriodoMensual):
        return [
            PeriodoMensual(a, m)
            for a in range(min_p.año, max_p.año + 1)
            for m in range(1, 13)
            if min_p <= PeriodoMensual(a, m) <= max_p  # type: ignore[operator]
        ]
    return [
        PeriodoQuincenal(a, m, q)
        for a in range(min_p.año, max_p.año + 1)
        for m in range(1, 13)
        for q in (1, 2)
        if min_p <= PeriodoQuincenal(a, m, q) <= max_p  # type: ignore[operator]
    ]


def _recortar_al_historico(
    periodos: list[_Periodo], historico: dict[_Periodo, float | None]
) -> dict[_Periodo, float | None]:
    """Deja solo los periodos que caen dentro del histórico publicado.

    La ausencia de una clave significa `fuera_rango_inegi` para el comparador, y
    `None` significa `no_disponible` (INEGI cubre el periodo pero no publicó
    valor). Recortar por AMBOS extremos es lo que mantiene esa distinción: un
    periodo posterior al último publicado —el caso corriente cuando la réplica
    llega más lejos que la publicación oficial— no es un hueco de la serie, es
    territorio que INEGI todavía no cubre.
    """
    if not historico:
        return {}
    min_p, max_p = min(historico), max(historico)
    return {p: historico.get(p) for p in periodos if min_p <= p <= max_p}  # type: ignore[operator]


def _exigir_periodos(periodos: list[_Periodo], metodo: str) -> None:
    """Rechaza una lista de periodos vacía antes de tocar caché o red."""
    if not periodos:
        raise InvarianteViolado(
            f"FuenteValidacionApi.{metodo}: 'periodos' no puede estar vacío; "
            f"sin periodos no hay nada que consultar."
        )


class FuenteValidacionApi:
    """Implementa `FuenteValidacion` sobre la API del BIE del INEGI.

    Ver: docs/diseño.md §8.6
    """

    _cache: dict[str, dict[_Periodo, float | None]] = {}

    @classmethod
    def indicadores_en_cache(cls) -> int:
        """Cuántos indicadores tiene descargados el cache de clase."""
        return len(cls._cache)

    @classmethod
    def limpiar_cache(cls) -> None:
        """Vacía el cache de clase; la siguiente consulta vuelve a descargar."""
        cls._cache.clear()

    def __init__(self, token: str, tipo: str, timeout: int = 10) -> None:
        if tipo not in _INDICADORES_QUINCENALES:
            raise ErrorConfiguracion(
                f"tipo '{tipo}' no tiene indicador INEGI disponible. "
                f"Tipos soportados: {list(_INDICADORES_QUINCENALES)}"
            )
        if not math.isfinite(timeout) or timeout <= 0:
            raise ErrorConfiguracion(
                f"timeout {timeout!r} inválido; debe ser un valor finito mayor a 0 segundos."
            )
        self._token = token
        self._tipo = tipo
        self._timeout = timeout

    def obtener_indices(self, periodos: list[_Periodo]) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve el valor publicado por el INEGI por índice y por periodo.

        Detecta automáticamente si los periodos son mensuales o quincenales y
        usa el indicador correspondiente. Usa cache de clase — la primera llamada
        descarga el histórico completo; las siguientes lo reutilizan sin hacer
        requests adicionales.

        Raises:
            InvarianteViolado: Si `periodos` está vacío.
        """
        _exigir_periodos(periodos, "obtener_indices")
        es_mensual = isinstance(periodos[0], PeriodoMensual)
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
            resultado[nombre] = _recortar_al_historico(periodos, historico)
        return resultado

    def obtener_variaciones(
        self,
        periodos: list[PeriodoQuincenal | PeriodoMensual],
        tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    ) -> dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]:
        """Devuelve series de variación publicadas por INEGI.

        Detecta automáticamente si los periodos son mensuales o quincenales y
        usa el mapa de indicadores correspondiente. Solo incluye en el resultado
        periodos entre `min(historico)` y `max(historico)`, inclusive; una clave
        ausente indica `fuera_rango_inegi`.

        Raises:
            InvarianteViolado: Si `periodos` está vacío.
        """
        _exigir_periodos(periodos, "obtener_variaciones")
        es_quincenal = isinstance(periodos[0], PeriodoQuincenal)
        mapa = _VARIACIONES_POR_TIPO_QUINCENAL if es_quincenal else _VARIACIONES_POR_TIPO_MENSUAL
        if tipo_variacion not in mapa:
            raise ErrorConfiguracion(
                f"tipo_variacion '{tipo_variacion}' no válido. Valores soportados: {list(mapa)}"
            )
        indicadores_tipo = mapa[tipo_variacion]
        if self._tipo not in indicadores_tipo:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicadores de variación '{tipo_variacion}'. "
                f"Tipos soportados: {list(indicadores_tipo)}"
            )
        indicadores = indicadores_tipo[self._tipo]
        resultado: dict[str, dict[PeriodoMensual | PeriodoQuincenal, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            resultado[nombre] = _recortar_al_historico(periodos, historico)
        return resultado

    def obtener_incidencias(
        self,
        periodos: list[PeriodoMensual],
        tipo_incidencia: Literal["periodica"],
    ) -> dict[str, dict[PeriodoMensual, float | None]]:
        """Devuelve series de incidencia publicadas por INEGI.

        Solo soporta `PeriodoMensual` e incidencia periódica. Una clave ausente
        indica `fuera_rango_inegi`: el periodo cae fuera del histórico publicado
        por cualquiera de sus dos extremos.

        Raises:
            InvarianteViolado: Si `periodos` está vacío.
        """
        _exigir_periodos(periodos, "obtener_incidencias")  # type: ignore[arg-type]
        if tipo_incidencia not in _INCIDENCIAS_POR_TIPO:
            raise ErrorConfiguracion(
                f"tipo_incidencia '{tipo_incidencia}' no válido. "
                f"Valores soportados: {list(_INCIDENCIAS_POR_TIPO)}"
            )
        indicadores_tipo = _INCIDENCIAS_POR_TIPO[tipo_incidencia]
        if self._tipo not in indicadores_tipo:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicadores de incidencia '{tipo_incidencia}'. "
                f"Tipos soportados: {list(indicadores_tipo)}"
            )
        indicadores = indicadores_tipo[self._tipo]
        resultado: dict[str, dict[PeriodoMensual, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            recortado = _recortar_al_historico(list(periodos), historico)
            resultado[nombre] = cast(dict[PeriodoMensual, float | None], recortado)
        return resultado

    def historico_indices(
        self, periodicidad: Literal["mensual", "quincenal"]
    ) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve el histórico completo de índices sin filtro de periodo.

        Cubre desde el primer hasta el último periodo que INEGI tiene en su
        serie. Periodos intermedios sin dato aparecen con valor `None`.
        """
        es_mensual = periodicidad == "mensual"
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
            rango = _rango_completo(historico)
            resultado[nombre] = {p: historico.get(p) for p in rango}
        return resultado

    def historico_variaciones(
        self,
        periodicidad: Literal["mensual", "quincenal"],
        tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    ) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve el histórico completo de variaciones sin filtro de periodo."""
        mapa = (
            _VARIACIONES_POR_TIPO_QUINCENAL
            if periodicidad == "quincenal"
            else _VARIACIONES_POR_TIPO_MENSUAL
        )
        if tipo_variacion not in mapa:
            raise ErrorConfiguracion(
                f"tipo_variacion '{tipo_variacion}' no válido. Valores soportados: {list(mapa)}"
            )
        indicadores_tipo = mapa[tipo_variacion]
        if self._tipo not in indicadores_tipo:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicadores de variación "
                f"'{tipo_variacion}'. Tipos soportados: {list(indicadores_tipo)}"
            )
        indicadores = indicadores_tipo[self._tipo]
        resultado: dict[str, dict[_Periodo, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            rango = _rango_completo(historico)
            resultado[nombre] = {p: historico.get(p) for p in rango}
        return resultado

    def historico_incidencias(
        self, tipo_incidencia: Literal["periodica"]
    ) -> dict[str, dict[_Periodo, float | None]]:
        """Devuelve el histórico completo de incidencias sin filtro de periodo."""
        if tipo_incidencia not in _INCIDENCIAS_POR_TIPO:
            raise ErrorConfiguracion(
                f"tipo_incidencia '{tipo_incidencia}' no válido. "
                f"Valores soportados: {list(_INCIDENCIAS_POR_TIPO)}"
            )
        indicadores_tipo = _INCIDENCIAS_POR_TIPO[tipo_incidencia]
        if self._tipo not in indicadores_tipo:
            raise ErrorConfiguracion(
                f"tipo '{self._tipo}' no tiene indicadores de incidencia "
                f"'{tipo_incidencia}'. Tipos soportados: {list(indicadores_tipo)}"
            )
        indicadores = indicadores_tipo[self._tipo]
        resultado: dict[str, dict[_Periodo, float | None]] = {}
        for nombre, indicador in indicadores.items():
            if indicador not in self._cache:
                self._cache[indicador] = self._fetch(indicador)
            historico = self._cache[indicador]
            rango = _rango_completo(historico)
            resultado[nombre] = {p: historico.get(p) for p in rango}
        return resultado

    def _fetch(self, indicador: str) -> dict[_Periodo, float | None]:
        # La URL lleva el token en texto plano (formato fijo de la API del BIE) —
        # nunca incluir `str(exc)` en el mensaje. Tampoco alcanza con `from None`
        # DENTRO del except: __context__ sigue apuntando a la excepción original
        # (con el token) aunque se suprima su impresión en el traceback por
        # defecto. Levantar la excepción sanitizada FUERA del try/except es lo
        # que evita que __context__ se fije en absoluto.
        url = _URL.format(indicador=indicador, token=self._token)
        resp: requests.Response | None = None
        error_msg: str | None = None
        try:
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "desconocido"
            error_msg = (
                f"La API del INEGI respondió {status} para el indicador {indicador!r}. "
                f"Verifica el token INEGI configurado."
            )
        except requests.exceptions.RequestException as exc:
            error_msg = (
                f"No se pudo conectar a la API del INEGI ({type(exc).__name__}) para "
                f"el indicador {indicador!r}."
            )
        if error_msg is not None:
            raise FuenteNoDisponible(error_msg)
        assert resp is not None  # error_msg es None solo si el try completó sin excepción

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
