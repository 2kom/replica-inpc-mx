from __future__ import annotations

from types import SimpleNamespace

import pytest

from replica_inpc.api import indices
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoQuincenal

# centinela sin __eq__ propio: solo `is` lo satisface, así que un wrapper que devuelva
# una copia igual en vez del objeto del calculador no puede colarse
_RESULTADO = object()

_GENERICOS = ("arroz", "frijol")


def _canasta(version: int, genericos: tuple[str, ...] = _GENERICOS) -> SimpleNamespace:
    return SimpleNamespace(version=version, df=SimpleNamespace(index=list(genericos)))


def _serie(genericos: tuple[str, ...] = _GENERICOS) -> SimpleNamespace:
    return SimpleNamespace(df=SimpleNamespace(index=list(genericos)))


# -- calcular_indice: guard de versiones encadenadas ---------------------------


@pytest.mark.parametrize("version", [2013, 2024])
def test_calcular_indice_encadenada_sin_referencia_falla(version: int) -> None:
    with pytest.raises(InvarianteViolado, match="es encadenada y requiere"):
        indices.calcular_indice(_canasta(version), _serie(), "inpc", referencia=None)  # type: ignore[arg-type]


@pytest.mark.parametrize("version", [2010, 2018])
def test_calcular_indice_base_sin_referencia_delega(version: int, mocker) -> None:
    canasta, serie = _canasta(version), _serie()
    para_canasta = mocker.patch.object(indices, "_para_canasta")
    calcular = para_canasta.return_value.calcular
    calcular.return_value = _RESULTADO

    salida = indices.calcular_indice(canasta, serie, "inpc")  # type: ignore[arg-type]

    assert salida is _RESULTADO
    para_canasta.assert_called_once_with(canasta, None)
    calcular.assert_called_once_with(canasta, serie, "INPC")


def test_calcular_indice_encadenada_con_referencia_normaliza(mocker) -> None:
    canasta = _canasta(2024)
    referencia = SimpleNamespace(
        manifiesto=[SimpleNamespace(version=2018), SimpleNamespace(version=2018)]
    )
    refs = mocker.patch.object(indices, "_referencias_normalizadas", return_value={"INPC": 100.0})
    para_canasta = mocker.patch.object(indices, "_para_canasta")

    indices.calcular_indice(canasta, _serie(), "inpc", referencia=referencia)  # type: ignore[arg-type]

    refs.assert_called_once_with(referencia, "INPC", 2018, 2024)
    para_canasta.assert_called_once_with(canasta, {"INPC": 100.0})


@pytest.mark.parametrize("version", [2010, 2018])
def test_calcular_indice_base_con_referencia_tambien_la_usa(version: int, mocker) -> None:
    """La referencia NO se ignora en versiones base: reexpresa el tramo en la escala previa.

    Medido sobre datos reales: pasarla en 2018 mueve el INPC de 100.0 a 133.11 en la
    base. `calcular_historia` depende de eso para encadenar 2018 sobre 2010-2013.
    """
    canasta = _canasta(version)
    referencia = SimpleNamespace(manifiesto=[SimpleNamespace(version=version - 5)])
    refs = mocker.patch.object(indices, "_referencias_normalizadas", return_value={"INPC": 99.0})
    para_canasta = mocker.patch.object(indices, "_para_canasta")

    indices.calcular_indice(canasta, _serie(), "inpc", referencia=referencia)  # type: ignore[arg-type]

    refs.assert_called_once_with(referencia, "INPC", version - 5, version)
    para_canasta.assert_called_once_with(canasta, {"INPC": 99.0})


def test_calcular_indice_toma_la_version_mas_reciente_de_una_referencia_empalmada(
    mocker,
) -> None:
    """Una referencia empalmada trae varios manifiestos; encadena contra el último tramo."""
    referencia = SimpleNamespace(
        manifiesto=[SimpleNamespace(version=2010), SimpleNamespace(version=2013)]
    )
    refs = mocker.patch.object(indices, "_referencias_normalizadas", return_value={})
    mocker.patch.object(indices, "_para_canasta")

    indices.calcular_indice(_canasta(2018), _serie(), "inpc", referencia=referencia)  # type: ignore[arg-type]

    refs.assert_called_once_with(referencia, "INPC", 2013, 2018)


def test_calcular_indice_valida_encadenamiento_antes_de_delegar(mocker) -> None:
    """Faltar `referencia` se reporta sin llegar al calculador."""
    para_canasta = mocker.patch.object(indices, "_para_canasta")

    with pytest.raises(InvarianteViolado, match="es encadenada y requiere"):
        indices.calcular_indice(_canasta(2013), _serie(), "inpc")  # type: ignore[arg-type]

    para_canasta.assert_not_called()


# -- transformaciones ----------------------------------------------------------


def test_rebasar_parsea_periodo_case_insensible(mocker) -> None:
    _rebasar = mocker.patch.object(indices, "_rebasar", return_value=_RESULTADO)

    salida = indices.rebasar("resultado", "2q jul 2018")  # type: ignore[arg-type]

    assert salida is _RESULTADO
    _rebasar.assert_called_once_with("resultado", PeriodoQuincenal(2018, 7, 2), 100.0)


def test_rebasar_reenvia_valor_referencia_custom(mocker) -> None:
    # Regresión: el wrapper solo se probaba con el default (100.0) — no
    # detectaría que se dejara de reenviar un valor_referencia distinto.
    _rebasar = mocker.patch.object(indices, "_rebasar", return_value=_RESULTADO)

    salida = indices.rebasar("resultado", "2q jul 2018", 200.0)  # type: ignore[arg-type]

    assert salida is _RESULTADO
    _rebasar.assert_called_once_with("resultado", PeriodoQuincenal(2018, 7, 2), 200.0)


def test_empalmar_delega(mocker) -> None:
    _empalmar = mocker.patch.object(indices, "_empalmar", return_value=_RESULTADO)
    salida = indices.empalmar(["a", "b"], forzar=True, version_nombres=2024)  # type: ignore[list-item]
    assert salida is _RESULTADO
    _empalmar.assert_called_once_with(["a", "b"], forzar=True, version_nombres=2024)


def test_a_mensual_delega(mocker) -> None:
    _a_mensual = mocker.patch.object(indices, "_a_mensual", return_value=_RESULTADO)
    assert indices.a_mensual("quincenal") is _RESULTADO  # type: ignore[arg-type]
    _a_mensual.assert_called_once_with("quincenal")
