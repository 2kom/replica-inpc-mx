from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica

_GENERICOS = ("arroz", "frijol", "leche", "huevo")
_PONDERADORES = ("10.0", "20.0", "30.0", "40.0")


def _df(
    genericos: tuple[str, ...] = _GENERICOS,
    ponderadores: tuple[str, ...] = _PONDERADORES,
    encadenamiento: tuple[str | None, ...] | None = None,
) -> pd.DataFrame:
    encadenamiento = encadenamiento or (None,) * len(genericos)
    return pd.DataFrame(
        {"ponderador": list(ponderadores), "encadenamiento": list(encadenamiento)},
        index=pd.Index(list(genericos), name="generico"),
    )


# ---------- Construcción ----------


def test_construccion_valida() -> None:
    c = CanastaCanonica(_df(), 2018)
    assert c.version == 2018
    assert list(c.df.index) == list(_GENERICOS)


# ---------- Invariantes ----------


@pytest.mark.parametrize("version_invalida", [2000, 2015, 2020])
def test_version_invalida_falla(version_invalida: int) -> None:
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(_df(), version_invalida)  # type: ignore[arg-type]


def test_indice_duplicado_falla() -> None:
    df = _df(genericos=("arroz", "arroz", "leche", "huevo"))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


def test_indice_con_cadena_vacia_falla() -> None:
    df = _df(genericos=("arroz", "", "leche", "huevo"))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


@pytest.mark.parametrize("ponderador_invalido", ["0", "-5.0"])
def test_ponderador_no_positivo_falla(ponderador_invalido: str) -> None:
    df = _df(ponderadores=(ponderador_invalido, "20.0", "30.0", "40.0"))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


def test_suma_ponderadores_distinta_de_100_falla() -> None:
    df = _df(ponderadores=("10.0", "20.0", "30.0", "30.0"))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


def test_suma_ponderadores_dentro_de_tolerancia_no_falla() -> None:
    # suma = 99.999995, diferencia real de 5e-6 (< 1e-5) — no cancela a 100.0 exacto
    df = _df(ponderadores=("9.999995", "20.0", "30.0", "40.0"))
    CanastaCanonica(df, 2018)


def test_suma_ponderadores_fuera_de_tolerancia_falla() -> None:
    # suma = 99.99998, diferencia real de 2e-5 (> 1e-5)
    df = _df(ponderadores=("9.99998", "20.0", "30.0", "40.0"))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


@pytest.mark.parametrize("encadenamiento_invalido", ["0", "-1.0"])
def test_encadenamiento_no_positivo_cuando_no_nulo_falla(encadenamiento_invalido: str) -> None:
    df = _df(encadenamiento=(encadenamiento_invalido, None, None, None))
    with pytest.raises(InvarianteViolado):
        CanastaCanonica(df, 2018)


def test_encadenamiento_nulo_no_falla() -> None:
    CanastaCanonica(_df(), 2018)


# ---------- Properties ----------


def test_df_conserva_ponderador_como_str() -> None:
    c = CanastaCanonica(_df(), 2018)
    assert c.df["ponderador"].dtype == object
    assert c.df.loc["arroz", "ponderador"] == "10.0"


def test_repr_html_devuelve_string() -> None:
    c = CanastaCanonica(_df(), 2018)
    assert isinstance(c._repr_html_(), str)
