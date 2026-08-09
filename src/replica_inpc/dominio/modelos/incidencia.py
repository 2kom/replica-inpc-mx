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
    """Resultado de una incidencia calculada sobre un `ResultadoIndice` de INPC y clasificación.

    Args:
        df_resultado: DataFrame con MultiIndex `(periodo, indice)` — ver Esquema abajo.
        manifiesto: Proveniencia de la corrida (tipo, clase, descripción, fecha).
        df_reporte: DataFrame con el mismo MultiIndex `(periodo, indice)` y columnas
            de cobertura/calidad por fila; incluye `metodo_incidencia`
            (`{within, cross_segmentado, cross_visible, cross_sin_frontera}`) para
            todas las filas. Es un **superconjunto** de `df_resultado`: incluye las
            filas no computables que el largo omite — por eso las validaciones de
            derivados extraen de acá los periodos a consultar.
        df_diagnostico: DataFrame plano de faltantes, esquema `DiagnosticoFaltantes`.
        indices_parciales: Solo cuando `clase_incidencia == "desde"` — índices
            intermedios usados en el cálculo acumulado; `None` en el resto de clases.

    Raises:
        InvarianteViolado: Si `df_resultado` no trae las columnas mínimas
            (`tipo`, `clase_incidencia`, `incidencia_pp`, `estado_calculo`), si
            `clase_incidencia` no es homogénea o no está en el catálogo válido,
            si `indices_parciales is not None` no coincide exactamente con
            `clase_incidencia == "desde"`, si `manifiesto.clase`/`manifiesto.tipo`
            no coinciden con los de `df_resultado`, o si `estado_calculo` tiene
            valores fuera de `{ok, parcial}`.

    Esquema de `df_resultado` (MultiIndex: `(periodo, indice)`):
        tipo (str): tipo de índice de clasificación sobre el que se calculó la incidencia.
        clase_incidencia (str): periodicidad de la incidencia, ver catálogo en
            `_CLASES_VALIDAS` (ej. `periodica_mensual`, `acumulada_anual`, `desde`).
        incidencia_pp (float): incidencia en puntos porcentuales sobre el INPC.
        estado_calculo (str): `{ok, parcial}` — `parcial` cuando solo hay una
            quincena disponible en el periodo base o final.

    Ver: docs/diseño.md §5.8
    """

    def __init__(
        self,
        df_resultado: pd.DataFrame,
        manifiesto: ManifestDerivado,
        df_reporte: pd.DataFrame,
        df_diagnostico: pd.DataFrame,
        indices_parciales: pd.DataFrame | None = None,
    ) -> None:
        faltantes = _COLUMNAS_MINIMAS - set(df_resultado.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ResultadoIncidencia.df_resultado requiere columnas {sorted(faltantes)}"
            )
        clases = set(df_resultado["clase_incidencia"].unique())
        if len(clases) != 1:
            raise InvarianteViolado(
                "ResultadoIncidencia.df_resultado.clase_incidencia debe ser homogénea"
            )
        clase = clases.pop()
        if clase not in _CLASES_VALIDAS:
            raise InvarianteViolado(
                f"clase_incidencia '{clase}' no está en {sorted(_CLASES_VALIDAS)}"
            )
        if (clase == "desde") != (indices_parciales is not None):
            raise InvarianteViolado("indices_parciales is not None ⇔ clase_incidencia == 'desde'")
        if manifiesto.clase != clase:
            raise InvarianteViolado(
                f"manifiesto.clase='{manifiesto.clase}' no coincide con "
                f"df_resultado.clase_incidencia='{clase}'"
            )
        tipos = set(df_resultado["tipo"].unique())
        if len(tipos) != 1:
            raise InvarianteViolado("ResultadoIncidencia.df_resultado['tipo'] debe ser homogéneo")
        tipo_df = tipos.pop()
        if manifiesto.tipo != tipo_df:
            raise InvarianteViolado(
                f"manifiesto.tipo='{manifiesto.tipo}' no coincide con df_resultado['tipo']='{tipo_df}'"
            )
        estados_invalidos = set(df_resultado["estado_calculo"].unique()) - _ESTADOS_VALIDOS
        if estados_invalidos:
            raise InvarianteViolado(
                f"ResultadoIncidencia.df_resultado.estado_calculo solo admite 'ok'/'parcial'; "
                f"recibió {sorted(estados_invalidos)}"
            )
        super().__init__(df_resultado[["incidencia_pp"]])
        self._df_resultado = df_resultado
        self._manifiesto = manifiesto
        self._df_reporte = df_reporte
        self._df_diagnostico = df_diagnostico
        self._indices_parciales = indices_parciales

    @property
    def manifiesto(self) -> ManifestDerivado:
        return self._manifiesto

    @property
    def resultado(self) -> Vista:
        return Vista(self._df_resultado, ["incidencia_pp"])

    @property
    def reporte(self) -> pd.DataFrame:
        return self._df_reporte

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._df_diagnostico

    @property
    def indices_parciales(self) -> pd.DataFrame | None:
        return self._indices_parciales

    @property
    def resumen(self) -> pd.DataFrame:
        df = self._df_resultado
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
                    "fecha": self._manifiesto.fecha,
                }
            ]
        )

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]
