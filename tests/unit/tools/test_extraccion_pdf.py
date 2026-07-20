from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
from canasta_inpc.esquema import VersionCanasta
from canasta_inpc.extraccion_pdf import extraer_pdf
from canasta_inpc.extraccion_xlsx import extraer_xlsx
from canasta_inpc.utilidades import quitar_prefijo_numerico

# fixtures reales de INEGI, no versionadas (data/ esta en .gitignore) -- si
# faltan, estos tests fallan con FileNotFoundError, no se saltan solos
_DIR_MANUALES = Path(__file__).parent.parent.parent.parent / "data" / "tests" / "manuales"
_DIR_XLSX = Path(__file__).parent.parent.parent.parent / "data" / "tests" / "xlsx"
_DIR_REFERENCIA = Path(__file__).parent.parent.parent.parent / "data" / "tests" / "ponderadores"

_VERSIONES: tuple[VersionCanasta, ...] = (2010, 2013)
_CONTEO_ESPERADO: dict[VersionCanasta, int] = {2010: 283, 2013: 283}

# el pdf imprime menos decimales que el xml crudo del xlsx -- no se espera
# igualdad exacta, match.py resuelve esto con tolerancia de redondeo al
# cruzar (ver test_match.py); acá se confirma que el pdf trae exactamente
# esta cantidad de decimales y que su valor coincide con el redondeo exacto
# del xlsx a esa precision (no solo "cerca", que un bug de redondeo
# incorrecto podria pasar igual con una tolerancia laxa)
_PRECISION_PONDERADOR: dict[VersionCanasta, int] = {2010: 4, 2013: 5}

_COG_CATEGORIAS_2010 = frozenset(
    {
        "alimentos bebidas y tabaco",
        "ropa calzado y accesorios",
        "vivienda",
        "muebles aparatos y accesorios domesticos",
        "salud y cuidado personal",
        "transporte",
        "educacion y esparcimiento",
        "otros servicios",
    }
)


# -- helpers ------------------------------------------------------------

# quitar_prefijo_numerico solo pela un codigo simple ("01 x" -> "x"); CCIF
# grupo/clase traen codigo jerarquico con puntos ("01.1 x", "01.1.1 x") que
# el pdf conserva a proposito (contrato final, ver utilidades.py) pero la
# referencia historica nunca tuvo -- este stripper es solo para la
# comparacion del test, no reemplaza a quitar_prefijo_numerico
_QUITAR_CODIGO_CCIF_RE = re.compile(r"^\d+(\.\d+)*\s+")


def _sin_codigo_ccif(texto: str) -> str:
    return _QUITAR_CODIGO_CCIF_RE.sub("", texto, count=1)


def _decimales(valor: str) -> int:
    return len(valor.split(".")[-1]) if "." in valor else 0


def _extraer(version: VersionCanasta) -> pd.DataFrame:
    return extraer_pdf(_DIR_MANUALES / f"manual_{version}.pdf", version)


def _extraer_xlsx(version: VersionCanasta) -> pd.DataFrame:
    return extraer_xlsx(_DIR_XLSX / f"{version}.xlsx", version)


def _referencia(version: VersionCanasta) -> pd.DataFrame:
    ruta = _DIR_REFERENCIA / f"ponderadores_{version}.csv"
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def _cruce_con_xlsx(version: VersionCanasta) -> pd.DataFrame:
    return _extraer(version).merge(_extraer_xlsx(version), on="generico", suffixes=("_pdf", "_xlsx"))


def _cruce_con_referencia(version: VersionCanasta) -> pd.DataFrame:
    return _extraer(version).merge(_referencia(version), on="generico", suffixes=("_pdf", "_ref"))


# -- forma del resultado -------------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_conteo_de_filas_coincide_con_lo_esperado(version: VersionCanasta) -> None:
    assert len(_extraer(version)) == _CONTEO_ESPERADO[version]


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_generico_es_unico(version: VersionCanasta) -> None:
    assert _extraer(version)["generico"].is_unique


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_genericos_coinciden_exactamente_con_extraccion_xlsx(version: VersionCanasta) -> None:
    assert set(_extraer(version)["generico"]) == set(_extraer_xlsx(version)["generico"])


@pytest.mark.requires_data
def test_2010_incluye_cog_2013_no() -> None:
    # FUENTES_POSIBLES: COG en 2013 solo sale de xlsx (extraccion_pdf.py no
    # la produce, el manual 2013 no tiene anexo COG, solo CCIF/SCIAN); en
    # 2010 sale de ambas fuentes -- el manual 2010 SI tiene un anexo COG
    # aparte (Anexo D), para cruzarse en match.py contra el COG del xlsx
    assert "COG" in _extraer(2010).columns
    assert "COG" not in _extraer(2013).columns


@pytest.mark.requires_data
def test_2010_no_produce_encadenamiento_ni_scian() -> None:
    # FUENTES_POSIBLES 2010: encadenamiento no tiene ninguna fuente, SCIAN
    # sector/rama solo vienen de "sync" (--sincronizar, no de pdf)
    columnas = _extraer(2010).columns
    assert "encadenamiento" not in columnas
    assert "SCIAN sector" not in columnas
    assert "SCIAN rama" not in columnas


# -- ponderador / encadenamiento ------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_ponderador_tiene_la_precision_impresa_esperada(version: VersionCanasta) -> None:
    decimales = _extraer(version)["ponderador"].apply(_decimales)
    assert (decimales == _PRECISION_PONDERADOR[version]).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_ponderador_coincide_con_el_redondeo_exacto_del_xlsx(version: VersionCanasta) -> None:
    m = _cruce_con_xlsx(version)
    precision = _PRECISION_PONDERADOR[version]
    redondeado_xlsx = m["ponderador_xlsx"].astype(float).round(precision)
    redondeado_pdf = m["ponderador_pdf"].astype(float).round(precision)
    assert (redondeado_pdf == redondeado_xlsx).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_suma_de_ponderador_es_100(version: VersionCanasta) -> None:
    # tolerancia mas laxa que la de extraccion_xlsx.py: acá se suman valores
    # ya redondeados por la impresion del pdf, no la precision cruda del xml
    assert _extraer(version)["ponderador"].astype(float).sum() == pytest.approx(100, abs=1e-2)


@pytest.mark.requires_data
def test_encadenamiento_2013_tiene_la_precision_impresa_esperada() -> None:
    decimales = _extraer(2013)["encadenamiento"].apply(_decimales)
    assert (decimales == 5).all()


@pytest.mark.requires_data
def test_encadenamiento_2013_coincide_con_el_redondeo_exacto_del_xlsx() -> None:
    m = _cruce_con_xlsx(2013)
    redondeado_xlsx = m["encadenamiento_xlsx"].astype(float).round(5)
    redondeado_pdf = m["encadenamiento_pdf"].astype(float).round(5)
    assert (redondeado_pdf == redondeado_xlsx).all()


# -- CCIF -------------------------------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_ccif_division_siempre_tiene_prefijo_numerico(version: VersionCanasta) -> None:
    # a diferencia de extraccion_xlsx.py (que siempre lo quita), el pdf es la
    # fuente que repone el prefijo consistente en las 4 versiones
    assert _extraer(version)["CCIF division"].str.match(r"^\d").all()


@pytest.mark.requires_data
def test_ccif_division_2013_coincide_con_xlsx_al_quitar_prefijo() -> None:
    m = _cruce_con_xlsx(2013)
    sin_prefijo = m["CCIF division_pdf"].apply(quitar_prefijo_numerico)
    assert (sin_prefijo == m["CCIF division_xlsx"]).all()


@pytest.mark.requires_data
def test_ccif_jerarquia_2010_coincide_con_la_referencia() -> None:
    # 2010 no tiene CCIF en el xlsx (sin hoja) -- se compara contra el csv
    # de referencia historico en vez de contra extraccion_xlsx
    m = _cruce_con_referencia(2010)
    for columna in ("CCIF division", "CCIF grupo", "CCIF clase"):
        sin_codigo = m[f"{columna}_pdf"].apply(_sin_codigo_ccif)
        assert (sin_codigo == m[f"{columna}_ref"]).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("columna", ["CCIF grupo", "CCIF clase"])
def test_ccif_grupo_clase_2013_nunca_vacios(columna: str) -> None:
    assert (_extraer(2013)[columna] != "").all()


# -- SCIAN (solo 2013) --------------------------------------------------


@pytest.mark.requires_data
def test_scian_2013_coincide_con_la_referencia() -> None:
    m = _cruce_con_referencia(2013)
    assert (m["SCIAN sector_pdf"] == m["SCIAN sector_ref"]).all()
    assert (m["SCIAN rama_pdf"] == m["SCIAN rama_ref"]).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("columna", ["SCIAN sector", "SCIAN rama"])
def test_scian_2013_nunca_vacio(columna: str) -> None:
    assert (_extraer(2013)[columna] != "").all()


# -- COG (solo 2010) ---------------------------------------------------------


@pytest.mark.requires_data
def test_cog_2010_coincide_con_xlsx() -> None:
    m = _cruce_con_xlsx(2010)
    assert (m["COG_pdf"] == m["COG_xlsx"]).all()


@pytest.mark.requires_data
def test_cog_2010_nunca_vacio() -> None:
    assert (_extraer(2010)["COG"] != "").all()


@pytest.mark.requires_data
def test_cog_2010_detecta_las_8_categorias() -> None:
    assert set(_extraer(2010)["COG"]) == _COG_CATEGORIAS_2010


@pytest.mark.requires_data
@pytest.mark.parametrize(
    "generico",
    ["otros chiles frescos", "otros mariscos", "servicios funerarios"],
)
def test_cog_2010_nombres_con_artefacto_de_justificacion_quedan_correctos(
    generico: str,
) -> None:
    # Anexo D (texto justificado) glitchea 3 nombres en modo raw:
    # "otroschilesfrescos", "otrosm ariscos" (genericos) y "otrosse rvicios"
    # (la categoria "otros servicios" misma) -- corregidos a mano en
    # _CORRECCIONES_COG_2010; este test asegura que el generico real quedo
    # bien y que "servicios funerarios" (que depende de que la categoria
    # "otros servicios" se haya detectado) tiene su COG real, no arrastrado
    # de la categoria anterior
    df = _extraer(2010)
    assert generico in set(df["generico"])


# -- reproducibilidad ---------------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_pdf_es_reproducible(version: VersionCanasta) -> None:
    pd.testing.assert_frame_equal(_extraer(version), _extraer(version))
