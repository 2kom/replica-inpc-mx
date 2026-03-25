from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class CanastaCanonica:
    def __init__(self, df: pd.DataFrame, version: int) -> None:
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
        self._version = version

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def version(self) -> int:
        return self._version

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
