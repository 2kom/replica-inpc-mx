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


# La fachada ya no valida ni extrae periodos: eso vive en ValidarResultado. Acá
# solo se prueba que construya la fabrica con `config` y delegue al metodo
# correcto con la tolerancia correcta. El resultado puede ser cualquier objeto:
# nunca se toca porque el caso de uso esta mockeado.
_RESULTADO = SimpleNamespace()


# -- la fabrica de la fuente ---------------------------------------------------


def test_crear_fuente_sin_token_falla() -> None:
    with pytest.raises(ErrorConfiguracion, match="token"):
        validaciones._crear_fuente("INPC")


def test_crear_fuente_usa_token_tipo_y_timeout_de_config(mocker) -> None:
    config.set_token("tok")
    config.timeout_api = 7
    fuente_cls = mocker.patch.object(validaciones, "FuenteValidacionApi")

    salida = validaciones._crear_fuente("INFLACION COMPONENTE")

    fuente_cls.assert_called_once_with("tok", "INFLACION COMPONENTE", timeout=7)
    assert salida is fuente_cls.return_value


def test_el_caso_de_uso_recibe_la_fabrica_no_una_fuente(mocker) -> None:
    # La fabrica debe llegar sin invocar: si api construyera la fuente antes,
    # un tipo o clase invalidos fallarian por token en vez de por su motivo.
    caso_cls = mocker.patch.object(validaciones, "ValidarResultado")
    mocker.patch.object(validaciones, "FuenteValidacionApi")

    validaciones.validar_indice(_RESULTADO)  # type: ignore[arg-type]

    (fabrica,) = caso_cls.call_args[0]
    assert fabrica is validaciones._crear_fuente


# -- delegación ----------------------------------------------------------------


@pytest.mark.parametrize(
    "funcion, metodo, atributo_tolerancia, valor",
    [
        ("validar_indice", "validar_indice", "tolerancia_indice", 0.002),
        ("validar_variacion", "validar_variacion", "tolerancia_derivados", 0.05),
        ("validar_incidencia", "validar_incidencia", "tolerancia_derivados", 0.03),
    ],
)
def test_delega_al_caso_de_uso_con_la_tolerancia_de_config(
    mocker, funcion: str, metodo: str, atributo_tolerancia: str, valor: float
) -> None:
    setattr(config, atributo_tolerancia, valor)
    caso = mocker.patch.object(validaciones, "ValidarResultado").return_value
    getattr(caso, metodo).return_value = "val"

    salida = getattr(validaciones, funcion)(_RESULTADO)

    assert salida == "val"
    getattr(caso, metodo).assert_called_once_with(_RESULTADO, valor)
