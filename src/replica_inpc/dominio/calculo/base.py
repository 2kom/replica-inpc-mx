from __future__ import annotations

from abc import ABC, abstractmethod

from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.serie import SerieNormalizada


class CalculadorBase(ABC):
    @abstractmethod
    def calcular(
        self, canasta: CanastaCanonica, serie: SerieNormalizada, id_corrida: str
    ) -> ResultadoCalculo: ...
