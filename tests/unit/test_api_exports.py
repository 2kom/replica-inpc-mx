from __future__ import annotations

import pytest

import replica_inpc as rep

_SIMBOLOS_CLAVE = [
    "cargar_canasta",
    "cargar_serie",
    "calcular_indice",
    "empalmar",
    "rebasar",
    "a_mensual",
    "variacion_periodica",
    "incidencia_periodica",
    "validar_indice",
    "validar_variacion",
    "validar_incidencia",
    "calcular_historia",
    "set_token",
    "limpiar_cache",
    "INDICES_VALIDABLES",
    "PeriodoMensual",
    "PeriodoQuincenal",
    "periodo_desde_str",
    "VersionCanasta",
    # errores re-exportados (api.md §D4)
    "ReplicaInpcError",
    "InvarianteViolado",
    "ErrorConfiguracion",
    "ArchivoNoEncontrado",
    "FuenteNoDisponible",
]

# Símbolos v1 que NO deben quedar expuestos en la superficie v2.
_SIMBOLOS_V1 = [
    "Corrida",
    "EjecutarCorrida",
    "validar_inpc",
    "validar_mensual",
    "ResultadoCorrida",
    "ManifestCorrida",
]


@pytest.mark.parametrize("nombre", _SIMBOLOS_CLAVE)
def test_simbolo_clave_expuesto(nombre: str) -> None:
    assert hasattr(rep, nombre)
    assert nombre in rep.__all__


@pytest.mark.parametrize("nombre", _SIMBOLOS_V1)
def test_simbolo_v1_no_expuesto(nombre: str) -> None:
    assert not hasattr(rep, nombre)
    assert nombre not in rep.__all__


def test_all_curado_sin_duplicados() -> None:
    assert len(rep.__all__) == len(set(rep.__all__))
