import pandas as pd
import pytest

from replica_inpc.aplicacion.casos_uso.ejecutar_corrida import _rellenar_faltantes
from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.modelos.validacion import DiagnosticoFaltantes
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.validar_inpc import validar

p1 = PeriodoQuincenal(2024, 7, 2)
p2 = PeriodoQuincenal(2024, 8, 1)
p3 = PeriodoQuincenal(2024, 8, 2)

_mapeo = {"arroz": "Arroz", "frijol": "Frijol", "leche": "Leche"}


def _serie(valores: dict) -> SerieNormalizada:
    df = pd.DataFrame(valores, index=[p1, p2, p3]).T
    return SerieNormalizada(df, _mapeo)


# --- _rellenar_faltantes ---


def test_sin_nan_devuelve_serie_intacta_e_imputados_vacios():
    serie = _serie(
        {
            "arroz": [100.0, 101.0, 102.0],
            "frijol": [100.0, 102.0, 104.0],
            "leche": [100.0, 103.0, 106.0],
        }
    )
    serie_out, imputados = _rellenar_faltantes(serie)
    assert imputados == {}
    pd.testing.assert_frame_equal(serie_out.df, serie.df)


def test_nan_en_medio_rellena_hacia_adelante():
    serie = _serie(
        {
            "arroz": [float("nan"), 101.0, 102.0],
            "frijol": [100.0, 102.0, 104.0],
            "leche": [100.0, 103.0, 106.0],
        }
    )
    serie_out, imputados = _rellenar_faltantes(serie)
    assert serie_out.df.at["arroz", p1] == pytest.approx(101.0)
    assert ("arroz", p1) in imputados
    assert imputados[("arroz", p1)] == p2


def test_nan_al_final_rellena_hacia_atras():
    serie = _serie(
        {
            "arroz": [100.0, 101.0, float("nan")],
            "frijol": [100.0, 102.0, 104.0],
            "leche": [100.0, 103.0, 106.0],
        }
    )
    serie_out, imputados = _rellenar_faltantes(serie)
    assert serie_out.df.at["arroz", p3] == pytest.approx(101.0)
    assert ("arroz", p3) in imputados
    assert imputados[("arroz", p3)] == p2


def test_nan_completo_no_se_imputa():
    serie = _serie(
        {
            "arroz": [float("nan"), float("nan"), float("nan")],
            "frijol": [100.0, 102.0, 104.0],
            "leche": [100.0, 103.0, 106.0],
        }
    )
    serie_out, imputados = _rellenar_faltantes(serie)
    assert ("arroz", p1) not in imputados
    assert bool(serie_out.df.loc["arroz"].isna().all())


# --- DiagnosticoFaltantes acepta indice_imputado ---


def test_diagnostico_acepta_tipo_indice_imputado():
    df = pd.DataFrame(
        {
            "id_corrida": ["abc"],
            "version": [2024],
            "tipo": ["inpc"],
            "periodo": [p1],
            "generico": ["arroz"],
            "nivel_faltante": ["periodo"],
            "tipo_faltante": ["indice_imputado"],
            "detalle": ["imputado desde 1Q Ago 2024"],
        }
    )
    diag = DiagnosticoFaltantes(df)
    assert diag.df["tipo_faltante"].iloc[0] == "indice_imputado"


def test_diagnostico_rechaza_tipo_invalido():
    df = pd.DataFrame(
        {
            "id_corrida": ["abc"],
            "version": [2024],
            "tipo": ["inpc"],
            "periodo": [p1],
            "generico": ["arroz"],
            "nivel_faltante": ["periodo"],
            "tipo_faltante": ["otro_invalido"],
            "detalle": ["x"],
        }
    )
    with pytest.raises(InvarianteViolado):
        DiagnosticoFaltantes(df)


# --- estado_validacion = diferencia_detectada_imputado ---


def test_diferencia_detectada_imputado_cuando_periodo_imputado_supera_tolerancia():
    df_canasta = pd.DataFrame(
        {"ponderador": ["50.0", "50.0"], "encadenamiento": [None, None]},
        index=["arroz", "frijol"],
    )
    canasta = CanastaCanonica(df_canasta, 2018)

    df_serie = pd.DataFrame({"arroz": [100.0, 101.0], "frijol": [100.0, 102.0]}, index=[p1, p2]).T
    serie = SerieNormalizada(df_serie, {"arroz": "Arroz", "frijol": "Frijol"})

    resultado = LaspeyresDirecto().calcular(canasta, serie, "id", tipo="inpc")
    inegi: dict[str, dict[PeriodoQuincenal, float | None]] = {"INPC": {p1: 99.0, p2: 101.5}}

    imputados = {("arroz", p1): p2}
    _, reporte, _ = validar(resultado, inegi, canasta, serie, "id", imputados)

    assert reporte.df.at[(p1, "INPC"), "estado_validacion"] == "diferencia_detectada_imputado"
    assert reporte.df.at[(p2, "INPC"), "estado_validacion"] == "ok"


def test_diferencia_detectada_sin_imputacion_cuando_periodo_no_imputado():
    df_canasta = pd.DataFrame(
        {"ponderador": ["50.0", "50.0"], "encadenamiento": [None, None]},
        index=["arroz", "frijol"],
    )
    canasta = CanastaCanonica(df_canasta, 2018)

    df_serie = pd.DataFrame({"arroz": [100.0, 101.0], "frijol": [100.0, 102.0]}, index=[p1, p2]).T
    serie = SerieNormalizada(df_serie, {"arroz": "Arroz", "frijol": "Frijol"})

    resultado = LaspeyresDirecto().calcular(canasta, serie, "id", tipo="inpc")
    inegi: dict[str, dict[PeriodoQuincenal, float | None]] = {"INPC": {p1: 99.0, p2: 101.5}}

    _, reporte, _ = validar(resultado, inegi, canasta, serie, "id")

    assert reporte.df.at[(p1, "INPC"), "estado_validacion"] == "diferencia_detectada"
