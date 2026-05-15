from __future__ import annotations

from types import SimpleNamespace

import pytest

from replica_inpc.api import config, validaciones
from replica_inpc.dominio.errores import ErrorConfiguracion


@pytest.fixture(autouse=True)
def _sin_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    config._token = None
    config.tolerancia_indice = 0.0009
    config.tolerancia_derivados = 0.009
    config.timeout_api = 10
    yield
    config._token = None


def _r_indice(*tipos: str) -> SimpleNamespace:
    return SimpleNamespace(manifiesto=[SimpleNamespace(tipo=t) for t in tipos])


def _r_derivado(tipo: str, clase: str) -> SimpleNamespace:
    return SimpleNamespace(manifiesto=SimpleNamespace(tipo=tipo, clase=clase))


# -- fail-fast antes de tocar token/fuente -------------------------------------


def test_validar_indice_multi_tipo_falla() -> None:
    with pytest.raises(ErrorConfiguracion, match="varios tipos"):
        validaciones.validar_indice(_r_indice("inpc", "inflacion componente"))


def test_validar_indice_tipo_no_comparable_falla() -> None:
    with pytest.raises(ErrorConfiguracion):
        validaciones.validar_indice(_r_indice("durabilidad"))


def test_validar_variacion_clase_no_comparable_falla_antes_que_token() -> None:
    # clase 'desde' no es comparable; el error debe ser por clase, no por token.
    with pytest.raises(ErrorConfiguracion, match="clase"):
        validaciones.validar_variacion(_r_derivado("inpc", "desde"))


def test_validar_incidencia_clase_no_comparable_falla() -> None:
    with pytest.raises(ErrorConfiguracion):
        validaciones.validar_incidencia(_r_derivado("inpc", "acumulada_anual"))


def test_validar_indice_sin_token_falla() -> None:
    with pytest.raises(ErrorConfiguracion, match="token"):
        validaciones.validar_indice(_r_indice("inpc"))


# -- delegación ----------------------------------------------------------------


def test_validar_indice_delega_con_fuente_y_tolerancia(mocker) -> None:
    config.set_token("tok")
    config.tolerancia_indice = 0.002
    fuente_cls = mocker.patch.object(validaciones, "FuenteValidacionApi")
    dominio = mocker.patch.object(validaciones, "validar_indices", return_value="val")

    resultado = _r_indice("inpc")
    salida = validaciones.validar_indice(resultado)

    assert salida == "val"
    fuente_cls.assert_called_once_with("tok", "inpc", timeout=10)
    dominio.assert_called_once_with(resultado, fuente_cls.return_value, 0.002)


def test_validar_variacion_delega_con_tolerancia_derivados(mocker) -> None:
    config.set_token("tok")
    config.tolerancia_derivados = 0.05
    mocker.patch.object(validaciones, "FuenteValidacionApi")
    dominio = mocker.patch.object(validaciones, "validar_variaciones", return_value="val")

    resultado = _r_derivado("inpc", "periodica_mensual")
    salida = validaciones.validar_variacion(resultado)

    assert salida == "val"
    assert dominio.call_args[0][2] == 0.05
