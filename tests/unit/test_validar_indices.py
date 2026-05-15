from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import ValidacionIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestUnidad
from replica_inpc.dominio.validacion.indices import validar_indices

_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)
_P3 = PeriodoQuincenal(2018, 2, 1)
_P4 = PeriodoQuincenal(2018, 2, 2)
_P5 = PeriodoQuincenal(2018, 3, 1)
_P6 = PeriodoQuincenal(2018, 3, 2)

# -- helpers -------------------------------------------------------------------


def _ri(
    filas: list[tuple[PeriodoQuincenal, float | None, str]],
    *,
    tipo: str = "inpc",
    indice: str = "INPC",
    version: int = 2018,
) -> ResultadoIndice:
    rows = []
    for periodo, valor, estado in filas:
        rows.append(
            {
                "periodo": periodo,
                "indice": indice,
                "version": version,
                "tipo": tipo,
                "indice_replicado": float("nan") if valor is None else float(valor),
                "estado_calculo": estado,
                "motivo_error": None if estado in ("ok", "parcial") else "faltante",
            }
        )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    reporte = pd.DataFrame({"cobertura_genericos_pct": [100.0] * len(df)}, index=df.index)
    manifiesto = [ManifestUnidad("c1", version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame())


class _Fuente:
    def __init__(self, datos: dict) -> None:
        self._datos = datos

    def obtener_indices(self, periodos: list) -> dict:
        return self._datos


class _FuenteExplota:
    def obtener_indices(self, periodos: list) -> dict:
        raise AssertionError("FuenteValidacion no debe llamarse")


# Fixture con las seis ramas de estado_validacion.
_FILAS = [
    (_P1, 100.0, "ok"),
    (_P2, 100.0, "ok"),
    (_P3, 100.0, "parcial"),
    (_P4, 100.0, "ok"),
    (_P5, None, "sin_datos"),
    (_P6, 100.0, "ok"),
]
_INEGI = {"INPC": {_P1: 100.0, _P2: 100.5, _P3: 100.5, _P4: None, _P5: 100.0}}


def _validacion() -> ValidacionIndice:
    return validar_indices(_ri(_FILAS), _Fuente(_INEGI))


# -- estado_validacion por rama ------------------------------------------------


@pytest.mark.parametrize(
    "periodo, esperado",
    [
        (_P1, "ok"),
        (_P2, "diferencia_detectada"),
        (_P3, "diferencia_por_parcial"),
        (_P4, "no_disponible"),
        (_P5, "sin_calculo"),
        (_P6, "fuera_rango_inegi"),
    ],
)
def test_estado_validacion_por_rama(periodo: PeriodoQuincenal, esperado: str) -> None:
    largo = _validacion().resultado.largo
    assert largo.loc[(periodo, "INPC"), "estado_validacion"] == esperado


def test_sin_calculo_conserva_inegi_y_error_nan() -> None:
    largo = _validacion().resultado.largo
    assert largo.loc[(_P5, "INPC"), "indice_inegi"] == pytest.approx(100.0)
    assert pd.isna(largo.loc[(_P5, "INPC"), "error_absoluto"])


def test_resumen_conteos_y_global() -> None:
    resumen = _validacion().resumen
    fila = resumen.iloc[0]
    assert fila["n_comparables"] == 3
    assert fila["n_no_disponibles"] == 1
    assert fila["n_fuera_rango_inegi"] == 1
    assert fila["n_sin_calculo"] == 1
    assert fila["n_diferencia_por_parcial"] == 1
    assert fila["error_absoluto_max"] == pytest.approx(0.5)
    assert fila["estado_validacion_global"] == "diferencia_detectada"
    assert list(resumen.index) == ["c1"]


def test_diagnostico_solo_no_ok() -> None:
    diag = _validacion().diagnostico
    assert set(diag["estado_validacion"]) == {
        "diferencia_detectada",
        "diferencia_por_parcial",
        "no_disponible",
        "sin_calculo",
        "fuera_rango_inegi",
    }
    assert (diag["id_corrida"] == "c1").all()


def test_tolerancia_personalizada() -> None:
    # Con tolerancia amplia, la diferencia de 0.5 cae dentro de rango.
    v = validar_indices(_ri(_FILAS), _Fuente(_INEGI), tolerancia=1.0)
    largo = v.resultado.largo
    assert largo.loc[(_P2, "INPC"), "estado_validacion"] == "ok"


# -- fail-fast -----------------------------------------------------------------


def test_tipo_no_comparable_falla_sin_tocar_fuente() -> None:
    resultado = _ri([(_P1, 100.0, "ok")], tipo="COG", indice="bienes")
    with pytest.raises(InvarianteViolado):
        validar_indices(resultado, _FuenteExplota())
