from __future__ import annotations

from replica_inpc.dominio.errores import CorrespondenciaInsuficiente
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada


def alinear_genericos(
    canasta: CanastaCanonica, serie: SerieNormalizada
) -> SerieNormalizada:

    # la serie asi como la canasta tienen como indices los genericos y de esta manera verificamos si hay genericos en la canasta que no esten en la serie
    genericos_serie = set(serie.df.index)
    faltantes = [g for g in canasta.df.index if g not in genericos_serie]
    if faltantes:
        raise CorrespondenciaInsuficiente(faltantes)

    # filtra y reordena la serie
    # Ejemplo:
    # serie.df tiene filas: ["frijol", "arroz", "leche", "huevo"]
    # canasta.df.index es:  ["arroz", "frijol", "leche"]
    # serie.df.loc[canasta.df.index] -> ["arroz", "frijol", "leche"] (reordenado y filtrado)
    serie_filtrada = serie.df.loc[canasta.df.index]

    # reordenamos el mapeo de serie para que coincida con el orden de la serie filtrada
    # ejemplo:
    # serie.mapeo = {"Frijol": "frijol",
    #                "Arroz": "arroz",
    #                "Leche": "leche",
    #                "Huevo": "huevo"}
    # canasta.df.index es:  ["arroz", "frijol", "leche"]
    # mapeo_reordenado = {"Arroz": "arroz",
    #                     "Frijol": "frijol",
    #                     "Leche": "leche"}
    mapeo_reordenado = {
        llave: valor
        for llave, valor in serie.mapeo.items()
        if valor in serie_filtrada.index
    }

    return SerieNormalizada(serie_filtrada, mapeo_reordenado)
