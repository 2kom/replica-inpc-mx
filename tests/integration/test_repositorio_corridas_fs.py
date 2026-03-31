from datetime import datetime
from pathlib import Path

import pytest

from replica_inpc.dominio.errores import ArtefactoNoEncontrado
from replica_inpc.dominio.tipos import ManifestCorrida
from replica_inpc.infraestructura.filesystem.repositorio_corridas_fs import RepositorioCorridasFs

ID = "abc-123"
MANIFEST = ManifestCorrida(
    id_corrida=ID,
    version=2018,
    ruta_canasta=Path("/data/canasta_2018.csv"),
    ruta_series=Path("/data/series_2018.csv"),
    fecha=datetime(2026, 3, 30, 14, 23, 0),
)


def _repo(tmp_path: Path) -> RepositorioCorridasFs:
    return RepositorioCorridasFs(tmp_path / "runs")


def test_round_trip_guardar_obtener(tmp_path: Path):
    repo = _repo(tmp_path)
    repo.guardar(MANIFEST)
    recuperado = repo.obtener(ID)

    assert recuperado.id_corrida == ID
    assert recuperado.version == 2018
    assert recuperado.ruta_canasta == Path("/data/canasta_2018.csv")
    assert recuperado.ruta_series == Path("/data/series_2018.csv")
    assert recuperado.fecha == datetime(2026, 3, 30, 14, 23, 0)


def test_guardar_crea_manifest_json(tmp_path: Path):
    repo = _repo(tmp_path)
    repo.guardar(MANIFEST)
    assert (tmp_path / "runs" / ID / "manifest.json").exists()


def test_listar_devuelve_ids(tmp_path: Path):
    repo = _repo(tmp_path)
    repo.guardar(MANIFEST)
    repo.guardar(ManifestCorrida(
        id_corrida="otro-id",
        version=2024,
        ruta_canasta=Path("/data/canasta_2024.csv"),
        ruta_series=Path("/data/series_2024.csv"),
        fecha=datetime(2026, 3, 30, 15, 0, 0),
    ))
    ids = repo.listar()
    assert set(ids) == {ID, "otro-id"}


def test_listar_ignora_directorios_sin_manifest(tmp_path: Path):
    repo = _repo(tmp_path)
    repo.guardar(MANIFEST)
    (tmp_path / "runs" / "sin-manifest").mkdir(parents=True)
    ids = repo.listar()
    assert ids == [ID]


def test_listar_ruta_base_inexistente(tmp_path: Path):
    repo = _repo(tmp_path)
    assert repo.listar() == []


def test_obtener_no_encontrado(tmp_path: Path):
    repo = _repo(tmp_path)
    with pytest.raises(ArtefactoNoEncontrado):
        repo.obtener("inexistente")
