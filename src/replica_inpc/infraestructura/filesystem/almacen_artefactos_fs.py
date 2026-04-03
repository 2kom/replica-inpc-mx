from __future__ import annotations

from pathlib import Path

import pandas as pd

from replica_inpc.dominio.errores import ArtefactoNoEncontrado
from replica_inpc.dominio.periodos import Periodo


class AlmacenArtefactosFs:
    def __init__(self, ruta_base: Path) -> None:
        self._ruta_base = ruta_base

    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None:
        ruta_corrida = self._ruta_base / id_corrida
        ruta_corrida.mkdir(parents=True, exist_ok=True)
        _serializar_periodos(df).to_parquet(ruta_corrida / f"{nombre}.parquet")

    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame:
        ruta = self._ruta_base / id_corrida / f"{nombre}.parquet"
        if not ruta.exists():
            raise ArtefactoNoEncontrado(
                f"Artefacto '{nombre}' no encontrado para corrida '{id_corrida}'"
            )
        return pd.read_parquet(ruta)


def _serializar_periodos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if isinstance(df.index, pd.MultiIndex):
        arrays = [
            level.map(str) if any(isinstance(v, Periodo) for v in level) else level
            for level in (df.index.get_level_values(i) for i in range(df.index.nlevels))
        ]
        df.index = pd.MultiIndex.from_arrays(arrays, names=df.index.names)
    elif any(isinstance(v, Periodo) for v in df.index):
        df.index = df.index.map(str)

    for col in df.columns:
        if df[col].dtype == object:
            muestra = df[col].dropna()
            if (
                not muestra.empty
                and muestra.apply(lambda x: isinstance(x, Periodo)).any()
            ):
                df[col] = df[col].apply(
                    lambda x: str(x) if isinstance(x, Periodo) else x
                )

    return df
