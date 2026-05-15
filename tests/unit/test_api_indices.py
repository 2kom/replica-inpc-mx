from __future__ import annotations

from types import SimpleNamespace

import pytest

from replica_inpc.api import indices
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoQuincenal

# -- calcular_indice: guard de versiones encadenadas ---------------------------


@pytest.mark.parametrize("version", [2013, 2024])
def test_calcular_indice_encadenada_sin_referencia_falla(version: int) -> None:
    canasta = SimpleNamespace(version=version)
    with pytest.raises(InvarianteViolado):
        indices.calcular_indice(canasta, object(), "inpc", referencia=None)


@pytest.mark.parametrize("version", [2010, 2018])
def test_calcular_indice_base_sin_referencia_delega(version: int, mocker) -> None:
    canasta = SimpleNamespace(version=version)
    para_canasta = mocker.patch.object(indices, "para_canasta")
    calcular = para_canasta.return_value.calcular
    calcular.return_value = "resultado"

    salida = indices.calcular_indice(canasta, "serie", "inpc")

    assert salida == "resultado"
    para_canasta.assert_called_once_with(canasta, None)
    calcular.assert_called_once_with(canasta, "serie", f"inpc:{version}", "inpc")


def test_calcular_indice_encadenada_con_referencia_normaliza(mocker) -> None:
    canasta = SimpleNamespace(version=2024)
    referencia = SimpleNamespace(
        manifiesto=[SimpleNamespace(version=2018), SimpleNamespace(version=2018)]
    )
    refs = mocker.patch.object(
        indices, "_referencias_normalizadas", return_value={"INPC": 100.0}
    )
    para_canasta = mocker.patch.object(indices, "para_canasta")

    indices.calcular_indice(canasta, "serie", "inpc", referencia=referencia)

    refs.assert_called_once_with(referencia, "inpc", 2018, 2024)
    para_canasta.assert_called_once_with(canasta, {"INPC": 100.0})


# -- transformaciones ----------------------------------------------------------


def test_rebasar_parsea_periodo_case_insensible(mocker) -> None:
    _rebasar = mocker.patch.object(indices, "_rebasar", return_value="rebased")

    salida = indices.rebasar("resultado", "2q jul 2018")

    assert salida == "rebased"
    _rebasar.assert_called_once_with("resultado", PeriodoQuincenal(2018, 7, 2), 100.0)


def test_empalmar_delega(mocker) -> None:
    _empalmar = mocker.patch.object(indices, "_empalmar", return_value="empalmado")
    salida = indices.empalmar(["a", "b"], forzar=True, version_nombres=2024)
    assert salida == "empalmado"
    _empalmar.assert_called_once_with(["a", "b"], forzar=True, version_nombres=2024)


def test_a_mensual_delega(mocker) -> None:
    _a_mensual = mocker.patch.object(indices, "_a_mensual", return_value="mensual")
    assert indices.a_mensual("quincenal") == "mensual"
    _a_mensual.assert_called_once_with("quincenal")
