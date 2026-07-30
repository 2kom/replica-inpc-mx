from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.tipos import VersionCanasta

_COLUMNAS_CORE = (
    "COG",
    "INFLACION COMPONENTE",
    "INFLACION SUBCOMPONENTE",
    "INFLACION AGRUPACION",
    "CANASTA BASICA",
)


class CanastaCanonica:
    """Representa la canasta canónica usada para el cálculo del índice.

    Args:
        df: DataFrame con `generico` como índice y columnas según el esquema
            canónico de la canasta. Las columnas `ponderador` y
            `encadenamiento` se conservan como texto del archivo fuente.
        version: Versión base de la canasta. Debe ser 2010, 2013, 2018 o 2024.

    Raises:
        InvarianteViolado: Si la versión no es válida, si el índice contiene
            duplicados o cadenas vacías, si `ponderador` o `encadenamiento`
            contienen texto no numérico, si algún ponderador no es positivo, si
            la suma de ponderadores no es 100, si algún encadenamiento no nulo
            no es positivo, o si `COG`/`INFLACION COMPONENTE`/`INFLACION
            SUBCOMPONENTE`/`INFLACION AGRUPACION`/`CANASTA BASICA` tienen
            valores vacíos (a diferencia de las clasificaciones finas,
            obligatorias en toda versión — ver Esquema abajo para las que sí
            pueden faltar según fuente o versión).

    Esquema del DataFrame (índice: `generico`). `LectorCanastaCsv` renombra
    todas las columnas de clasificación a mayúsculas al cargar — el nombre de
    columna real, tal como viene del CSV fuente, se conserva solo en
    `tools/canasta_inpc/` (fuera del dominio):
        ponderador (object/str): texto decimal exacto del ponderador.
        encadenamiento (object/str/NaN): texto decimal exacto o `NaN` cuando no aplica.
        COG (object/str): clasificacion por objeto del gasto.
        CCIF DIVISION (object/str): clasificacion de consumo por finalidades — division.
        CCIF GRUPO (object/str): clasificacion de consumo por finalidades — grupo.
        CCIF CLASE (object/str): clasificacion de consumo por finalidades — clase.
        INFLACION COMPONENTE (object/str): componente de inflacion.
        INFLACION SUBCOMPONENTE (object/str): subcomponente de inflacion.
        INFLACION AGRUPACION (object/str): agrupacion de inflacion.
        SCIAN SECTOR (object/str): numero y nombre del sector, ej. "32 Industrias manufactureras".
        SCIAN RAMA (object/str): codigo y nombre de la rama, ej. "3241 Fabricacion de...".
        DURABILIDAD (object/str): categoria de durabilidad; vacio cuando no aplica.
        CANASTA BASICA (object/str): "X" si pertenece, "-" si no; nunca
            vacío — siempre disponible vía xlsx en las 4 versiones (ver
            tools/canasta_inpc/esquema.py::FUENTES_POSIBLES).
        CANASTA CONSUMO MINIMO (object/str): "X" si pertenece, "-" si no
            pertenece (solo en la versión donde la clasificación existe,
            2024); NaN cuando la clasificación no aplica a la versión
            (2010/2013/2018).

    Example:
        DataFrame interno:
        | generico | ponderador | encadenamiento | COG       |
        | -------- | ---------: | -------------: | --------: |
        | arroz    | "10.0"     | NaN            | Legumbres |
        | frijol   | "20.0"     | NaN            | Legumbres |
        | leche    | "30.0"     | NaN            | Lácteos   |
        | huevo    | "40.0"     | NaN            | Avicolas? |

        Metadatos asociados:
        | atributo | valor |
        | -------- | ----- |
        | version  | 2018  |

        En este ejemplo, los ponderadores suman 100 y `encadenamiento` está
        vacío porque la estrategia aplicable es directa.

    Ver: docs/diseño.md §5.4, §11.5, §11.32
    """

    def __init__(self, df: pd.DataFrame, version: VersionCanasta) -> None:
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El índice del DataFrame de la canasta no puede tener valores duplicados."
            )
        if version not in {2010, 2013, 2018, 2024}:
            raise InvarianteViolado("La versión de la canasta debe ser 2010, 2013, 2018 o 2024.")
        if (df.index == "").any():
            raise InvarianteViolado("El índice del DataFrame no puede contener cadenas vacías.")
        try:
            ponderador_float = df["ponderador"].astype(float)
        except ValueError as e:
            raise InvarianteViolado(
                f"La columna 'ponderador' contiene un valor no numérico: {e}"
            ) from e
        if not (ponderador_float > 0).all():
            raise InvarianteViolado("La columna 'ponderador' debe contener solo valores positivos.")
        if abs(ponderador_float.sum() - 100) > 1e-5:  # Permitir una pequeña tolerancia numérica
            raise InvarianteViolado("La suma de los ponderadores debe ser igual a 100.")
        try:
            encadenamiento_float = df["encadenamiento"].astype(float)
        except ValueError as e:
            raise InvarianteViolado(
                f"La columna 'encadenamiento' contiene un valor no numérico: {e}"
            ) from e
        if df["encadenamiento"].notnull().any() and (encadenamiento_float <= 0).any():
            raise InvarianteViolado(
                "La columna 'encadenamiento' debe contener solo valores positivos cuando no es nula."
            )
        columnas_vacias = [
            col
            for col in _COLUMNAS_CORE
            if col in df.columns
            and (df[col].isna() | (df[col].astype(str).str.strip() == "")).any()
        ]
        if columnas_vacias:
            raise InvarianteViolado(
                f"Las columnas {columnas_vacias} no pueden tener valores vacíos "
                "— a diferencia de las clasificaciones finas (CCIF GRUPO/CLASE, "
                "SCIAN SECTOR/RAMA, DURABILIDAD), son obligatorias en toda versión "
                "de la canasta."
            )

        self._df = df
        self._version: VersionCanasta = version

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def version(self) -> VersionCanasta:
        """Devuelve la versión base de la canasta."""
        return self._version

    def _repr_html_(self) -> str:
        """Renderiza la canasta como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]
