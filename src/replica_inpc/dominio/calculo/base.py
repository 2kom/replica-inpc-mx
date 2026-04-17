from __future__ import annotations

from abc import ABC, abstractmethod

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada


class CalculadorBase(ABC):
    """Contrato abstracto para las estrategias de cálculo del dominio.

    Este `ABC` define la interfaz común que implementan
    `LaspeyresDirecto` y `LaspeyresEncadenado`. La selección concreta de la
    estrategia ocurre fuera de esta clase, a partir de la canasta.

    Ver: docs/diseño.md §1.2, §5.8, §11.12
    """

    @abstractmethod
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        tipo: str,
    ) -> ResultadoCalculo:
        """Calcula el resultado del índice para una canasta y una serie dadas.

        Args:
            tipo: Tipo lógico del cálculo. Si está en `INDICE_POR_TIPO` calcula
                el índice agregado; si está en `COLUMNAS_CLASIFICACION` calcula
                un subíndice por cada categoría del clasificador.

        Returns:
            El resultado del cálculo con la estructura de `ResultadoCalculo`.

        Ver: docs/diseño.md §5.8, §11.18
        """
