from __future__ import annotations

import pytest

from replica_inpc.api import config, consultas
from replica_inpc.dominio.errores import ErrorConfiguracion


@pytest.fixture(autouse=True)
def _config_valida(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    config._token = None
    config.set_token("tok")
    config.timeout_api = 10
    yield
    config._token = None
    config.timeout_api = 10


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
