from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.validacion import ValidacionIncidencia
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.tipos import ManifestDerivado
from replica_inpc.dominio.validacion.incidencias import validar_incidencias

_P1 = PeriodoMensual(2024, 1)
_P2 = PeriodoMensual(2024, 2)
_P3 = PeriodoMensual(2024, 3)
_P4 = PeriodoMensual(2024, 4)
_P5 = PeriodoMensual(2024, 5)


# -- helpers -------------------------------------------------------------------


def _ri(
    filas: list[tuple[PeriodoMensual, float, str]],
    *,
    tipo: str = "INFLACION COMPONENTE",
    clase: str = "periodica_mensual",
    indice: str = "subyacente",
) -> ResultadoIncidencia:
    rows = []
    for periodo, valor, estado in filas:
        rows.append(
            {
                "periodo": periodo,
                "indice": indice,
                "tipo": tipo,
                "clase_incidencia": clase,
                "incidencia_pp": float(valor),
                "estado_calculo": estado,
                "version_t": 2024,
            }
        )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = ManifestDerivado(
        versiones=[2018, 2018],
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    reporte = pd.DataFrame(
        {"estado_calculo": [e for _, _, e in filas], "version_t": [2024] * len(filas)},
        index=df.index,
    )
    return ResultadoIncidencia(df, manifiesto, reporte, pd.DataFrame())


_FILAS = [
    (_P1, 1.0, "ok"),
    (_P2, 1.0, "ok"),
    (_P3, 1.0, "parcial"),
    (_P4, 1.0, "ok"),
    (_P5, 1.0, "ok"),
]
_INEGI = {"subyacente": {_P1: 1.0, _P2: 2.0, _P3: 2.0, _P4: None}}


def _validacion() -> ValidacionIncidencia:
    return validar_incidencias(_ri(_FILAS), _INEGI)


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
    assert largo.loc[(periodo, "subyacente"), "estado_validacion"] == esperado  # type: ignore[index]


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


@pytest.mark.parametrize("estado_no_computable", ["sin_datos", "fallida"])
def test_fila_no_computable_es_sin_calculo_y_no_entra_al_resumen(
    estado_no_computable: str,
) -> None:
    # El .resumen de derivados se calcula sobre .resultado.largo, que solo tiene
    # filas computables. La asimetría es deliberada (docs/diseño.md §5.9): el
    # resumen de derivados NO lleva n_sin_calculo y su global nunca vale
    # sin_calculo, aunque el .reporte sí marque esas filas.
    df = pd.DataFrame(
        [
            {
                "periodo": _P1,
                "indice": "subyacente",
                "tipo": "INFLACION COMPONENTE",
                "clase_incidencia": "periodica_mensual",
                "incidencia_pp": 1.0,
                "estado_calculo": "ok",
                "version_t": 2024,
            }
        ]
    ).set_index(["periodo", "indice"])
    reporte = pd.DataFrame(
        {"estado_calculo": ["ok", estado_no_computable], "version_t": [2024, 2024]},
        index=pd.MultiIndex.from_tuples(
            [(_P1, "subyacente"), (_P2, "subyacente")], names=["periodo", "indice"]
        ),
    )
    manifiesto = ManifestDerivado(
        versiones=[2018, 2018],
        tipo="INFLACION COMPONENTE",
        clase="periodica_mensual",
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    resultado = ResultadoIncidencia(df, manifiesto, reporte, pd.DataFrame())

    v = validar_incidencias(resultado, {"subyacente": {_P1: 1.0, _P2: 5.0}})

    assert v.reporte.loc[(_P2, "subyacente"), "estado_validacion"] == "sin_calculo"  # type: ignore[index]
    assert not v.reporte["estado_validacion"].isna().any()
    assert (_P2, "subyacente") not in v.resultado.largo.index
    # Contrato del resumen: la fila sin_calculo no lo afecta de ninguna forma.
    assert "n_sin_calculo" not in v.resumen.columns
    assert v.resumen.iloc[0]["estado_validacion_global"] == "ok"


# -- fail-fast -----------------------------------------------------------------


def test_tipo_no_comparable_falla() -> None:
    # El comparador rechaza el tipo aunque el llamador ya lo haya validado.
    resultado = _ri([(_P1, 1.0, "ok")], tipo="COG", indice="bienes")
    with pytest.raises(InvarianteViolado):
        validar_incidencias(resultado, _INEGI)


def test_clase_no_mapeable_falla() -> None:
    # Idem para la clase: el rechazo sobrevive a invocar el comparador directo.
    resultado = _ri([(_P1, 1.0, "ok")], clase="periodica_quincenal")
    with pytest.raises(ErrorConfiguracion):
        validar_incidencias(resultado, _INEGI)
