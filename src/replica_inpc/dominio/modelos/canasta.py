from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.tipos import VersionCanasta


class CanastaCanonica:
    """Representa la canasta canónica usada para el cálculo del índice.

    Args:
        df: DataFrame con `generico` como índice y columnas según el esquema
            canónico de la canasta. Las columnas `ponderador` y
            `encadenamiento` se conservan como texto del archivo fuente.
        version: Versión base de la canasta. Debe ser 2010, 2013, 2018 o 2024.

    Raises:
        InvarianteViolado: Si la versión no es válida, si el índice contiene
            duplicados o cadenas vacías, si algún ponderador no es positivo, si
            la suma de ponderadores no es 100 o si algún encadenamiento no nulo
            no es positivo.

    Esquema del DataFrame (índice: `generico`):
        ponderador (object/str): texto decimal exacto del ponderador.
        encadenamiento (object/str/NaN): texto decimal exacto o `NaN` cuando no aplica.
        COG (object/str): clasificacion por objeto del gasto.
        CCIF division (object/str): clasificacion de consumo por finalidades — division.
        CCIF grupo (object/str): clasificacion de consumo por finalidades — grupo.
        CCIF clase (object/str): clasificacion de consumo por finalidades — clase.
        inflacion componente (object/str): componente de inflacion.
        inflacion subcomponente (object/str): subcomponente de inflacion.
        inflacion agrupacion (object/str): agrupacion de inflacion.
        SCIAN sector (object/str): numero y nombre del sector, ej. "32 Industrias manufactureras".
        SCIAN rama (object/str): codigo y nombre de la rama, ej. "3241 Fabricacion de...".
        durabilidad (object/str): categoria de durabilidad; vacio cuando no aplica.
        canasta basica (object/str): "X" si pertenece, "" si no.
        canasta consumo minimo (object/str): "X" si pertenece, "" o null si no aplica.

    Example:
        DataFrame interno:
        | generico | ponderador | encadenamiento | COG       |
        | -------- | ---------: | -------------: | --------: |
        | arroz    | "10.0"     | NaN            | Legumbres |
        | frijol   | "20.0"     | NaN            | Legumbres |
        | leche    | "30.0"     | NaN            | Lácteos   |
        | huevo    | "40.0"     | NaN            | Avicolas? |

        Metadatos asociados:
        | atributo | valor |
        | -------- | ----- |
        | version  | 2018  |

        En este ejemplo, los ponderadores suman 100 y `encadenamiento` está
        vacío porque la estrategia aplicable es directa.

    Ver: docs/diseño.md §5.1, §11.5
    """

    def __init__(self, df: pd.DataFrame, version: VersionCanasta) -> None:
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El índice del DataFrame de la canasta no puede tener valores duplicados."
            )
        if version not in {2010, 2013, 2018, 2024}:
            raise InvarianteViolado(
                "La versión de la canasta debe ser 2010, 2013, 2018 o 2024."
            )
        if (df.index == "").any():
            raise InvarianteViolado(
                "El índice del DataFrame no puede contener cadenas vacías."
            )
        if not (df["ponderador"].astype(float) > 0).all():
            raise InvarianteViolado(
                "La columna 'ponderador' debe contener solo valores positivos."
            )
        if (
            abs(df["ponderador"].astype(float).sum() - 100) > 1e-5
        ):  # Permitir una pequeña tolerancia numérica
            raise InvarianteViolado("La suma de los ponderadores debe ser igual a 100.")
        if (
            df["encadenamiento"].notnull().any()
            and (df["encadenamiento"].astype(float) <= 0).any()
        ):
            raise InvarianteViolado(
                "La columna 'encadenamiento' debe contener solo valores positivos cuando no es nula."
            )

        self._df = df
        self._version: VersionCanasta = version

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def version(self) -> VersionCanasta:
        """Devuelve la versión base de la canasta."""
        return self._version

    def _repr_html_(self) -> str:
        """Renderiza la canasta como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]
