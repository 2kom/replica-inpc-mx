from __future__ import annotations

from typing import Literal

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_CLASES_VALIDAS = {"periodica", "acumulada_anual", "desde"}


class ResultadoVariacion:
    def __init__(
        self,
        df: pd.DataFrame,
        tipo: str,
        descripcion: str,
        clase_variacion: Literal["periodica", "acumulada_anual", "desde"],
        indices_parciales: dict[str, PeriodoQuincenal | PeriodoMensual] | None = None,
        periodos_semiok: frozenset[PeriodoQuincenal | PeriodoMensual] | None = None,
    ) -> None:
        if df.empty:
            raise InvarianteViolado("El DataFrame de ResultadoVariacion no puede estar vacío.")
        if not isinstance(df.index, pd.MultiIndex) or list(df.index.names) != ["periodo", "indice"]:
            raise InvarianteViolado(
                "El índice debe ser MultiIndex con niveles ['periodo', 'indice']."
            )
        if "variacion" not in df.columns:
            raise InvarianteViolado("El DataFrame debe contener la columna 'variacion'.")
        if not tipo or not tipo.strip():
            raise InvarianteViolado("'tipo' no puede ser vacío.")
        if not descripcion or not descripcion.strip():
            raise InvarianteViolado("'descripcion' no puede ser vacía.")
        if clase_variacion not in _CLASES_VALIDAS:
            raise InvarianteViolado(
                f"'clase_variacion' debe ser uno de {sorted(_CLASES_VALIDAS)}, "
                f"se recibió '{clase_variacion}'."
            )

        self._df = df
        self._tipo = tipo
        self._descripcion = descripcion
        self._clase_variacion = clase_variacion
        self._indices_parciales = indices_parciales or {}
        self._periodos_semiok: frozenset[PeriodoQuincenal | PeriodoMensual] = (
            periodos_semiok or frozenset()
        )

    @property
    def tipo(self) -> str:
        return self._tipo

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def clase_variacion(self) -> str:
        return self._clase_variacion

    @property
    def periodos_semiok(self) -> frozenset[PeriodoQuincenal | PeriodoMensual]:
        return self._periodos_semiok

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def indices_parciales(self) -> dict[str, PeriodoQuincenal | PeriodoMensual]:
        return self._indices_parciales

    def como_tabla(self, ancho: bool = False, pct: bool = True) -> pd.DataFrame:
        df_out = self._df.copy()
        df_out["variacion"] = df_out["variacion"] * 100 if pct else df_out["variacion"]
        if not ancho:
            return df_out
        return df_out["variacion"].unstack(level="periodo")  # type: ignore[operator]

    def _repr_html_(self) -> str:
        header = f"<strong>{self._tipo} — {self._descripcion}</strong>"
        tabla = self.como_tabla(ancho=False, pct=True)._repr_html_()  # type: ignore[operator]
        parts = [header, tabla]
        if self._indices_parciales:
            items = "".join(
                f"<li><code>{idx}</code>: base ajustada a {periodo}</li>"
                for idx, periodo in sorted(self._indices_parciales.items())
            )
            parts.append(f"<p><em>Índices con base ajustada:</em><ul>{items}</ul></p>")
        return "".join(parts)
