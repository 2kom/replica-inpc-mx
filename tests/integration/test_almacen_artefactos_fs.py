from pathlib import Path

import pandas as pd
import pytest

from replica_inpc.dominio.errores import ArtefactoNoEncontrado
from replica_inpc.dominio.periodos import Periodo
from replica_inpc.infraestructura.filesystem.almacen_artefactos_fs import AlmacenArtefactosFs

P1 = Periodo(2018, 1, 1)
P2 = Periodo(2018, 1, 2)
ID = "abc-123"


def _almacen(tmp_path: Path) -> AlmacenArtefactosFs:
    return AlmacenArtefactosFs(tmp_path / "runs")


# --- resultado ---

def test_round_trip_resultado(tmp_path: Path):
    df = pd.DataFrame(
        {"version": 2018, "inpc_replicado": [100.1, 100.2], "estado_calculo": "ok", "motivo_error": None},
        index=pd.Index([P1, P2]),
    )
    almacen = _almacen(tmp_path)
    almacen.guardar(ID, "resultado", df)
    recuperado = almacen.obtener(ID, "resultado")

    assert list(recuperado.index) == [str(P1), str(P2)]
    assert list(recuperado["inpc_replicado"]) == [100.1, 100.2]


# --- reporte (MultiIndex) ---

def test_round_trip_reporte_preserva_multiindex(tmp_path: Path):
    idx = pd.MultiIndex.from_tuples(
        [(P1, "INPC general"), (P2, "INPC general")],
        names=["periodo", "subindice"],
    )
    df = pd.DataFrame(
        {"version": 2018, "inpc_replicado": [100.1, 100.2], "estado_validacion": "no_disponible"},
        index=idx,
    )
    almacen = _almacen(tmp_path)
    almacen.guardar(ID, "reporte", df)
    recuperado = almacen.obtener(ID, "reporte")

    assert isinstance(recuperado.index, pd.MultiIndex)
    assert recuperado.index.names == ["periodo", "subindice"]
    assert recuperado.index[0] == (str(P1), "INPC general")
    assert list(recuperado["inpc_replicado"]) == [100.1, 100.2]


# --- resumen ---

def test_round_trip_resumen(tmp_path: Path):
    df = pd.DataFrame(
        {"version": 2018, "total_periodos_esperados": 2, "estado_corrida": "ok"},
        index=pd.Index([ID]),
    )
    almacen = _almacen(tmp_path)
    almacen.guardar(ID, "resumen", df)
    recuperado = almacen.obtener(ID, "resumen")

    assert recuperado.iloc[0]["estado_corrida"] == "ok"
    assert recuperado.iloc[0]["version"] == 2018


# --- diagnostico (Periodo en columna) ---

def test_round_trip_diagnostico_con_periodo_en_columna(tmp_path: Path):
    df = pd.DataFrame(
        {
            "id_corrida": [ID, ID],
            "version": [2018, 2018],
            "periodo": [P1, P2],
            "generico": ["arroz", "frijol"],
            "nivel_faltante": ["periodo", "periodo"],
            "tipo_faltante": ["indice", "indice"],
            "detalle": ["sin dato", "sin dato"],
        }
    )
    almacen = _almacen(tmp_path)
    almacen.guardar(ID, "diagnostico", df)
    recuperado = almacen.obtener(ID, "diagnostico")

    assert list(recuperado["periodo"]) == [str(P1), str(P2)]
    assert list(recuperado["generico"]) == ["arroz", "frijol"]


def test_round_trip_diagnostico_con_periodo_null(tmp_path: Path):
    df = pd.DataFrame(
        {
            "id_corrida": [ID],
            "version": [2018],
            "periodo": [None],
            "generico": ["arroz"],
            "nivel_faltante": ["estructural"],
            "tipo_faltante": ["ponderador"],
            "detalle": ["sin ponderador"],
        }
    )
    almacen = _almacen(tmp_path)
    almacen.guardar(ID, "diagnostico", df)
    recuperado = almacen.obtener(ID, "diagnostico")

    assert pd.isna(recuperado.iloc[0]["periodo"])


# --- errores ---

def test_obtener_artefacto_no_encontrado(tmp_path: Path):
    almacen = _almacen(tmp_path)
    with pytest.raises(ArtefactoNoEncontrado):
        almacen.obtener(ID, "resultado")


def test_guardar_crea_directorio_si_no_existe(tmp_path: Path):
    df = pd.DataFrame({"x": [1]})
    ruta_base = tmp_path / "runs" / "nested"
    almacen = AlmacenArtefactosFs(ruta_base)
    almacen.guardar(ID, "resultado", df)
    assert (ruta_base / ID / "resultado.parquet").exists()
