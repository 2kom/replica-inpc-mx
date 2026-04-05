from dataclasses import dataclass
from typing import Literal

VersionCanasta = Literal[2010, 2013, 2018, 2024]

COLUMNAS_FIJAS: list[str] = [
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
]

# Fuente de cada columna por versión: "xlsx", "pdf", "sync", o None (vacía)
FUENTES: dict[int, dict[str, str | None]] = {
    2010: {
        "generico": "xlsx",
        "ponderador": "xlsx",
        "encadenamiento": None,
        "COG": "xlsx",
        "CCIF division": "pdf",
        "CCIF grupo": "pdf",
        "CCIF clase": "pdf",
        "inflacion componente": "xlsx",
        "inflacion subcomponente": "xlsx",
        "inflacion agrupacion": "xlsx",
        "SCIAN sector": "sync",
        "SCIAN rama": "sync",
        "durabilidad": None,
        "canasta basica": "xlsx",
        "canasta consumo minimo": None,
    },
    2013: {
        "generico": "xlsx",
        "ponderador": "xlsx",
        "encadenamiento": "xlsx",
        "COG": "xlsx",
        "CCIF division": "xlsx",
        "CCIF grupo": "pdf",
        "CCIF clase": "pdf",
        "inflacion componente": "xlsx",
        "inflacion subcomponente": "xlsx",
        "inflacion agrupacion": "xlsx",
        "SCIAN sector": "pdf",
        "SCIAN rama": "pdf",
        "durabilidad": None,
        "canasta basica": "xlsx",
        "canasta consumo minimo": None,
    },
    2018: {
        "generico": "xlsx",
        "ponderador": "xlsx",
        "encadenamiento": None,
        "COG": "xlsx",
        "CCIF division": "xlsx",
        "CCIF grupo": "pdf",
        "CCIF clase": "pdf",
        "inflacion componente": "xlsx",
        "inflacion subcomponente": "xlsx",
        "inflacion agrupacion": "xlsx",
        "SCIAN sector": "pdf",
        "SCIAN rama": "pdf",
        "durabilidad": "pdf",
        "canasta basica": "xlsx",
        "canasta consumo minimo": None,
    },
    2024: {
        "generico": "xlsx",
        "ponderador": "xlsx",
        "encadenamiento": "xlsx",
        "COG": "xlsx",
        "CCIF division": "xlsx",
        "CCIF grupo": "pdf",
        "CCIF clase": "pdf",
        "inflacion componente": "xlsx",
        "inflacion subcomponente": "xlsx",
        "inflacion agrupacion": "xlsx",
        "SCIAN sector": "pdf",
        "SCIAN rama": "pdf",
        "durabilidad": "pdf",
        "canasta basica": "xlsx",
        "canasta consumo minimo": "xlsx",
    },
}

@dataclass(frozen=True)
class LayoutXlsx:
    """Posiciones de columnas y hojas para cada versión de xlsx."""

    hoja_cog: str
    hoja_ccif: str | None
    col_concepto_agg: int  # columna con nombres de grupo (COG o CCIF division)
    col_concepto_gen: int  # columna con nombres de genérico
    col_ponderador: int
    col_encadenamiento: int | None
    col_canasta_basica: int
    col_canasta_consumo_minimo: int | None
    # Columnas hoja (leaf) de agrupación: col → (componente, subcomponente, agrupación)
    agrupaciones: dict[int, tuple[str, str, str]]


# fmt: off
LAYOUTS_XLSX: dict[int, LayoutXlsx] = {
    2010: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI",
        hoja_ccif=None,
        col_concepto_agg=1, col_concepto_gen=2,
        col_ponderador=3, col_encadenamiento=None,
        col_canasta_basica=19, col_canasta_consumo_minimo=None,
        agrupaciones={
            6:  ("subyacente", "mercancias", "alimentos, bebidas y tabaco"),
            7:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            9:  ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            11: ("subyacente", "servicios", "educacion"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        },
    ),
    2013: LayoutXlsx(
        hoja_cog="Ponderadores INPC INEGI",
        hoja_ccif="Ponderadores INPC COICOP INEGI",
        col_concepto_agg=1, col_concepto_gen=2,
        col_ponderador=3, col_encadenamiento=4,
        col_canasta_basica=20, col_canasta_consumo_minimo=None,
        agrupaciones={
            7:  ("subyacente", "mercancias", "alimentos, bebidas y tabaco"),
            8:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            12: ("subyacente", "servicios", "educacion"),
            15: ("no subyacente", "agropecuarios", "frutas y verduras"),
            16: ("no subyacente", "agropecuarios", "pecuarios"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            19: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        },
    ),
    2018: LayoutXlsx(
        hoja_cog="Objeto de gasto",
        hoja_ccif="CCIF",
        col_concepto_agg=1, col_concepto_gen=1,
        col_ponderador=2, col_encadenamiento=None,
        col_canasta_basica=19, col_canasta_consumo_minimo=None,
        agrupaciones={
            5:  ("subyacente", "mercancias", "alimentos, bebidas y tabaco"),
            6:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            8:  ("subyacente", "servicios", "educacion (colegiaturas)"),
            9:  ("subyacente", "servicios", "vivienda"),
            10: ("subyacente", "servicios", "otros servicios"),
            13: ("no subyacente", "agropecuarios", "frutas y verduras"),
            14: ("no subyacente", "agropecuarios", "pecuarios"),
            16: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        },
    ),
    2024: LayoutXlsx(
        hoja_cog="Objeto de gasto",
        hoja_ccif="CCIF",
        col_concepto_agg=1, col_concepto_gen=1,
        col_ponderador=2, col_encadenamiento=3,
        col_canasta_basica=20, col_canasta_consumo_minimo=21,
        agrupaciones={
            6:  ("subyacente", "mercancias", "alimentos, bebidas y tabaco"),
            7:  ("subyacente", "mercancias", "mercancias no alimenticias"),
            9:  ("subyacente", "servicios", "educacion (colegiaturas)"),
            10: ("subyacente", "servicios", "vivienda"),
            11: ("subyacente", "servicios", "otros servicios"),
            14: ("no subyacente", "agropecuarios", "frutas y verduras"),
            15: ("no subyacente", "agropecuarios", "pecuarios"),
            17: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "energeticos"),
            18: ("no subyacente", "energeticos y tarifas autorizadas por el gobierno", "tarifas autorizadas por el gobierno"),
        },
    ),
}
# fmt: on


PRECISION_DECIMALES: dict[int, int] = {
    2010: 4,
    2013: 5,
    2018: 4,
    2024: 4,
}


def columnas_xlsx(version: int) -> list[str]:
    """Columnas que se extraen del xlsx para esta versión."""
    return [col for col, fuente in FUENTES[version].items() if fuente == "xlsx"]


def columnas_pdf(version: int) -> list[str]:
    """Columnas que se extraen del pdf para esta versión."""
    return [col for col, fuente in FUENTES[version].items() if fuente == "pdf"]
