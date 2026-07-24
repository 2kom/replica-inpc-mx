from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Validacion, Vista
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.tipos import INDICES_VALIDABLES

_COLS_VISTA_INDICE = ["indice_replicado", "indice_inegi", "error_absoluto", "estado_validacion"]
_COLS_VISTA_VARIACION = [
    "variacion_pp",
    "variacion_inegi_pp",
    "error_absoluto_pp",
    "estado_validacion",
]
_COLS_VISTA_INCIDENCIA = [
    "incidencia_pp",
    "incidencia_inegi_pp",
    "error_absoluto_pp",
    "estado_validacion",
]


class ValidacionIndice(Validacion):
    def __init__(
        self,
        resultado: ResultadoIndice,
        resultado_largo_df: pd.DataFrame,
        resumen_df: pd.DataFrame,
        reporte_df: pd.DataFrame,
        diagnostico_df: pd.DataFrame,
    ) -> None:
        invalidos = [m.tipo for m in resultado.manifiesto if m.tipo not in INDICES_VALIDABLES]
        if invalidos:
            raise InvarianteViolado(
                f"ValidacionIndice solo admite tipos en INDICES_VALIDABLES; "
                f"recibió {sorted(set(invalidos))}"
            )
        faltantes = set(_COLS_VISTA_INDICE) - set(resultado_largo_df.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ValidacionIndice.resultado_largo_df requiere {sorted(faltantes)}"
            )
        self._resultado = resultado
        self._resultado_largo_df = resultado_largo_df
        self._resumen_df = resumen_df
        self._reporte_df = reporte_df
        self._diagnostico_df = diagnostico_df

    @property
    def resultado(self) -> Vista:
        return Vista(self._resultado_largo_df, _COLS_VISTA_INDICE)

    @property
    def resumen(self) -> pd.DataFrame:
        return self._resumen_df

    @property
    def reporte(self) -> pd.DataFrame:
        return self._reporte_df

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._diagnostico_df

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]


class ValidacionVariacion(Validacion):
    def __init__(
        self,
        resultado: ResultadoVariacion,
        resultado_largo_df: pd.DataFrame,
        resumen_df: pd.DataFrame,
        reporte_df: pd.DataFrame,
        diagnostico_df: pd.DataFrame,
    ) -> None:
        if resultado.manifiesto.tipo not in INDICES_VALIDABLES:
            raise InvarianteViolado(
                f"ValidacionVariacion: tipo '{resultado.manifiesto.tipo}' no está en "
                f"INDICES_VALIDABLES"
            )
        faltantes = set(_COLS_VISTA_VARIACION) - set(resultado_largo_df.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ValidacionVariacion.resultado_largo_df requiere {sorted(faltantes)}"
            )
        self._resultado = resultado
        self._resultado_largo_df = resultado_largo_df
        self._resumen_df = resumen_df
        self._reporte_df = reporte_df
        self._diagnostico_df = diagnostico_df

    @property
    def resultado(self) -> Vista:
        return Vista(self._resultado_largo_df, _COLS_VISTA_VARIACION)

    @property
    def resumen(self) -> pd.DataFrame:
        return self._resumen_df

    @property
    def reporte(self) -> pd.DataFrame:
        return self._reporte_df

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._diagnostico_df

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]


class ValidacionIncidencia(Validacion):
    def __init__(
        self,
        resultado: ResultadoIncidencia,
        resultado_largo_df: pd.DataFrame,
        resumen_df: pd.DataFrame,
        reporte_df: pd.DataFrame,
        diagnostico_df: pd.DataFrame,
    ) -> None:
        if resultado.manifiesto.tipo not in INDICES_VALIDABLES:
            raise InvarianteViolado(
                f"ValidacionIncidencia: tipo '{resultado.manifiesto.tipo}' no está en "
                f"INDICES_VALIDABLES"
            )
        faltantes = set(_COLS_VISTA_INCIDENCIA) - set(resultado_largo_df.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ValidacionIncidencia.resultado_largo_df requiere {sorted(faltantes)}"
            )
        self._resultado = resultado
        self._resultado_largo_df = resultado_largo_df
        self._resumen_df = resumen_df
        self._reporte_df = reporte_df
        self._diagnostico_df = diagnostico_df

    @property
    def resultado(self) -> Vista:
        return Vista(self._resultado_largo_df, _COLS_VISTA_INCIDENCIA)

    @property
    def resumen(self) -> pd.DataFrame:
        return self._resumen_df

    @property
    def reporte(self) -> pd.DataFrame:
        return self._reporte_df

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._diagnostico_df

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]
