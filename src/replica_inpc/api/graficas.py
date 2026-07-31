"""Graficación de resultados."""

from __future__ import annotations

from replica_inpc.dominio.errores import PeriodoNoDisponible
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal, periodo_desde_str
from replica_inpc.infraestructura.graficacion.graficador import graficar_indice


def _periodos_disponibles(
    resultado: ResultadoIndice, comparacion: ResultadoIndice | None
) -> set[PeriodoQuincenal | PeriodoMensual]:
    periodos = set(resultado.resultado.largo.index.get_level_values("periodo"))
    if comparacion is not None:
        periodos |= set(comparacion.resultado.largo.index.get_level_values("periodo"))
    return periodos


def graficar(
    resultado: ResultadoIndice,
    comparacion: ResultadoIndice | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> None:
    """Grafica `resultado`; no devuelve nada, muestra la(s) imagen(es) directo.

    Cada `indice` distinto que trae `resultado` (ej. cada categoría de una
    clasificación como CCIF o SCIAN) se dibuja como su propia línea de
    color. Si `resultado` (+ `comparacion`) trae más de 8 categorías
    distintas sin contar INPC, se genera más de una imagen — cada una con
    máximo 8 líneas coloreadas, e INPC repetido completo en todas.

    Args:
        resultado: Resultado principal a graficar.
        comparacion: Un segundo `ResultadoIndice` opcional para superponer
            en el mismo panel (ej. INPC junto a una clasificación). Se
            dibuja con línea PUNTEADA para distinguirse de `resultado`
            (línea sólida) aunque comparta color — típicamente así se usa
            para INPC, que además siempre se dibuja por encima de las
            demás líneas, sea cual sea el parámetro por el que entre.
        desde: Periodo inicial del tramo a mostrar (ej. `"1Q Ene 2018"`,
            `"Ene 2018"` si es mensual) — recorta el eje X. Tiene que ser
            un periodo que exista de verdad en los datos de `resultado` o
            `comparacion`, no basta con que el texto tenga formato válido.
            `None` = desde el primer periodo disponible.
        hasta: Igual que `desde`, pero el límite final del tramo. `None` =
            hasta el último periodo disponible.

    Raises:
        PeriodoNoDisponible: `desde` o `hasta` no están presentes en los
            datos a graficar.
    """
    periodo_desde = periodo_desde_str(desde) if desde is not None else None
    periodo_hasta = periodo_desde_str(hasta) if hasta is not None else None

    if periodo_desde is not None or periodo_hasta is not None:
        disponibles = _periodos_disponibles(resultado, comparacion)
        for periodo, nombre in ((periodo_desde, "desde"), (periodo_hasta, "hasta")):
            if periodo is not None and periodo not in disponibles:
                raise PeriodoNoDisponible(
                    f"'{nombre}' ({periodo}) no está presente en los datos a graficar."
                )

    graficar_indice(resultado, comparacion, periodo_desde, periodo_hasta)
