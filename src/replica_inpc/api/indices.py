"""Cálculo y transformaciones de índices."""

from __future__ import annotations

from replica_inpc.aplicacion.casos_uso.calcular_historia import BASE_ENCADENADA as _ENCADENADAS
from replica_inpc.aplicacion.casos_uso.calcular_historia import (
    referencias_normalizadas as _referencias_normalizadas,
)
from replica_inpc.dominio.calculo.estrategia import para_canasta as _para_canasta
from replica_inpc.dominio.conversion import a_mensual as _a_mensual
from replica_inpc.dominio.conversion import empalmar as _empalmar
from replica_inpc.dominio.conversion import rebasar as _rebasar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import periodo_desde_str
from replica_inpc.dominio.tipos import VersionCanasta


def calcular_indice(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    tipo: str,
    referencia: ResultadoIndice | None = None,
) -> ResultadoIndice:
    """Calcula el índice de un tramo de canasta.

    `canasta` y `serie` deben ser de la misma versión: la serie tiene que traer
    todos los genéricos que `tipo` usa de la canasta. Con `tipo="INPC"` son
    todos; con una clasificación, solo los que tienen valor en esa columna.

    `referencia` es el resultado del tramo anterior y **afecta el número en las
    cuatro versiones**, no solo en las encadenadas. En 2013 y 2024 es obligatoria
    porque su calculador encadena contra la canasta previa. En 2010 y 2018 es
    opcional, y pasarla no es inocuo: reexpresa el tramo en la escala del
    resultado anterior en vez de anclarlo en 100 en su propio periodo de
    traslape. Así es como `calcular_historia` pone el tramo 2018 en la escala de
    la cadena 2010-2013. Omitirla en una versión base da un tramo de escala
    propia, que es lo que se quiere si se piensa rebasar a mano después.

    Args:
        canasta: canasta ya cargada; su atributo `version` decide el calculador.
        serie: serie de la misma versión que `canasta`.
        tipo: `"INPC"` o una columna de clasificación (`"COG"`,
            `"DURABILIDAD"`, ...). Se normaliza a mayúsculas.
        referencia: resultado del tramo anterior.

    Raises:
        InvarianteViolado: la versión es encadenada y falta `referencia`; `tipo`
            no es válido; o `tipo` es una clasificación sin datos en esta
            canasta.
        ErrorCalculo: a la serie le faltan genéricos que `tipo` necesita — suele
            ser canasta y serie de versiones distintas.
        CanastaSinGenericos: la canasta no tiene genéricos utilizables.
        PonderadorFaltante: falta un ponderador necesario para el cálculo.

    Ver: docs/diseño.md §6.3
    """
    tipo = tipo.upper()
    if canasta.version in _ENCADENADAS and referencia is None:
        raise InvarianteViolado(
            f"la versión {canasta.version} es encadenada y requiere `referencia` "
            f"(el ResultadoIndice del tramo anterior)."
        )

    referencias: dict[str, float] | None = None
    if referencia is not None:
        version_origen = max(m.version for m in referencia.manifiesto)
        referencias = _referencias_normalizadas(referencia, tipo, version_origen, canasta.version)

    return _para_canasta(canasta, referencias).calcular(canasta, serie, tipo)


def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: VersionCanasta | None = None,
) -> ResultadoIndice:
    """Une tramos de índice del mismo tipo en orden cronológico.

    Los tramos se ordenan solos por periodo mínimo. Cada par vecino debe
    compartir exactamente un periodo —la frontera— y los pares no vecinos
    ninguno. En la frontera manda el tramo anterior, salvo para un índice que
    solo exista en el posterior.

    Args:
        resultados: al menos dos tramos, todos del mismo `tipo`.
        forzar: permite empalmar cuando un tramo llega con una base que no es la
            frontera, o sea con la escala cortada ahí. Emite `UserWarning` en vez
            de fallar. Los tramos recién calculados tienen `periodo_referencia`
            en `None` y no necesitan esto; hace falta al empalmar algo ya
            rebasado.
        version_nombres: versión cuyo vocabulario de categorías se usa en la
            salida. Por defecto, la más reciente de los tramos.

    Raises:
        InvarianteViolado: hay menos de dos tramos, mezclan `tipo`, la topología
            de fronteras no cierra, `version_nombres` cae fuera del rango de los
            tramos, o un tramo trae una base distinta de la frontera sin
            `forzar`.

    Ver: docs/diseño.md §6.3
    """
    return _empalmar(resultados, forzar=forzar, version_nombres=version_nombres)


def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: str,
    valor_referencia: float = 100.0,
) -> ResultadoIndice:
    """Reexpresa los índices a una nueva referencia.

    Divide toda la serie entre el valor del periodo elegido y la multiplica por
    `valor_referencia`, así que ese periodo pasa a valer exactamente eso. No toca
    la columna interna que alimenta las incidencias, así que las incidencias
    within-canasta no cambian al rebasar.

    Args:
        resultado: índice a reexpresar; puede ser quincenal o mensual.
        periodo_referencia: `"2Q Jul 2018"` para una quincena, `"Jul 2018"` para
            un mes. La periodicidad debe coincidir con la de `resultado`.
        valor_referencia: cuánto valdrá ese periodo. 100.0 por convención.

    Raises:
        PeriodoNoInterpretable: el texto no es un periodo reconocible.
        InvarianteViolado: el periodo no existe en el resultado, su periodicidad
            no coincide con la del resultado, o su valor no sirve como divisor.

    Ver: docs/diseño.md §6.3
    """
    return _rebasar(resultado, periodo_desde_str(periodo_referencia), valor_referencia)


def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
    """Convierte un resultado quincenal a mensual (promedio simple de 1Q y 2Q).

    `periodo_referencia` se propaga **sin convertir**: una serie mensual conserva
    la quincena como ancla, igual que el INPC mensual publicado conserva su base
    quincenal. Por eso no se garantiza que el mes que contiene al ancla valga
    100 — es el promedio de sus dos quincenas. Para anclar un mes en 100, llamar
    `a_mensual` primero y `rebasar` después con un periodo mensual.

    Un mes con una sola quincena disponible se calcula igual y queda marcado
    `parcial` en el reporte; no es un fallo.

    Empalmar tramos ya mensualizados emite `UserWarning`: el orden correcto es
    `a_mensual(empalmar([...]))`.

    Ver: docs/diseño.md §6.3
    """
    return _a_mensual(resultado)
