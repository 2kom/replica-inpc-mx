from __future__ import annotations

from typing import Protocol

import pandas as pd


class AlmacenArtefactos(Protocol):
    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None: ...

    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame: ...
