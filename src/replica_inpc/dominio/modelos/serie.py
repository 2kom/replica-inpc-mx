from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import Periodo


class SerieNormalizada:
    """Representa una matriz de índices por genérico y periodo.

    Args:
        df: DataFrame en formato ancho con `generico_limpio` como índice,
            columnas `Periodo` y valores numéricos no negativos o `NaN`.
        mapeo: Correspondencia de trazabilidad `generico_limpio ->
            generico_original`. Si se omite, se usa un diccionario vacío.

    Raises:
        InvarianteViolado: Si el índice contiene duplicados o cadenas vacías,
            si no hay columnas, si alguna columna no es `Periodo` o si el
            DataFrame contiene valores negativos.

    Esquema del DataFrame:
        Índice (str): `generico_limpio`.
        Columnas (Periodo): una columna por quincena.
        Valores (float64/NaN): índice del genérico en cada periodo.

    Example:
        DataFrame interno:
        | generico_limpio | 2Q Jul 2018 | 1Q Ago 2018 | 2Q Ago 2018 |
        | :-------------- | :---------- | :---------- | :---------- |
        | arroz           | 100.0       | 101.0       | 102.0       |
        | frijol          | 100.0       | 102.0       | 104.0       |
        | leche           | 100.0       | NaN         | 106.0       |

        Trazabilidad (`generico_limpio -> generico_original`):
        | generico_limpio | generico_original |
        | :-------------- | :---------------- |
        | arroz           | Arroz             |
        | frijol          | Frijol            |
        | leche           | Leche             |

        `NaN` indica que no hubo índice disponible para un genérico en ese
        periodo.

    Ver: docs/diseño.md §5.2, §11.1, §11.2
    """

    def __init__(self, df: pd.DataFrame, mapeo: dict[str, str] | None = None) -> None:
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El índice del DataFrame no puede contener valores duplicados."
            )
        if (df.index == "").any():
            raise InvarianteViolado(
                "El índice del DataFrame no puede contener cadenas vacías."
            )
        if len(df.columns) == 0:
            raise InvarianteViolado("El DataFrame debe tener al menos una columna.")
        if not all(isinstance(col, Periodo) for col in df.columns):
            raise InvarianteViolado(
                "Las columnas del DataFrame deben ser del tipo Periodo."
            )

        if (df < 0).any().any():
            raise InvarianteViolado(
                "Los valores del DataFrame no pueden ser negativos."
            )

        self._df = df
        self._mapeo = mapeo or {}

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def mapeo(self) -> dict[str, str]:
        """Devuelve la trazabilidad `generico_limpio -> generico_original`."""
        return self._mapeo

    def _repr_html_(self) -> str:
        """Renderiza la serie como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]
