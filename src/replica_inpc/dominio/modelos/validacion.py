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


class ReporteDetalladoValidacion:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None:
        if df.empty:
            raise InvarianteViolado(
                "El DataFrame del reporte detallado de validación no puede estar vacío."
            )
        if df.index.duplicated().any():
            raise InvarianteViolado("El índice no puede tener valores duplicados.")
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["estado_calculo"].isin({"ok", "null_por_faltantes", "fallida"}).all():
            raise InvarianteViolado(
                "La columna 'estado_calculo' debe contener solo los valores 'ok', 'null_por_faltantes' o 'fallida'."
            )
        if (
            not df["estado_validacion"]
            .isin({"ok", "diferencia_detectada", "no_disponible"})
            .all()
        ):
            raise InvarianteViolado(
                "La columna 'estado_validacion' debe contener solo los valores 'ok', 'diferencia_detectada' o 'no_disponible'."
            )

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


class DiagnosticoFaltantes:
    def __init__(self, df: pd.DataFrame) -> None:
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["nivel_faltante"].isin({"periodo", "estructural"}).all():
            raise InvarianteViolado(
                "La columna 'nivel_faltante' debe contener solo los valores 'periodo' o 'estructural'."
            )
        if not df["tipo_faltante"].isin({"indice", "ponderador"}).all():
            raise InvarianteViolado(
                "La columna 'tipo_faltante' debe contener solo los valores 'indice' o 'ponderador'."
            )

        filas_indice = df["tipo_faltante"] == "indice"
        if df.loc[filas_indice, "periodo"].isnull().any():
            raise InvarianteViolado(
                "periodo no puede ser null cuando tipo_faltante es 'indice'."
            )

        filas_ponderador = df["tipo_faltante"] == "ponderador"
        if df.loc[filas_ponderador, "periodo"].notnull().any():
            raise InvarianteViolado(
                "periodo debe ser null cuando tipo_faltante es 'ponderador'."
            )

        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]
