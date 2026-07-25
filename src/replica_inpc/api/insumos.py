"""IO de insumos: carga de canastas y series desde CSV."""

from __future__ import annotations

from pathlib import Path

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.tipos import VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv

_VERSIONES_VALIDAS = (2010, 2013, 2018, 2024)


def _validar_version(version: int) -> None:
    if version not in _VERSIONES_VALIDAS:
        raise InvarianteViolado(f"version {version!r} inválida; usa una de {_VERSIONES_VALIDAS}.")


def _mostrar_resumen_carga_canasta(canasta: CanastaCanonica, version: VersionCanasta) -> None:
    """Imprime tabla resumen de genéricos, encadenamientos y categorías por columna."""
    resumen = [
        ("Genericos", str(len(canasta.df.index))),
        ("Encadenamientos", str(len(canasta.df["encadenamiento"].dropna()))),
    ]
    columnas = [
        (str(col), str(n))
        for col, n in canasta.df.nunique().items()
        if col not in ("ponderador", "encadenamiento")
    ]
    encabezado = (f"Columnas = {len(canasta.df.columns)}", "Categorias")
    filas = [*resumen, encabezado, *columnas]

    ancho_izq = max(len(izq) for izq, _ in filas)
    ancho_der = max(len(der) for _, der in filas)
    ancho_total = ancho_izq + ancho_der + 3
    borde_split = f"+{'-' * (ancho_izq + 2)}+{'-' * (ancho_der + 2)}+"

    def fila(izq: str, der: str) -> str:
        return f"| {izq:<{ancho_izq}} | {der:>{ancho_der}} |"

    print(f"+{'-' * (ancho_total + 2)}+")
    print(f"| {f'Canasta: {version}':^{ancho_total}} |")
    print(borde_split)
    for izq, der in resumen:
        print(fila(izq, der))
    print(borde_split)
    print(fila(*encabezado))
    print(borde_split)
    for izq, der in columnas:
        print(fila(izq, der))
    print(borde_split)


def cargar_canasta(ruta: str, version: VersionCanasta) -> CanastaCanonica:
    """Carga una canasta de ponderadores desde un CSV.

    `version` es obligatoria — 2010 y 2013 tienen genéricos idénticos y un
    auto-detect elegiría mal en silencio (ver api.md §D3).
    """
    _validar_version(version)
    canasta = LectorCanastaCsv().leer(Path(ruta), version)
    _mostrar_resumen_carga_canasta(canasta, version)
    return canasta


def cargar_serie(ruta: str, version: VersionCanasta) -> SerieNormalizada:
    """Carga una serie de índices desde un CSV.

    La serie es siempre quincenal; los datos mensuales se obtienen vía
    `a_mensual`, nunca cargando CSV mensuales. `version` se valida pero la
    lectura de la serie no depende de ella.
    """
    _validar_version(version)
    return LectorSeriesCsv().leer(Path(ruta))
