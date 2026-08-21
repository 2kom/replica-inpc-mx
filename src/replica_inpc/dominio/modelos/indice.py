from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.base import Resultado, Vista
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo

_COLUMNAS_MINIMAS = {"version", "tipo", "indice_replicado", "estado_calculo"}
_ORDEN_SEVERIDAD = {"ok": 0, "rellenado": 1, "parcial": 2, "sin_datos": 3, "fallida": 4}
_ESTADOS_VALIDOS = frozenset(_ORDEN_SEVERIDAD)


class ResultadoIndice(Resultado):
    """Resultado de un cálculo de índice elemental sobre una canasta, o de un empalme entre tramos.

    Args:
        df_resultado: DataFrame con MultiIndex `(periodo, indice)` — ver Esquema abajo.
        manifiesto: Un `ManifestCalculo` por corrida elemental que compone este
            resultado; `empalmar` concatena listas sin colapsar.
        df_reporte: DataFrame paralelo a `df_resultado` (mismo MultiIndex) con
            columnas de cobertura/calidad por fila.
        df_diagnostico: DataFrame plano, una fila por celda `(periodo, generico)`
            sin dato — esquema `DiagnosticoFaltantes`, no comparte índice con
            `df_resultado`.
        periodo_referencia: Ancla de escala — el periodo cuyo valor se fijó en
            `valor_base` (default 100) al rebasar, y respecto del cual está
            expresada toda la serie. `None` = resultado en escala natural del
            cálculo; lo setea `rebasar()`.

            No es necesariamente un periodo presente en el índice: `a_mensual`
            lo propaga sin convertir, así que una serie mensual rebasada en
            quincenal conserva la quincena como ancla, igual que el INPC mensual
            publicado conserva la base "2Q jul 2018 = 100". En ese caso no se
            garantiza que el mes que contiene al ancla valga 100 —es el promedio
            de sus dos quincenas—, y eso es correcto: el ancla describe la
            escala, no promete un valor en el eje.
        frontera: Anclas de junta de canasta para reconstrucción cross-canasta
            mensual. `None` en quincenal y en resultados directos sin
            junta; lo crea `a_mensual`.

    Raises:
        InvarianteViolado: Si `manifiesto` está vacío, si `df_resultado` no
            trae las columnas mínimas (`version`, `tipo`, `indice_replicado`,
            `estado_calculo`), si `estado_calculo` tiene valores fuera de
            `{ok, rellenado, parcial, sin_datos, fallida}`, o si algún
            `ManifestCalculo` no tiene fila correspondiente en `df_resultado`.

    Esquema de `df_resultado` (MultiIndex: `(periodo, indice)`):
        version (int): versión de canasta de la corrida.
        tipo (str): tipo de índice calculado (`"INPC"` o categoría de clasificación).
        indice_replicado (float): valor del índice; `NaN` si `estado_calculo`
            es `sin_datos` o `fallida`.
        indice_incidencia (float): columna interna, índice de-encadenado que
            preserva `Σ inc = var`; no se expone en ninguna vista pública, el
            motor de incidencias la lee vía `._completo`.
        estado_calculo (str): `{ok, rellenado, parcial, sin_datos, fallida}`.
        motivo_error (str | None): motivo cuando `estado_calculo` no es `ok`,
            `parcial` ni `rellenado`.

    Example:
        `.resumen`:
        | version_tipo | estado_calculo | periodo_inicio | periodo_fin |
        | ------------ | -------------- | -------------- | ----------- |
        | 2018:INPC    | ok             | 2Q Jul 2018    | 2Q Jun 2024 |

    Ver: docs/diseño.md §5.7
    """

    def __init__(
        self,
        df_resultado: pd.DataFrame,
        manifiesto: list[ManifestCalculo],
        df_reporte: pd.DataFrame,
        df_diagnostico: pd.DataFrame,
        periodo_referencia: PeriodoQuincenal | PeriodoMensual | None = None,
        frontera: pd.DataFrame | None = None,
    ) -> None:
        if not manifiesto:
            raise InvarianteViolado("ResultadoIndice.manifiesto no puede estar vacío")
        faltantes = _COLUMNAS_MINIMAS - set(df_resultado.columns)
        if faltantes:
            raise InvarianteViolado(
                f"ResultadoIndice.df_resultado requiere columnas mínimas {sorted(faltantes)}"
            )
        estados_invalidos = set(df_resultado["estado_calculo"].unique()) - _ESTADOS_VALIDOS
        if estados_invalidos:
            raise InvarianteViolado(
                f"ResultadoIndice.df_resultado.estado_calculo admite solo "
                f"{sorted(_ESTADOS_VALIDOS)}; recibió {sorted(estados_invalidos)}"
            )
        for m in manifiesto:
            if not (
                (df_resultado["version"] == m.version) & (df_resultado["tipo"] == m.tipo)
            ).any():
                raise InvarianteViolado(
                    f"ManifestCalculo(version={m.version}, tipo={m.tipo!r}) "
                    "no tiene filas correspondientes en df_resultado"
                )
        super().__init__(df_resultado[["indice_replicado"]])
        self._df_resultado = df_resultado
        self._manifiesto = manifiesto
        self._df_reporte = df_reporte
        self._df_diagnostico = df_diagnostico
        self._periodo_referencia = periodo_referencia
        # Anclas de junta de canasta para reconstrucción cross-canasta mensual.
        # `None` en quincenal y en resultados directos sin junta. Lo crea `a_mensual`.
        # Esquema: MultiIndex (periodo, indice); columnas
        # [version_old, version_new, indice_incidencia_old, indice_replicado_old].
        # INPC: una fila por junta (indice="INPC"), `indice_replicado_old`=INPC_visible(e).
        # Clasificación: una fila por (junta, categoría), `indice_replicado_old`=I_K_visible(e).
        # Lo que la frontera de clasificación NO guarda es INPC_visible(e) — ese vive solo en
        # la del INPC, porque `rebasar(clasificacion)` no conoce k_INPC (docs/diseño §11.23).
        self._frontera = frontera

    @property
    def manifiesto(self) -> list[ManifestCalculo]:
        return self._manifiesto

    @property
    def periodo_referencia(self) -> PeriodoQuincenal | PeriodoMensual | None:
        return self._periodo_referencia

    @property
    def resultado(self) -> Vista:
        # `indice_incidencia` es columna interna (la consume el motor de incidencias vía
        # `_completo`); no se expone en la vista pública.
        return Vista(
            self._df_resultado.drop(columns=["indice_incidencia"], errors="ignore"),
            ["indice_replicado"],
        )

    @property
    def _completo(self) -> pd.DataFrame:
        """Vista interna con todas las columnas, incl. `indice_incidencia`.

        Uso exclusivo del motor de incidencias (`calculo/incidencias.py`); no es API
        pública. `indice_incidencia` es el índice de-encadenado que preserva la
        aditividad `Σ inc = var`.
        """
        return self._df_resultado

    @property
    def reporte(self) -> pd.DataFrame:
        return self._df_reporte

    @property
    def diagnostico(self) -> pd.DataFrame:
        return self._df_diagnostico

    @property
    def resumen(self) -> pd.DataFrame:
        df = self._df_resultado
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
                    "version_tipo": f"{m.version}:{m.tipo}",
                    "estado_calculo": estado,
                    "periodo_inicio": periodo_inicio,
                    "periodo_fin": periodo_fin,
                    "fecha": m.fecha,
                }
            )
        return pd.DataFrame(filas).set_index("version_tipo")

    def _repr_html_(self) -> str:
        return self.resumen._repr_html_()  # type: ignore[operator]
