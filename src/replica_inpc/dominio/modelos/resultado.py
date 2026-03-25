from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class ResultadoCalculo:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None:

        if df.empty:
            raise InvarianteViolado("El DataFrame de resultados no puede estar vacío.")
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El DataFrame de resultados no puede tener índices duplicados."
            )
        if not df["estado_calculo"].isin({"ok", "null_por_faltantes", "fallida"}).all():
            raise InvarianteViolado("estado_calculo contiene valores invalidos.")

        filas_ok = df["estado_calculo"] == "ok"
        if df.loc[filas_ok, "inpc_replicado"].isnull().any():
            raise InvarianteViolado(
                "inpc_replicado no puede ser null cuando estado_calculo es 'ok'."
            )

        filas_fallo = df["estado_calculo"] != "ok"
        if df.loc[filas_fallo, "inpc_replicado"].notnull().any():
            raise InvarianteViolado(
                "inpc_replicado debe ser null cuando estado_calculo no es 'ok'."
            )

        self._df = df
        self._id_corrida = id_corrida

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def id_corrida(self) -> str:
        return self._id_corrida

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
