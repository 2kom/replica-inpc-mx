"""Caso de uso `CalcularHistoria`.

Orquesta carga, cálculo, empalme, conversión de frecuencia y rebase para
producir un `ResultadoIndice` histórico a partir de insumos por versión de
canasta. Reemplaza a `EjecutarCorrida` (v1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from replica_inpc.aplicacion.puertos.lector_canasta import LectorCanasta
from replica_inpc.aplicacion.puertos.lector_series import LectorSeries
from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.conversion import (
    _construir_mapa_renombre,
    a_mensual,
    empalmar,
    rebasar,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_VALIDOS, VersionCanasta

_ORDEN_VERSIONES: tuple[int, ...] = (2010, 2013, 2018, 2024)
# Cada versión encadenada requiere su versión base contigua en `insumos`.
_BASE_ENCADENADA: dict[int, int] = {2013: 2010, 2024: 2018}
_PERIODICIDADES = ("quincenal", "mensual")

_Periodo = PeriodoQuincenal | PeriodoMensual


def _referencias_normalizadas(
    resultado_prev: ResultadoIndice,
    tipo: str,
    version_origen: int,
    version_destino: int,
) -> dict[str, float]:
    """Referencias de empalme para `version_destino`, por índice.

    Extrae el `indice_replicado` del resultado de la versión anterior en el
    periodo de traslape de `version_destino`, y normaliza las claves al
    vocabulario de `version_destino` (vía `RENOMBRES_INDICES`) — el calculador
    encadenado busca la referencia con el nombre de la canasta actual.
    """
    traslape = RANGOS_VALIDOS[version_destino][0]  # type: ignore[index]
    mapa = _construir_mapa_renombre(tipo, version_origen, version_destino)
    df = resultado_prev.df
    refs: dict[str, float] = {}
    for indice in df.index.get_level_values("indice").unique():
        try:
            valor = df.loc[(traslape, indice), "indice_replicado"]  # type: ignore[index]
        except KeyError:
            continue
        if pd.isna(valor):
            continue
        refs[mapa.get(str(indice), str(indice))] = float(valor)  # type: ignore[arg-type]
    return refs


class CalcularHistoria:
    """Produce un `ResultadoIndice` histórico empalmado, rebased y en la
    periodicidad indicada."""

    def __init__(self, lector_canasta: LectorCanasta, lector_series: LectorSeries) -> None:
        self._lector_canasta = lector_canasta
        self._lector_series = lector_series

    def ejecutar(
        self,
        insumos: list[tuple[VersionCanasta, Path, Path]],
        tipo: str,
        periodo_referencia: _Periodo,
        periodicidad: Literal["quincenal", "mensual"],
    ) -> ResultadoIndice:
        self._validar(insumos, periodicidad)
        ordenados = sorted(insumos, key=lambda insumo: insumo[0])

        resultados: list[tuple[VersionCanasta, ResultadoIndice]] = []
        previo: ResultadoIndice | None = None
        for version, ruta_canasta, ruta_series in ordenados:
            canasta = self._lector_canasta.leer(ruta_canasta, version)
            serie = self._lector_series.leer(ruta_series)
            referencias: dict[str, float] | None = None
            if previo is not None:
                version_origen = max(m.version for m in previo.manifiesto)
                referencias = _referencias_normalizadas(previo, tipo, version_origen, version)
            resultado = para_canasta(canasta, referencias).calcular(
                canasta, serie, f"{tipo}:{version}", tipo, ruta_canasta, ruta_series
            )
            resultados.append((version, resultado))
            previo = resultado

        acc = resultados[0][1]
        for version, resultado in resultados[1:]:
            acc = empalmar([acc, resultado], forzar=True, version_nombres=version)

        ref_rebase = periodo_referencia
        if periodicidad == "mensual" and isinstance(periodo_referencia, PeriodoMensual):
            ref_rebase = PeriodoQuincenal(periodo_referencia.año, periodo_referencia.mes, 2)
        acc = rebasar(acc, ref_rebase)
        if periodicidad == "mensual":
            acc = a_mensual(acc)
        return acc

    @staticmethod
    def _validar(insumos: list[tuple[VersionCanasta, Path, Path]], periodicidad: str) -> None:
        if not insumos:
            raise InvarianteViolado("insumos no puede estar vacío.")
        if periodicidad not in _PERIODICIDADES:
            raise InvarianteViolado(
                f"periodicidad '{periodicidad}' inválida; usa {_PERIODICIDADES}."
            )

        versiones = [insumo[0] for insumo in insumos]
        if len(versiones) != len(set(versiones)):
            raise InvarianteViolado(f"insumos tiene versiones duplicadas: {sorted(versiones)}.")
        desconocidas = [v for v in versiones if v not in _ORDEN_VERSIONES]
        if desconocidas:
            raise InvarianteViolado(f"versiones fuera de {_ORDEN_VERSIONES}: {desconocidas}.")

        posiciones = sorted(_ORDEN_VERSIONES.index(v) for v in versiones)
        contiguas = list(range(posiciones[0], posiciones[0] + len(posiciones)))
        if posiciones != contiguas:
            raise InvarianteViolado(
                f"las versiones de insumos no son contiguas en {_ORDEN_VERSIONES}: "
                f"{sorted(versiones)}."
            )

        conjunto = set(versiones)
        for encadenada, base in _BASE_ENCADENADA.items():
            if encadenada in conjunto and base not in conjunto:
                raise InvarianteViolado(
                    f"la versión {encadenada} (encadenada) requiere su versión "
                    f"base {base} en insumos."
                )
