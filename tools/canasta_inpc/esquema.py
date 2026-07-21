from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

VersionCanasta = Literal[2010, 2013, 2018, 2024]

COLUMNAS_BASE: tuple[str, ...] = (
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


# fmt: off
@dataclass(frozen=True)
class LayoutXlsx:
    """Posiciones de columna (1-indexadas, como en el xlsx) y hojas por version.

    Cubre solo lo que el xlsx puede dar: generico, ponderador, encadenamiento,
    COG, CCIF division, inflacion componente/subcomponente/agrupacion, canasta
    basica y canasta consumo minimo. CCIF grupo/clase, SCIAN sector/rama y
    durabilidad nunca salen del xlsx en ninguna version.

    Ver: tools/uso_generar_canasta.md §Hojas esperadas por version.
    """

    hoja_cog: str  # pestaña con generico + ponderador (Objeto de Gasto / COG)
    hoja_ccif: str | None  # pestaña con CCIF; None si la version no trae hoja CCIF en el xlsx (2010)
    col_generico: int  # columna con el nombre del generico
    col_grupo: int | None  # columna con el nombre de categoria (COG); None si comparte columna con col_generico (patron B)
    col_ponderador: int  # columna con el ponderador del generico (o de la categoria, en su fila de totales)
    col_encadenamiento: int | None  # columna con el factor de encadenamiento; None si la version no lo tiene
    col_canasta_basica: int  # columna con la marca "X" de pertenencia a canasta basica
    col_canasta_consumo_minimo: int | None  # columna con la marca "X" de canasta consumo minimo; None si la version no lo tiene
    # columna -> (inflacion componente, inflacion subcomponente, inflacion agrupacion)
    # se recorre buscando cual columna trae la marca "X" en la fila del generico
    # Mapping (no dict) + MappingProxyType al construir: frozen=True solo bloquea
    # reasignar el atributo, no mutar un dict compartido a nivel de modulo por
    # dentro -- ver tests/unit/tools/test_esquema.py
    agrupaciones: Mapping[int, tuple[str, str, str]]
# fmt: on


# fmt: off
LAYOUTS_XLSX: dict[VersionCanasta, LayoutXlsx] = {
    2010: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI", hoja_ccif=None,
        col_generico=2, col_grupo=1,
        col_ponderador=3, col_encadenamiento=None,
        col_canasta_basica=19, col_canasta_consumo_minimo=None,
        agrupaciones=MappingProxyType({
            6:  ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            7:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            9:  ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            11: ("subyacente", "servicios", "educacion"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        }),
    ),
    2013: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI", hoja_ccif="Ponderadores INPC COICOP INEGI",
        col_generico=2, col_grupo=1,
        col_ponderador=3, col_encadenamiento=4,
        col_canasta_basica=20, col_canasta_consumo_minimo=None,
        agrupaciones=MappingProxyType({
            7:  ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            8:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            12: ("subyacente", "servicios", "educacion"),
            15: ("no subyacente", "agropecuarios", "frutas y verduras"),
            16: ("no subyacente", "agropecuarios", "pecuarios"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            19: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        }),
    ),
    2018: LayoutXlsx(
        hoja_cog="Objeto de gasto", hoja_ccif="CCIF",
        col_generico=1, col_grupo=None,
        col_ponderador=2, col_encadenamiento=None,
        col_canasta_basica=19, col_canasta_consumo_minimo=None,
        agrupaciones=MappingProxyType({
            5:  ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            6:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            8:  ("subyacente", "servicios", "educacion colegiaturas"),
            9:  ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            13: ("no subyacente", "agropecuarios", "frutas y verduras"),
            14: ("no subyacente", "agropecuarios", "pecuarios"),
            16: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        }),
    ),
    2024: LayoutXlsx(
        hoja_cog="Objeto de gasto", hoja_ccif="CCIF",
        col_generico=1, col_grupo=None,
        col_ponderador=2, col_encadenamiento=3,
        col_canasta_basica=20, col_canasta_consumo_minimo=21,
        agrupaciones=MappingProxyType({
            6:  ("subyacente", "mercancias", "alimentos bebidas y tabaco"),
            7:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            9:  ("subyacente", "servicios", "educacion colegiaturas"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        }),
    ),
}
# fmt: on


# fuentes POSIBLES de cada columna por version -- no es "de aqui sale el valor
# final" (esa decision es de match.py cuando corre xlsx+pdf junto), es "en
# cuales archivos se puede encontrar". Sirve para saber que
# columnas se pueden cruzar/validar entre xlsx y pdf y cuales no tienen con
# que comparar (una sola fuente posible, o ninguna).
# frozenset vacio == "-": ninguna fuente, la columna queda vacia en el csv.
# fmt: off
FUENTES_POSIBLES: dict[VersionCanasta, dict[str, frozenset[str]]] = {
    2010: {
        "generico":                frozenset({"xlsx", "pdf"}),
        "ponderador":               frozenset({"xlsx", "pdf"}),
        "encadenamiento":           frozenset(),
        "COG":                      frozenset({"xlsx", "pdf"}),
        "CCIF division":            frozenset({"pdf"}),
        "CCIF grupo":               frozenset({"pdf"}),
        "CCIF clase":               frozenset({"pdf"}),
        "inflacion componente":     frozenset({"xlsx"}),
        "inflacion subcomponente":  frozenset({"xlsx"}),
        "inflacion agrupacion":     frozenset({"xlsx"}),
        "SCIAN sector":             frozenset({"sync"}),
        "SCIAN rama":               frozenset({"sync"}),
        "durabilidad":              frozenset(),
        "canasta basica":           frozenset({"xlsx"}),
        "canasta consumo minimo":   frozenset(),
    },
    2013: {
        "generico":                 frozenset({"xlsx", "pdf"}),
        "ponderador":               frozenset({"xlsx", "pdf"}),
        "encadenamiento":           frozenset({"xlsx", "pdf"}),
        "COG":                      frozenset({"xlsx"}),
        "CCIF division":            frozenset({"xlsx", "pdf"}),
        "CCIF grupo":               frozenset({"pdf"}),
        "CCIF clase":               frozenset({"pdf"}),
        "inflacion componente":     frozenset({"xlsx"}),
        "inflacion subcomponente":  frozenset({"xlsx"}),
        "inflacion agrupacion":     frozenset({"xlsx"}),
        "SCIAN sector":             frozenset({"pdf"}),
        "SCIAN rama":               frozenset({"pdf"}),
        "durabilidad":              frozenset(),
        "canasta basica":           frozenset({"xlsx"}),
        "canasta consumo minimo":   frozenset(),
    },
    2018: {
        "generico":                 frozenset({"xlsx", "pdf"}),
        "ponderador":               frozenset({"xlsx", "pdf"}),
        "encadenamiento":           frozenset(),
        "COG":                      frozenset({"xlsx", "pdf"}),
        "CCIF division":            frozenset({"xlsx", "pdf"}),
        "CCIF grupo":               frozenset({"pdf"}),
        "CCIF clase":               frozenset({"pdf"}),
        "inflacion componente":     frozenset({"xlsx"}),
        "inflacion subcomponente":  frozenset({"xlsx"}),
        "inflacion agrupacion":     frozenset({"xlsx"}),
        "SCIAN sector":             frozenset({"pdf"}),
        "SCIAN rama":               frozenset({"pdf"}),
        "durabilidad":              frozenset({"pdf"}),
        "canasta basica":           frozenset({"xlsx"}),
        "canasta consumo minimo":   frozenset(),
    },
    2024: {
        "generico":                 frozenset({"xlsx", "pdf"}),
        "ponderador":               frozenset({"xlsx", "pdf"}),
        "encadenamiento":           frozenset({"xlsx"}),
        "COG":                      frozenset({"xlsx"}),
        "CCIF division":            frozenset({"xlsx", "pdf"}),
        "CCIF grupo":               frozenset({"pdf"}),
        "CCIF clase":               frozenset({"pdf"}),
        "inflacion componente":     frozenset({"xlsx"}),
        "inflacion subcomponente":  frozenset({"xlsx"}),
        "inflacion agrupacion":     frozenset({"xlsx"}),
        "SCIAN sector":             frozenset({"pdf"}),
        "SCIAN rama":               frozenset({"pdf"}),
        "durabilidad":              frozenset({"pdf"}),
        "canasta basica":           frozenset({"xlsx"}),
        "canasta consumo minimo":   frozenset({"xlsx"}),
    },
}
# fmt: on
