from __future__ import annotations

import numpy as np
import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoQuincenal


class SerieNormalizada:
    """Representa una matriz de índices por genérico y periodo.

    Args:
        df: DataFrame en formato ancho con `generico` como índice,
            columnas `PeriodoQuincenal` y valores numéricos finitos no
            negativos o `NaN`.

    Raises:
        InvarianteViolado: Si el índice contiene duplicados o cadenas vacías,
            si no hay columnas, si alguna columna no es `PeriodoQuincenal`, si
            hay columnas de periodo duplicadas, si el DataFrame contiene
            valores negativos, o si contiene valores no finitos (`inf`/`-inf`).

    Esquema del DataFrame:
        Índice (str): `generico`.
        Columnas (PeriodoQuincenal): una columna por quincena.
        Valores (float64/NaN): índice del genérico en cada periodo.

    Example:
        DataFrame interno:
        | generico        | 2Q Jul 2018 | 1Q Ago 2018 | 2Q Ago 2018 |
        | :-------------- | :---------- | :---------- | :---------- |
        | arroz           | 100.0       | 101.0       | 102.0       |
        | frijol          | 100.0       | 102.0       | 104.0       |
        | leche           | 100.0       | NaN         | 106.0       |

        `NaN` indica que no hubo índice disponible para un genérico en ese
        periodo.

    Ver: docs/diseño.md §5.4, §11.1
    """

    def __init__(self, df: pd.DataFrame) -> None:
        if df.index.duplicated().any():
            raise InvarianteViolado("El índice del DataFrame no puede contener valores duplicados.")
        if (df.index == "").any():
            raise InvarianteViolado("El índice del DataFrame no puede contener cadenas vacías.")
        if len(df.columns) == 0:
            raise InvarianteViolado("El DataFrame debe tener al menos una columna.")
        if not all(isinstance(col, PeriodoQuincenal) for col in df.columns):
            raise InvarianteViolado(
                "Las columnas del DataFrame deben ser del tipo PeriodoQuincenal."
            )
        if df.columns.duplicated().any():
            raise InvarianteViolado(
                "Las columnas del DataFrame no pueden contener periodos duplicados."
            )

        if (df < 0).any().any():
            raise InvarianteViolado("Los valores del DataFrame no pueden ser negativos.")
        if not (df.isna() | np.isfinite(df.astype(float))).all().all():
            raise InvarianteViolado("Los valores del DataFrame deben ser finitos o NaN (no ±inf).")

        # Orden cronológico explícito: el relleno bfill/ffill de calculo/base.py opera
        # por posición física de columna, no por valor — columnas desordenadas
        # propagarían el dato del vecino físico equivocado en vez del cronológico.
        self._df = df.sort_index(axis=1)

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        """Renderiza la serie como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]
