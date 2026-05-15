from __future__ import annotations

import pytest

import replica_inpc as rep
from replica_inpc.api import config
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi


@pytest.fixture(autouse=True)
def _reset_estado_global():
    """Restaura el estado global de config tras cada caso."""
    yield
    config._token = None
    config.tolerancia_indice = 0.0009
    config.tolerancia_derivados = 0.009
    config.timeout_api = 10
    FuenteValidacionApi._cache.clear()


# -- token ---------------------------------------------------------------------


def test_set_token_se_recupera_con_get_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    rep.set_token("token-de-sesion")
    assert config.get_token() == "token-de-sesion"


def test_env_var_gana_sobre_set_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INEGI_TOKEN", "token-de-entorno")
    rep.set_token("token-de-sesion")
    assert config.get_token() == "token-de-entorno"


def test_sin_token_lanza_error_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    with pytest.raises(ErrorConfiguracion):
        config.get_token()


# -- proxy de variables configurables ------------------------------------------


@pytest.mark.parametrize(
    "nombre, valor",
    [
        ("tolerancia_indice", 0.001),
        ("tolerancia_derivados", 0.05),
        ("timeout_api", 30),
    ],
)
def test_proxy_escribe_y_lee_en_config(nombre: str, valor: float) -> None:
    setattr(rep, nombre, valor)
    assert getattr(rep, nombre) == valor
    assert getattr(config, nombre) == valor


def test_proxy_lee_default_sin_escritura() -> None:
    assert rep.tolerancia_indice == 0.0009
    assert rep.tolerancia_derivados == 0.009
    assert rep.timeout_api == 10


# -- cache ---------------------------------------------------------------------


def test_limpiar_cache_vacia_el_cache_de_la_fuente() -> None:
    FuenteValidacionApi._cache["910420"] = {}
    rep.limpiar_cache()
    assert FuenteValidacionApi._cache == {}
