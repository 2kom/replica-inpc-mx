"""Graficación de resultados."""

from __future__ import annotations

from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.infraestructura.graficacion.graficador import graficar_indice


def graficar(resultado: ResultadoIndice) -> None:

    graficar_indice(resultado)
