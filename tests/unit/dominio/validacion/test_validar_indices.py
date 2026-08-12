from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.conversion import empalmar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.validacion import ValidacionIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo
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
    tipo: str = "INPC",
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
    manifiesto = [ManifestCalculo(version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame())


def _ri_dos_tramos() -> ResultadoIndice:
    """Dos manifiestos con versión, periodos y desenlace de validación distintos.

    Cada tramo tiene que ser distinguible en las tres dimensiones que el resumen
    reporta: si el emparejamiento entre manifiesto y fila se cruzara, la versión
    quedaría con los periodos y los conteos del otro tramo.
    """
    filas = [
        (_P1, 2018, 100.0),  # coincide con INEGI  -> ok
        (_P2, 2018, 100.0),
        (_P5, 2024, 500.0),  # discrepa de INEGI   -> diferencia_detectada
        (_P6, 2024, 500.0),
    ]
    df = pd.DataFrame(
        [
            {
                "periodo": periodo,
                "indice": "INPC",
                "version": version,
                "tipo": "INPC",
                "indice_replicado": valor,
                "estado_calculo": "ok",
                "motivo_error": None,
            }
            for periodo, version, valor in filas
        ]
    ).set_index(["periodo", "indice"])
    reporte = pd.DataFrame({"cobertura_genericos_pct": [100.0] * len(df)}, index=df.index)
    manifiesto = [
        ManifestCalculo(2018, "INPC", "LaspeyresDirecto"),
        ManifestCalculo(2024, "INPC", "LaspeyresEncadenadoT2"),
    ]
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame())


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
    return validar_indices(_ri(_FILAS), _INEGI)


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
    assert largo.loc[(periodo, "INPC"), "estado_validacion"] == esperado  # type: ignore[index]


def test_sin_calculo_conserva_inegi_y_error_nan() -> None:
    largo = _validacion().resultado.largo
    assert largo.loc[(_P5, "INPC"), "indice_inegi"] == pytest.approx(100.0)  # type: ignore[index]
    assert pd.isna(largo.loc[(_P5, "INPC"), "error_absoluto"])  # type: ignore[index]


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
    assert list(resumen.index) == [(2018, "INPC")]


def test_diagnostico_solo_no_ok() -> None:
    diag = _validacion().diagnostico
    assert set(diag["estado_validacion"]) == {
        "diferencia_detectada",
        "diferencia_por_parcial",
        "no_disponible",
        "sin_calculo",
        "fuera_rango_inegi",
    }


def test_tolerancia_personalizada() -> None:
    # Con tolerancia amplia, la diferencia de 0.5 cae dentro de rango.
    v = validar_indices(_ri(_FILAS), _INEGI, tolerancia=1.0)
    largo = v.resultado.largo
    assert largo.loc[(_P2, "INPC"), "estado_validacion"] == "ok"  # type: ignore[index]


def test_estado_calculo_fallida_es_sin_calculo() -> None:
    # `sin_calculo` cubre sin_datos Y fallida; el fixture principal solo ejerce
    # el primero, así que un mutante que quitara "fallida" pasaba en verde.
    v = validar_indices(_ri([(_P1, None, "fallida")]), {"INPC": {_P1: 100.0}})
    assert v.resultado.largo.loc[(_P1, "INPC"), "estado_validacion"] == "sin_calculo"  # type: ignore[index]


@pytest.mark.parametrize(
    "tolerancia, esperado",
    [(0.5, "ok"), (0.4999, "diferencia_detectada")],
    ids=["error_igual_a_tolerancia", "error_apenas_mayor"],
)
def test_frontera_de_la_tolerancia_es_inclusiva(tolerancia: float, esperado: str) -> None:
    # La comparación es `error <= tolerancia`. Sin este par, el mutante `<`
    # pasaba la suite entera: ningún otro caso cae justo en la frontera.
    v = validar_indices(_ri([(_P1, 100.0, "ok")]), {"INPC": {_P1: 100.5}}, tolerancia=tolerancia)
    assert v.resultado.largo.loc[(_P1, "INPC"), "estado_validacion"] == esperado  # type: ignore[index]


def test_resumen_sin_comparables_deja_error_maximo_nan() -> None:
    v = validar_indices(_ri([(_P1, 100.0, "ok")]), {})
    fila = v.resumen.iloc[0]
    assert fila["n_comparables"] == 0
    assert pd.isna(fila["error_absoluto_max"])
    assert fila["estado_validacion_global"] == "no_disponible"


def test_mapa_inegi_con_varias_claves_empareja_cada_indice_con_la_suya() -> None:
    # INFLACION COMPONENTE y SUBCOMPONENTE traen 2 y 4 claves; el fixture normal
    # usa una sola y no distingue un emparejamiento correcto de uno degenerado.
    df = pd.DataFrame(
        [
            {
                "periodo": _P1,
                "indice": indice,
                "version": 2018,
                "tipo": "INFLACION COMPONENTE",
                "indice_replicado": valor,
                "estado_calculo": "ok",
                "motivo_error": None,
            }
            for indice, valor in (("subyacente", 100.0), ("no subyacente", 200.0))
        ]
    ).set_index(["periodo", "indice"])
    reporte = pd.DataFrame({"cobertura_genericos_pct": [100.0] * 2}, index=df.index)
    resultado = ResultadoIndice(
        df,
        [ManifestCalculo(2018, "INFLACION COMPONENTE", "LaspeyresDirecto")],
        reporte,
        pd.DataFrame(),
    )

    v = validar_indices(
        resultado,
        {"subyacente": {_P1: 100.0}, "no subyacente": {_P1: 999.0}},
    )

    largo = v.resultado.largo
    assert largo.loc[(_P1, "subyacente"), "estado_validacion"] == "ok"  # type: ignore[index]
    assert largo.loc[(_P1, "no subyacente"), "estado_validacion"] == "diferencia_detectada"  # type: ignore[index]
    assert largo.loc[(_P1, "no subyacente"), "indice_inegi"] == pytest.approx(999.0)  # type: ignore[index]


# -- resumen con varios manifiestos --------------------------------------------


def test_resumen_asigna_a_cada_manifiesto_sus_propias_filas() -> None:
    # Regresión del emparejamiento manifiesto <-> fila del resumen: los dos tramos
    # difieren en versión, periodos y desenlace, así que un cruce se ve en las tres.
    resumen = validar_indices(_ri_dos_tramos(), _INEGI).resumen

    assert list(resumen.index) == [(2018, "INPC"), (2024, "INPC")]

    viejo: pd.Series = resumen.loc[(2018, "INPC")]  # type: ignore[assignment]
    nuevo: pd.Series = resumen.loc[(2024, "INPC")]  # type: ignore[assignment]

    assert (viejo["periodo_inicio"], viejo["periodo_fin"]) == (_P1, _P2)
    assert (nuevo["periodo_inicio"], nuevo["periodo_fin"]) == (_P5, _P6)

    # 2018 compara contra 100.0 y 100.5 -> un ok y una diferencia.
    assert viejo["n_comparables"] == 2
    assert viejo["estado_validacion_global"] == "diferencia_detectada"
    assert viejo["error_absoluto_max"] == pytest.approx(0.5)

    # 2024 solo tiene _P5 en el mapa (=100.0) y _P6 fuera de rango.
    assert nuevo["n_comparables"] == 1
    assert nuevo["n_fuera_rango_inegi"] == 1
    assert nuevo["error_absoluto_max"] == pytest.approx(400.0)


def test_resumen_soporta_manifiestos_repetidos_producidos_por_empalmar() -> None:
    tramo_a = _ri([(_P1, 100.0, "ok"), (_P2, 100.0, "ok")])
    tramo_b = _ri([(_P2, 100.0, "ok"), (_P3, 100.0, "ok")])
    resultado = empalmar([tramo_a, tramo_b])
    inegi = {"INPC": {_P1: 100.0, _P2: 100.0, _P3: 100.5}}

    resumen = validar_indices(resultado, inegi).resumen

    assert list(resumen.index) == [(2018, "INPC"), (2018, "INPC")]
    assert list(resumen["estado_calculo"]) == ["ok", "ok"]
    assert list(resumen["periodo_inicio"]) == [_P1, _P1]
    assert list(resumen["periodo_fin"]) == [_P3, _P3]
    assert list(resumen["n_comparables"]) == [3, 3]
    assert list(resumen["error_absoluto_max"]) == pytest.approx([0.5, 0.5])
    assert list(resumen["estado_validacion_global"]) == [
        "diferencia_detectada",
        "diferencia_detectada",
    ]


# -- fail-fast -----------------------------------------------------------------


def test_tipo_no_comparable_falla() -> None:
    # El comparador rechaza el tipo aunque el llamador ya lo haya validado.
    resultado = _ri([(_P1, 100.0, "ok")], tipo="COG", indice="bienes")
    with pytest.raises(InvarianteViolado):
        validar_indices(resultado, _INEGI)


@pytest.mark.parametrize("tolerancia", [-1.0, float("nan"), float("inf")])
def test_tolerancia_no_finita_o_negativa_falla(tolerancia: float) -> None:
    # Sin la guardia esto NO fallaba: dos series idénticas salían como
    # diferencia_detectada con error_absoluto = 0.0.
    with pytest.raises(InvarianteViolado):
        validar_indices(_ri([(_P1, 100.0, "ok")]), _INEGI, tolerancia=tolerancia)
