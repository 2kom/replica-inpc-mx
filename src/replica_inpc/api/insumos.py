"""IO de insumos: carga de canastas y series desde CSV."""

from __future__ import annotations

from pathlib import Path

from replica_inpc.dominio.correspondencia_canastas import ORDEN_VERSIONES
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import RANGOS_CANASTAS, VersionCanasta
from replica_inpc.infraestructura.csv.lector_canasta_csv import LectorCanastaCsv
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv


def _validar_version(version: int) -> None:
    """Rechaza una versión de canasta que no exista."""
    if version not in ORDEN_VERSIONES:
        raise InvarianteViolado(f"versiones fuera de {ORDEN_VERSIONES}: [{version}].")


def _validar_cobertura(serie: SerieNormalizada, version: VersionCanasta, ruta: Path) -> None:
    """Rechaza una serie cuyo tramo de periodos no toca el de la canasta declarada."""
    # SerieNormalizada.__init__ garantiza al menos una columna, todas PeriodoQuincenal y
    # ya ordenadas cronológicamente; los stubs de pandas las tipan como str
    primero: PeriodoQuincenal = serie.df.columns[0]  # type: ignore[assignment]
    ultimo: PeriodoQuincenal = serie.df.columns[-1]  # type: ignore[assignment]
    inicio_canasta, fin_canasta = RANGOS_CANASTAS[version]
    if primero <= (fin_canasta or ultimo) and inicio_canasta <= ultimo:
        return
    raise InvarianteViolado(
        f"la serie de {ruta} cubre {primero} a {ultimo}, que no toca el tramo de la "
        f"canasta {version} ({inicio_canasta} a {fin_canasta or 'sin límite'}). Revisa "
        f"si la versión declarada corresponde al archivo."
    )


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


def cargar_canasta(ruta: str, version: VersionCanasta, resumen: bool = True) -> CanastaCanonica:
    """Carga una canasta de ponderadores desde un CSV.

    `version` es obligatoria y no se puede inferir del archivo: las canastas 2010
    y 2013 tienen genéricos idénticos, el CSV no trae marca de versión, y de ella
    dependen el mapa de renombres entre canastas y el calculador (directo o
    encadenado) que se usará después. Un auto-detect elegiría mal en silencio.

    Imprime una tabla resumen de genéricos, encadenamientos y categorías por
    columna; pasar `resumen=False` la suprime (útil al cargar varias canastas
    seguidas).

    Args:
        ruta: CSV con la columna `generico` como identificador, más `ponderador`,
            `encadenamiento` y las 12 columnas de clasificación (la lista exacta es
            `COLUMNAS_REQUERIDAS`, en `infraestructura.csv.lector_canasta_csv`).
        version: 2010, 2013, 2018 o 2024.
        resumen: si imprimir la tabla resumen. Por defecto sí.

    Raises:
        InvarianteViolado: la versión no es una de las cuatro válidas.
        ArchivoNoEncontrado: la ruta no existe.
        ArchivoVacio: el CSV no tiene contenido.
        ArchivoCorrupto: el CSV no se puede parsear.
        EncodingNoLegible: el archivo no es legible como texto.
        ColumnasMinFaltantes: falta alguna columna requerida.

    Ver: docs/diseño.md §6.2, §D3
    """
    _validar_version(version)
    canasta = LectorCanastaCsv().leer(Path(ruta), version)
    if resumen:
        _mostrar_resumen_carga_canasta(canasta, version)
    return canasta


def cargar_serie(ruta: str, version: VersionCanasta) -> SerieNormalizada:
    """Carga una serie de índices desde un CSV.

    La serie es siempre quincenal; los datos mensuales se obtienen vía
    `a_mensual`, nunca cargando CSV mensuales.

    `version` no cambia cómo se lee el archivo: sirve para verificar que el tramo
    de periodos de la serie toque el de esa canasta. Es una comprobación parcial
    a propósito — atrapa confusiones lejanas (una serie de 2024 declarada 2010)
    pero no vecinas, porque los tramos de canastas contiguas comparten frontera y
    las series traen histórico previo a su propia canasta.

    Args:
        ruta: CSV de series del BIE, en orientación horizontal o vertical (se
            detecta sola), con o sin bloque de metadatos.
        version: 2010, 2013, 2018 o 2024. Debe ser la canasta a la que se le va a
            aplicar esta serie.

    Raises:
        InvarianteViolado: la versión no es válida, o su tramo no toca el de la
            serie.
        ArchivoNoEncontrado: la ruta no existe.
        ArchivoVacio: el CSV no tiene contenido.
        ArchivoCorrupto: el CSV no se puede parsear.
        OrientacionNoDetectable: no se pudo determinar si es horizontal o vertical.
        SerieVacia: no se encontraron genéricos en el archivo.

    Ver: docs/diseño.md §6.2, §D3
    """
    _validar_version(version)
    serie = LectorSeriesCsv().leer(Path(ruta))
    _validar_cobertura(serie, version, Path(ruta))
    return serie
