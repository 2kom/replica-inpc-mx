from __future__ import annotations

import pandas as pd


class ResumenValidacion:
    def __init__(self, df: pd.DataFrame) -> None:

        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
