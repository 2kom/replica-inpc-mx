from __future__ import annotations

import traceback

import pytest
import requests

from replica_inpc.dominio.errores import (
    ErrorConfiguracion,
    FuenteNoDisponible,
    InvarianteViolado,
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
        FuenteValidacionApi(token="cualquier-token", tipo="INPC")

    @pytest.mark.parametrize(
        "timeout",
        [0, -1, -10, float("nan"), float("inf"), float("-inf")],
        ids=["cero", "negativo", "negativo_grande", "nan", "inf", "menos_inf"],
    )
    def test_timeout_no_positivo_lanza_error_configuracion(self, timeout):
        # timeout<=0 no atrapa NaN ni inf (ambas comparaciones dan False) — la
        # guardia real exige valor finito Y positivo, no solo "no <= 0".
        with pytest.raises(ErrorConfiguracion, match="timeout"):
            FuenteValidacionApi(token="cualquier-token", tipo="INPC", timeout=timeout)

    def test_timeout_positivo_no_lanza(self):
        FuenteValidacionApi(token="cualquier-token", tipo="INPC", timeout=1)


class TestRespuestaQuincenal:
    def test_devuelve_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([_P1, _P2])

        assert resultado["INPC"][_P1] == pytest.approx(145.446)
        assert resultado["INPC"][_P2] == pytest.approx(144.551)

    @pytest.mark.parametrize(
        "fuera_de_rango",
        [PeriodoQuincenal(2000, 1, 1), PeriodoQuincenal(2030, 1, 1)],
        ids=["anterior_al_historico", "posterior_al_historico"],
    )
    def test_periodo_fuera_del_historico_se_omite(self, mocker, fuera_de_rango):
        # Clave ausente = fuera_rango_inegi; None = INEGI cubre el periodo pero no
        # publicó valor. Un periodo fuera del histórico por cualquiera de los dos
        # extremos es lo primero, no lo segundo — ver el esquema del puerto.
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([fuera_de_rango, _P1])

        assert fuera_de_rango not in resultado["INPC"]
        assert resultado["INPC"][_P1] == pytest.approx(145.446)

    def test_obs_value_null_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL_CON_NULL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([_P1, _P2])

        assert resultado["INPC"][_P1] is None
        assert resultado["INPC"][_P2] == pytest.approx(144.551)


class TestRespuestaMensual:
    def test_devuelve_valores_para_periodos_mensuales(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([_PM1, _PM2])

        assert resultado["INPC"][_PM1] == pytest.approx(145.200)
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    @pytest.mark.parametrize(
        "fuera_de_rango",
        [PeriodoMensual(2000, 1), PeriodoMensual(2030, 1)],
        ids=["anterior_al_historico", "posterior_al_historico"],
    )
    def test_periodo_mensual_fuera_del_historico_se_omite(self, mocker, fuera_de_rango):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([fuera_de_rango, _PM1])

        assert fuera_de_rango not in resultado["INPC"]
        assert resultado["INPC"][_PM1] == pytest.approx(145.200)

    def test_obs_value_null_mensual_devuelve_none(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL_CON_NULL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_indices([_PM1, _PM2])

        assert resultado["INPC"][_PM1] is None
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    def test_inflacion_subcomponente_mensual_devuelve_claves_correctas(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INFLACION SUBCOMPONENTE")
        resultado = fuente.obtener_indices([_PM1])
        assert "mercancias" in resultado


class TestDeteccionAutomatica:
    def test_periodos_quincenales_usan_indicador_quincenal(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_indices([_P1])
        url = mock_get.call_args[0][0]
        assert "910420" in url

    def test_periodos_mensuales_usan_indicador_mensual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_indices([_PM1])
        url = mock_get.call_args[0][0]
        assert "910392" in url

    def test_timeout_del_constructor_se_pasa_a_requests_get(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))
        FuenteValidacionApi(token="token", tipo="INPC", timeout=42).obtener_indices([_P1])
        assert mock_get.call_args.kwargs["timeout"] == 42

    def test_timeout_default_es_10(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_indices([_P1])
        assert mock_get.call_args.kwargs["timeout"] == 10

    def test_cache_mensual_y_quincenal_son_independientes(self, mocker):
        mock_get = mocker.patch("requests.get")
        mock_get.side_effect = [
            _mock_resp(200, _RESPUESTA_QUINCENAL),
            _mock_resp(200, _RESPUESTA_MENSUAL),
        ]

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        fuente.obtener_indices([_P1])
        fuente.obtener_indices([_PM1])

        assert mock_get.call_count == 2


class TestCache:
    def test_segunda_llamada_quincenal_no_hace_request(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        fuente.obtener_indices([_P1])
        fuente.obtener_indices([_P2])

        assert mock_get.call_count == 1

    def test_segunda_llamada_mensual_no_hace_request(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        fuente.obtener_indices([_PM1])
        fuente.obtener_indices([_PM2])

        assert mock_get.call_count == 1

    def test_cache_compartido_entre_instancias(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_QUINCENAL))

        FuenteValidacionApi(token="token", tipo="INPC").obtener_indices([_P1])
        FuenteValidacionApi(token="token", tipo="INPC").obtener_indices([_P1])

        assert mock_get.call_count == 1


class TestApiNoDisponible:
    def test_timeout_lanza_fuente_no_disponible(self, mocker):
        mocker.patch("requests.get", side_effect=requests.exceptions.Timeout("timeout"))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(FuenteNoDisponible):
            fuente.obtener_indices([_P1])

    def test_http_400_lanza_fuente_no_disponible(self, mocker):
        mock_resp = _mock_resp(400, {})
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400")
        mocker.patch("requests.get", return_value=mock_resp)

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(FuenteNoDisponible):
            fuente.obtener_indices([_P1])

    def test_error_no_expone_token_en_mensaje_ni_traceback(self, mocker):
        # La URL real de la API lleva el token en texto plano; un HTTPError de
        # requests incluye la URL completa en su propio mensaje. `_fetch` no debe
        # dejarlo pasar ni en el mensaje de FuenteNoDisponible ni encadenado como
        # causa (eso también lo imprime el traceback por defecto).
        resp = requests.Response()
        resp.status_code = 401
        resp.reason = "Unauthorized"
        resp.url = (
            "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/"
            "INDICATOR/910420/es/00/false/BIE-BISE/2.0/TOKEN_SECRETO?type=json"
        )
        mocker.patch("requests.get", return_value=resp)

        fuente = FuenteValidacionApi(token="TOKEN_SECRETO", tipo="INPC")
        with pytest.raises(FuenteNoDisponible) as exc_info:
            fuente.obtener_indices([_P1])

        assert "TOKEN_SECRETO" not in str(exc_info.value)
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__context__ is None
        traza = "".join(
            traceback.format_exception(
                type(exc_info.value), exc_info.value, exc_info.value.__traceback__
            )
        )
        assert "TOKEN_SECRETO" not in traza

    def test_connection_error_no_expone_token_en_mensaje_ni_traceback(self, mocker):
        # Cubre la rama genérica RequestException (no HTTPError): el mensaje de
        # requests.exceptions.ConnectionError también trae la URL completa —
        # sin este caso, restaurar str(exc) solo ahí volvería a filtrar el token
        # sin que el test de HTTPError se enterara.
        mocker.patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError(
                "No se pudo conectar a https://www.inegi.org.mx/.../2.0/TOKEN_SECRETO?type=json"
            ),
        )

        fuente = FuenteValidacionApi(token="TOKEN_SECRETO", tipo="INPC")
        with pytest.raises(FuenteNoDisponible) as exc_info:
            fuente.obtener_indices([_P1])

        assert "TOKEN_SECRETO" not in str(exc_info.value)
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__context__ is None
        traza = "".join(
            traceback.format_exception(
                type(exc_info.value), exc_info.value, exc_info.value.__traceback__
            )
        )
        assert "TOKEN_SECRETO" not in traza


class TestRespuestaInvalida:
    def test_sin_clave_series_lanza_respuesta_invalida(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, {"Header": {}}))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener_indices([_P1])

    def test_series_vacio_lanza_respuesta_invalida(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, {"Series": []}))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener_indices([_P1])

    def test_observations_vacio_lanza_respuesta_invalida(self, mocker):
        # Series no vacío, pero la única serie no trae observaciones — antes
        # producía un histórico {} silencioso en vez de fallar.
        mocker.patch(
            "requests.get", return_value=_mock_resp(200, {"Series": [{"OBSERVATIONS": []}]})
        )

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida, match="OBSERVATIONS"):
            fuente.obtener_indices([_P1])

    def test_periodicidad_cruzada_lanza_respuesta_invalida(self, mocker):
        # Se pide mensual (_PM1) pero la respuesta trae TIME_PERIOD quincenal —
        # antes se aceptaba, dejando PeriodoQuincenal en un histórico "mensual".
        respuesta = {
            "Series": [{"OBSERVATIONS": [{"TIME_PERIOD": "2026/03/01", "OBS_VALUE": "145.4"}]}]
        }
        mocker.patch("requests.get", return_value=_mock_resp(200, respuesta))

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida, match="PeriodoMensual"):
            fuente.obtener_indices([_PM1])

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

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener_indices([_P1])

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

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener_indices([_P1])

    def test_json_invalido_lanza_respuesta_invalida(self, mocker):
        mock_resp = _mock_resp(200, {})
        mock_resp.json.side_effect = ValueError("no es json")
        mocker.patch("requests.get", return_value=mock_resp)

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(RespuestaInvalida):
            fuente.obtener_indices([_P1])


class TestObtenerVariaciones:
    def test_retorna_dict_keyed_por_indice(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_variaciones([_PM1], "periodica")
        assert "INPC" in resultado

    def test_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_variaciones([_PM1, _PM2], "periodica")
        assert resultado["INPC"][_PM1] == pytest.approx(145.200)
        assert resultado["INPC"][_PM2] == pytest.approx(144.300)

    def test_tipo_variacion_invalido_lanza_error(self):
        from replica_inpc.dominio.errores import ErrorConfiguracion

        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        with pytest.raises(ErrorConfiguracion):
            fuente.obtener_variaciones([_PM1], "invalido")  # pyright: ignore[reportArgumentType]

    def test_usa_indicador_periodica(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones([_PM1], "periodica")
        url = mock_get.call_args[0][0]
        assert "910399" in url

    def test_usa_indicador_interanual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones([_PM1], "interanual")
        url = mock_get.call_args[0][0]
        assert "910406" in url

    def test_usa_indicador_acumulada_anual(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones(
            [_PM1], "acumulada_anual"
        )
        url = mock_get.call_args[0][0]
        assert "910413" in url

    def test_reutiliza_cache_de_obtener(self, mocker):
        mock_get = mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        # primera llamada llena cache con indicador 910399
        fuente.obtener_variaciones([_PM1], "periodica")
        # segunda llamada con mismo indicador no hace request
        fuente.obtener_variaciones([_PM2], "periodica")
        assert mock_get.call_count == 1

    def test_subcomponentes_devuelven_claves_correctas(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INFLACION SUBCOMPONENTE")
        resultado = fuente.obtener_variaciones([_PM1], "periodica")
        assert set(resultado.keys()) == {
            "mercancias",
            "servicios",
            "agropecuarios",
            "energeticos y tarifas autorizadas por el gobierno",
        }

    def test_periodo_antes_de_min_ausente_del_resultado(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        periodo_antiguo = PeriodoMensual(2000, 1)
        resultado = fuente.obtener_variaciones([_PM1, periodo_antiguo], "periodica")
        # min_p = _PM2 (Feb 2026); periodo_antiguo < min_p → no está en resultado
        assert periodo_antiguo not in resultado["INPC"]
        assert _PM1 in resultado["INPC"]


_RESPUESTA_VAR_QUINCENAL = {
    "Series": [
        {
            "OBSERVATIONS": [
                {"TIME_PERIOD": "2026/03/01", "OBS_VALUE": "0.62", "OBS_STATUS": "3"},
                {"TIME_PERIOD": "2026/02/02", "OBS_VALUE": "0.45", "OBS_STATUS": "3"},
            ]
        }
    ]
}


class TestObtenerVariacionesQuincenal:
    def test_usa_indicador_quincenal_periodica(self, mocker):
        mock_get = mocker.patch(
            "requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL)
        )
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones([_P1], "periodica")
        url = mock_get.call_args[0][0]
        assert "910427" in url

    def test_usa_indicador_quincenal_interanual(self, mocker):
        mock_get = mocker.patch(
            "requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL)
        )
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones([_P1], "interanual")
        url = mock_get.call_args[0][0]
        assert "910438" in url

    def test_usa_indicador_quincenal_acumulada_anual(self, mocker):
        mock_get = mocker.patch(
            "requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL)
        )
        FuenteValidacionApi(token="token", tipo="INPC").obtener_variaciones(
            [_P1], "acumulada_anual"
        )
        url = mock_get.call_args[0][0]
        assert "910445" in url

    def test_valores_para_periodos_pedidos(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        resultado = fuente.obtener_variaciones([_P1, _P2], "periodica")
        assert resultado["INPC"][_P1] == pytest.approx(0.62)
        assert resultado["INPC"][_P2] == pytest.approx(0.45)

    def test_periodo_antes_de_min_ausente_del_resultado(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL))
        fuente = FuenteValidacionApi(token="token", tipo="INPC")
        periodo_antiguo = PeriodoQuincenal(2000, 1, 1)
        resultado = fuente.obtener_variaciones([_P1, periodo_antiguo], "periodica")
        # min_p = _P2 (2026/02/02); periodo_antiguo < min_p → ausente
        assert periodo_antiguo not in resultado["INPC"]
        assert _P1 in resultado["INPC"]

    def test_subcomponentes_quincenal_claves_correctas(self, mocker):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_VAR_QUINCENAL))
        fuente = FuenteValidacionApi(token="token", tipo="INFLACION SUBCOMPONENTE")
        resultado = fuente.obtener_variaciones([_P1], "periodica")
        assert set(resultado.keys()) == {
            "mercancias",
            "servicios",
            "agropecuarios",
            "energeticos y tarifas autorizadas por el gobierno",
        }


class TestRecorteHistoricoDerivados:
    @pytest.mark.parametrize(
        "metodo, extra",
        [
            ("obtener_variaciones", ("periodica",)),
            ("obtener_incidencias", ("periodica",)),
        ],
    )
    def test_recorta_ambos_extremos_y_conserva_periodos_interiores(self, mocker, metodo, extra):
        mocker.patch("requests.get", return_value=_mock_resp(200, _RESPUESTA_MENSUAL))
        anterior = PeriodoMensual(2000, 1)
        posterior = PeriodoMensual(2030, 1)
        fuente = FuenteValidacionApi(token="token", tipo="INPC")

        resultado = getattr(fuente, metodo)(
            [anterior, _PM2, _PM1, posterior],
            *extra,
        )["INPC"]

        assert list(resultado) == [_PM2, _PM1]
        assert resultado[_PM2] == pytest.approx(144.300)
        assert resultado[_PM1] == pytest.approx(145.200)

    @pytest.mark.parametrize(
        "metodo, extra",
        [
            ("obtener_variaciones", ("periodica",)),
            ("obtener_incidencias", ("periodica",)),
        ],
    )
    def test_periodo_interior_sin_publicacion_conserva_none(self, mocker, metodo, extra):
        mocker.patch(
            "requests.get",
            return_value=_mock_resp(200, _RESPUESTA_MENSUAL_CON_NULL),
        )
        fuente = FuenteValidacionApi(token="token", tipo="INPC")

        resultado = getattr(fuente, metodo)([_PM2, _PM1], *extra)["INPC"]

        assert resultado[_PM2] == pytest.approx(144.300)
        assert resultado[_PM1] is None


class TestPeriodosVacios:
    # El puerto promete InvarianteViolado con `periodos == []`. Antes los tres
    # metodos gastaban un request y devolvian {'INPC': {}}: la guardia va antes
    # de tocar cache o red, asi que call_count debe quedar en 0.
    @pytest.mark.parametrize(
        "metodo, extra",
        [
            ("obtener_indices", ()),
            ("obtener_variaciones", ("periodica",)),
            ("obtener_incidencias", ("periodica",)),
        ],
    )
    def test_lista_vacia_lanza_invariante_sin_hacer_request(self, mocker, metodo, extra):
        mock_get = mocker.patch("requests.get")
        fuente = FuenteValidacionApi(token="token", tipo="INPC")

        with pytest.raises(InvarianteViolado, match=metodo):
            getattr(fuente, metodo)([], *extra)

        assert mock_get.call_count == 0

    def test_mensaje_nombra_el_parametro_vacio(self, mocker):
        mocker.patch("requests.get")
        fuente = FuenteValidacionApi(token="token", tipo="INPC")

        with pytest.raises(InvarianteViolado) as exc:
            fuente.obtener_indices([])

        assert "periodos" in str(exc.value)
        assert "vacío" in str(exc.value)


# --- helpers ---


def _mock_resp(status_code: int, json_data: dict):
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp
