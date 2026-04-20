import pandas as pd
import pytest

from replica_inpc import combinar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import Periodo

p1 = Periodo(2018, 7, 2)
p2 = Periodo(2018, 8, 1)
p3 = Periodo(2024, 7, 2)  # traslape
p4 = Periodo(2024, 8, 1)


def _resultado(periodos: list[Periodo], version: int, id_corrida: str = "abc") -> ResultadoCalculo:
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
    periodos: list[Periodo], version: int, categoria: str, id_corrida: str = "abc"
) -> ResultadoCalculo:
    idx = pd.MultiIndex.from_tuples(
        [(p, categoria) for p in periodos], names=["periodo", "indice"]
    )
    df = pd.DataFrame(
        {
            "version": version,
            "tipo": "CCIF division",
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        },
        index=idx,
    )
    return ResultadoCalculo(df, id_corrida)


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
    assert periodos.count(p3) == 1  # sin duplicado
    fila_traslape = resultado.df.loc[(p3, "INPC")]  # type: ignore[index]
    assert fila_traslape["version"] == 2024  # vino del posterior


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


# --- normalización CCIF division ---


def test_combinar_ccif_forward_rename_por_defecto():
    r_2018 = _resultado_ccif([p1, p2, p3], 2018, "comunicaciones")
    r_2024 = _resultado_ccif([p3, p4], 2024, "informacion y comunicacion")
    resultado = combinar([r_2018, r_2024])
    indices = set(resultado.df.index.get_level_values("indice"))
    assert indices == {"informacion y comunicacion"}


def test_combinar_ccif_backward_rename_version_canonica_2018():
    r_2018 = _resultado_ccif([p1, p2, p3], 2018, "comunicaciones")
    r_2024 = _resultado_ccif([p3, p4], 2024, "informacion y comunicacion")
    resultado = combinar([r_2018, r_2024], version_canonica=2018)
    indices = set(resultado.df.index.get_level_values("indice"))
    assert indices == {"comunicaciones"}


def test_combinar_ccif_categoria_sin_mapeo_pasa_sin_modificar():
    r_2018 = _resultado_ccif([p1, p2, p3], 2018, "salud")
    r_2024 = _resultado_ccif([p3, p4], 2024, "salud")
    resultado = combinar([r_2018, r_2024])
    indices = set(resultado.df.index.get_level_values("indice"))
    assert indices == {"salud"}


def test_combinar_ccif_categoria_nueva_en_2024_aparece_sin_historia():
    r_2018 = _resultado_ccif([p1, p2], 2018, "salud")
    r_2024 = _resultado_ccif([p3, p4], 2024, "seguros y servicios financieros")
    resultado = combinar([r_2018, r_2024])
    indices = set(resultado.df.index.get_level_values("indice"))
    assert "salud" in indices
    assert "seguros y servicios financieros" in indices


def test_combinar_inpc_no_afectado_por_normalizacion():
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2018, r_2024])
    indices = set(resultado.df.index.get_level_values("indice"))
    assert indices == {"INPC"}


# --- tres corridas ---


def test_combinar_tres_corridas():
    p0 = Periodo(2013, 4, 1)
    r_2013 = _resultado([p0, p1], 2013)
    r_2018 = _resultado([p1, p2, p3], 2018)
    r_2024 = _resultado([p3, p4], 2024)
    resultado = combinar([r_2013, r_2018, r_2024])

    periodos = list(resultado.df.index.get_level_values("periodo"))
    assert len(periodos) == len(set(periodos))  # sin duplicados
    assert periodos == sorted(periodos)
    assert resultado.df.loc[(p1, "INPC"), "version"] == 2018  # type: ignore[index]
    assert resultado.df.loc[(p3, "INPC"), "version"] == 2024  # type: ignore[index]
