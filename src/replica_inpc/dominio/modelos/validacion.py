from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class ResumenValidacion:
    def __init__(self, df: pd.DataFrame) -> None:

        if df.empty:
            raise InvarianteViolado(
                "El DataFrame de resumen de validación no puede estar vacío."
            )
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El DataFrame de resumen de validación no puede tener índices duplicados."
            )
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["estado_corrida"].isin({"ok", "parcial", "fallida"}).all():
            raise InvarianteViolado(
                "La columna 'estado_corrida' debe contener solo los valores 'ok', 'parcial' o 'fallida'."
            )
        if (
            not df["estado_validacion_global"]
            .isin({"ok", "diferencia_detectada", "no_disponible"})
            .all()
        ):
            raise InvarianteViolado(
                "La columna 'estado_validacion_global' debe contener solo los valores 'ok', 'diferencia_detectada' o 'no_disponible'."
            )
        if (df["total_periodos_calculados"] > df["total_periodos_esperados"]).any():
            raise InvarianteViolado(
                "La columna 'total_periodos_calculados' no puede tener más valores que 'total_periodos_esperados'."
            )
        if (df["total_periodos_con_null"] > df["total_periodos_calculados"]).any():
            raise InvarianteViolado(
                "La columna 'total_periodos_con_null' no puede tener más valores que 'total_periodos_calculados'."
            )

        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
