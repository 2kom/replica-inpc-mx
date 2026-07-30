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
_COLUMNAS_MINIMAS = {"tipo", "clase_variacion", "variacion_pp", "estado_calculo"}
_ESTADOS_VALIDOS = frozenset({"ok", "parcial"})
_ORDEN_SEVERIDAD = {"ok": 0, "parcial": 1}


class ResultadoVariacion(Resultado):
    """Resultado de una variación (inflación) calculada sobre un `ResultadoIndice`.

    Args:
        df_resultado: DataFrame con MultiIndex `(periodo, indice)` — ver Esquema abajo.
        manifiesto: Proveniencia de la corrida (tipo, clase, descripción, fecha).
        df_reporte: DataFrame paralelo a `df_resultado` (mismo MultiIndex) con
            columnas de cobertura/calidad por fila.
        df_diagnostico: DataFrame plano de faltantes, esquema `DiagnosticoFaltantes`.
        indices_parciales: Solo cuando `clase_variacion == "desde"` — índices
            intermedios usados en el cálculo acumulado; `None` en el resto de clases.

    Raises:
        InvarianteViolado: Si `df_resultado` no trae las columnas mínimas
            (`tipo`, `clase_variacion`, `variacion_pp`, `estado_calculo`), si
            `clase_variacion` no es homogénea o no está en el catálogo válido,
            si `indices_parciales is not None` no coincide exactamente con
            `clase_variacion == "desde"`, si `manifiesto.clase`/`manifiesto.tipo`
            no coinciden con los de `df_resultado`, o si `estado_calculo` tiene
            valores fuera de `{ok, parcial}`.

    Esquema de `df_resultado` (MultiIndex: `(periodo, indice)`):
        tipo (str): tipo de índice sobre el que se calculó la variación.
        clase_variacion (str): periodicidad de la variación, ver catálogo en
            `_CLASES_VALIDAS` (ej. `periodica_mensual`, `acumulada_anual`, `desde`).
        variacion_pp (float): variación en puntos porcentuales.
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
                f"ResultadoVariacion.df_resultado requiere columnas {sorted(faltantes)}"
            )
        clases = set(df_resultado["clase_variacion"].unique())
        if len(clases) != 1:
            raise InvarianteViolado(
                "ResultadoVariacion.df_resultado.clase_variacion debe ser homogénea"
            )
        clase = clases.pop()
        if clase not in _CLASES_VALIDAS:
            raise InvarianteViolado(
                f"clase_variacion '{clase}' no está en {sorted(_CLASES_VALIDAS)}"
            )
        if (clase == "desde") != (indices_parciales is not None):
            raise InvarianteViolado("indices_parciales is not None ⇔ clase_variacion == 'desde'")
        if manifiesto.clase != clase:
            raise InvarianteViolado(
                f"manifiesto.clase='{manifiesto.clase}' no coincide con "
                f"df_resultado.clase_variacion='{clase}'"
            )
        tipos = set(df_resultado["tipo"].unique())
        if len(tipos) != 1:
            raise InvarianteViolado("ResultadoVariacion.df_resultado['tipo'] debe ser homogéneo")
        tipo_df = tipos.pop()
        if manifiesto.tipo != tipo_df:
            raise InvarianteViolado(
                f"manifiesto.tipo='{manifiesto.tipo}' no coincide con df_resultado['tipo']='{tipo_df}'"
            )
        estados_invalidos = set(df_resultado["estado_calculo"].unique()) - _ESTADOS_VALIDOS
        if estados_invalidos:
            raise InvarianteViolado(
                f"ResultadoVariacion.df_resultado.estado_calculo solo admite 'ok'/'parcial'; "
                f"recibió {sorted(estados_invalidos)}"
            )
        super().__init__(df_resultado[["variacion_pp"]])
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
        return Vista(self._df_resultado, ["variacion_pp"])

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
                    "clase_variacion": self._manifiesto.clase,
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
