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

_VERSIONES: tuple[VersionCanasta, ...] = (2010, 2013, 2018, 2024)
_CONTEO_ESPERADO: dict[VersionCanasta, int] = {2010: 283, 2013: 283, 2018: 299, 2024: 292}

# el pdf imprime menos decimales que el xml crudo del xlsx -- no se espera
# igualdad exacta, match.py resuelve esto con tolerancia de redondeo al
# cruzar (ver test_match.py); acá se confirma que el pdf trae exactamente
# esta cantidad de decimales y que su valor coincide con el redondeo exacto
# del xlsx a esa precision (no solo "cerca", que un bug de redondeo
# incorrecto podria pasar igual con una tolerancia laxa)
_PRECISION_PONDERADOR: dict[VersionCanasta, int] = {2010: 4, 2013: 5, 2018: 4, 2024: 4}

_DURABILIDAD = frozenset({"duradero", "no duradero", "semiduradero", "servicio"})

_COG_CATEGORIAS = frozenset(
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
    return _extraer(version).merge(
        _extraer_xlsx(version), on="generico", suffixes=("_pdf", "_xlsx")
    )


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
def test_2010_y_2018_incluyen_cog_2013_no() -> None:
    # FUENTES_POSIBLES: COG en 2013 solo sale de xlsx (extraccion_pdf.py no
    # la produce, el manual 2013 no tiene anexo COG, solo CCIF/SCIAN); en
    # 2010 y 2018 sale de ambas fuentes -- ambos manuales SI tienen un anexo
    # COG aparte (Anexo D), para cruzarse en match.py contra el COG del xlsx
    assert "COG" in _extraer(2010).columns
    assert "COG" in _extraer(2018).columns
    assert "COG" not in _extraer(2013).columns


@pytest.mark.requires_data
def test_2010_no_produce_encadenamiento_ni_scian() -> None:
    # FUENTES_POSIBLES 2010: encadenamiento no tiene ninguna fuente, SCIAN
    # sector/rama solo vienen de "sync" (--sincronizar, no de pdf)
    columnas = _extraer(2010).columns
    assert "encadenamiento" not in columnas
    assert "SCIAN sector" not in columnas
    assert "SCIAN rama" not in columnas


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2018, 2024])
def test_2018_y_2024_no_producen_encadenamiento_pero_si_scian(version: VersionCanasta) -> None:
    # a diferencia de 2010, estos manuales SI tienen anexo SCIAN propio --
    # solo encadenamiento esta ausente (ninguna de las 2 versiones tiene esa
    # columna en el pdf; 2024 la tiene en el xlsx, ver FUENTES_POSIBLES)
    columnas = _extraer(version).columns
    assert "encadenamiento" not in columnas
    assert "SCIAN sector" in columnas
    assert "SCIAN rama" in columnas


_COLUMNAS_PDF_2024 = frozenset(
    {
        "generico",
        "ponderador",
        "durabilidad",
        "CCIF division",
        "CCIF grupo",
        "CCIF clase",
        "SCIAN sector",
        "SCIAN rama",
    }
)


@pytest.mark.requires_data
def test_2024_columnas_son_exactamente_las_esperadas() -> None:
    # FUENTES_POSIBLES 2024: encadenamiento/COG/canasta basica/canasta
    # consumo minimo son xlsx-only (el manual 2024 no tiene anexo COG
    # aparte, a diferencia de 2010 y 2018) -- afirmar el conjunto exacto en
    # vez de solo las columnas conocidas cubre también cualquier columna
    # inesperada que aparezca por error
    assert set(_extraer(2024).columns) == _COLUMNAS_PDF_2024


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
def test_ccif_division_2018_coincide_con_xlsx_salvo_29_divergencias_conocidas() -> None:
    # ya documentado en test_extraccion_xlsx.py: el xlsx 2018 trae "ropa y
    # calzado" (nombre literal de la celda) en 29 filas donde el pdf (nombre
    # CCIF oficial) trae "prendas de vestir y calzado" -- no es bug de
    # ninguna de las 2 extracciones, es una divergencia real de la fuente
    m = _cruce_con_xlsx(2018)
    sin_prefijo = m["CCIF division_pdf"].apply(quitar_prefijo_numerico)
    difieren = m[sin_prefijo != m["CCIF division_xlsx"]]
    assert len(difieren) == 29
    assert (difieren["CCIF division_xlsx"] == "ropa y calzado").all()
    assert difieren["CCIF division_pdf"].str.endswith("prendas de vestir y calzado").all()


@pytest.mark.requires_data
def test_ccif_division_2024_coincide_con_xlsx_sin_divergencias() -> None:
    # a diferencia de 2018 (29 divergencias reales de nombre), 2024 reusa
    # _extraer_ccif_2018 sobre el mismo Anexo C "por la CCIF 2018" -- acá
    # coincide exacto con el xlsx, sin snapshot de divergencias
    m = _cruce_con_xlsx(2024)
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
@pytest.mark.parametrize("version", [2013, 2018, 2024])
@pytest.mark.parametrize("columna", ["CCIF grupo", "CCIF clase"])
def test_ccif_grupo_clase_nunca_vacios(version: VersionCanasta, columna: str) -> None:
    assert (_extraer(version)[columna] != "").all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2013, 2018, 2024])
@pytest.mark.parametrize("columna", ["CCIF grupo", "CCIF clase"])
def test_ccif_grupo_clase_coincide_con_la_referencia(version: VersionCanasta, columna: str) -> None:
    # a diferencia de "division" (que sí tiene divergencias reales de nombre
    # en 2018, ver test de arriba), grupo/clase coinciden exacto en 2013,
    # 2018 y 2024 -- verificado contra data/tests/ponderadores/ antes de
    # agregar este test, 0 diferencias en las 3 versiones
    m = _cruce_con_referencia(version)
    sin_codigo = m[f"{columna}_pdf"].apply(_sin_codigo_ccif)
    assert (sin_codigo == m[f"{columna}_ref"]).all()


# -- SCIAN (2013, 2018 y 2024) --------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2013, 2018, 2024])
def test_scian_coincide_con_la_referencia(version: VersionCanasta) -> None:
    m = _cruce_con_referencia(version)
    assert (m["SCIAN sector_pdf"] == m["SCIAN sector_ref"]).all()
    assert (m["SCIAN rama_pdf"] == m["SCIAN rama_ref"]).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2013, 2018, 2024])
@pytest.mark.parametrize("columna", ["SCIAN sector", "SCIAN rama"])
def test_scian_nunca_vacio(version: VersionCanasta, columna: str) -> None:
    assert (_extraer(version)[columna] != "").all()


@pytest.mark.requires_data
@pytest.mark.parametrize(
    ("generico", "fragmento_correcto", "fragmento_roto"),
    [
        ("carne de cerdo", "comestibles", "comesti bles"),
        ("tramites vehiculares", "internacionales", "interna cionales"),
    ],
)
def test_scian_2024_corrige_nombres_partidos_a_mitad_de_palabra(
    generico: str, fragmento_correcto: str, fragmento_roto: str
) -> None:
    # modo raw del Anexo D parte 2 nombres de sector/rama a mitad de palabra
    # al reconstruir el wrap ("comesti"+"bles", "interna"+"cionales") --
    # _CORRECCIONES_SCIAN_2024 los arregla; confirmado 1:1 contra el SCIAN
    # real de data/tests/ponderadores/ponderadores_2024.csv
    df = _extraer(2024).set_index("generico")
    sector = str(df.loc[generico, "SCIAN sector"])
    rama = str(df.loc[generico, "SCIAN rama"])
    assert fragmento_correcto in f"{sector} {rama}"
    assert fragmento_roto not in f"{sector} {rama}"


# -- COG (2010 y 2018) --------------------------------------------------


@pytest.mark.requires_data
def test_cog_2010_coincide_con_xlsx() -> None:
    m = _cruce_con_xlsx(2010)
    assert (m["COG_pdf"] == m["COG_xlsx"]).all()


@pytest.mark.requires_data
def test_cog_2010_nunca_vacio() -> None:
    assert (_extraer(2010)["COG"] != "").all()


@pytest.mark.requires_data
def test_cog_2010_detecta_las_8_categorias() -> None:
    assert set(_extraer(2010)["COG"]) == _COG_CATEGORIAS


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


@pytest.mark.requires_data
def test_cog_2018_coincide_con_xlsx() -> None:
    # a diferencia de 2010, el Anexo D de 2018 no tiene artefactos de
    # justificacion (physical layout limpio, ver _extraer_cog_2018)
    m = _cruce_con_xlsx(2018)
    assert (m["COG_pdf"] == m["COG_xlsx"]).all()


@pytest.mark.requires_data
def test_cog_2018_detecta_las_8_categorias() -> None:
    assert set(_extraer(2018)["COG"]) == _COG_CATEGORIAS


# -- durabilidad (2018 y 2024) -------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2018, 2024])
def test_durabilidad_coincide_con_la_referencia(version: VersionCanasta) -> None:
    m = _cruce_con_referencia(version)
    assert (m["durabilidad_pdf"] == m["durabilidad_ref"]).all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2018, 2024])
def test_durabilidad_nunca_vacia(version: VersionCanasta) -> None:
    assert (_extraer(version)["durabilidad"] != "").all()


@pytest.mark.requires_data
@pytest.mark.parametrize("version", [2018, 2024])
def test_durabilidad_solo_trae_valores_esperados(version: VersionCanasta) -> None:
    assert set(_extraer(version)["durabilidad"]) == _DURABILIDAD


# -- reproducibilidad ---------------------------------------------------


@pytest.mark.requires_data
@pytest.mark.parametrize("version", _VERSIONES)
def test_extraer_pdf_es_reproducible(version: VersionCanasta) -> None:
    pd.testing.assert_frame_equal(_extraer(version), _extraer(version))
