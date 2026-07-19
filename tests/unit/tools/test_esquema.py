from __future__ import annotations

import dataclasses

import pytest
from canasta_inpc.esquema import (
    COLUMNAS_BASE,
    FUENTES_POSIBLES,
    LAYOUTS_XLSX,
    LayoutXlsx,
    VersionCanasta,
)

_VERSIONES: tuple[VersionCanasta, ...] = (2010, 2013, 2018, 2024)

# snapshot congelado de los valores de FUENTES_POSIBLES verificados contra la
# tabla "Fuentes por columna y versión" de tools/uso_generar_canasta.md al
# escribir este test. Protege contra edicion accidental de esquema.py -- NO
# es un chequeo en vivo contra el .md: si alguien edita solo el markdown,
# este test no se entera (habria que actualizar ambos a mano)
_FUENTES_ESPERADAS: dict[VersionCanasta, dict[str, frozenset[str]]] = {
    2010: {
        "generico": frozenset({"xlsx", "pdf"}),
        "ponderador": frozenset({"xlsx", "pdf"}),
        "encadenamiento": frozenset(),
        "COG": frozenset({"xlsx", "pdf"}),
        "CCIF division": frozenset({"pdf"}),
        "CCIF grupo": frozenset({"pdf"}),
        "CCIF clase": frozenset({"pdf"}),
        "inflacion componente": frozenset({"xlsx"}),
        "inflacion subcomponente": frozenset({"xlsx"}),
        "inflacion agrupacion": frozenset({"xlsx"}),
        "SCIAN sector": frozenset({"sync"}),
        "SCIAN rama": frozenset({"sync"}),
        "durabilidad": frozenset(),
        "canasta basica": frozenset({"xlsx"}),
        "canasta consumo minimo": frozenset(),
    },
    2013: {
        "generico": frozenset({"xlsx", "pdf"}),
        "ponderador": frozenset({"xlsx", "pdf"}),
        "encadenamiento": frozenset({"xlsx", "pdf"}),
        "COG": frozenset({"xlsx"}),
        "CCIF division": frozenset({"xlsx", "pdf"}),
        "CCIF grupo": frozenset({"pdf"}),
        "CCIF clase": frozenset({"pdf"}),
        "inflacion componente": frozenset({"xlsx"}),
        "inflacion subcomponente": frozenset({"xlsx"}),
        "inflacion agrupacion": frozenset({"xlsx"}),
        "SCIAN sector": frozenset({"pdf"}),
        "SCIAN rama": frozenset({"pdf"}),
        "durabilidad": frozenset(),
        "canasta basica": frozenset({"xlsx"}),
        "canasta consumo minimo": frozenset(),
    },
    2018: {
        "generico": frozenset({"xlsx", "pdf"}),
        "ponderador": frozenset({"xlsx", "pdf"}),
        "encadenamiento": frozenset(),
        "COG": frozenset({"xlsx", "pdf"}),
        "CCIF division": frozenset({"xlsx", "pdf"}),
        "CCIF grupo": frozenset({"pdf"}),
        "CCIF clase": frozenset({"pdf"}),
        "inflacion componente": frozenset({"xlsx"}),
        "inflacion subcomponente": frozenset({"xlsx"}),
        "inflacion agrupacion": frozenset({"xlsx"}),
        "SCIAN sector": frozenset({"pdf"}),
        "SCIAN rama": frozenset({"pdf"}),
        "durabilidad": frozenset({"pdf"}),
        "canasta basica": frozenset({"xlsx"}),
        "canasta consumo minimo": frozenset(),
    },
    2024: {
        "generico": frozenset({"xlsx", "pdf"}),
        "ponderador": frozenset({"xlsx", "pdf"}),
        "encadenamiento": frozenset({"xlsx"}),
        "COG": frozenset({"xlsx"}),
        "CCIF division": frozenset({"xlsx", "pdf"}),
        "CCIF grupo": frozenset({"pdf"}),
        "CCIF clase": frozenset({"pdf"}),
        "inflacion componente": frozenset({"xlsx"}),
        "inflacion subcomponente": frozenset({"xlsx"}),
        "inflacion agrupacion": frozenset({"xlsx"}),
        "SCIAN sector": frozenset({"pdf"}),
        "SCIAN rama": frozenset({"pdf"}),
        "durabilidad": frozenset({"pdf"}),
        "canasta basica": frozenset({"xlsx"}),
        "canasta consumo minimo": frozenset({"xlsx"}),
    },
}

# snapshot congelado de LAYOUTS_XLSX (mismos valores que esquema.py, verificados
# contra las 4 xlsx reales en sesion anterior) -- protege contra edicion
# accidental (ej. columna 6 -> 5, o swap de col_generico/col_grupo) que un
# chequeo de solo-conteo no detectaria. NO protege contra que INEGI cambie el
# xlsx oficial -- esquema.py no lee ningun xlsx, eso lo cubre extraccion_xlsx.py
_LAYOUTS_ESPERADOS: dict[VersionCanasta, LayoutXlsx] = {
    2010: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI",
        hoja_ccif=None,
        col_generico=2,
        col_grupo=1,
        col_ponderador=3,
        col_encadenamiento=None,
        col_canasta_basica=19,
        col_canasta_consumo_minimo=None,
        agrupaciones={
            6: ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            7: ("subyacente", "mercancias", "mercancias no alimenticias"),
            9: ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            11: ("subyacente", "servicios", "educacion"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "energeticos",
            ),
            18: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "tarifas autorizadas por el gobierno",
            ),
        },
    ),
    2013: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI",
        hoja_ccif="Ponderadores INPC COICOP INEGI",
        col_generico=2,
        col_grupo=1,
        col_ponderador=3,
        col_encadenamiento=4,
        col_canasta_basica=20,
        col_canasta_consumo_minimo=None,
        agrupaciones={
            7: ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            8: ("subyacente", "mercancias", "mercancias no alimenticias"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            12: ("subyacente", "servicios", "educacion"),
            15: ("no subyacente", "agropecuarios", "frutas y verduras"),
            16: ("no subyacente", "agropecuarios", "pecuarios"),
            18: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "energeticos",
            ),
            19: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "tarifas autorizadas por el gobierno",
            ),
        },
    ),
    2018: LayoutXlsx(
        hoja_cog="Objeto de gasto",
        hoja_ccif="CCIF",
        col_generico=1,
        col_grupo=None,
        col_ponderador=2,
        col_encadenamiento=None,
        col_canasta_basica=19,
        col_canasta_consumo_minimo=None,
        agrupaciones={
            5: ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            6: ("subyacente", "mercancias", "mercancias no alimenticias"),
            8: ("subyacente", "servicios", "educacion colegiaturas"),
            9: ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            13: ("no subyacente", "agropecuarios", "frutas y verduras"),
            14: ("no subyacente", "agropecuarios", "pecuarios"),
            16: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "energeticos",
            ),
            17: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "tarifas autorizadas por el gobierno",
            ),
        },
    ),
    2024: LayoutXlsx(
        hoja_cog="Objeto de gasto",
        hoja_ccif="CCIF",
        col_generico=1,
        col_grupo=None,
        col_ponderador=2,
        col_encadenamiento=3,
        col_canasta_basica=20,
        col_canasta_consumo_minimo=21,
        agrupaciones={
            6: ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            7: ("subyacente", "mercancias", "mercancias no alimenticias"),
            9: ("subyacente", "servicios", "educacion colegiaturas"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "energeticos",
            ),
            18: (
                "no subyacente",
                "energeticos y tarifas autorizadas por el gobierno",
                "tarifas autorizadas por el gobierno",
            ),
        },
    ),
}


# -- COLUMNAS_BASE -----------------------------------------------------------


def test_columnas_base_orden_y_cantidad() -> None:
    assert COLUMNAS_BASE == (
        "generico",
        "ponderador",
        "encadenamiento",
        "COG",
        "CCIF division",
        "CCIF grupo",
        "CCIF clase",
        "inflacion componente",
        "inflacion subcomponente",
        "inflacion agrupacion",
        "SCIAN sector",
        "SCIAN rama",
        "durabilidad",
        "canasta basica",
        "canasta consumo minimo",
    )


# -- LayoutXlsx ---------------------------------------------------------------


def test_layouts_xlsx_cubre_exactamente_las_4_versiones() -> None:
    assert set(LAYOUTS_XLSX) == set(_VERSIONES)


def test_layout_xlsx_bloquea_reasignar_un_campo() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        LAYOUTS_XLSX[2018].col_generico = 99  # type: ignore[misc]


def test_layout_xlsx_agrupaciones_bloquea_mutacion_interna() -> None:
    # frozen=True solo bloquea reasignar el atributo -- sin MappingProxyType,
    # layout.agrupaciones[6] = (...) mutaria en silencio el dict compartido
    # a nivel de modulo (LAYOUTS_XLSX se reusa en cada llamada a extraer_xlsx)
    with pytest.raises(TypeError):
        LAYOUTS_XLSX[2018].agrupaciones[6] = ("x", "y", "z")  # type: ignore[index]


@pytest.mark.parametrize(
    ("version", "tiene_hoja_ccif"),
    [(2010, False), (2013, True), (2018, True), (2024, True)],
)
def test_hoja_ccif_ausente_solo_en_2010(version: VersionCanasta, tiene_hoja_ccif: bool) -> None:
    assert (LAYOUTS_XLSX[version].hoja_ccif is not None) == tiene_hoja_ccif


@pytest.mark.parametrize(
    ("version", "tiene_encadenamiento"),
    [(2010, False), (2013, True), (2018, False), (2024, True)],
)
def test_col_encadenamiento_solo_en_2013_2024(
    version: VersionCanasta, tiene_encadenamiento: bool
) -> None:
    assert (LAYOUTS_XLSX[version].col_encadenamiento is not None) == tiene_encadenamiento


@pytest.mark.parametrize(
    ("version", "tiene_consumo_minimo"),
    [(2010, False), (2013, False), (2018, False), (2024, True)],
)
def test_col_canasta_consumo_minimo_solo_en_2024(
    version: VersionCanasta, tiene_consumo_minimo: bool
) -> None:
    assert (LAYOUTS_XLSX[version].col_canasta_consumo_minimo is not None) == tiene_consumo_minimo


@pytest.mark.parametrize("version", _VERSIONES)
def test_agrupaciones_tiene_9_entradas_por_version(version: VersionCanasta) -> None:
    # 9 agrupaciones fijas de inflacion (5 subyacente + 4 no subyacente), mismo conteo en las 4 versiones
    assert len(LAYOUTS_XLSX[version].agrupaciones) == 9


@pytest.mark.parametrize("version", _VERSIONES)
def test_agrupaciones_solo_dos_tipos_de_indice(version: VersionCanasta) -> None:
    tipos = {tipo for tipo, _, _ in LAYOUTS_XLSX[version].agrupaciones.values()}
    assert tipos == {"subyacente", "no subyacente"}


@pytest.mark.parametrize("version", _VERSIONES)
def test_layout_xlsx_coincide_con_snapshot_esperado(version: VersionCanasta) -> None:
    assert LAYOUTS_XLSX[version] == _LAYOUTS_ESPERADOS[version]


# -- FUENTES_POSIBLES ----------------------------------------------------


def test_fuentes_posibles_cubre_exactamente_las_4_versiones() -> None:
    assert set(FUENTES_POSIBLES) == set(_VERSIONES)


@pytest.mark.parametrize("version", _VERSIONES)
def test_fuentes_posibles_cubre_exactamente_columnas_base(version: VersionCanasta) -> None:
    assert set(FUENTES_POSIBLES[version]) == set(COLUMNAS_BASE)


@pytest.mark.parametrize("version", _VERSIONES)
def test_fuentes_posibles_valores_son_subconjunto_de_xlsx_pdf_sync(version: VersionCanasta) -> None:
    fuentes_validas = {"xlsx", "pdf", "sync"}
    for fuentes in FUENTES_POSIBLES[version].values():
        assert isinstance(fuentes, frozenset)
        assert fuentes <= fuentes_validas


@pytest.mark.parametrize("version", _VERSIONES)
def test_fuentes_posibles_coincide_con_tabla_documentada(version: VersionCanasta) -> None:
    assert FUENTES_POSIBLES[version] == _FUENTES_ESPERADAS[version]


# -- consistencia LAYOUTS_XLSX <-> FUENTES_POSIBLES --------------------------
# invariantes internas: si el layout dice que no hay columna en el xlsx,
# FUENTES_POSIBLES no debe listar "xlsx" como fuente posible para esa columna


@pytest.mark.parametrize("version", _VERSIONES)
def test_encadenamiento_xlsx_como_fuente_coincide_con_layout(version: VersionCanasta) -> None:
    hay_columna = LAYOUTS_XLSX[version].col_encadenamiento is not None
    xlsx_es_fuente = "xlsx" in FUENTES_POSIBLES[version]["encadenamiento"]
    assert hay_columna == xlsx_es_fuente


@pytest.mark.parametrize("version", _VERSIONES)
def test_canasta_consumo_minimo_xlsx_como_fuente_coincide_con_layout(
    version: VersionCanasta,
) -> None:
    hay_columna = LAYOUTS_XLSX[version].col_canasta_consumo_minimo is not None
    xlsx_es_fuente = "xlsx" in FUENTES_POSIBLES[version]["canasta consumo minimo"]
    assert hay_columna == xlsx_es_fuente


@pytest.mark.parametrize("version", _VERSIONES)
def test_ccif_division_xlsx_como_fuente_coincide_con_hoja_ccif(version: VersionCanasta) -> None:
    hay_hoja = LAYOUTS_XLSX[version].hoja_ccif is not None
    xlsx_es_fuente = "xlsx" in FUENTES_POSIBLES[version]["CCIF division"]
    assert hay_hoja == xlsx_es_fuente
