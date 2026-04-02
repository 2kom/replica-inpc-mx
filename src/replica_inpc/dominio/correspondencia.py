from __future__ import annotations

from replica_inpc.dominio.errores import CorrespondenciaInsuficiente
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada


def alinear_genericos(
    canasta: CanastaCanonica, serie: SerieNormalizada
) -> SerieNormalizada:
    """Verifica y alinea los genéricos de una serie al orden de la canasta.

    Esta función asume que `canasta.df.index` y `serie.df.index` ya fueron
    normalizados y pueden compararse por igualdad exacta, sin aplicar una
    normalización adicional.

    Args:
        canasta: Canasta canónica cuyo índice contiene los genéricos esperados.
        serie: Serie normalizada cuyos índices representan `generico_limpio` y
            cuyo `mapeo` conserva la trazabilidad hacia `generico_original`.

    Returns:
        Una `SerieNormalizada` filtrada a los genéricos de la canasta y
        reordenada para que su índice coincida exactamente con
        `canasta.df.index`. El `mapeo` resultante se filtra al mismo
        subconjunto de genéricos.

    Raises:
        CorrespondenciaInsuficiente: Si algún genérico de la canasta no está
            presente en `serie.df.index`.

    Example:
        Antes:
            canasta.df.index = ["arroz", "frijol", "leche"]
            serie.df.index = ["frijol", "arroz", "leche", "huevo"]

        Después:
            resultado.df.index = ["arroz", "frijol", "leche"]
            resultado.mapeo.keys() = ["arroz", "frijol", "leche"]

    Ver: docs/diseño.md §5.10, §11.2, §11.3
    """

    genericos_serie = set(serie.df.index)
    faltantes = [g for g in canasta.df.index if g not in genericos_serie]
    if faltantes:
        raise CorrespondenciaInsuficiente(faltantes)

    serie_filtrada = serie.df.loc[canasta.df.index]

    mapeo_reordenado = {
        llave: valor
        for llave, valor in serie.mapeo.items()
        if llave in serie_filtrada.index
    }

    return SerieNormalizada(serie_filtrada, mapeo_reordenado)
