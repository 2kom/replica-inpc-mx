import pandas as pd
import pytest

from replica_inpc.dominio.calculo.encadenado import LaspeyresEncadenado
from replica_inpc.dominio.calculo.laspeyres import LaspeyresDirecto
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal

traslape = PeriodoQuincenal(2024, 7, 2)
post_traslape = PeriodoQuincenal(2024, 8, 1)

_df_canasta = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": ["1.5", "1.4", "1.6", "1.3"],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)

"""
Serie con valores ya encadenados (base 2018=100):
  traslape     : I_k^pub = f_k * 100  →  de-enc = 100 exacto por genérico
  post_traslape: índices crudos distintos por genérico para que
                 LaspeyresEncadenado ≠ LaspeyresDirecto
"""
_df_serie = pd.DataFrame(
    {
        "arroz": [150.0, 151.5],
        "frijol": [140.0, 144.2],
        "leche": [160.0, 168.0],
        "huevo": [130.0, 132.6],
    },
    index=[traslape, post_traslape],
).T

_mapeo = {"arroz": "Arroz", "frijol": "Frijol", "leche": "Leche", "huevo": "Huevo"}

canasta = CanastaCanonica(_df_canasta, 2024)
serie = SerieNormalizada(_df_serie, _mapeo)

# f_h = (10*1.5 + 20*1.4 + 30*1.6 + 40*1.3) / 100 = 1.43
_F_H = (10 * 1.5 + 20 * 1.4 + 30 * 1.6 + 40 * 1.3) / 100


def test_inpc_en_traslape_es_f_h_por_100():
    resultado = LaspeyresEncadenado().calcular(canasta, serie, "", tipo="inpc")
    inpc_traslape = resultado.df.at[(traslape, "INPC"), "indice_replicado"]
    assert inpc_traslape == pytest.approx(_F_H * 100)


def test_inpc_post_traslape_difiere_de_laspeyres_directo():
    enc = LaspeyresEncadenado().calcular(canasta, serie, "", tipo="inpc")
    directo = LaspeyresDirecto().calcular(canasta, serie, "", tipo="inpc")

    enc_post = enc.df.at[(post_traslape, "INPC"), "indice_replicado"]
    dir_post = directo.df.at[(post_traslape, "INPC"), "indice_replicado"]

    assert enc_post != pytest.approx(dir_post)


def test_subindice_traslape_es_f_h_subgrupo_por_100():
    df_cog = _df_canasta.assign(COG=["Alimentos", "Alimentos", "Bebidas", "Bebidas"])
    canasta_cog = CanastaCanonica(df_cog, 2024)
    resultado = LaspeyresEncadenado().calcular(canasta_cog, serie, "", tipo="COG")

    indices = sorted(resultado.df.index.get_level_values("indice").unique().tolist())
    assert indices == ["Alimentos", "Bebidas"]

    f_h_alimentos = (10 * 1.5 + 20 * 1.4) / 30
    inpc_traslape_alimentos = resultado.df.at[(traslape, "Alimentos"), "indice_replicado"]
    assert inpc_traslape_alimentos == pytest.approx(f_h_alimentos * 100)

    f_h_bebidas = (30 * 1.6 + 40 * 1.3) / 70
    inpc_traslape_bebidas = resultado.df.at[(traslape, "Bebidas"), "indice_replicado"]
    assert inpc_traslape_bebidas == pytest.approx(f_h_bebidas * 100)


def test_f_k_desde_serie_igual_a_desde_canasta():
    df_sin_enc = _df_canasta.assign(encadenamiento=[None, None, None, None])  # type: ignore
    canasta_sin_enc = CanastaCanonica(df_sin_enc, 2024)

    res_canasta = LaspeyresEncadenado().calcular(canasta, serie, "", tipo="inpc")
    res_serie = LaspeyresEncadenado().calcular(canasta_sin_enc, serie, "", tipo="inpc")

    assert res_canasta.df["indice_replicado"].tolist() == pytest.approx(
        res_serie.df["indice_replicado"].tolist()
    )


def test_null_por_faltantes_detectado_en_serie_original():
    df_con_nan = _df_serie.copy()
    df_con_nan.loc["arroz", post_traslape] = float("nan")
    serie_con_nan = SerieNormalizada(df_con_nan, _mapeo)

    resultado = LaspeyresEncadenado().calcular(canasta, serie_con_nan, "", tipo="inpc")

    assert resultado.df.at[(post_traslape, "INPC"), "estado_calculo"] == "null_por_faltantes"
    assert resultado.df.at[(traslape, "INPC"), "estado_calculo"] == "ok"


# ── Tests versión 2013 ─────────────────────────────────────────────────────────

_traslape_2013 = PeriodoQuincenal(2013, 3, 2)
_post_2013 = PeriodoQuincenal(2013, 4, 1)

# Canasta 2013: f_k = encadenamiento (ratios ENIGH, no niveles de índice)
_df_canasta_2013 = pd.DataFrame(
    {
        "ponderador": ["10.0", "20.0", "30.0", "40.0"],
        "encadenamiento": ["1.2", "0.8", "1.1", "0.9"],
    },
    index=["arroz", "frijol", "leche", "huevo"],
)

# Serie en escala publicada BIE (ya multiplicada por f_k respecto a base 2010)
_df_serie_2013 = pd.DataFrame(
    {
        "arroz": [120.0, 123.0],
        "frijol": [80.0, 82.0],
        "leche": [110.0, 113.0],
        "huevo": [90.0, 91.5],
    },
    index=[_traslape_2013, _post_2013],
).T

_canasta_2013 = CanastaCanonica(_df_canasta_2013, 2013)
_serie_2013 = SerieNormalizada(_df_serie_2013, _mapeo)


def test_2013_divide_por_f_k_antes_de_laspeyres():
    # sin referencia → factor_h = 1.0, resultado = Laspeyres(serie/f_k)
    resultado = LaspeyresEncadenado().calcular(_canasta_2013, _serie_2013, "", tipo="inpc")

    f_k = _df_canasta_2013["encadenamiento"].astype(float)
    ponderadores = _df_canasta_2013["ponderador"].astype(float)
    serie_div = _df_serie_2013.divide(f_k, axis=0)
    esperado_traslape = (serie_div[_traslape_2013] * ponderadores).sum() / ponderadores.sum()

    inpc_traslape = resultado.df.at[(_traslape_2013, "INPC"), "indice_replicado"]
    assert inpc_traslape == pytest.approx(esperado_traslape)


def test_2013_con_referencia_empalme_ancla_en_traslape():
    ref = 109.172
    resultado = LaspeyresEncadenado({"INPC": ref}).calcular(
        _canasta_2013, _serie_2013, "", tipo="inpc"
    )
    inpc_traslape = resultado.df.at[(_traslape_2013, "INPC"), "indice_replicado"]
    # Con factor_h = ref / i_tramo[traslape], resultado[traslape] = ref
    assert inpc_traslape == pytest.approx(ref)
