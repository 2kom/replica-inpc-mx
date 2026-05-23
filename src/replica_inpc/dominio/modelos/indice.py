from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Resultado, Vista
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestUnidad

_COLUMNAS_MINIMAS = {"version", "tipo", "indice_replicado", "estado_calculo"}
_ORDEN_SEVERIDAD = {"ok": 0, "rellenado": 1, "parcial": 2, "sin_datos": 3, "fallida": 4}
_ESTADOS_VALIDOS = frozenset(_ORDEN_SEVERIDAD)


class ResultadoIndice(Resultado):
    def __init__(
        self,
        df: pd.DataFrame,
        manifiesto: list[ManifestUnidad],
        reporte_df: pd.DataFrame,
        diagnostico_df: pd.DataFrame,
        periodo_referencia: PeriodoQuincenal | PeriodoMensual | None = None,
    ) -> None:
        if not manifiesto:
            raise InvarianteViolado("ResultadoIndice.manifiesto no puede estar vacío")
        faltantes = _COLUMNAS_MINIMAS - set(df.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ResultadoIndice.df requiere columnas mínimas {sorted(faltantes)}"
            )
        estados_invalidos = set(df["estado_calculo"].unique()) - _ESTADOS_VALIDOS
        if estados_invalidos:
            raise InvarianteViolado(
                f"ResultadoIndice.df.estado_calculo admite solo "
                f"{sorted(_ESTADOS_VALIDOS)}; recibió {sorted(estados_invalidos)}"
            )
        for m in manifiesto:
            if not ((df["version"] == m.version) & (df["tipo"] == m.tipo)).any():
                raise InvarianteViolado(
                    f"ManifestUnidad(id_corrida={m.id_corrida!r}, version={m.version}, "
                    f"tipo={m.tipo!r}) no tiene filas correspondientes en df"
                )
        super().__init__(df[["indice_replicado"]])
        self._df_completo = df
        self._manifiesto = manifiesto
        self._reporte_df = reporte_df
        self._diagnostico_df = diagnostico_df
        self._periodo_referencia = periodo_referencia

    @property
    def manifiesto(self) -> list[ManifestUnidad]:
        return self._manifiesto

    @property
    def periodo_referencia(self) -> PeriodoQuincenal | PeriodoMensual | None:
        return self._periodo_referencia

    @property
    def resultado(self) -> Vista:
        return Vista(self._df_completo, ["indice_replicado"])

    @property
    def reporte(self) -> pd.DataFrame:
        return self._reporte_df

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._diagnostico_df

    @property
    def resumen(self) -> pd.DataFrame:
        df = self._df_completo
        filas = []
        for m in self._manifiesto:
            mascara = (df["version"] == m.version) & (df["tipo"] == m.tipo)
            subset = df[mascara]
            estados = subset["estado_calculo"].unique()
            estado = max(estados, key=lambda e: _ORDEN_SEVERIDAD[e])
            periodos = subset.index.get_level_values("periodo")
            periodo_inicio = min(periodos)
            periodo_fin = max(periodos)
            filas.append(
                {
                    "id_corrida": m.id_corrida,
                    "version": m.version,
                    "tipo": m.tipo,
                    "estado_calculo": estado,
                    "periodo_inicio": periodo_inicio,
                    "periodo_fin": periodo_fin,
                }
            )
        return pd.DataFrame(filas).set_index("id_corrida")

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]
