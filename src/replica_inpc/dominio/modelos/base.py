from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class Vista:
    def __init__(self, df: pd.DataFrame, columnas: list[str]) -> None:
        self._df = df
        self._columnas = columnas

    @property
    def largo(self) -> pd.DataFrame:
        return self._df

    @property
    def ancho(self) -> pd.DataFrame:
        if len(self._columnas) == 1:
            return self._df[self._columnas[0]].unstack("periodo")
        return self._df[self._columnas].stack().unstack("periodo")

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]


class Resultado(ABC):
    def __init__(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise InvarianteViolado("Resultado.df no puede estar vacío")
        if (
            not isinstance(df.index, pd.MultiIndex)
            or df.index.nlevels != 2
            or list(df.index.names) != ["periodo", "indice"]
        ):
            raise InvarianteViolado(
                "Resultado.df requiere MultiIndex exacto con niveles ('periodo', 'indice')"
            )
        if df.shape[1] != 1:
            raise InvarianteViolado(
                "Resultado.df debe contener exactamente una columna calculada"
            )
        if df.index.duplicated().any():
            raise InvarianteViolado("Resultado.df no puede tener índices duplicados")
        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    @abstractmethod
    def resultado(self) -> Vista: ...

    @property
    @abstractmethod
    def resumen(self) -> pd.DataFrame: ...

    @property
    @abstractmethod
    def reporte(self) -> pd.DataFrame: ...

    @property
    @abstractmethod
    def diagnostico(self) -> pd.DataFrame: ...

    @abstractmethod
    def _repr_html_(self) -> str: ...

    def pipe(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(self, *args, **kwargs)


class Validacion(ABC):
    @property
    @abstractmethod
    def resultado(self) -> Vista: ...

    @property
    @abstractmethod
    def resumen(self) -> pd.DataFrame: ...

    @property
    @abstractmethod
    def reporte(self) -> pd.DataFrame: ...

    @property
    @abstractmethod
    def diagnostico(self) -> pd.DataFrame: ...

    @abstractmethod
    def _repr_html_(self) -> str: ...
