"""
Tests para el cálculo de subíndices por clasificación (v1.1.0).

Cubre:
- Loop por categorías con re-normalización de ponderadores
- validar_inpc.py con tipo fuera de TIPOS_CON_VALIDACION (sin columnas INEGI)
- Cobertura calculada por subgrupo (ponderadores originales, no renormalizados)
- como_tabla(True) con múltiples índices
- validar_inpc.py con tipo en TIPOS_CON_VALIDACION y en COLUMNAS_CLASIFICACION (inflacion componente)
"""

import uuid

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.validar_inpc import validar

ID_CORRIDA = str(uuid.uuid4())

periodos = [PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)]

"""
Canasta con dos categorías COG:
  "alimentos"  → arroz (10) + frijol (20)   → suman 30
  "servicios"  → leche (30) + huevo  (40)   → suman 70
Los ponderadores totales suman 100 (invariante de CanastaCanonica).
"""
df_canasta = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
        "COG": ["alimentos", "alimentos", "servicios", "servicios"],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)
canasta = CanastaCanonica(df_canasta, 2018)

"""
Serie:
generico | 2Q Jul 2018 | 1Q Ago 2018
arroz    | 100.0       | 101.0
frijol   | 100.0       | 102.0
leche    | 100.0       | 103.0
huevo    | 100.0       | 104.0
"""
df_serie = pd.DataFrame(
    {
        "arroz": [100.0, 101.0],
        "frijol": [100.0, 102.0],
        "leche": [100.0, 103.0],
        "huevo": [100.0, 104.0],
    },
    index=periodos,
).T
mapeo = {"arroz": "Arroz", "frijol": "Frijol", "leche": "Leche", "huevo": "Huevo"}
serie = SerieNormalizada(df_serie, mapeo)


def _get_grupo(resultado: ResultadoCalculo, categoria: str) -> ResultadoCalculo:
    mask = resultado.df.index.get_level_values("indice") == categoria
    return ResultadoCalculo(resultado.df[mask], ID_CORRIDA)


resultado_combinado = LaspeyresDirecto().calcular(canasta, serie, ID_CORRIDA, "COG")
resultado_alimentos = _get_grupo(resultado_combinado, "alimentos")
resultado_servicios = _get_grupo(resultado_combinado, "servicios")


# ---------------------------------------------------------------------------
# Cálculo con re-normalización
# ---------------------------------------------------------------------------


def test_subindice_periodo_base_es_100():
    """En el período base, ambos subíndices arrancan en 100."""
    p_base = PeriodoQuincenal(2018, 7, 2)
    assert resultado_alimentos.df.loc[(p_base, "alimentos"), "indice_replicado"] == pytest.approx(  # type: ignore[index]
        100.0
    )
    assert resultado_servicios.df.loc[(p_base, "servicios"), "indice_replicado"] == pytest.approx(  # type: ignore[index]
        100.0
    )


def test_subindice_calculo_laspeyres_por_subgrupo():
    """
    Verifica que Laspeyres por subgrupo usa los ponderadores originales (suma < 100).

    alimentos (arroz=10, frijol=20, sum=30):
        1Q Ago 2018 = (10 × 101 + 20 × 102) / 30 = 305/3

    servicios (leche=30, huevo=40, sum=70):
        1Q Ago 2018 = (30 × 103 + 40 × 104) / 70 = 725/7
    """
    p2 = PeriodoQuincenal(2018, 8, 1)
    assert resultado_alimentos.df.loc[(p2, "alimentos"), "indice_replicado"] == pytest.approx(  # type: ignore[index]
        305 / 3
    )
    assert resultado_servicios.df.loc[(p2, "servicios"), "indice_replicado"] == pytest.approx(  # type: ignore[index]
        725 / 7
    )


def test_subindice_resultado_combinado_multiindex():
    """El resultado combinado tiene MultiIndex (periodo, indice) con ambas categorías."""
    assert isinstance(resultado_combinado.df.index, pd.MultiIndex)
    assert resultado_combinado.df.index.names == ["periodo", "indice"]
    assert set(resultado_combinado.df.index.get_level_values("indice").unique()) == {
        "alimentos",
        "servicios",
    }
    assert len(resultado_combinado.df) == 4  # 2 categorías × 2 periodos


def test_subindice_tipo_en_resultado_es_nombre_columna():
    """La columna 'tipo' del resultado contiene el nombre de la columna de clasificación."""
    assert (resultado_combinado.df["tipo"] == "COG").all()


# ---------------------------------------------------------------------------
# validar_inpc.py sin columnas INEGI
# ---------------------------------------------------------------------------


def test_validar_subindice_sin_columnas_inegi():
    """
    tipo='COG' no está en TIPOS_CON_VALIDACION → el reporte no incluye
    indice_inegi, error_absoluto, error_relativo ni estado_validacion.
    """
    _, reporte, _ = validar(resultado_combinado, {}, canasta, serie, ID_CORRIDA)

    for col in (
        "indice_inegi",
        "error_absoluto",
        "error_relativo",
        "estado_validacion",
    ):
        assert col not in reporte.df.columns


def test_validar_subindice_resumen_sin_estado_validacion_global():
    """
    tipo='COG' → el resumen no incluye estado_validacion_global,
    error_absoluto_max ni error_relativo_max.
    """
    resumen, _, _ = validar(resultado_combinado, {}, canasta, serie, ID_CORRIDA)

    assert "estado_validacion_global" not in resumen.df.columns
    assert "error_absoluto_max" not in resumen.df.columns
    assert "error_relativo_max" not in resumen.df.columns


def test_validar_subindice_estado_corrida_ok():
    """Sin faltantes, estado_corrida='ok'. total_periodos_esperados = 2 cats × 2 periodos = 4."""
    resumen, reporte, diagnostico = validar(resultado_combinado, {}, canasta, serie, ID_CORRIDA)

    assert resumen.df.loc[ID_CORRIDA, "estado_corrida"] == "ok"
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_con_null"] == 0
    assert resumen.df.loc[ID_CORRIDA, "total_periodos_esperados"] == 4
    assert (reporte.df["estado_calculo"] == "ok").all()
    assert diagnostico.df.empty


# ---------------------------------------------------------------------------
# Cobertura por subgrupo
# ---------------------------------------------------------------------------


def test_validar_subindice_cobertura_por_grupo():
    """
    La cobertura usa los ponderadores ORIGINALES (no renormalizados) del subgrupo.
    'alimentos': total_genericos=2, ponderador_total_esperado=30.0
    'servicios': total_genericos=2, ponderador_total_esperado=70.0
    """
    _, reporte, _ = validar(resultado_combinado, {}, canasta, serie, ID_CORRIDA)

    p_base = PeriodoQuincenal(2018, 7, 2)

    fila_al = reporte.df.loc[(p_base, "alimentos")]  # type: ignore[index]
    assert fila_al["total_genericos_esperados"] == 2
    assert fila_al["ponderador_total_esperado"] == pytest.approx(30.0)
    assert fila_al["cobertura_genericos_pct"] == pytest.approx(100.0)
    assert fila_al["ponderador_total_cubierto"] == pytest.approx(30.0)

    fila_sv = reporte.df.loc[(p_base, "servicios")]  # type: ignore[index]
    assert fila_sv["total_genericos_esperados"] == 2
    assert fila_sv["ponderador_total_esperado"] == pytest.approx(70.0)
    assert fila_sv["cobertura_genericos_pct"] == pytest.approx(100.0)
    assert fila_sv["ponderador_total_cubierto"] == pytest.approx(70.0)


def test_validar_subindice_cobertura_parcial():
    """
    Con un NaN en 'arroz' en el periodo 2, la cobertura de 'alimentos' baja:
    - 1 de 2 genéricos disponible
    - ponderador_cubierto = 20.0 (solo frijol), cobertura_pct = 50.0
    'servicios' no se ve afectado.
    """
    serie_con_nan = df_serie.copy()
    serie_con_nan.loc["arroz", PeriodoQuincenal(2018, 8, 1)] = float("nan")

    serie_nan = SerieNormalizada(serie_con_nan, mapeo)

    res_al_nan = _calcular_grupo_con_serie("alimentos", serie_con_nan)
    res_sv_nan = _calcular_grupo_con_serie("servicios", serie_con_nan)
    resultado_nan = ResultadoCalculo(pd.concat([res_al_nan.df, res_sv_nan.df]), ID_CORRIDA)

    _, reporte, _ = validar(resultado_nan, {}, canasta, serie_nan, ID_CORRIDA)

    p2 = PeriodoQuincenal(2018, 8, 1)
    fila_al_p2 = reporte.df.loc[(p2, "alimentos")]  # type: ignore[index]
    assert fila_al_p2["total_genericos_con_indice"] == 1
    assert fila_al_p2["cobertura_genericos_pct"] == pytest.approx(50.0)
    assert fila_al_p2["ponderador_total_cubierto"] == pytest.approx(20.0)

    fila_sv_p2 = reporte.df.loc[(p2, "servicios")]  # type: ignore[index]
    assert fila_sv_p2["total_genericos_con_indice"] == 2
    assert fila_sv_p2["cobertura_genericos_pct"] == pytest.approx(100.0)


def _calcular_grupo_con_serie(categoria: str, serie_df: pd.DataFrame) -> ResultadoCalculo:
    serie_custom = SerieNormalizada(serie_df, mapeo)
    resultado = LaspeyresDirecto().calcular(canasta, serie_custom, ID_CORRIDA, "COG")
    return _get_grupo(resultado, categoria)


# ---------------------------------------------------------------------------
# como_tabla(True) con múltiples índices
# ---------------------------------------------------------------------------


def test_resultado_como_tabla_ancho_multiples_indices():
    """
    ResultadoCalculo.como_tabla(True) con dos índices produce un DataFrame
    con los índices como filas y los periodos como columnas.
    """
    tabla = resultado_combinado.como_tabla(ancho=True)

    assert set(tabla.index) == {"alimentos", "servicios"}
    assert set(tabla.columns) == set(periodos)
    assert tabla.loc["alimentos", PeriodoQuincenal(2018, 7, 2)] == pytest.approx(100.0)  # type: ignore[index]
    assert tabla.loc["servicios", PeriodoQuincenal(2018, 7, 2)] == pytest.approx(100.0)  # type: ignore[index]


def test_reporte_como_tabla_ancho_multiples_indices():
    """
    ReporteDetalladoValidacion.como_tabla(True) sin validación INEGI produce
    filas {indice}_<metrica> y columnas = periodos.
    """
    _, reporte, _ = validar(resultado_combinado, {}, canasta, serie, ID_CORRIDA)

    tabla = reporte.como_tabla(ancho=True)

    assert set(tabla.columns) == set(periodos)
    assert "alimentos_calculado" in tabla.index
    assert "alimentos_estado_calculo" in tabla.index
    assert "alimentos_motivo_error" in tabla.index
    assert "alimentos_cobertura_pct" in tabla.index
    assert "alimentos_ponderador_cubierto" in tabla.index
    assert "servicios_calculado" in tabla.index
    assert tabla.loc["alimentos_calculado", PeriodoQuincenal(2018, 7, 2)] == pytest.approx(100.0)  # type: ignore[index]
    assert tabla.loc["servicios_calculado", PeriodoQuincenal(2018, 7, 2)] == pytest.approx(100.0)  # type: ignore[index]
    assert tabla.loc["alimentos_calculado", PeriodoQuincenal(2018, 8, 1)] == pytest.approx(  # type: ignore[index]
        305 / 3
    )
    assert tabla.loc["servicios_calculado", PeriodoQuincenal(2018, 8, 1)] == pytest.approx(  # type: ignore[index]
        725 / 7
    )


# ---------------------------------------------------------------------------
# tipo in TIPOS_CON_VALIDACION y in COLUMNAS_CLASIFICACION (inflacion componente)
# ---------------------------------------------------------------------------

"""
Canasta con columna 'inflacion componente':
  "subyacente"    → arroz (10) + frijol (20)  → ponderador original 30
  "no subyacente" → leche (30) + huevo  (40)  → ponderador original 70
"""
_df_canasta_ic = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": [None, None, None, None],
        "inflacion componente": [
            "subyacente",
            "subyacente",
            "no subyacente",
            "no subyacente",
        ],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)
_canasta_ic = CanastaCanonica(_df_canasta_ic, 2018)


_resultado_ic = LaspeyresDirecto().calcular(_canasta_ic, serie, ID_CORRIDA, "inflacion componente")

# subyacente   p2: (100/3 × 101 + 200/3 × 102) / 100 = 305/3
# no subyacente p2: (300/7 × 103 + 400/7 × 104) / 100 = 725/7
_inegi_ic: dict[str, dict[PeriodoQuincenal, float | None]] = {
    "subyacente": {
        PeriodoQuincenal(2018, 7, 2): 100.0,
        PeriodoQuincenal(2018, 8, 1): 305 / 3,
    },
    "no subyacente": {
        PeriodoQuincenal(2018, 7, 2): 100.0,
        PeriodoQuincenal(2018, 8, 1): 725 / 7,
    },
}


def test_subindice_con_validacion_inegi_incluye_columnas():
    """
    tipo='inflacion componente' está en TIPOS_CON_VALIDACION →
    el reporte incluye indice_inegi, error_absoluto, error_relativo, estado_validacion.
    """
    _, reporte, _ = validar(_resultado_ic, _inegi_ic, _canasta_ic, serie, ID_CORRIDA)

    for col in (
        "indice_inegi",
        "error_absoluto",
        "error_relativo",
        "estado_validacion",
    ):
        assert col in reporte.df.columns


def test_subindice_con_validacion_inegi_estado_ok():
    """
    Con datos INEGI exactos, todos los periodos tienen estado_validacion='ok'.
    """
    _, reporte, _ = validar(_resultado_ic, _inegi_ic, _canasta_ic, serie, ID_CORRIDA)

    assert (reporte.df["estado_validacion"] == "ok").all()
    assert reporte.df["error_absoluto"].max() == pytest.approx(0.0)


def test_subindice_con_validacion_inegi_resumen_incluye_estado_global():
    """
    tipo='inflacion componente' → el resumen incluye estado_validacion_global='ok'.
    """
    resumen, _, _ = validar(_resultado_ic, _inegi_ic, _canasta_ic, serie, ID_CORRIDA)

    assert "estado_validacion_global" in resumen.df.columns
    assert resumen.df.loc[ID_CORRIDA, "estado_validacion_global"] == "ok"


def test_subindice_con_validacion_inegi_lookup_independiente_por_indice():
    """
    El lookup de INEGI se hace por nombre de índice: 'subyacente' no usa
    los datos de 'no subyacente' y viceversa. Con solo un subíndice en inegi,
    el otro queda 'no_disponible'.
    """
    inegi_parcial: dict[str, dict[PeriodoQuincenal, float | None]] = {
        "subyacente": {
            PeriodoQuincenal(2018, 7, 2): 100.0,
            PeriodoQuincenal(2018, 8, 1): 305 / 3,
        },
        # "no subyacente" ausente → no_disponible
    }

    _, reporte, _ = validar(_resultado_ic, inegi_parcial, _canasta_ic, serie, ID_CORRIDA)

    p1, p2 = PeriodoQuincenal(2018, 7, 2), PeriodoQuincenal(2018, 8, 1)
    assert reporte.df.loc[(p1, "subyacente"), "estado_validacion"] == "ok"  # type: ignore[index]
    assert reporte.df.loc[(p2, "subyacente"), "estado_validacion"] == "ok"  # type: ignore[index]
    assert reporte.df.loc[(p1, "no subyacente"), "estado_validacion"] == "no_disponible"  # type: ignore[index]
    assert reporte.df.loc[(p2, "no subyacente"), "estado_validacion"] == "no_disponible"  # type: ignore[index]
