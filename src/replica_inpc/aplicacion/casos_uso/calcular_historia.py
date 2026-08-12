"""Caso de uso `CalcularHistoria`.

Orquesta carga, cálculo, empalme, rebase y conversión de frecuencia —en ese
orden— para producir un `ResultadoIndice` histórico a partir de insumos por
versión de canasta. Reemplaza a `EjecutarCorrida` (v1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from replica_inpc.aplicacion.puertos.lector_canasta import LectorCanasta
from replica_inpc.aplicacion.puertos.lector_series import LectorSeries
from replica_inpc.dominio.calculo.estrategia import para_canasta
from replica_inpc.dominio.conversion import a_mensual, empalmar, rebasar
from replica_inpc.dominio.correspondencia_canastas import (
    ORDEN_VERSIONES,
    construir_mapa_renombre,
    renombrar_valor,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta

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
    traslape = RANGOS_CANASTAS[version_destino][0]  # type: ignore[index]
    mapa = construir_mapa_renombre(tipo, version_origen, version_destino)
    df = resultado_prev.df
    refs: dict[str, float] = {}
    for indice in df.index.get_level_values("indice").unique():
        try:
            valor = df.loc[(traslape, indice), "indice_replicado"]  # type: ignore[index]
        except KeyError:
            continue
        if pd.isna(valor):
            continue
        refs[renombrar_valor(str(indice), tipo, version_origen, mapa)] = float(valor)  # type: ignore[arg-type]
    return refs


class CalcularHistoria:
    """Ruta automática del cálculo histórico: resuelve la cadena completa de una vez.

    Hace por el usuario lo que de otro modo se compone a mano — cargar los
    insumos de cada versión, calcular directo (2010, 2018) o encadenado (2013,
    2024) propagando la referencia de empalme, unir los tramos y anclarlos a una
    base común.

    Args:
        lector_canasta: puerto de lectura de canastas.
        lector_series: puerto de lectura de series de índices.

    Ver: docs/diseño.md §7.2
    """

    def __init__(self, lector_canasta: LectorCanasta, lector_series: LectorSeries) -> None:
        self._lector_canasta = lector_canasta
        self._lector_series = lector_series

    def ejecutar(
        self,
        insumos: list[tuple[VersionCanasta, Path, Path]],
        tipo: str,
        periodicidad: Literal["quincenal", "mensual"],
        periodo_referencia: PeriodoQuincenal,
    ) -> ResultadoIndice:
        """Calcula la serie histórica completa, empalmada y rebasada.

        Args:
            insumos: una tupla `(version, ruta_canasta, ruta_series)` por versión
                de canasta. Deben ser contiguas y cada versión encadenada exige
                la suya base.
            tipo: `"INPC"` o una columna de clasificación, en mayúsculas.
            periodicidad: decide únicamente si el resultado se mensualiza al
                final; no altera la base.
            periodo_referencia: quincena en la que el índice vale 100.

        Raises:
            InvarianteViolado: si los insumos están vacíos, traen versiones
                duplicadas, no contiguas o sin su base encadenada; si la
                periodicidad no es válida; o si `tipo`/`periodo_referencia` no
                cumplen su contrato.

        Ver: docs/diseño.md §7.2
        """
        _validar(insumos, tipo, periodicidad, periodo_referencia)
        ordenados = sorted(insumos, key=lambda insumo: insumo[0])

        resultados: list[tuple[VersionCanasta, ResultadoIndice]] = []
        previo: ResultadoIndice | None = None
        for version, ruta_canasta, ruta_series in ordenados:
            canasta = self._lector_canasta.leer(ruta_canasta, version)
            serie = self._lector_series.leer(ruta_series)
            referencias: dict[str, float] | None = None
            if previo is not None:
                # `previo` es el resultado de UNA versión: el empalme viene después
                # del bucle, así que su manifiesto tiene exactamente una entrada.
                (manifiesto_previo,) = previo.manifiesto
                referencias = _referencias_normalizadas(
                    previo, tipo, manifiesto_previo.version, version
                )
            resultado = para_canasta(canasta, referencias).calcular(canasta, serie, tipo)
            resultados.append((version, resultado))
            previo = resultado

        acc = resultados[0][1]
        for version, resultado in resultados[1:]:
            # Sin `forzar`: los tramos recién calculados llegan con
            # `periodo_referencia=None`, así que la guardia de juntura discontinua
            # de `empalmar` no se dispara acá. Forzarla la dejaría desarmada para
            # un futuro en que sí llegara un tramo ya rebasado.
            acc = empalmar([acc, resultado], version_nombres=version)

        # Rebase ANTES de mensualizar: ancla exacta la quincena base, que es la
        # que el INPC publica (`data/glosario.md`, "Periodo base / de referencia").
        # El promedio mensual queda entonces aproximado a propósito — no se
        # garantiza que el mes que contiene al ancla valga 100, y
        # `periodo_referencia` sigue nombrando la quincena real.
        #
        # Para admitir una base MENSUAL exacta —útil para comparar contra un
        # índice de periodicidad mensual, como el INPP— hay que invertir el orden
        # solo en ese caso: `a_mensual` primero y `rebasar` después, con un
        # `PeriodoMensual`. Ambos órdenes son válidos y `rebasar` ya acepta un
        # resultado mensual (docs/diseño.md §5.10); lo que falta es ensanchar el
        # tipo de `periodo_referencia` y ramificar acá. Hoy la guardia de
        # `_validar` lo rechaza antes de llegar a este punto.
        acc = rebasar(acc, periodo_referencia)
        if periodicidad == "mensual":
            acc = a_mensual(acc)
        return acc


def _validar(
    insumos: list[tuple[VersionCanasta, Path, Path]],
    tipo: str,
    periodicidad: str,
    periodo_referencia: _Periodo,
) -> None:
    """Rechaza insumos, tipo, periodicidad o referencia inválidos antes de leer nada."""
    if not insumos:
        raise InvarianteViolado("insumos no puede estar vacío.")
    if periodicidad not in _PERIODICIDADES:
        raise InvarianteViolado(f"periodicidad '{periodicidad}' inválida; usa {_PERIODICIDADES}.")
    if not tipo or tipo != tipo.upper():
        raise InvarianteViolado(
            f"tipo '{tipo}' debe venir en mayúsculas y no vacío; la fachada lo normaliza."
        )
    # El INPC se calcula por quincena y su base oficial siempre es una quincena
    # —2Q dic 2010 para las canastas 2010/2013, 2Q jul 2018 para 2018/2024—, así
    # que una base mensual no tiene contraparte en este flujo. Ver el comentario
    # de `ejecutar` para qué haría falta si algún día se admite.
    if not isinstance(periodo_referencia, PeriodoQuincenal):
        raise InvarianteViolado(
            f"periodo_referencia debe ser quincenal; se recibió "
            f"{type(periodo_referencia).__name__}. Los cálculos son quincenales y la "
            f"base del INPC siempre es una quincena."
        )

    versiones = [insumo[0] for insumo in insumos]
    if len(versiones) != len(set(versiones)):
        raise InvarianteViolado(f"insumos tiene versiones duplicadas: {sorted(versiones)}.")
    desconocidas = [v for v in versiones if v not in ORDEN_VERSIONES]
    if desconocidas:
        raise InvarianteViolado(f"versiones fuera de {ORDEN_VERSIONES}: {desconocidas}.")

    posiciones = sorted(ORDEN_VERSIONES.index(v) for v in versiones)
    contiguas = list(range(posiciones[0], posiciones[0] + len(posiciones)))
    if posiciones != contiguas:
        raise InvarianteViolado(
            f"las versiones de insumos no son contiguas en {ORDEN_VERSIONES}: {sorted(versiones)}."
        )

    conjunto = set(versiones)
    for encadenada, base in _BASE_ENCADENADA.items():
        if encadenada in conjunto and base not in conjunto:
            raise InvarianteViolado(
                f"la versión {encadenada} (encadenada) requiere su versión base {base} en insumos."
            )
