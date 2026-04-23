from pathlib import Path

import pandas as pd

from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
)
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.infraestructura.csv.escritor_resultados_csv import EscritorResultadosCsv

P1 = PeriodoQuincenal(2018, 1, 1)
P2 = PeriodoQuincenal(2018, 1, 2)
ID = "abc-123"


def _reporte() -> ReporteDetalladoValidacion:
    idx = pd.MultiIndex.from_tuples(
        [(P1, "INPC"), (P2, "INPC")],
        names=["periodo", "indice"],
    )
    df = pd.DataFrame(
        {
            "version": [2018, 2018],
            "tipo": ["inpc", "inpc"],
            "indice_replicado": [100.1, 100.2],
            "indice_inegi": [float("nan"), float("nan")],
            "error_absoluto": [float("nan"), float("nan")],
            "error_relativo": [float("nan"), float("nan")],
            "estado_calculo": ["ok", "ok"],
            "motivo_error": [None, None],
            "estado_validacion": ["no_disponible", "no_disponible"],
            "total_genericos_esperados": [2, 2],
            "total_genericos_con_indice": [2, 2],
            "total_genericos_sin_indice": [0, 0],
            "cobertura_genericos_pct": [100.0, 100.0],
            "ponderador_total_esperado": [100.0, 100.0],
            "ponderador_total_cubierto": [100.0, 100.0],
        },
        index=idx,
    )
    return ReporteDetalladoValidacion(df, ID)


def _diagnostico_con_periodos() -> DiagnosticoFaltantes:
    df = pd.DataFrame(
        {
            "id_corrida": [ID, ID],
            "version": [2018, 2018],
            "tipo": ["inpc", "inpc"],
            "periodo": [P1, P2],
            "generico": ["arroz", "frijol"],
            "nivel_faltante": ["periodo", "periodo"],
            "tipo_faltante": ["indice", "indice"],
            "detalle": ["sin dato", "sin dato"],
        }
    )
    return DiagnosticoFaltantes(df)


def _diagnostico_estructural() -> DiagnosticoFaltantes:
    df = pd.DataFrame(
        {
            "id_corrida": [ID],
            "version": [2018],
            "tipo": ["inpc"],
            "periodo": [None],
            "generico": ["arroz"],
            "nivel_faltante": ["estructural"],
            "tipo_faltante": ["ponderador"],
            "detalle": ["sin ponderador"],
        }
    )
    return DiagnosticoFaltantes(df)


def _diagnostico_vacio() -> DiagnosticoFaltantes:
    df = pd.DataFrame(
        columns=[
            "id_corrida",
            "version",
            "tipo",
            "periodo",
            "generico",
            "nivel_faltante",
            "tipo_faltante",
            "detalle",
        ]
    )
    return DiagnosticoFaltantes(df)


# --- reporte ---


def test_reporte_multiindex_aplanado(tmp_path: Path):
    ruta = tmp_path / "reporte.csv"
    EscritorResultadosCsv().escribir_reporte(_reporte(), ruta)
    df = pd.read_csv(ruta)

    assert "periodo" in df.columns
    assert "indice" in df.columns
    assert list(df["periodo"]) == [str(P1), str(P2)]
    assert list(df["indice"]) == ["INPC", "INPC"]


def test_reporte_valores_correctos(tmp_path: Path):
    ruta = tmp_path / "reporte.csv"
    EscritorResultadosCsv().escribir_reporte(_reporte(), ruta)
    df = pd.read_csv(ruta)

    assert list(df["indice_replicado"]) == [100.1, 100.2]
    assert list(df["estado_validacion"]) == ["no_disponible", "no_disponible"]


def test_reporte_crea_archivo(tmp_path: Path):
    ruta = tmp_path / "reporte.csv"
    EscritorResultadosCsv().escribir_reporte(_reporte(), ruta)
    assert ruta.exists()


# --- diagnostico ---


def test_diagnostico_periodo_serializado(tmp_path: Path):
    ruta = tmp_path / "diagnostico.csv"
    EscritorResultadosCsv().escribir_diagnostico(_diagnostico_con_periodos(), ruta)
    df = pd.read_csv(ruta)

    assert list(df["periodo"]) == [str(P1), str(P2)]
    assert list(df["generico"]) == ["arroz", "frijol"]


def test_diagnostico_periodo_null_estructural(tmp_path: Path):
    ruta = tmp_path / "diagnostico.csv"
    EscritorResultadosCsv().escribir_diagnostico(_diagnostico_estructural(), ruta)
    df = pd.read_csv(ruta)

    assert pd.isna(df.iloc[0]["periodo"])


def test_diagnostico_sin_indice_entero(tmp_path: Path):
    ruta = tmp_path / "diagnostico.csv"
    EscritorResultadosCsv().escribir_diagnostico(_diagnostico_con_periodos(), ruta)
    df = pd.read_csv(ruta)

    assert list(df.columns)[:1] != ["Unnamed: 0"]
    assert "id_corrida" in df.columns


def test_diagnostico_vacio(tmp_path: Path):
    ruta = tmp_path / "diagnostico.csv"
    EscritorResultadosCsv().escribir_diagnostico(_diagnostico_vacio(), ruta)
    df = pd.read_csv(ruta)

    assert df.empty
    assert "periodo" in df.columns
