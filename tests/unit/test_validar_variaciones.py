from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.tipos import ManifestDerivado
from replica_inpc.dominio.validacion.variaciones import validar_variaciones

_P1 = PeriodoMensual(2024, 1)
_P2 = PeriodoMensual(2024, 2)
_P3 = PeriodoMensual(2024, 3)
_P4 = PeriodoMensual(2024, 4)
_P5 = PeriodoMensual(2024, 5)

# -- helpers -------------------------------------------------------------------


def _rv(
    filas: list[tuple[PeriodoMensual, float, str]],
    *,
    tipo: str = "inpc",
    clase: str = "periodica_mensual",
    indice: str = "INPC",
) -> ResultadoVariacion:
    rows = []
    for periodo, valor, estado in filas:
        rows.append(
            {
                "periodo": periodo,
                "indice": indice,
                "tipo": tipo,
                "clase_variacion": clase,
                "variacion_pp": float(valor),
                "estado_calculo": estado,
                "version_t": 2024,
            }
        )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = ManifestDerivado(
        id_corrida=["c1"], tipo=tipo, clase=clase, descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    reporte = pd.DataFrame(
        {"estado_calculo": [e for _, _, e in filas], "version_t": [2024] * len(filas)},
        index=df.index,
    )
    return ResultadoVariacion(df, manifiesto, reporte, pd.DataFrame())


class _Fuente:
    def __init__(self, datos: dict) -> None:
        self._datos = datos

    def obtener_variaciones(self, periodos: list, tipo_variacion: str) -> dict:
        return self._datos


class _FuenteExplota:
    def obtener_variaciones(self, periodos: list, tipo_variacion: str) -> dict:
        raise AssertionError("FuenteValidacion no debe llamarse")


_FILAS = [
    (_P1, 1.0, "ok"),
    (_P2, 1.0, "ok"),
    (_P3, 1.0, "parcial"),
    (_P4, 1.0, "ok"),
    (_P5, 1.0, "ok"),
]
_INEGI = {"INPC": {_P1: 1.0, _P2: 2.0, _P3: 2.0, _P4: None}}


def _validacion() -> object:
    return validar_variaciones(_rv(_FILAS), _Fuente(_INEGI))


# -- estado_validacion por rama ------------------------------------------------


@pytest.mark.parametrize(
    "periodo, esperado",
    [
        (_P1, "ok"),
        (_P2, "diferencia_detectada"),
        (_P3, "diferencia_por_parcial"),
        (_P4, "no_disponible"),
        (_P5, "fuera_rango_inegi"),
    ],
)
def test_estado_validacion_por_rama(periodo: PeriodoMensual, esperado: str) -> None:
    largo = _validacion().resultado.largo
    assert largo.loc[(periodo, "INPC"), "estado_validacion"] == esperado


def test_resumen_conteos_y_global() -> None:
    fila = _validacion().resumen.iloc[0]
    assert fila["n_comparables"] == 3
    assert fila["n_no_disponibles"] == 1
    assert fila["n_fuera_rango_inegi"] == 1
    assert fila["n_diferencia_por_parcial"] == 1
    assert fila["error_absoluto_max_pp"] == pytest.approx(1.0)
    assert fila["estado_validacion_global"] == "diferencia_detectada"


def test_diagnostico_solo_no_ok() -> None:
    diag = _validacion().diagnostico
    assert set(diag["estado_validacion"]) == {
        "diferencia_detectada",
        "diferencia_por_parcial",
        "no_disponible",
        "fuera_rango_inegi",
    }
    assert "id_corrida" not in diag.columns


def test_reporte_fila_no_computable_es_sin_calculo() -> None:
    # El .reporte derivado incluye filas no computables ausentes del largo.
    df = pd.DataFrame(
        [
            {
                "periodo": _P1,
                "indice": "INPC",
                "tipo": "inpc",
                "clase_variacion": "periodica_mensual",
                "variacion_pp": 1.0,
                "estado_calculo": "ok",
                "version_t": 2024,
            }
        ]
    ).set_index(["periodo", "indice"])
    reporte = pd.DataFrame(
        {"estado_calculo": ["ok", "sin_datos"], "version_t": [2024, 2024]},
        index=pd.MultiIndex.from_tuples(
            [(_P1, "INPC"), (_P2, "INPC")], names=["periodo", "indice"]
        ),
    )
    manifiesto = ManifestDerivado(
        id_corrida=["c1"], tipo="inpc", clase="periodica_mensual", descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    resultado = ResultadoVariacion(df, manifiesto, reporte, pd.DataFrame())
    v = validar_variaciones(resultado, _Fuente({"INPC": {_P1: 1.0, _P2: 5.0}}))
    assert v.reporte.loc[(_P2, "INPC"), "estado_validacion"] == "sin_calculo"
    assert not v.reporte["estado_validacion"].isna().any()
    assert (_P2, "INPC") not in v.resultado.largo.index


# -- fail-fast -----------------------------------------------------------------


def test_tipo_no_comparable_falla_sin_tocar_fuente() -> None:
    resultado = _rv([(_P1, 1.0, "ok")], tipo="COG", indice="bienes")
    with pytest.raises(InvarianteViolado):
        validar_variaciones(resultado, _FuenteExplota())


def test_clase_no_mapeable_falla_sin_tocar_fuente() -> None:
    resultado = _rv([(_P1, 1.0, "ok")], clase="periodica_bimestral")
    with pytest.raises(ErrorConfiguracion):
        validar_variaciones(resultado, _FuenteExplota())
