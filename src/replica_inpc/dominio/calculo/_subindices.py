from __future__ import annotations

from collections.abc import Iterator

import pandas as pd

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada


def grupos_por_clasificacion(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    tipo: str,
) -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Divide canasta y serie por categoría en un solo groupby.

    Yields (categoria, df_canasta_grupo, df_serie_grupo) para cada categoría
    única no vacía de canasta.df[tipo]. Genéricos sin categoría se excluyen.
    Los DataFrames devueltos son vistas crudas — no se construye CanastaCanonica
    por subgrupo ni se renormalizan los ponderadores.

    Ver: docs/diseño.md §5.8.3, §11.18
    """
    for categoria, df_grupo in canasta.df.groupby(tipo, dropna=True, sort=True):
        yield str(categoria), df_grupo, serie.df.loc[df_grupo.index]
