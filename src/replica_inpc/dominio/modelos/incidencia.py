from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_CLASES_VALIDAS = {"periodica", "acumulada_anual", "desde"}


class ResultadoIncidencia:
    def __init__(
        self,
        df: pd.DataFrame,
        clase_incidencia: Literal["periodica", "acumulada_anual", "desde"],
        periodos_semiok: frozenset[PeriodoQuincenal | PeriodoMensual] | None = None,
    ) -> None:
        if df.empty:
            raise InvarianteViolado("El DataFrame de ResultadoIncidencia no puede estar vacío.")
        if not isinstance(df.index, pd.MultiIndex) or list(df.index.names) != ["periodo", "indice"]:
            raise InvarianteViolado(
                "El índice debe ser MultiIndex con niveles ['periodo', 'indice']."
            )
        if df.index.duplicated().any():
            raise InvarianteViolado("El índice de ResultadoIncidencia no puede tener duplicados.")
        if clase_incidencia not in _CLASES_VALIDAS:
            raise InvarianteViolado(
                f"'clase_incidencia' debe ser uno de {sorted(_CLASES_VALIDAS)}, "
                f"se recibió '{clase_incidencia}'."
            )
        pp_null = df["incidencia_pp"].isna()
        ec_null = df["estado_calculo"].isna()
        if not (pp_null == ec_null).all():
            raise InvarianteViolado(
                "incidencia_pp debe ser NaN si y solo si estado_calculo es NaN."
            )

        self._df = df
        self._clase_incidencia = clase_incidencia
        self._periodos_semiok: frozenset[PeriodoQuincenal | PeriodoMensual] = (
            periodos_semiok or frozenset()
        )

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def tipo(self) -> str:
        return str(self._df["tipo"].iloc[0])

    @property
    def frecuencia(self) -> str:
        return str(self._df["frecuencia"].iloc[0])

    @property
    def clase_incidencia(self) -> str:
        return self._clase_incidencia

    @property
    def periodos_semiok(self) -> frozenset[PeriodoQuincenal | PeriodoMensual]:
        return self._periodos_semiok

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame:
        if not ancho:
            return self._df
        return self._df["incidencia_pp"].unstack(level="periodo")  # type: ignore[operator]

    def _repr_html_(self) -> str:
        header = (
            f"<strong>{self.tipo} — incidencia {self._clase_incidencia}"
            f" ({self.frecuencia})</strong>"
        )
        return header + self.como_tabla()._repr_html_()  # type: ignore[operator]
