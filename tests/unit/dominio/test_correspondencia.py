"""Pruebas unitarias de `alinear_genericos()`.

La suite cubre la alineación base, el descarte de genéricos sobrantes y el
fallo cuando la serie no cubre todos los genéricos de la canasta.
"""

import pandas as pd
import pytest

from replica_inpc.dominio.correspondencia import alinear_genericos
from replica_inpc.dominio.correspondencia_canastas import (
    RENOMBRES_INDICES,
    validar_renombres_indices,
)
from replica_inpc.dominio.errores import CorrespondenciaInsuficiente
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

"""
La canasta queda como:
generico | ponderador | encadenamiento
arroz    | 10.0       | None
frijol   | 20.0       | None
leche    | 30.0       | None
huevo    | 40.0       | None
"""
df_canasta = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)

"""
La serie queda como:
generico | 2018-Jul-2Q | 2018-Ago-1Q | 2018-Ago-2Q | 2018-Sep-1Q
arroz    | 100         | 101         | 102         | 103
frijol   | 100         | 102         | 104         | 106
leche    | 100         | 103         | 106         | 109
huevo    | 100         | 104         | 108         | 112
"""
periodos = [
    PeriodoQuincenal(2018, 7, 2),
    PeriodoQuincenal(2018, 8, 1),
    PeriodoQuincenal(2018, 8, 2),
    PeriodoQuincenal(2018, 9, 1),
]
df_serie = pd.DataFrame(
    {
        "arroz": [100, 101, 102, 103],
        "frijol": [100, 102, 104, 106],
        "leche": [100, 103, 106, 109],
        "huevo": [100, 104, 108, 112],
    },
    index=periodos,
).T

mapeo_serie = {
    "arroz": "Arroz",
    "frijol": "Frijol",
    "leche": "Leche",
    "huevo": "Huevo",
}

# `mapeo` conserva la trazabilidad `generico_limpio -> generico_original`.
canasta = CanastaCanonica(df_canasta, 2018)
serie = SerieNormalizada(df_serie, mapeo_serie)


def test_alinear_genericos_valido():
    serie_alineada = alinear_genericos(canasta, serie)

    # La serie resultante adopta exactamente el orden de la canasta.
    assert serie_alineada.df.index.equals(canasta.df.index)
    # El mapeo conserva solo los genéricos presentes tras la alineación.
    assert set(serie_alineada.mapeo.keys()) == set(canasta.df.index)


def test_alinear_genericos_sobrantes():
    df_extra = df_serie.copy()
    df_extra.loc["azucar"] = [100, 105, 110, 115]
    mapeo_extra = mapeo_serie.copy()
    mapeo_extra["azucar"] = "Azucar"
    serie_extra = SerieNormalizada(df_extra, mapeo_extra)

    serie_alineada = alinear_genericos(canasta, serie_extra)

    # Un genérico sobrante en la serie no aparece en la salida.
    assert set(serie_alineada.mapeo.keys()) == set(canasta.df.index)


def test_alinear_genericos_insuficiente():
    df_faltante = df_serie.copy()
    df_faltante.drop("huevo", inplace=True)
    mapeo_faltante = mapeo_serie.copy()
    del mapeo_faltante["huevo"]
    serie_faltante = SerieNormalizada(df_faltante, mapeo_faltante)

    # La función falla cuando falta un genérico requerido por la canasta.
    with pytest.raises(CorrespondenciaInsuficiente):
        alinear_genericos(canasta, serie_faltante)


# -- invariantes de RENOMBRES_INDICES -----------------------------------------
#
# El loader normaliza el punto final de las ramas SCIAN (rstrip('.')). Un mapa de
# renombre que apunte a un nombre con punto, o que renombre un nombre a sí mismo,
# es residuo obsoleto: corrompe el alineamiento de ponderadores en incidencias
# (queda "sin ponderador") y genera nombres fantasma en `empalmar`.


def test_renombres_indices_sin_artefacto_de_punto():
    con_punto = [
        (tipo, version, origen, destino)
        for tipo, por_version in RENOMBRES_INDICES.items()
        for version, mapa in por_version.items()
        for origen, destino in mapa.items()
        if origen.endswith(".") or destino.endswith(".")
    ]
    assert con_punto == []


def test_renombres_indices_sin_renombre_identidad():
    identidades = [
        (tipo, version, origen)
        for tipo, por_version in RENOMBRES_INDICES.items()
        for version, mapa in por_version.items()
        for origen, destino in mapa.items()
        if origen == destino
    ]
    assert identidades == []


class _CanastaFalsa:
    def __init__(self, nombres: list[str], tipo: str = "T") -> None:
        self.df = pd.DataFrame({tipo: nombres})


def test_validar_renombres_indices_detecta_obsoleto():
    canastas = {
        2013: _CanastaFalsa(["a", "b"]),
        2018: _CanastaFalsa(["a", "B2"]),
    }
    renombres = {"T": {2013: {"b": "B2", "a": "FANTASMA"}}}
    problemas = validar_renombres_indices(canastas, renombres)
    # "b" -> "B2" es válido; "a" -> "FANTASMA" tiene destino ausente en 2018.
    assert any("FANTASMA" in p for p in problemas)
    assert all("B2" not in p for p in problemas)


def test_validar_renombres_indices_consistente_no_reporta():
    canastas = {
        2013: _CanastaFalsa(["a", "b"]),
        2018: _CanastaFalsa(["a", "B2"]),
    }
    renombres = {"T": {2013: {"b": "B2"}}}
    assert validar_renombres_indices(canastas, renombres) == []
