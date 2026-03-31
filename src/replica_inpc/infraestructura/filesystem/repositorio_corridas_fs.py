from __future__ import annotations

import json
from pathlib import Path

from replica_inpc.dominio.errores import ArtefactoNoEncontrado
from replica_inpc.dominio.tipos import ManifestCorrida


class RepositorioCorridasFs:
    def __init__(self, ruta_base: Path) -> None:
        self._ruta_base = ruta_base

    def guardar(self, manifest: ManifestCorrida) -> None:
        ruta_corrida = self._ruta_base / manifest.id_corrida
        ruta_corrida.mkdir(parents=True, exist_ok=True)
        datos = {
            "id_corrida": manifest.id_corrida,
            "version": manifest.version,
            "ruta_canasta": str(manifest.ruta_canasta),
            "ruta_series": str(manifest.ruta_series),
            "fecha": manifest.fecha.isoformat(),
        }
        (ruta_corrida / "manifest.json").write_text(
            json.dumps(datos, indent=2), encoding="utf-8"
        )

    def obtener(self, id_corrida: str) -> ManifestCorrida:
        ruta = self._ruta_base / id_corrida / "manifest.json"
        if not ruta.exists():
            raise ArtefactoNoEncontrado(
                f"manifest.json no encontrado para corrida '{id_corrida}'"
            )
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        from datetime import datetime
        return ManifestCorrida(
            id_corrida=datos["id_corrida"],
            version=datos["version"],
            ruta_canasta=Path(datos["ruta_canasta"]),
            ruta_series=Path(datos["ruta_series"]),
            fecha=datetime.fromisoformat(datos["fecha"]),
        )

    def listar(self) -> list[str]:
        if not self._ruta_base.exists():
            return []
        return [
            d.name
            for d in self._ruta_base.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ]
