from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from replica_inpc.api import graficas
from replica_inpc.dominio.errores import PeriodoNoDisponible
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo

# --------------------------------------------------------------------------- helpers


def _manifiesto(version: int = 2018, tipo: str = "INPC") -> ManifestCalculo:
    return ManifestCalculo(
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador="LaspeyresDirecto",
        fecha=datetime(2024, 1, 1),
    )


def _resultado(
    periodos: list[Any], version: int = 2018, tipo: str = "INPC"
) -> ResultadoIndice:
    filas = [
        {
            "periodo": p,
            "indice": "INPC" if tipo == "INPC" else "cat",
            "version": version,
            "tipo": tipo,
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        }
        for p in periodos
    ]
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = df[[]].copy()
    diag = pd.DataFrame(
        columns=["periodo", "generico", "nivel_faltante", "tipo_faltante", "detalle"]
    )
    return ResultadoIndice(df, [_manifiesto(version, tipo)], reporte, diag)


_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)
_P3 = PeriodoQuincenal(2018, 2, 1)


# --------------------------------------------------------------------------- delegación


def test_graficar_sin_tramo_delega_sin_validar_periodos(mocker) -> None:
    fn = mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1, _P2])
    graficas.graficar(r)
    fn.assert_called_once_with(r, None, None, None)


def test_graficar_convierte_desde_y_hasta(mocker) -> None:
    fn = mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1, _P2, _P3])
    graficas.graficar(r, desde="1Q Ene 2018", hasta="1Q Feb 2018")
    fn.assert_called_once_with(r, None, _P1, _P3)


def test_graficar_pasa_comparacion(mocker) -> None:
    fn = mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1])
    comparacion = _resultado([_P1], tipo="CCIF DIVISION")
    graficas.graficar(r, comparacion=comparacion)
    fn.assert_called_once_with(r, comparacion, None, None)


# --------------------------------------------------------------------------- validación de tramo


def test_graficar_desde_ausente_lanza_periodo_no_disponible(mocker) -> None:
    mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1, _P2])
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(r, desde="1Q Ene 2030")


def test_graficar_hasta_ausente_lanza_periodo_no_disponible(mocker) -> None:
    mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1, _P2])
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(r, hasta="1Q Ene 2030")


def test_graficar_desde_presente_solo_en_comparacion_no_lanza(mocker) -> None:
    # el periodo pedido puede venir de resultado O de comparacion -- la
    # union de ambos es lo que realmente termina en el panel.
    fn = mocker.patch.object(graficas, "graficar_indice")
    r = _resultado([_P1], tipo="CCIF DIVISION")
    comparacion = _resultado([_P1, _P3])
    graficas.graficar(r, comparacion=comparacion, desde="1Q Feb 2018")
    fn.assert_called_once_with(r, comparacion, _P3, None)


# --------------------------------------------------------------------------- _periodos_disponibles


def test_periodos_disponibles_sin_comparacion() -> None:
    r = _resultado([_P1, _P2])
    assert graficas._periodos_disponibles(r, None) == {_P1, _P2}


def test_periodos_disponibles_union_con_comparacion() -> None:
    r = _resultado([_P1])
    comparacion = _resultado([_P2], tipo="CCIF DIVISION")
    assert graficas._periodos_disponibles(r, comparacion) == {_P1, _P2}
