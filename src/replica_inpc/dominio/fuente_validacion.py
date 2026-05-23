from __future__ import annotations

from typing import Literal, Protocol

from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_Periodo = PeriodoQuincenal | PeriodoMensual


class FuenteValidacion(Protocol):
    """Contrato para obtener series publicadas por INEGI para validación.

    Cubre tres tipos de dato: niveles de índice, variaciones e incidencias.
    El `tipo` (`"inpc"`, `"inflacion componente"`, `"inflacion subcomponente"`)
    se fija en el constructor del implementador, no en el método.

    Implementado por `infraestructura/inegi/fuente_validacion_api.py`
    (`FuenteValidacionApi`). Usado por `dominio/validacion/`.

    Esquema de retorno compartido — `dict[str, dict[Periodo, float | None]]`:

    - clave exterior: nombre del índice (`"INPC"`, `"subyacente"`, ...).
    - clave interior: el `Periodo` consultado.
    - valor `float`: valor publicado por INEGI.
    - valor `None`: INEGI tiene el periodo en rango pero sin dato.
    - periodo ausente del dict interior: anterior al inicio del histórico INEGI.

    Errores comunes a los tres métodos:

    - `len(periodos) == 0` → `InvarianteViolado`.
    - `tipo`/`tipo_variacion`/`tipo_incidencia` sin indicador INEGI →
      `ErrorConfiguracion`.
    - API no responde / HTTP error → `FuenteNoDisponible`.
    - respuesta INEGI con formato inesperado → `RespuestaInvalida`.
    """

    def obtener_indices(
        self,
        periodos: list[_Periodo],
    ) -> dict[str, dict[_Periodo, float | None]]:
        """Niveles de índice publicados por INEGI (series BIE de nivel).

        `periodos` es una lista homogénea; la frecuencia (quincenal o mensual)
        se detecta por `type(periodos[0])`.
        """
        ...

    def obtener_variaciones(
        self,
        periodos: list[_Periodo],
        tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    ) -> dict[str, dict[_Periodo, float | None]]:
        """Series de variación publicadas por INEGI.

        `periodos` homogénea (quincenal o mensual); `tipo_variacion` selecciona
        la clase de variación.
        """
        ...

    def obtener_incidencias(
        self,
        periodos: list[PeriodoMensual],
        tipo_incidencia: Literal["periodica"],
    ) -> dict[str, dict[PeriodoMensual, float | None]]:
        """Series de incidencia publicadas por INEGI.

        Solo mensuales — INEGI no publica incidencias quincenales.
        """
        ...
