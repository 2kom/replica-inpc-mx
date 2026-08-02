from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

import replica_inpc as rep
from replica_inpc.dominio.calculo.laspeyres_directo import LaspeyresDirecto
from replica_inpc.dominio.errores import ErrorCalculo, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

_periodos = [
    PeriodoQuincenal(2018, 7, 2),
    PeriodoQuincenal(2018, 8, 1),
    PeriodoQuincenal(2018, 8, 2),
    PeriodoQuincenal(2018, 9, 1),
]


def _canasta(cog: list[str] | None = None) -> CanastaCanonica:
    datos: dict[str, list[Any]] = {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
    }
    if cog is not None:
        datos["COG"] = cog
    df = pd.DataFrame(datos, index=["arroz", "frijol", "leche", "huevo"])
    return CanastaCanonica(df, 2018)


def _serie() -> SerieNormalizada:
    df = pd.DataFrame(
        {
            "arroz": [100, 101, 102, 103],
            "frijol": [100, 102, 104, 106],
            "leche": [100, 103, 106, 109],
            "huevo": [100, 104, 108, 112],
        },
        index=_periodos,
    ).T
    return SerieNormalizada(df)


# ---------- básicos ----------


def test_calcular_retorna_resultado_indice() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "INPC")
    assert isinstance(r, ResultadoIndice)


def test_valores_inpc_correctos() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "INPC")
    valores = r.df["indice_replicado"].tolist()
    assert valores == pytest.approx([100.0, 103.0, 106.0, 109.0])


def test_multiindex_periodo_indice() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "INPC")
    assert list(r.df.index.names) == ["periodo", "indice"]
    assert r.df.index.get_level_values("periodo").tolist() == _periodos
    assert (r.df.index.get_level_values("indice") == "INPC").all()


def test_manifiesto_calculador_y_version() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "INPC")
    assert len(r.manifiesto) == 1
    m = r.manifiesto[0]
    assert m.calculador == "LaspeyresDirecto"
    assert m.version == 2018
    assert m.tipo == "INPC"
    assert m.ruta_canasta is None
    assert m.ruta_series is None


def test_tipo_invalido_lanza_invariante_violado() -> None:
    with pytest.raises(InvarianteViolado):
        LaspeyresDirecto().calcular(_canasta(), _serie(), "tipo_inventado")


# ---------- categoría, múltiples grupos reales (calculo.md regla 6) ----------


def test_valores_categoria_multiples_grupos_correctos() -> None:
    # dos categorías reales, no edge-case: "granos" = arroz+frijol, "animal" = leche+huevo
    canasta = _canasta(cog=["granos", "granos", "animal", "animal"])
    r = LaspeyresDirecto().calcular(canasta, _serie(), "COG")
    largo = r.resultado.largo

    # a mano, Laspeyres simple sin rebase: Σ(w·I)/Σw por grupo
    p_1q_ago = _periodos[1]
    granos_esperado = (10 * 101 + 20 * 102) / 30
    animal_esperado = (30 * 103 + 40 * 104) / 70
    assert largo.loc[cast(Any, (p_1q_ago, "granos")), "indice_replicado"] == pytest.approx(
        granos_esperado
    )
    assert largo.loc[cast(Any, (p_1q_ago, "animal")), "indice_replicado"] == pytest.approx(
        animal_esperado
    )


# ---------- referencia de empalme (rebase) ----------


def test_referencia_empalme_rebasa_serie_completa() -> None:
    # traslape de v2018 = 2Q Jul 2018 = _periodos[0], donde INPC crudo vale 100
    r = LaspeyresDirecto(referencia_empalme_por_indice={"INPC": 200.0}).calcular(
        _canasta(), _serie(), "INPC"
    )
    # factor_rebase = 200/100 = 2 — toda la serie se reescala por ese factor
    assert r.df["indice_replicado"].tolist() == pytest.approx([200.0, 206.0, 212.0, 218.0])
    # indice_incidencia preserva la escala PRE-rebase (r_c, antes de aplicar R_c)
    assert list(r._completo["indice_incidencia"]) == pytest.approx([100.0, 103.0, 106.0, 109.0])


@pytest.mark.parametrize(
    "valor_grupo_invalido",
    [
        pytest.param(float("nan"), id="sin_dato_en_ningun_periodo"),
        pytest.param(0.0, id="indice_crudo_cero"),
        pytest.param(float("inf"), id="indice_crudo_no_finito"),
    ],
)
def test_referencia_empalme_denominador_invalido_lanza_error_calculo(
    valor_grupo_invalido: float,
) -> None:
    # el crudo del grupo en el traslape queda inválido (NaN sin rellenar → 0 al
    # sumar, o dato presente pero 0/inf) — dividir la referencia entre eso debe
    # fallar claro, no corromper la serie en silencio con inf (calculo.md regla 3)
    periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]
    df = pd.DataFrame(
        {
            "arroz": [valor_grupo_invalido, valor_grupo_invalido],
            "frijol": [valor_grupo_invalido, valor_grupo_invalido],
            "leche": [100.0, 103.0],
            "huevo": [100.0, 104.0],
        },
        index=periodos,
    ).T
    serie = SerieNormalizada(df)
    canasta = _canasta(cog=["invalido", "invalido", "real", "real"])
    calc = LaspeyresDirecto(referencia_empalme_por_indice={"invalido": 150.0})
    with pytest.raises(ErrorCalculo):
        calc.calcular(canasta, serie, "COG")


@pytest.mark.parametrize("referencia_invalida", [float("nan"), float("inf"), float("-inf")])
def test_referencia_empalme_no_finita_lanza_error_calculo(referencia_invalida: float) -> None:
    # referencia_empalme_por_indice viene de _referencias_normalizadas (calcular_historia.py),
    # que ya filtra NaN — esta guardia protege la API pública de LaspeyresDirecto de todas
    # formas, por si se llama directo con datos no saneados
    r = LaspeyresDirecto(referencia_empalme_por_indice={"INPC": referencia_invalida})
    with pytest.raises(ErrorCalculo):
        r.calcular(_canasta(), _serie(), "INPC")


# ---------- recorte de fechas ----------


def test_periodos_fuera_de_rango_2018_se_recortan() -> None:
    # Serie con periodos antes de 2Q Jul 2018 (inicio del rango válido de v2018)
    periodos_con_extra = [
        PeriodoQuincenal(2018, 1, 1),
        PeriodoQuincenal(2018, 7, 1),
        PeriodoQuincenal(2018, 7, 2),  # inicio válido
        PeriodoQuincenal(2018, 8, 1),
    ]
    df = pd.DataFrame(
        {
            "arroz": [99, 99, 100, 101],
            "frijol": [99, 99, 100, 102],
            "leche": [99, 99, 100, 103],
            "huevo": [99, 99, 100, 104],
        },
        index=periodos_con_extra,
    ).T
    serie_extra = SerieNormalizada(df)

    r = LaspeyresDirecto().calcular(_canasta(), serie_extra, "INPC")

    periodos_resultado = r.df.index.get_level_values("periodo").tolist()
    assert PeriodoQuincenal(2018, 1, 1) not in periodos_resultado
    assert PeriodoQuincenal(2018, 7, 1) not in periodos_resultado
    assert PeriodoQuincenal(2018, 7, 2) in periodos_resultado
    assert PeriodoQuincenal(2018, 8, 1) in periodos_resultado


# ---------- faltantes / relleno ----------


def test_nan_parcial_produce_estado_rellenado() -> None:
    # arroz sin dato en 1Q Ago 2018 — otros genéricos sí tienen dato
    periodos = [
        PeriodoQuincenal(2018, 7, 2),
        PeriodoQuincenal(2018, 8, 1),
        PeriodoQuincenal(2018, 8, 2),
    ]
    df = pd.DataFrame(
        {
            "arroz": [100.0, float("nan"), 102.0],
            "frijol": [100.0, 102.0, 104.0],
            "leche": [100.0, 103.0, 106.0],
            "huevo": [100.0, 104.0, 108.0],
        },
        index=periodos,
    ).T
    serie = SerieNormalizada(df)

    r = LaspeyresDirecto().calcular(_canasta(), serie, "INPC")

    largo = r.resultado.largo
    estados = dict(zip(largo.index.get_level_values("periodo"), largo["estado_calculo"]))
    assert estados[PeriodoQuincenal(2018, 8, 1)] == "rellenado"
    assert estados[PeriodoQuincenal(2018, 7, 2)] == "ok"
    assert estados[PeriodoQuincenal(2018, 8, 2)] == "ok"
    # arroz en 1Q Ago se rellena con bfill desde 2Q Ago (102.0): (10*102+20*102+30*103+40*104)/100
    p_nan = PeriodoQuincenal(2018, 8, 1)
    assert r.df.loc[cast(Any, (p_nan, "INPC")), "indice_replicado"] == pytest.approx(103.1)
    fila_diag = r.diagnostico[
        (r.diagnostico["generico"] == "arroz") & (r.diagnostico["periodo"] == p_nan)
    ].iloc[0]
    assert "2Q Ago 2018" in fila_diag["detalle"]


def test_nan_total_generico_produce_sin_datos() -> None:
    # arroz con NaN en TODOS los periodos — no hay valor adyacente con qué rellenar
    periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]
    df = pd.DataFrame(
        {
            "arroz": [float("nan"), float("nan")],
            "frijol": [100.0, 102.0],
            "leche": [100.0, 103.0],
            "huevo": [100.0, 104.0],
        },
        index=periodos,
    ).T
    serie = SerieNormalizada(df)

    r = LaspeyresDirecto().calcular(_canasta(), serie, "INPC")

    largo = r.resultado.largo
    # Ningún periodo queda "rellenado" — arroz all-NaN no puede rellenarse
    assert "rellenado" not in largo["estado_calculo"].values
    assert (largo["estado_calculo"] == "sin_datos").all()
    assert largo["indice_replicado"].isna().all()
    assert (largo["motivo_error"] == "faltantes en serie").all()
    assert (r.reporte["genericos_esperados"] == 4).all()
    assert (r.reporte["genericos_sin_indice"] == 1).all()
    assert r.reporte["cobertura_genericos_pct"].tolist() == pytest.approx([75.0, 75.0])
    assert r.reporte["ponderador_cubierto"].tolist() == pytest.approx([90.0, 90.0])
    diag_arroz = r.diagnostico[r.diagnostico["generico"] == "arroz"]
    assert len(diag_arroz) == 2
    assert (diag_arroz["tipo_faltante"] == "indice").all()
    assert set(diag_arroz["periodo"]) == set(periodos)


def test_sin_nan_no_produce_estado_rellenado() -> None:
    r = LaspeyresDirecto().calcular(_canasta(), _serie(), "INPC")
    largo = r.resultado.largo
    assert "rellenado" not in largo["estado_calculo"].values
    assert (largo["estado_calculo"] == "ok").all()


# ---------- dato real (calculo.md regla 8) ----------

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "inputs"
_DATA_DIR_CANASTA = Path(__file__).parent.parent.parent.parent.parent / "data" / "tests" / "p_pdf"
_CANASTA_2018_REAL = _DATA_DIR_CANASTA / "ponderadores_2018.csv"
_SERIE_2018_REAL = _DATA_DIR / "series2018_horizontal_metadata.CSV"


@pytest.mark.requires_data
def test_categoria_real_ccif_division_valores_no_triviales() -> None:
    # sanity check contra dato real: LaspeyresDirecto sobre "CCIF DIVISION" de la
    # canasta 2018 real produce valores finitos para todas las categorías — no
    # verifica magnitud (eso es trabajo de validar_indices contra INEGI), solo que
    # el mecanismo de categoría no se rompe con datos de producción reales
    canasta = rep.cargar_canasta(str(_CANASTA_2018_REAL), 2018)
    serie = rep.cargar_serie(str(_SERIE_2018_REAL), 2018)
    r = LaspeyresDirecto().calcular(canasta, serie, "CCIF DIVISION")
    largo = r.resultado.largo
    assert not largo.empty
    assert largo["indice_replicado"].notna().any()
