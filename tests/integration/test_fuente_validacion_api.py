from __future__ import annotations

import pytest
import requests

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    RespuestaInvalida,
)
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

_P1 = PeriodoQuincenal(2026, 3, 1)
_P2 = PeriodoQuincenal(2026, 2, 2)

_RESPUESTA_NORMAL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {
                    "TIME_PERIOD": "2026/03/01",
                    "OBS_VALUE": "145.446",
                    "OBS_STATUS": "3",
                },
                {
                    "TIME_PERIOD": "2026/02/02",
                    "OBS_VALUE": "144.551",
                    "OBS_STATUS": "3",
                },
            ]
        }
    ]
}

_RESPUESTA_CON_NULL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03/01", "OBS_VALUE": None, "OBS_STATUS": "3"},
                {
                    "TIME_PERIOD": "2026/02/02",
                    "OBS_VALUE": "144.551",
                    "OBS_STATUS": "3",
                },
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


class TestRespuestaNormal:
    def test_devuelve_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_NORMAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_P1, _P2])

        assert resultado["INPC"][_P1] == pytest.approx(145.446)
        assert resultado["INPC"][_P2] == pytest.approx(144.551)

    def test_periodo_no_en_api_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_NORMAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([PeriodoQuincenal(2000, 1, 1)])

        assert resultado["INPC"][PeriodoQuincenal(2000, 1, 1)] is None

    def test_obs_value_null_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_CON_NULL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        resultado = fuente.obtener([_P1, _P2])

        assert resultado["INPC"][_P1] is None
        assert resultado["INPC"][_P2] == pytest.approx(144.551)


class TestCache:
    def test_segunda_llamada_no_hace_request(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_NORMAL))

        fuente = FuenteValidacionApi(token="token", tipo="inpc")
        fuente.obtener([_P1])
        fuente.obtener([_P2])

        assert mock_get.call_count == 1

    def test_cache_compartido_entre_instancias(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_NORMAL))

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
                        {
                            "TIME_PERIOD": "formato-malo",
                            "OBS_VALUE": "145.0",
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


# --- helpers ---


def _mock_resp(status_code: int, json_data: dict):
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp
