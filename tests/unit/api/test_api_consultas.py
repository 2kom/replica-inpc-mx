from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from replica_inpc.api import config, consultas
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi


@pytest.fixture(autouse=True)
def _config_valida(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    config._token = None
    config.set_token("tok")
    config.timeout_api = 10
    FuenteValidacionApi._cache.clear()
    yield
    config._token = None
    config.timeout_api = 10
    FuenteValidacionApi._cache.clear()


def _mock_resp(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


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


# -- timeout inválido, en las tres funciones ------------------------------------
#
# consultar_indice, consultar_variacion y consultar_incidencia construyen cada
# una su propia FuenteValidacionApi (no comparten una fábrica común como
# validaciones._crear_fuente) — probar solo una no protege a las otras dos si
# alguna deja de reenviar config.timeout_api.


@pytest.mark.parametrize(
    "funcion, args",
    [
        (consultas.consultar_indice, ("INPC",)),
        (consultas.consultar_variacion, ("INPC",)),
        (consultas.consultar_incidencia, ("INPC",)),
    ],
    ids=["consultar_indice", "consultar_variacion", "consultar_incidencia"],
)
def test_timeout_invalido_lanza_error_configuracion_sin_tocar_red(mocker, funcion, args) -> None:
    mock_get = mocker.patch("requests.get")
    config.timeout_api = 0

    with pytest.raises(ErrorConfiguracion, match="timeout"):
        funcion(*args)

    assert mock_get.call_count == 0


# -- consultar_indice: ruta exitosa ---------------------------------------------


def test_consultar_indice_mensual_devuelve_dataframe(mocker) -> None:
    mocker.patch("requests.get", return_value=_mock_resp(_RESPUESTA_MENSUAL))

    df = consultas.consultar_indice("inpc")  # minúsculas: se normaliza con .upper()

    assert list(df.columns) == ["INPC"]
    assert df.index.name == "periodo"
    assert list(df.index) == [PeriodoMensual(2026, 2), PeriodoMensual(2026, 3)]  # ordenado
    # float("145.200") directo del parseo en _fetch, sin cálculo de por medio —
    # igualdad exacta, no tolerancia (145.2001 pasaría el default de approx).
    assert df["INPC"][PeriodoMensual(2026, 3)] == 145.200  # type: ignore[call-overload]


def test_consultar_indice_quincenal_usa_indicador_correcto(mocker) -> None:
    mock_get = mocker.patch("requests.get", return_value=_mock_resp(_RESPUESTA_QUINCENAL))

    df = consultas.consultar_indice("INPC", "quincenal")

    url = mock_get.call_args[0][0]
    assert "910420" in url  # indicador quincenal de INPC, no el mensual (910392)
    assert list(df.index) == [PeriodoQuincenal(2026, 2, 2), PeriodoQuincenal(2026, 3, 1)]


def test_consultar_indice_periodicidad_invalida() -> None:
    with pytest.raises(ErrorConfiguracion, match="periodicidad"):
        consultas.consultar_indice("INPC", "anual")  # type: ignore[arg-type]


# -- consultar_variacion: mapeo frecuencia -> tipo_variacion --------------------


@pytest.mark.parametrize(
    "periodicidad, frecuencia, indicador_esperado, respuesta",
    [
        ("mensual", "mensual", "910399", _RESPUESTA_MENSUAL),  # periodica mensual
        ("mensual", "anual", "910406", _RESPUESTA_MENSUAL),  # interanual mensual
        ("mensual", "acumulada_anual", "910413", _RESPUESTA_MENSUAL),  # acumulada_anual mensual
        ("quincenal", "quincenal", "910427", _RESPUESTA_QUINCENAL),  # periodica quincenal
    ],
    ids=["mensual_vs_anterior", "mensual_interanual", "mensual_acumulada", "quincenal"],
)
def test_consultar_variacion_usa_el_indicador_del_mapeo(
    mocker, periodicidad, frecuencia, indicador_esperado, respuesta
) -> None:
    mock_get = mocker.patch("requests.get", return_value=_mock_resp(respuesta))

    consultas.consultar_variacion("INPC", periodicidad, frecuencia)

    url = mock_get.call_args[0][0]
    assert indicador_esperado in url


def test_consultar_variacion_frecuencia_mensual_exige_periodicidad_mensual() -> None:
    with pytest.raises(ErrorConfiguracion, match="periodicidad"):
        consultas.consultar_variacion("INPC", "quincenal", "mensual")


def test_consultar_variacion_frecuencia_quincenal_exige_periodicidad_quincenal() -> None:
    with pytest.raises(ErrorConfiguracion, match="periodicidad"):
        consultas.consultar_variacion("INPC", "mensual", "quincenal")


def test_consultar_variacion_frecuencia_invalida() -> None:
    with pytest.raises(ErrorConfiguracion, match="frecuencia"):
        consultas.consultar_variacion("INPC", "mensual", "invalida")  # type: ignore[arg-type]


# -- consultar_incidencia: ruta exitosa -----------------------------------------


def test_consultar_incidencia_usa_indicador_periodica_mensual(mocker) -> None:
    # "INFLACION COMPONENTE" tiene 2 indicadores (subyacente/no subyacente) — dos
    # llamadas a requests.get, así que se revisan todas, no solo la última.
    mock_get = mocker.patch("requests.get", return_value=_mock_resp(_RESPUESTA_MENSUAL))

    df = consultas.consultar_incidencia("inflacion componente")

    urls = [llamada.args[0] for llamada in mock_get.call_args_list]
    assert any("909282" in url for url in urls)  # subyacente, incidencia periódica mensual
    assert any("909290" in url for url in urls)  # no subyacente
    assert {"subyacente", "no subyacente"} == set(df.columns)
