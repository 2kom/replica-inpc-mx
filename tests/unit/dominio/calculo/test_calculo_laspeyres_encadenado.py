from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

import replica_inpc as rep
from replica_inpc.dominio.calculo.laspeyres_encadenado import (
    LaspeyresEncadenadoT1,
    LaspeyresEncadenadoT2,
)
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

# ---------- T2 (v2024) ----------

_traslape_t2 = PeriodoQuincenal(2024, 7, 2)
_post_t2 = PeriodoQuincenal(2024, 8, 1)


def _canasta_t2(
    encadenamiento: list[str | None] | None = None, cog: list[str] | None = None
) -> CanastaCanonica:
    enc = encadenamiento if encadenamiento is not None else ["1.5", "1.4", "1.6", "1.3"]
    datos: dict[str, list[Any]] = {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": enc,
    }
    if cog is not None:
        datos["COG"] = cog
    df = pd.DataFrame(datos, index=["arroz", "frijol", "leche", "huevo"])
    return CanastaCanonica(df, 2024)


def _serie_t2() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [150.0, 151.5],
            "frijol": [140.0, 144.2],
            "leche": [160.0, 168.0],
            "huevo": [130.0, 132.6],
        },
        index=[_traslape_t2, _post_t2],
    ).T
    return SerieNormalizada(df)


_F_H_T2 = (10 * 1.5 + 20 * 1.4 + 30 * 1.6 + 40 * 1.3) / 100


def test_t2_traslape_es_fh_por_100_sin_referencia() -> None:
    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "INPC")
    valor = r.df.at[(_traslape_t2, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(_F_H_T2 * 100)


def test_t2_difiere_de_directo() -> None:
    enc = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "INPC")
    val_enc = enc.df.at[(_post_t2, "INPC"), "indice_replicado"]
    # Laspeyres naive (sin de-encadenamiento) para el mismo periodo
    serie_df = _serie_t2().df
    pond = [10.0, 20.0, 30.0, 40.0]
    vals = [
        float(cast(Any, serie_df.at[g, _post_t2])) for g in ["arroz", "frijol", "leche", "huevo"]
    ]
    val_naive = sum(v * p for v, p in zip(vals, pond)) / sum(pond)
    assert val_enc != pytest.approx(val_naive)


def test_t2_con_referencia_ancla_traslape_en_ref() -> None:
    ref = 134.471
    r = LaspeyresEncadenadoT2({"INPC": ref}).calcular(_canasta_t2(), _serie_t2(), "INPC")
    # factor_h = ref/100, i_tramo[traslape] = 100 (porque serie/f_k = 100 en traslape)
    valor = r.df.at[(_traslape_t2, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(ref)


def test_t2_fk_desde_serie_igual_a_desde_canasta() -> None:
    r_can = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "INPC")
    r_ser = LaspeyresEncadenadoT2().calcular(
        _canasta_t2([None, None, None, None]), _serie_t2(), "INPC"
    )
    assert r_can.df["indice_replicado"].tolist() == pytest.approx(
        r_ser.df["indice_replicado"].tolist()
    )


def test_t2_manifiesto() -> None:
    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "INPC")
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresEncadenadoT2"
    assert m.version == 2024


def test_t2_rechaza_canasta_no_2024() -> None:
    df = pd.DataFrame(
        {
            "ponderador": ["10.0", "20.0", "30.0", "40.0"],
            "encadenamiento": ["1.5", "1.4", "1.6", "1.3"],
        },
        index=["arroz", "frijol", "leche", "huevo"],
    )
    canasta_2013 = CanastaCanonica(df, 2013)
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT2().calcular(canasta_2013, _serie_t2(), "INPC")


def test_t2_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "no_existe")


# ---------- T1 (v2013) ----------

_traslape_t1 = PeriodoQuincenal(2013, 3, 2)
_post_t1 = PeriodoQuincenal(2013, 4, 1)


def _canasta_t1(cog: list[str] | None = None) -> CanastaCanonica:
    datos: dict[str, list[Any]] = {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": ["1.2", "0.8", "1.1", "0.9"],
    }
    if cog is not None:
        datos["COG"] = cog
    df = pd.DataFrame(datos, index=["arroz", "frijol", "leche", "huevo"])
    return CanastaCanonica(df, 2013)


def _serie_t1() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [120.0, 123.0],
            "frijol": [80.0, 82.0],
            "leche": [110.0, 113.0],
            "huevo": [90.0, 91.5],
        },
        index=[_traslape_t1, _post_t1],
    ).T
    return SerieNormalizada(df)


def test_t1_sin_referencia_factor_h_es_1() -> None:
    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "INPC")
    f_k = _canasta_t1().df["encadenamiento"].astype(float)
    pond = _canasta_t1().df["ponderador"].astype(float)
    serie_div = _serie_t1().df.divide(f_k, axis=0)
    esperado = (serie_div[_traslape_t1] * pond).sum() / pond.sum()
    valor = r.df.at[(_traslape_t1, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(esperado)


def test_t1_con_referencia_ancla_traslape() -> None:
    ref = 109.172
    r = LaspeyresEncadenadoT1({"INPC": ref}).calcular(_canasta_t1(), _serie_t1(), "INPC")
    valor = r.df.at[(_traslape_t1, "INPC"), "indice_replicado"]
    assert valor == pytest.approx(ref)


def test_t1_manifiesto() -> None:
    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "INPC")
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresEncadenadoT1"
    assert m.version == 2013


def test_t1_rechaza_canasta_no_2013() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT1().calcular(_canasta_t2(), _serie_t2(), "INPC")


def test_t1_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresEncadenadoT1().calcular(_canasta_t1(), _serie_t1(), "no_existe")


# ---------- recorte de fechas ----------


def test_periodos_fuera_de_rango_2024_se_recortan() -> None:
    # Serie con periodos antes de 2Q Jul 2024 (inicio del rango válido de v2024)
    pre_traslape = PeriodoQuincenal(2024, 1, 1)
    periodos_con_extra = [pre_traslape, _traslape_t2, _post_t2]
    df = pd.DataFrame(
        {
            "arroz": [140.0, 150.0, 151.5],
            "frijol": [130.0, 140.0, 144.2],
            "leche": [150.0, 160.0, 168.0],
            "huevo": [120.0, 130.0, 132.6],
        },
        index=periodos_con_extra,
    ).T
    serie_extra = SerieNormalizada(df)

    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), serie_extra, "INPC")

    periodos_resultado = r.df.index.get_level_values("periodo").tolist()
    assert pre_traslape not in periodos_resultado
    assert _traslape_t2 in periodos_resultado
    assert _post_t2 in periodos_resultado


def test_periodos_fuera_de_rango_2013_se_recortan() -> None:
    # Serie con periodos antes de 2Q Mar 2013 (inicio del rango válido de v2013)
    pre_traslape = PeriodoQuincenal(2013, 1, 1)
    periodos_con_extra = [pre_traslape, _traslape_t1, _post_t1]
    df = pd.DataFrame(
        {
            "arroz": [110.0, 120.0, 123.0],
            "frijol": [70.0, 80.0, 82.0],
            "leche": [100.0, 110.0, 113.0],
            "huevo": [80.0, 90.0, 91.5],
        },
        index=periodos_con_extra,
    ).T
    serie_extra = SerieNormalizada(df)

    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), serie_extra, "INPC")

    periodos_resultado = r.df.index.get_level_values("periodo").tolist()
    assert pre_traslape not in periodos_resultado
    assert _traslape_t1 in periodos_resultado
    assert _post_t1 in periodos_resultado


# ---------- faltantes / relleno, path INPC ----------


def test_nan_parcial_t2_produce_estado_rellenado() -> None:
    # arroz sin dato en _post_t2 — otros genéricos sí tienen dato
    df = pd.DataFrame(
        {
            "arroz": [150.0, None],
            "frijol": [140.0, 144.2],
            "leche": [160.0, 168.0],
            "huevo": [130.0, 132.6],
        },
        index=[_traslape_t2, _post_t2],
    ).T
    serie = SerieNormalizada(df)

    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), serie, "INPC")

    largo = r.resultado.largo
    estados = dict(zip(largo.index.get_level_values("periodo"), largo["estado_calculo"]))
    assert estados[_post_t2] == "rellenado"
    assert estados[_traslape_t2] == "ok"


def test_sin_nan_encadenado_no_produce_estado_rellenado() -> None:
    r = LaspeyresEncadenadoT2().calcular(_canasta_t2(), _serie_t2(), "INPC")
    assert "rellenado" not in r.resultado.largo["estado_calculo"].values


# ---------- categoría, múltiples grupos reales ----------


def test_t1_valores_categoria_multiples_grupos_sin_referencia_correctos() -> None:
    # dos categorías reales: "granos" = arroz+frijol, "animal" = leche+huevo
    # sin referencia -> factor_h=1.0 por defecto, resultado = i_tramo directo
    canasta = _canasta_t1(cog=["granos", "granos", "animal", "animal"])
    r = LaspeyresEncadenadoT1().calcular(canasta, _serie_t1(), "COG")
    largo = r.resultado.largo

    granos_esperado = (10 * (123.0 / 1.2) + 20 * (82.0 / 0.8)) / 30
    animal_esperado = (30 * (113.0 / 1.1) + 40 * (91.5 / 0.9)) / 70
    assert largo.loc[cast(Any, (_post_t1, "granos")), "indice_replicado"] == pytest.approx(
        granos_esperado
    )
    assert largo.loc[cast(Any, (_post_t1, "animal")), "indice_replicado"] == pytest.approx(
        animal_esperado
    )


def test_t2_valores_categoria_multiples_grupos_sin_referencia_correctos() -> None:
    canasta = _canasta_t2(cog=["granos", "granos", "animal", "animal"])
    r = LaspeyresEncadenadoT2().calcular(canasta, _serie_t2(), "COG")
    largo = r.resultado.largo

    factor_h_granos = (10 * 1.5 + 20 * 1.4) / 30
    i_tramo_granos_post = (10 * (151.5 / 1.5) + 20 * (144.2 / 1.4)) / 30
    granos_esperado = i_tramo_granos_post * factor_h_granos

    factor_h_animal = (30 * 1.6 + 40 * 1.3) / 70
    i_tramo_animal_post = (30 * (168.0 / 1.6) + 40 * (132.6 / 1.3)) / 70
    animal_esperado = i_tramo_animal_post * factor_h_animal

    assert largo.loc[cast(Any, (_post_t2, "granos")), "indice_replicado"] == pytest.approx(
        granos_esperado
    )
    assert largo.loc[cast(Any, (_post_t2, "animal")), "indice_replicado"] == pytest.approx(
        animal_esperado
    )


def test_t1_valores_categoria_con_referencia_parcial_ancla_solo_ese_grupo() -> None:
    # referencia solo para "granos" -> factor_h[granos]=ref/i_tramo[traslape];
    # "animal" sin referencia queda en factor_h=1.0 (default T1)
    canasta = _canasta_t1(cog=["granos", "granos", "animal", "animal"])
    ref_granos = 105.0
    r = LaspeyresEncadenadoT1({"granos": ref_granos}).calcular(canasta, _serie_t1(), "COG")
    largo = r.resultado.largo

    valor_granos = largo.loc[cast(Any, (_traslape_t1, "granos")), "indice_replicado"]
    assert valor_granos == pytest.approx(ref_granos)

    # animal: i_tramo(traslape) = (30*(110/1.1) + 40*(90/0.9))/70 = 100 exacto, factor_h=1.0
    animal_traslape_esperado = (30 * (110.0 / 1.1) + 40 * (90.0 / 0.9)) / 70
    valor_animal = largo.loc[cast(Any, (_traslape_t1, "animal")), "indice_replicado"]
    assert valor_animal == pytest.approx(animal_traslape_esperado)


# ---------- faltantes / relleno, path categoría ----------


def test_nan_parcial_categoria_produce_estado_rellenado_y_reporte() -> None:
    # arroz sin dato en el periodo post, dentro de la categoría "granos"
    df = pd.DataFrame(
        {
            "arroz": [120.0, None],
            "frijol": [80.0, 82.0],
            "leche": [110.0, 113.0],
            "huevo": [90.0, 91.5],
        },
        index=[_traslape_t1, _post_t1],
    ).T
    serie = SerieNormalizada(df)
    canasta = _canasta_t1(cog=["granos", "granos", "animal", "animal"])

    r = LaspeyresEncadenadoT1().calcular(canasta, serie, "COG")
    largo = r.resultado.largo

    assert largo.loc[cast(Any, (_post_t1, "granos")), "estado_calculo"] == "rellenado"
    assert largo.loc[cast(Any, (_post_t1, "animal")), "estado_calculo"] == "ok"

    reporte_granos_post = r.reporte.loc[cast(Any, (_post_t1, "granos"))]
    assert reporte_granos_post["genericos_esperados"] == 2
    assert reporte_granos_post["genericos_con_indice"] == 2
    assert reporte_granos_post["cobertura_genericos_pct"] == pytest.approx(100.0)


def test_nan_total_categoria_produce_sin_datos() -> None:
    # arroz sin dato en NINGÚN periodo dentro de "granos" — frijol sigue con dato
    df = pd.DataFrame(
        {
            "arroz": [None, None],
            "frijol": [80.0, 82.0],
            "leche": [110.0, 113.0],
            "huevo": [90.0, 91.5],
        },
        index=[_traslape_t1, _post_t1],
    ).T
    serie = SerieNormalizada(df)
    canasta = _canasta_t1(cog=["granos", "granos", "animal", "animal"])

    r = LaspeyresEncadenadoT1().calcular(canasta, serie, "COG")
    largo = r.resultado.largo

    assert largo.loc[cast(Any, (_post_t1, "granos")), "estado_calculo"] == "sin_datos"
    assert pd.isna(largo.loc[cast(Any, (_post_t1, "granos")), "indice_replicado"])
    assert largo.loc[cast(Any, (_post_t1, "animal")), "estado_calculo"] == "ok"

    reporte_granos_post = r.reporte.loc[cast(Any, (_post_t1, "granos"))]
    assert reporte_granos_post["genericos_esperados"] == 2
    assert reporte_granos_post["genericos_sin_indice"] == 1
    assert reporte_granos_post["cobertura_genericos_pct"] == pytest.approx(50.0)


# ---------- traslape ausente en la serie ----------
#
# Política permisiva: el traslape solo se valida si el cálculo efectivamente
# lo necesita (hay referencia_empalme para ese índice). Sin referencia,
# factor_h=1.0 nunca toca el traslape — su ausencia no debe tirar el cálculo
# de los periodos que sí tienen dato.


def test_t1_traslape_ausente_sin_referencia_no_lanza_error() -> None:
    otro_periodo = PeriodoQuincenal(2013, 4, 2)
    df = pd.DataFrame(
        {
            "arroz": [123.0, 124.0],
            "frijol": [82.0, 83.0],
            "leche": [113.0, 114.0],
            "huevo": [91.5, 92.0],
        },
        index=[_post_t1, otro_periodo],
    ).T
    serie = SerieNormalizada(df)
    r = LaspeyresEncadenadoT1().calcular(_canasta_t1(), serie, "INPC")
    assert (_traslape_t1, "INPC") not in r.df.index
    assert r.resultado.largo.at[(_post_t1, "INPC"), "estado_calculo"] == "ok"


def test_t1_traslape_ausente_con_referencia_lanza_error_calculo() -> None:
    # con referencia_empalme, factor_h SÍ necesita el traslape — su ausencia
    # debe rechazarse
    otro_periodo = PeriodoQuincenal(2013, 4, 2)
    df = pd.DataFrame(
        {
            "arroz": [123.0, 124.0],
            "frijol": [82.0, 83.0],
            "leche": [113.0, 114.0],
            "huevo": [91.5, 92.0],
        },
        index=[_post_t1, otro_periodo],
    ).T
    serie = SerieNormalizada(df)
    with pytest.raises(ErrorCalculo):
        LaspeyresEncadenadoT1({"INPC": 150.0}).calcular(_canasta_t1(), serie, "INPC")


# ---------- guardia de división por cero/no finito ----------
#
# T1 categoría ya porta la guardia (grupos_invalidos, mismo patrón que
# LaspeyresDirecto, ver test_calculo_laspeyres_directo.py) — cerrado sesión
# 2026-08-02 (crash real reproducido, RuntimeWarning: divide by zero seguido
# de ValueError; causa raíz: .groupby().sum() de categoría 100% NaN da 0.0
# silencioso, no NaN — mismo patrón recurrente que el bug ya cerrado en
# Directo). Guardia lo atrapa: i_tramo_mat[traslape]==0 → ErrorCalculo claro.
#
# T1 escalar NO tiene el mismo problema — repro real (misma sesión) da un
# resultado DISTINTO: no crashea, no lanza nada, corrompe en silencio (ambos
# periodos devuelven el mismo valor). Causa raíz distinta: cuando TODOS los
# genéricos del INPC faltan justo en el traslape pero tienen dato en periodos
# posteriores, `_rellenar_dato_serie_faltante` (bfill) rellena el traslape
# tomando el dato FUTURO — el denominador queda finito y ≠0 (no lo atrapa la
# guardia de Directo, que solo chequea cero/no-finito), solo semánticamente
# prestado. Confirmado NO alcanzable en producción contra serie real de 283
# genéricos (2010): 0 NaN en el traslape real (2Q Mar 2013) — un apagón total
# de publicación INEGI en una quincena específica no ocurre. Queda
# documentado como hallazgo de bajo riesgo, no como bug a perseguir.


def test_t1_categoria_denominador_invalido_en_traslape_lanza_error_calculo() -> None:
    # categoría "fantasma" sin dato en ningún periodo, con referencia asignada
    df = pd.DataFrame(
        {
            "arroz": [None, None],
            "frijol": [None, None],
            "leche": [110.0, 113.0],
            "huevo": [90.0, 91.5],
        },
        index=[_traslape_t1, _post_t1],
    ).T
    serie = SerieNormalizada(df)
    canasta = _canasta_t1(cog=["fantasma", "fantasma", "real", "real"])
    with pytest.raises(ErrorCalculo):
        LaspeyresEncadenadoT1({"fantasma": 150.0}).calcular(canasta, serie, "COG")


# ---------- dato real ----------

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "inputs"
_DATA_DIR_CANASTA = Path(__file__).parent.parent.parent.parent.parent / "data" / "tests" / "p_pdf"
_CANASTA_2013_REAL = _DATA_DIR_CANASTA / "ponderadores_2013.csv"
_SERIE_2013_REAL = _DATA_DIR / "series2010_horizontal_metadata.CSV"  # serie continua 2010-2013


@pytest.mark.requires_data
def test_t1_categoria_real_ccif_division_valores_no_triviales() -> None:
    # sanity check contra dato real: LaspeyresEncadenadoT1 sobre "CCIF DIVISION"
    # de la canasta 2013 real produce valores finitos, sin referencia de empalme
    # (factor_h=1.0 por defecto) — no verifica magnitud contra INEGI, solo que
    # el mecanismo de categoría no se rompe con datos de producción reales
    canasta = rep.cargar_canasta(str(_CANASTA_2013_REAL), 2013)
    serie = rep.cargar_serie(str(_SERIE_2013_REAL), 2010)
    r = LaspeyresEncadenadoT1().calcular(canasta, serie, "CCIF DIVISION")
    largo = r.resultado.largo
    assert not largo.empty
    assert largo["indice_replicado"].notna().any()
