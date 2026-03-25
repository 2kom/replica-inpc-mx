from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import Periodo


class SerieNormalizada:
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
        return self._mapeo

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
