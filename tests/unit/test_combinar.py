import pandas as pd
import pytest

from replica_inpc import combinar
from replica_inpc.dominio.correspondencia_canastas import RENOMBRES_INDICES
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoQuincenal

p1 = PeriodoQuincenal(2018, 7, 2)
p2 = PeriodoQuincenal(2018, 8, 1)
p3 = PeriodoQuincenal(2024, 7, 2)  # traslape
p4 = PeriodoQuincenal(2024, 8, 1)


def _resultado(
    periodos: list[PeriodoQuincenal], version: int, id_corrida: str = "abc"
) -> ResultadoCalculo:
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    df = pd.DataFrame(
        {
            "version": version,
            "tipo": "inpc",
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    return ResultadoCalculo(df, id_corrida)


def _resultado_ccif(
    periodos: list[PeriodoQuincenal],
    version: int,
    categoria: str,
    id_corrida: str = "abc",
    tipo: str = "CCIF division",
) -> ResultadoCalculo:
    idx = pd.MultiIndex.from_tuples([(p, categoria) for p in periodos], names=["periodo", "indice"])
    df = pd.DataFrame(
        {
            "version": version,
            "tipo": tipo,
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    return ResultadoCalculo(df, id_corrida)


# (tipo, version_origen, origen, canonico) para todos los renombres declarados
_TODOS_RENOMBRES = [
    (tipo, version_origen, origen, canonico)
    for tipo, versiones in RENOMBRES_INDICES.items()
    for version_origen, renombres in versiones.items()
    for origen, canonico in renombres.items()
]


# --- mínimo de elementos ---


def test_combinar_requiere_minimo_dos():
    r = _resultado([p1], 2018)
    with pytest.raises(InvarianteViolado):
        combinar([r])


# --- orden cronológico ---


def test_combinar_ordena_cronologicamente():
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2024, r_2018])  # orden inverso
    periodos = list(resultado.df.index.get_level_values("periodo"))
    assert periodos == sorted(periodos)


# --- traslape queda en el posterior ---


def test_traslape_queda_en_posterior():
    r_2018 = _resultado([p1, p2, p3], 2018, "id_2018")
    r_2024 = _resultado([p3, p4], 2024, "id_2024")
    resultado = combinar([r_2018, r_2024])

    periodos = list(resultado.df.index.get_level_values("periodo"))
    assert periodos.count(p3) == 1
    fila_traslape = resultado.df.loc[(p3, "INPC")]  # type: ignore[index]
    assert fila_traslape["version"] == 2024


# --- sin duplicados de índice ---


def test_sin_duplicados_en_resultado():
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2018, r_2024])
    assert not resultado.df.index.duplicated().any()


# --- id_corrida nuevo ---


def test_id_corrida_es_nuevo():
    r_2018 = _resultado([p1, p2, p3], 2018, "id_2018")
    r_2024 = _resultado([p3, p4], 2024, "id_2024")
    resultado = combinar([r_2018, r_2024])
    assert resultado.id_corrida not in {"id_2018", "id_2024"}


# --- normalización: forward (default → canonico 2024) ---


@pytest.mark.parametrize(("tipo", "version_origen", "origen", "canonico"), _TODOS_RENOMBRES)
def test_normalizar_forward(tipo: str, version_origen: int, origen: str, canonico: str):
    r_viejo = _resultado_ccif([p1, p2, p3], version_origen, origen, tipo=tipo)
    r_2024 = _resultado_ccif([p3, p4], 2024, canonico, tipo=tipo)
    resultado = combinar([r_viejo, r_2024])
    assert set(resultado.df.index.get_level_values("indice")) == {canonico}


# --- normalización: backward (version_canonica=version_origen) ---


@pytest.mark.parametrize(("tipo", "version_origen", "origen", "canonico"), _TODOS_RENOMBRES)
def test_normalizar_backward(tipo: str, version_origen: int, origen: str, canonico: str):
    r_viejo = _resultado_ccif([p1, p2, p3], version_origen, origen, tipo=tipo)
    r_2024 = _resultado_ccif([p3, p4], 2024, canonico, tipo=tipo)
    resultado = combinar([r_viejo, r_2024], version_canonica=version_origen)  # type: ignore[arg-type]
    assert set(resultado.df.index.get_level_values("indice")) == {origen}


# --- normalización: sin mapeo pasa sin modificar ---


def test_categoria_sin_mapeo_pasa_sin_modificar():
    r_2018 = _resultado_ccif([p1, p2, p3], 2018, "salud")
    r_2024 = _resultado_ccif([p3, p4], 2024, "salud")
    resultado = combinar([r_2018, r_2024])
    assert set(resultado.df.index.get_level_values("indice")) == {"salud"}


# --- normalización: categoría nueva en 2024 aparece sin historia ---


def test_categoria_nueva_en_2024_aparece_sin_historia():
    r_2018 = _resultado_ccif([p1, p2], 2018, "salud")
    r_2024 = _resultado_ccif([p3, p4], 2024, "seguros y servicios financieros")
    resultado = combinar([r_2018, r_2024])
    indices = set(resultado.df.index.get_level_values("indice"))
    assert "salud" in indices
    assert "seguros y servicios financieros" in indices


# --- normalización: split no se renombra ---


def test_split_no_se_renombra():
    r_2018 = _resultado_ccif(
        [p1, p2, p3], 2018, "agua mineral, refrescos y jugos", tipo="CCIF clase"
    )
    r_2024 = _resultado_ccif([p3, p4], 2024, "refrescos", tipo="CCIF clase")
    resultado = combinar([r_2018, r_2024])
    assert set(resultado.df.index.get_level_values("indice")) == {
        "agua mineral, refrescos y jugos",
        "refrescos",
    }


# --- normalización: eliminada no se renombra ---


def test_eliminada_no_se_renombra():
    r_2018 = _resultado_ccif(
        [p1, p2, p3], 2018, "4921 servicios de mensajeria y paqueteria foranea", tipo="SCIAN rama"
    )
    r_2024 = _resultado_ccif(
        [p3, p4],
        2024,
        "7113 promotores de espectaculos artisticos, culturales, deportivos y similares",
        tipo="SCIAN rama",
    )
    resultado = combinar([r_2018, r_2024])
    assert set(resultado.df.index.get_level_values("indice")) == {
        "4921 servicios de mensajeria y paqueteria foranea",
        "7113 promotores de espectaculos artisticos, culturales, deportivos y similares",
    }


# --- INPC no afectado por normalización ---


def test_inpc_no_afectado_por_normalizacion():
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2018, r_2024])
    assert set(resultado.df.index.get_level_values("indice")) == {"INPC"}


# --- tres corridas ---


def test_combinar_tres_corridas():
    p0 = PeriodoQuincenal(2013, 4, 1)
    r_2013 = _resultado([p0, p1], 2013)
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2013, r_2018, r_2024])

    periodos = list(resultado.df.index.get_level_values("periodo"))
    assert len(periodos) == len(set(periodos))
    assert periodos == sorted(periodos)
    assert resultado.df.loc[(p1, "INPC"), "version"] == 2018  # type: ignore[index]
    assert resultado.df.loc[(p3, "INPC"), "version"] == 2024  # type: ignore[index]
