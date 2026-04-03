from __future__ import annotations

from typing import Protocol

import pandas as pd


class AlmacenArtefactos(Protocol):
    """Contrato para persistir artefactos computados del pipeline.

    Implementado por `AlmacenArtefactosFs`.

    Opera sobre DataFrames genéricos para guardar y recuperar `resultado`,
    `resumen`, `reporte` y `diagnostico` sin acoplarse al tipo concreto del
    artefacto.

    Ver: docs/diseño.md §7.1.6, §8.4
    """

    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None:
        """Guarda el DataFrame de un artefacto identificado por `nombre`."""
        ...

    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame:
        """Recupera el DataFrame persistido para el artefacto solicitado."""
        ...
