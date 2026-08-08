"""Graficación de resultados."""

from __future__ import annotations

from replica_inpc.dominio.calculo._temporal import es_mensual
from replica_inpc.dominio.errores import InvarianteViolado, PeriodoNoDisponible
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal, periodo_desde_str
from replica_inpc.infraestructura.graficacion.graficador import graficar as _graficar


def _periodos_disponibles(
    resultado: ResultadoIndice | ResultadoVariacion | ResultadoIncidencia,
    comparacion: ResultadoIndice | ResultadoVariacion | None,
) -> set[PeriodoQuincenal | PeriodoMensual]:
    """Periodos que pueden usarse como `desde`/`hasta`.

    En líneas cuenta la unión: `resultado` y `comparacion` se concatenan en un
    solo DataFrame y se dibujan en el mismo panel, así que un límite que solo
    exista en la comparación sigue recortando algo real.

    En incidencias NO: las barras y la línea se recortan por separado, y un
    límite que solo exista en la línea deja las barras vacías — una gráfica de
    incidencias sin barras no es una gráfica de incidencias. Ahí solo cuentan
    los periodos del resultado principal, y el error sale de acá con un
    mensaje sobre el parámetro en vez de un `InvarianteViolado` genérico desde
    el recorte.
    """
    periodos = set(resultado.resultado.largo.index.get_level_values("periodo"))
    if comparacion is not None and not isinstance(resultado, ResultadoIncidencia):
        periodos |= set(comparacion.resultado.largo.index.get_level_values("periodo"))
    return periodos


def graficar(
    resultado: ResultadoIndice | ResultadoVariacion | ResultadoIncidencia,
    comparacion: ResultadoIndice | ResultadoVariacion | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> None:
    """Grafica `resultado` (índice, variación o incidencia); no devuelve nada, muestra la(s) imagen(es) directo.

    Cada `indice` distinto que trae `resultado` (ej. cada categoría de una
    clasificación como CCIF o SCIAN) se dibuja como su propia línea de
    color. Si `resultado` (+ `comparacion`) trae más de 8 categorías
    distintas sin contar INPC, se genera más de una imagen — cada una con
    máximo 8 líneas coloreadas, e INPC repetido completo en todas. Si
    `resultado` es un `ResultadoVariacion`, el eje Y muestra `variacion_pp`
    con base en 0 en vez del índice con base 100.

    Un `ResultadoIncidencia` se dibuja distinto: barras apiladas por periodo,
    un segmento de color por categoría, positivas hacia arriba desde 0 y
    negativas hacia abajo. Pasando como `comparacion` la variación del INPC de
    la misma clase, esta se superpone como línea negra: marca el NETO de cada
    periodo, que coincide con el techo de la barra solo cuando todas las
    categorías son positivas.

    Con muchas categorías se generan varias imágenes, las que hagan falta para
    detallar las que concentran el 80% de la magnitud. En cada imagen, lo que
    esa imagen no detalla se dibuja igual, agregado en dos grises — así la
    barra sigue valiendo el total del periodo y la línea cierra en todas. El
    gris claro se detalla en otra imagen; el oscuro no se detalla en ninguna,
    porque su tamaño lo haría invisible contra un eje fijado por el total (en
    `SCIAN RAMA` la categoría más chica vale `0.0007` pp contra un eje que
    llega a `8.7`). Ambos grises aparecen en la leyenda con su nombre, y al pie
    va el alcance de la imagen: cuántas categorías detalla de cuántas hay, a la
    izquierda, y cuál de cuántas imágenes es, a la derecha. Para forzar el
    detalle de una categoría chica no hay parámetro — se ve en la gráfica de
    líneas, que particiona con un eje propio por imagen.

    Los puntos sobre la línea aparecen solo en dos casos: cuando el tramo
    graficado cabe en un año (25 periodos quincenales o 13 mensuales, contando
    ambos extremos), donde marcan cada observación real sin saturar; y, en
    cualquier tramo, sobre las series que aparecen en un único periodo — sin
    punto quedarían invisibles, porque una línea necesita al menos dos
    observaciones.

    Args:
        resultado: Resultado principal a graficar — `ResultadoIndice`,
            `ResultadoVariacion` o `ResultadoIncidencia`.
        comparacion: Un segundo resultado opcional, con la MISMA periodicidad
            que `resultado` (quincenal o mensual). Si algo de lo que sigue no
            se cumple, no se levanta excepción: se imprime un mensaje de error
            y no se dibuja nada.

            Para un `ResultadoIndice` o un `ResultadoVariacion` debe ser del
            MISMO tipo que `resultado`, y si ambos son `ResultadoVariacion`
            además deben compartir `clase_variacion` (ej. no se puede comparar
            una variación mensual contra una trimestral). Se superpone en el
            mismo panel (ej. INPC junto a una clasificación) con línea PUNTEADA
            para distinguirse de `resultado` (línea sólida) aunque comparta
            color — típicamente así se usa para INPC, que además siempre se
            dibuja por encima de las demás líneas, sea cual sea el parámetro
            por el que entre.

            Para un `ResultadoIncidencia` es el único caso donde el tipo NO
            coincide: se espera el `ResultadoVariacion` **del INPC** (`tipo`
            debe ser `"INPC"`, y la clase la misma que la incidencia), que es
            justo lo que las barras descomponen. Se dibuja como línea negra
            sobre ellas. Si con `desde`/`hasta` la comparación se queda sin
            datos en el tramo, la gráfica NO se cancela: se avisa y se dibujan
            las barras solas.
        desde: Periodo inicial del tramo a mostrar (ej. `"1Q Ene 2018"`,
            `"Ene 2018"` si es mensual) — recorta el eje X. Tiene que ser de
            la MISMA periodicidad que `resultado` y existir de verdad en los
            datos; no basta con que el texto tenga formato válido. Para
            índices y variaciones basta con que exista en `resultado` o en
            `comparacion`; para una incidencia tiene que existir en la
            incidencia misma, porque un límite que solo cubra la línea de
            referencia dejaría la gráfica sin barras. `None` = desde el
            primer periodo disponible.
        hasta: Igual que `desde`, pero el límite final del tramo. `None` =
            hasta el último periodo disponible.

    Raises:
        InvarianteViolado: `desde` o `hasta` son de otra periodicidad que
            `resultado` (ej. `"1Q Ene 2018"` contra un resultado mensual).
        PeriodoNoDisponible: `desde` o `hasta` son de la periodicidad
            correcta pero no están presentes en los datos a graficar.
    """
    periodo_desde = periodo_desde_str(desde) if desde is not None else None
    periodo_hasta = periodo_desde_str(hasta) if hasta is not None else None

    if periodo_desde is not None or periodo_hasta is not None:
        # La periodicidad se valida antes que la disponibilidad para no reportar
        # "no está presente" cuando el problema real es que un periodo quincenal
        # jamás podría estar en datos mensuales (ni al revés).
        mensual = es_mensual(resultado.resultado.largo)
        esperado = "mensual" if mensual else "quincenal"
        for periodo, nombre in ((periodo_desde, "desde"), (periodo_hasta, "hasta")):
            if periodo is not None and isinstance(periodo, PeriodoMensual) != mensual:
                recibido = "mensual" if isinstance(periodo, PeriodoMensual) else "quincenal"
                ejemplo = "Ene 2018" if mensual else "1Q Ene 2018"
                raise InvarianteViolado(
                    f"'{nombre}' ({periodo}) es {recibido}, pero resultado es {esperado}. "
                    f"Usa un periodo {esperado} (ej. '{ejemplo}')."
                )

        disponibles = _periodos_disponibles(resultado, comparacion)
        for periodo, nombre in ((periodo_desde, "desde"), (periodo_hasta, "hasta")):
            if periodo is not None and periodo not in disponibles:
                raise PeriodoNoDisponible(
                    f"'{nombre}' ({periodo}) no está presente en los datos a graficar."
                )

    _graficar(resultado, comparacion, periodo_desde, periodo_hasta)
