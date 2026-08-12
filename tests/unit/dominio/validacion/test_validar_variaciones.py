from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.validacion import ValidacionVariacion
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
    tipo: str = "INPC",
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
        versiones=[2018],
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    reporte = pd.DataFrame(
        {"estado_calculo": [e for _, _, e in filas], "version_t": [2024] * len(filas)},
        index=df.index,
    )
    return ResultadoVariacion(df, manifiesto, reporte, pd.DataFrame())


_FILAS = [
    (_P1, 1.0, "ok"),
    (_P2, 1.0, "ok"),
    (_P3, 1.0, "parcial"),
    (_P4, 1.0, "ok"),
    (_P5, 1.0, "ok"),
]
_INEGI = {"INPC": {_P1: 1.0, _P2: 2.0, _P3: 2.0, _P4: None}}


def _validacion() -> ValidacionVariacion:
    return validar_variaciones(_rv(_FILAS), _INEGI)


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
    assert largo.loc[(periodo, "INPC"), "estado_validacion"] == esperado  # type: ignore[index]


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


@pytest.mark.parametrize("estado_no_computable", ["sin_datos", "fallida"])
def test_fila_no_computable_es_sin_calculo_y_no_entra_al_resumen(
    estado_no_computable: str,
) -> None:
    # El .resumen de derivados se calcula sobre .resultado.largo, que solo tiene
    # filas computables. La asimetría es deliberada (docs/diseño.md §5.8, §11.x):
    # el resumen de derivados NO lleva n_sin_calculo y su global nunca vale
    # sin_calculo, aunque el .reporte sí marque esas filas.
    df = pd.DataFrame(
        [
            {
                "periodo": _P1,
                "indice": "INPC",
                "tipo": "INPC",
                "clase_variacion": "periodica_mensual",
                "variacion_pp": 1.0,
                "estado_calculo": "ok",
                "version_t": 2024,
            }
        ]
    ).set_index(["periodo", "indice"])
    reporte = pd.DataFrame(
        {"estado_calculo": ["ok", estado_no_computable], "version_t": [2024, 2024]},
        index=pd.MultiIndex.from_tuples(
            [(_P1, "INPC"), (_P2, "INPC")], names=["periodo", "indice"]
        ),
    )
    manifiesto = ManifestDerivado(
        versiones=[2018],
        tipo="INPC",
        clase="periodica_mensual",
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    resultado = ResultadoVariacion(df, manifiesto, reporte, pd.DataFrame())

    v = validar_variaciones(resultado, {"INPC": {_P1: 1.0, _P2: 5.0}})

    assert v.reporte.loc[(_P2, "INPC"), "estado_validacion"] == "sin_calculo"  # type: ignore[index]
    assert not v.reporte["estado_validacion"].isna().any()
    assert (_P2, "INPC") not in v.resultado.largo.index
    # Contrato del resumen: la fila sin_calculo no lo afecta de ninguna forma.
    assert "n_sin_calculo" not in v.resumen.columns
    assert v.resumen.iloc[0]["estado_validacion_global"] == "ok"


# -- fail-fast -----------------------------------------------------------------


def test_tipo_no_comparable_falla() -> None:
    # El comparador rechaza el tipo aunque el llamador ya lo haya validado.
    resultado = _rv([(_P1, 1.0, "ok")], tipo="COG", indice="bienes")
    with pytest.raises(InvarianteViolado):
        validar_variaciones(resultado, _INEGI)


def test_clase_no_mapeable_falla() -> None:
    # Idem para la clase: el rechazo sobrevive a invocar el comparador directo.
    resultado = _rv([(_P1, 1.0, "ok")], clase="periodica_bimestral")
    with pytest.raises(ErrorConfiguracion):
        validar_variaciones(resultado, _INEGI)


@pytest.mark.parametrize("tolerancia_pp", [-1.0, float("nan"), float("inf")])
def test_tolerancia_no_finita_o_negativa_falla(tolerancia_pp: float) -> None:
    with pytest.raises(InvarianteViolado):
        validar_variaciones(_rv(_FILAS), _INEGI, tolerancia_pp=tolerancia_pp)


@pytest.mark.parametrize(
    "tolerancia_pp, esperado",
    [(0.5, "ok"), (0.4999, "diferencia_detectada")],
    ids=["error_igual_a_tolerancia", "error_apenas_mayor"],
)
def test_frontera_de_la_tolerancia_es_inclusiva(tolerancia_pp: float, esperado: str) -> None:
    validacion = validar_variaciones(
        _rv([(_P1, 1.0, "ok")]),
        {"INPC": {_P1: 1.5}},
        tolerancia_pp=tolerancia_pp,
    )
    assert validacion.resultado.largo.loc[(_P1, "INPC"), "estado_validacion"] == esperado  # type: ignore[index]


# -- propagación del valor oficial al largo ------------------------------------


def test_valor_oficial_y_error_llegan_al_largo() -> None:
    # El largo se arma reindexando el reporte; sin esto solo se afirmaba que
    # estado_validacion cruzaba, no el valor de INEGI ni el error.
    largo = _validacion().resultado.largo
    assert largo.loc[(_P2, "INPC"), "variacion_inegi_pp"] == pytest.approx(2.0)  # type: ignore[index]
    assert largo.loc[(_P2, "INPC"), "error_absoluto_pp"] == pytest.approx(1.0)  # type: ignore[index]
    # _P4 está en el mapa con None: INEGI cubre el periodo pero no publicó valor.
    assert pd.isna(largo.loc[(_P4, "INPC"), "variacion_inegi_pp"])  # type: ignore[index]
    assert pd.isna(largo.loc[(_P4, "INPC"), "error_absoluto_pp"])  # type: ignore[index]
