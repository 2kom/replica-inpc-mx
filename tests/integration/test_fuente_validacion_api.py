from __future__ import annotations

import pytest
import requests  # type: ignore

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

_P1 = PeriodoQuincenal(2026, 3, 1)
_P2 = PeriodoQuincenal(2026, 2, 2)
_PM1 = PeriodoMensual(2026, 3)
_PM2 = PeriodoMensual(2026, 2)

_RESPUESTA_QUINCENAL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03/01", "OBS_VALUE": "145.446", "OBS_STATUS": "3"},
                {"TIME_PERIOD": "2026/02/02", "OBS_VALUE": "144.551", "OBS_STATUS": "3"},
            ]
        }
    ]
}

_RESPUESTA_QUINCENAL_CON_NULL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03/01", "OBS_VALUE": None, "OBS_STATUS": "3"},
                {"TIME_PERIOD": "2026/02/02", "OBS_VALUE": "144.551", "OBS_STATUS": "3"},
            ]
        }
    ]
}

_RESPUESTA_MENSUAL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03", "OBS_VALUE": "145.200", "OBS_STATUS": "3"},
                {"TIME_PERIOD": "2026/02", "OBS_VALUE": "144.300", "OBS_STATUS": "3"},
            ]
        }
    ]
}

_RESPUESTA_MENSUAL_CON_NULL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03", "OBS_VALUE": None, "OBS_STATUS": "3"},
                {"TIME_PERIOD": "2026/02", "OBS_VALUE": "144.300", "OBS_STATUS": "3"},
            ]
        }
    ]
}


@pytest.fixture(autouse=True)
def limpiar_cache():
    FuenteValidacionApi._cache.clear()
    yield
    FuenteValidacionApi._cache.clear()


class TestInicializacion:
    def test_tipo_invalido_lanza_error_configuracion(self):
        with pytest.raises(ErrorConfiguracion):
            FuenteValidacionApi(token="cualquier-token", tipo="tipo_inexistente")

    def test_tipo_valido_no_lanza(self):
        FuenteValidacionApi(token="cualquier-token", tipo="inpc")


class TestRespuestaQuincenal:
    def test_devuelve_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_P1, _P2])

        assert resultado["INPC"][_P1] == pytest.approx(145.446)
        assert resultado["INPC"][_P2] == pytest.approx(144.551)

    def test_periodo_no_en_api_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([PeriodoQuincenal(2000, 1, 1)])

        assert resultado["INPC"][PeriodoQuincenal(2000, 1, 1)] is None

    def test_obs_value_null_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL_CON_NULL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_P1, _P2])

        assert resultado["INPC"][_P1] is None
        assert resultado["INPC"][_P2] == pytest.approx(144.551)


class TestRespuestaMensual:
    def test_devuelve_valores_para_periodos_mensuales(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_PM1, _PM2])

        assert resultado["INPC"][_PM1] == pytest.approx(145.200)
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    def test_periodo_mensual_no_en_api_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([PeriodoMensual(2000, 1)])

        assert resultado["INPC"][PeriodoMensual(2000, 1)] is None

    def test_obs_value_null_mensual_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL_CON_NULL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_PM1, _PM2])

        assert resultado["INPC"][_PM1] is None
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    def test_inflacion_subcomponente_mensual_devuelve_claves_correctas(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="inflacion subcomponente")
        resultado = fuente.obtener([_PM1])
        assert "mercancias" in resultado


class TestDeteccionAutomatica:
    def test_periodos_quincenales_usan_indicador_quincenal(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))
        FuenteValidacionApi(token="token", tipo="inpc").obtener([_P1])
        url = mock_get.call_args[0][0]
        assert "910420" in url

    def test_periodos_mensuales_usan_indicador_mensual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="inpc").obtener([_PM1])
        url = mock_get.call_args[0][0]
        assert "910392" in url

    def test_cache_mensual_y_quincenal_son_independientes(self, mocker):
        mock_get = mocker.patch("requests.get")
        mock_get.side_effect = [
            _mock_resp(200, _RESPUESTA_QUINCENAL),
            _mock_resp(200, _RESPUESTA_MENSUAL),
        ]

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        fuente.obtener([_P1])
        fuente.obtener([_PM1])

        assert mock_get.call_count == 2


class TestCache:
    def test_segunda_llamada_quincenal_no_hace_request(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        fuente.obtener([_P1])
        fuente.obtener([_P2])

        assert mock_get.call_count == 1

    def test_segunda_llamada_mensual_no_hace_request(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        fuente.obtener([_PM1])
        fuente.obtener([_PM2])

        assert mock_get.call_count == 1

    def test_cache_compartido_entre_instancias(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        FuenteValidacionApi(token="token", tipo="inpc").obtener([_P1])
        FuenteValidacionApi(token="token", tipo="inpc").obtener([_P1])

        assert mock_get.call_count == 1


class TestApiNoDisponible:
    def test_timeout_lanza_fuente_no_disponible(self, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.Timeout("timeout"))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(FuenteNoDisponible):
            fuente.obtener([_P1])

    def test_http_400_lanza_fuente_no_disponible(self, mocker):
        mock_resp = _mock_resp(400, {})
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400")
        mocker.patch("requests.get", return_value=mock_resp)

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(FuenteNoDisponible):
            fuente.obtener([_P1])


class TestRespuestaInvalida:
    def test_sin_clave_series_lanza_respuesta_invalida(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, {"Header": {}}))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener([_P1])

    def test_series_vacio_lanza_respuesta_invalida(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, {"Series": []}))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener([_P1])

    def test_time_period_malformado_lanza_respuesta_invalida(self, mocker):
        respuesta = {
            "Series": [
                {
                    "OBSERVATIONS": [
                        {"TIME_PERIOD": "formato-malo", "OBS_VALUE": "145.0", "OBS_STATUS": "3"},
                    ]
                }
            ]
        }
        mocker.patch("requests.get", return_value=_mock_resp(200, respuesta))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener([_P1])

    def test_obs_value_malformado_lanza_respuesta_invalida(self, mocker):
        respuesta = {
            "Series": [
                {
                    "OBSERVATIONS": [
                        {
                            "TIME_PERIOD": "2026/03/01",
                            "OBS_VALUE": "no-es-numero",
                            "OBS_STATUS": "3",
                        },
                    ]
                }
            ]
        }
        mocker.patch("requests.get", return_value=_mock_resp(200, respuesta))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener([_P1])

    def test_json_invalido_lanza_respuesta_invalida(self, mocker):
        mock_resp = _mock_resp(200, {})
        mock_resp.json.side_effect = ValueError("no es json")
        mocker.patch("requests.get", return_value=mock_resp)

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener([_P1])


class TestObtenerVariaciones:
    def test_retorna_dict_keyed_por_indice(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener_variaciones([_PM1], "periodica")
        assert "INPC" in resultado

    def test_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener_variaciones([_PM1, _PM2], "periodica")
        assert resultado["INPC"][_PM1] == pytest.approx(145.200)
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    def test_tipo_variacion_invalido_lanza_error(self, mocker):
        from replica_inpc.dominio.errores import ErrorConfiguracion

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        with pytest.raises(ErrorConfiguracion):
            fuente.obtener_variaciones([_PM1], "invalido")  # type: ignore[arg-type]

    def test_usa_indicador_periodica(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="inpc").obtener_variaciones([_PM1], "periodica")
        url = mock_get.call_args[0][0]
        assert "910399" in url

    def test_usa_indicador_interanual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="inpc").obtener_variaciones([_PM1], "interanual")
        url = mock_get.call_args[0][0]
        assert "910406" in url

    def test_usa_indicador_acumulada_anual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="inpc").obtener_variaciones(
            [_PM1], "acumulada_anual"
        )
        url = mock_get.call_args[0][0]
        assert "910413" in url

    def test_reutiliza_cache_de_obtener(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        # primera llamada llena cache con indicador 910399
        fuente.obtener_variaciones([_PM1], "periodica")
        # segunda llamada con mismo indicador no hace request
        fuente.obtener_variaciones([_PM2], "periodica")
        assert mock_get.call_count == 1

    def test_subcomponentes_devuelven_claves_correctas(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="inflacion subcomponente")
        resultado = fuente.obtener_variaciones([_PM1], "periodica")
        assert set(resultado.keys()) == {
            "mercancias",
            "servicios",
            "agropecuarios",
            "energeticos y tarifas autorizadas por el gobierno",
        }


# --- helpers ---


def _mock_resp(status_code: int, json_data: dict):
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp
