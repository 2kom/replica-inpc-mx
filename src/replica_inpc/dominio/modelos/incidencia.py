from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Resultado, Vista
from replica_inpc.dominio.tipos import ManifestDerivado

_CLASES_VALIDAS = frozenset(
    {
        "periodica_quincenal",
        "periodica_mensual",
        "periodica_bimestral",
        "periodica_trimestral",
        "periodica_cuatrimestral",
        "periodica_semestral",
        "periodica_anual",
        "acumulada_anual",
        "desde",
    }
)
_COLUMNAS_MINIMAS = {"tipo", "clase_incidencia", "incidencia_pp", "estado_calculo"}
_ESTADOS_VALIDOS = frozenset({"ok", "parcial"})
_ORDEN_SEVERIDAD = {"ok": 0, "parcial": 1}


class ResultadoIncidencia(Resultado):
    def __init__(
        self,
        df: pd.DataFrame,
        manifiesto: ManifestDerivado,
        reporte_df: pd.DataFrame,
        diagnostico_df: pd.DataFrame,
        indices_parciales: pd.DataFrame | None = None,
    ) -> None:
        faltantes = _COLUMNAS_MINIMAS - set(df.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ResultadoIncidencia.df requiere columnas {sorted(faltantes)}"
            )
        clases = set(df["clase_incidencia"].unique())
        if len(clases) != 1:
            raise InvarianteViolado(
                "ResultadoIncidencia.df.clase_incidencia debe ser homogénea"
            )
        clase = clases.pop()
        if clase not in _CLASES_VALIDAS:
            raise InvarianteViolado(
                f"clase_incidencia '{clase}' no está en {sorted(_CLASES_VALIDAS)}"
            )
        if (clase == "desde") != (indices_parciales is not None):
            raise InvarianteViolado(
                "indices_parciales is not None ⇔ clase_incidencia == 'desde'"
            )
        if manifiesto.clase != clase:
            raise InvarianteViolado(
                f"manifiesto.clase='{manifiesto.clase}' no coincide con "
                f"df.clase_incidencia='{clase}'"
            )
        tipos = set(df["tipo"].unique())
        if len(tipos) != 1:
            raise InvarianteViolado("ResultadoIncidencia.df['tipo'] debe ser homogéneo")
        tipo_df = tipos.pop()
        if manifiesto.tipo != tipo_df:
            raise InvarianteViolado(
                f"manifiesto.tipo='{manifiesto.tipo}' no coincide con df['tipo']='{tipo_df}'"
            )
        estados_invalidos = set(df["estado_calculo"].unique()) - _ESTADOS_VALIDOS
        if estados_invalidos:
            raise InvarianteViolado(
                f"ResultadoIncidencia.df.estado_calculo solo admite 'ok'/'parcial'; "
                f"recibió {sorted(estados_invalidos)}"
            )
        super().__init__(df[["incidencia_pp"]])
        self._df_completo = df
        self._manifiesto = manifiesto
        self._reporte_df = reporte_df
        self._diagnostico_df = diagnostico_df
        self._indices_parciales = indices_parciales

    @property
    def manifiesto(self) -> ManifestDerivado:
        return self._manifiesto

    @property
    def resultado(self) -> Vista:
        return Vista(self._df_completo, ["incidencia_pp"])

    @property
    def reporte(self) -> pd.DataFrame:
        return self._reporte_df

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._diagnostico_df

    @property
    def indices_parciales(self) -> pd.DataFrame | None:
        return self._indices_parciales

    @property
    def resumen(self) -> pd.DataFrame:
        df = self._df_completo
        estados = df["estado_calculo"].unique()
        estado = max(estados, key=lambda e: _ORDEN_SEVERIDAD[e])
        periodos = df.index.get_level_values("periodo")
        return pd.DataFrame(
            [
                {
                    "tipo": self._manifiesto.tipo,
                    "clase_incidencia": self._manifiesto.clase,
                    "descripcion": self._manifiesto.descripcion,
                    "estado_calculo": estado,
                    "periodo_inicio": min(periodos),
                    "periodo_fin": max(periodos),
                }
            ]
        )

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]
