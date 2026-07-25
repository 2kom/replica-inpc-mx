from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.aplicacion.casos_uso.calcular_historia import (
    CalcularHistoria,
    _referencias_normalizadas,
)
from replica_inpc.dominio.correspondencia_canastas import RENOMBRES_INDICES
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo, VersionCanasta

# -- fixtures: canastas y series sintéticas ------------------------------------


def _canasta(version: int, *, encadenado: bool) -> CanastaCanonica:
    enc = [float("nan"), float("nan")] if encadenado else [None, None]
    df = pd.DataFrame(
        {"ponderador": ["50.0", "50.0"], "encadenamiento": enc},
        index=pd.Index(["a", "b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _serie(
    periodos: list[PeriodoQuincenal],
    vals_a: list[float],
    vals_b: list[float],
) -> SerieNormalizada:
    df = pd.DataFrame({"a": vals_a, "b": vals_b}, index=periodos).T
    return SerieNormalizada(df, {"a": "A", "b": "B"})


class _LectorCanastaFake:
    def __init__(self, mapa: dict[Path, CanastaCanonica]) -> None:
        self._mapa = mapa

    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica:
        return self._mapa[ruta]


class _LectorSeriesFake:
    def __init__(self, mapa: dict[Path, SerieNormalizada]) -> None:
        self._mapa = mapa

    def leer(self, ruta: Path) -> SerieNormalizada:
        return self._mapa[ruta]


# Periodos: traslape 2013 = Q(2013,3,2); traslape 2018 = Q(2018,7,2).
# _P13 incluye Q(2018,7,2) para compartir frontera con _P18 (requisito topología PATH).
_P10 = [PeriodoQuincenal(2013, 2, 2), PeriodoQuincenal(2013, 3, 1), PeriodoQuincenal(2013, 3, 2)]
_P13 = [PeriodoQuincenal(2013, 3, 2), PeriodoQuincenal(2013, 4, 1), PeriodoQuincenal(2013, 4, 2), PeriodoQuincenal(2018, 7, 2)]
_P18 = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]

_RC10, _RC13, _RC18 = Path("c2010"), Path("c2013"), Path("c2018")
_RS10, _RS13, _RS18 = Path("s2010"), Path("s2013"), Path("s2018")


def _historia_3_versiones() -> CalcularHistoria:
    canastas = {
        _RC10: _canasta(2010, encadenado=False),
        _RC13: _canasta(2013, encadenado=True),
        _RC18: _canasta(2018, encadenado=False),
    }
    series = {
        _RS10: _serie(_P10, [100.0, 101.0, 102.0], [100.0, 103.0, 104.0]),
        _RS13: _serie(_P13, [110.0, 111.0, 112.0, 115.0], [110.0, 113.0, 114.0, 116.0]),
        _RS18: _serie(_P18, [200.0, 201.0], [200.0, 203.0]),
    }
    return CalcularHistoria(_LectorCanastaFake(canastas), _LectorSeriesFake(series))


_INSUMOS_3 = [
    (2010, _RC10, _RS10),
    (2013, _RC13, _RS13),
    (2018, _RC18, _RS18),
]


# -- ejecución exitosa ---------------------------------------------------------


def test_una_version_directo() -> None:
    historia = _historia_3_versiones()
    r = historia.ejecutar([(2018, _RC18, _RS18)], "inpc", PeriodoQuincenal(2018, 7, 2), "quincenal")
    assert isinstance(r, ResultadoIndice)
    assert r.periodo_referencia == PeriodoQuincenal(2018, 7, 2)
    assert {m.version for m in r.manifiesto} == {2018}


def test_tres_versiones_contiguas_fold_left() -> None:
    # calcular_historia encadena versiones vía fold-left con forzar=True;
    # cada par consecutivo comparte exactamente 1 periodo (frontera).
    historia = _historia_3_versiones()
    r = historia.ejecutar(_INSUMOS_3, "inpc", PeriodoQuincenal(2013, 4, 1), "quincenal")
    assert isinstance(r, ResultadoIndice)
    assert {m.version for m in r.manifiesto} == {2010, 2013, 2018}
    assert r.periodo_referencia == PeriodoQuincenal(2013, 4, 1)


def test_tres_versiones_propagacion_referencia_empalme() -> None:
    # Con la referencia propagada, el tramo T1 (2013) en el traslape vale
    # exactamente el índice 2010 en ese periodo. Rebasando cadena y corrida
    # 2010-sola en el mismo periodo (2010-tramo), el valor en el traslape debe
    # coincidir; sin referencia (fallback factor_h endógeno) diferiría.
    historia = _historia_3_versiones()
    base = PeriodoQuincenal(2013, 3, 1)
    traslape = PeriodoQuincenal(2013, 3, 2)
    cadena = historia.ejecutar(_INSUMOS_3, "inpc", base, "quincenal")
    solo_2010 = historia.ejecutar([(2010, _RC10, _RS10)], "inpc", base, "quincenal")
    assert cadena.df.loc[(traslape, "INPC"), "indice_replicado"] == pytest.approx(
        solo_2010.df.loc[(traslape, "INPC"), "indice_replicado"]
    )


def test_periodicidad_mensual_preserva_periodo_referencia() -> None:
    historia = _historia_3_versiones()
    r = historia.ejecutar([(2018, _RC18, _RS18)], "inpc", PeriodoMensual(2018, 8), "mensual")
    assert r.periodo_referencia == PeriodoMensual(2018, 8)
    assert all(isinstance(p, PeriodoMensual) for p in r.df.index.get_level_values("periodo"))


# -- errores -------------------------------------------------------------------


@pytest.mark.parametrize(
    "insumos, periodicidad",
    [
        pytest.param([], "quincenal", id="insumos_vacio"),
        pytest.param(
            [(2018, _RC18, _RS18), (2018, _RC18, _RS18)], "quincenal", id="version_duplicada"
        ),
        pytest.param([(2010, _RC10, _RS10), (2018, _RC18, _RS18)], "quincenal", id="no_contiguas"),
        pytest.param([(2013, _RC13, _RS13), (2018, _RC18, _RS18)], "quincenal", id="2013_sin_2010"),
        pytest.param([(2024, _RC18, _RS18)], "quincenal", id="2024_sin_2018"),
        pytest.param([(2018, _RC18, _RS18)], "semanal", id="periodicidad_invalida"),
    ],
)
def test_validaciones_fallan(insumos: list, periodicidad: str) -> None:
    historia = _historia_3_versiones()
    with pytest.raises(InvarianteViolado):
        historia.ejecutar(insumos, "inpc", PeriodoQuincenal(2018, 7, 2), periodicidad)  # type: ignore[arg-type]


def test_periodo_referencia_inexistente_emite_warning() -> None:
    # Periodo de referencia fuera de rango → todos los índices huérfanos → warning.
    historia = _historia_3_versiones()
    with pytest.warns(UserWarning, match="sin dato"):
        historia.ejecutar([(2018, _RC18, _RS18)], "inpc", PeriodoQuincenal(2099, 1, 1), "quincenal")


# -- _referencias_normalizadas -------------------------------------------------


def test_referencias_inpc_identidad() -> None:
    traslape = PeriodoQuincenal(2024, 7, 2)
    df = pd.DataFrame(
        {
            "version": [2018],
            "tipo": ["inpc"],
            "indice_replicado": [123.4],
            "estado_calculo": ["ok"],
        },
        index=pd.MultiIndex.from_tuples([(traslape, "INPC")], names=["periodo", "indice"]),
    )
    prev = ResultadoIndice(
        df,
        [ManifestCalculo("x", 2018, "inpc", "LaspeyresDirecto")],  # type: ignore[arg-type]
        pd.DataFrame(),
        pd.DataFrame(),
    )
    refs = _referencias_normalizadas(prev, "inpc", 2018, 2024)
    assert refs == {"INPC": pytest.approx(123.4)}


def test_referencias_normaliza_clave_renombrada() -> None:
    # Toma dinámicamente una pareja old -> new del catálogo para CCIF division.
    tipo = "CCIF division"
    old, new = next(iter(RENOMBRES_INDICES[tipo][2018].items()))
    traslape = PeriodoQuincenal(2024, 7, 2)
    df = pd.DataFrame(
        {
            "version": [2018],
            "tipo": [tipo],
            "indice_replicado": [55.5],
            "estado_calculo": ["ok"],
        },
        index=pd.MultiIndex.from_tuples([(traslape, old)], names=["periodo", "indice"]),
    )
    prev = ResultadoIndice(
        df,
        [ManifestCalculo("x", 2018, tipo, "LaspeyresDirecto")],  # type: ignore[arg-type]
        pd.DataFrame(),
        pd.DataFrame(),
    )
    refs = _referencias_normalizadas(prev, tipo, 2018, 2024)
    assert refs == {new: pytest.approx(55.5)}
