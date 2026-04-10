from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class ResultadoCalculo:
    """Representa el resultado del cálculo por periodo e índice.

    Args:
        df: DataFrame con índice compuesto `(periodo, indice)` y columnas del
            resultado calculado. En v1, `tipo` es `"inpc"` e `indice` suele ser
            `"INPC"`.
        id_corrida: Identificador de la corrida que produjo este resultado.

    Raises:
        InvarianteViolado: Si el DataFrame está vacío, si la `version` contiene
            valores inválidos, si el índice tiene duplicados, si
            `estado_calculo` usa valores fuera del catálogo permitido, si
            `indice_replicado` es nulo cuando `estado_calculo == "ok"` o si
            `indice_replicado` no es nulo o `motivo_error` es nulo cuando
            `estado_calculo != "ok"`.

    Esquema del DataFrame interno (índice: `periodo`, `indice`):
        version (int): versión de la canasta usada en el cálculo.
        tipo (str): tipo lógico del cálculo; en v1, `"inpc"`.
        indice_replicado (float/NaN): valor calculado del índice.
        estado_calculo (str): `ok`, `null_por_faltantes` o `fallida`.
        motivo_error (str/NaN): motivo del fallo cuando `estado_calculo != "ok"`.

    Example:
        DataFrame interno (`df`):
        | periodo     | indice | version | tipo | indice_replicado | estado_calculo     | motivo_error       |
        | ----------- | ------ | ------: | ---- | ---------------- | ------------------ | ------------------ |
        | 2Q Jul 2018 | INPC   | 2018    | inpc | 100.0            | ok                 | NaN                |
        | 1Q Ago 2018 | INPC   | 2018    | inpc | NaN              | null_por_faltantes | faltantes en serie |

        Metadatos asociados:
        | atributo   | valor        |
        | ---------- | ------------ |
        | id_corrida | "uuid_valor" |

    Ver: docs/diseño.md §5.4, §11.12
    """

    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None:

        if df.empty:
            raise InvarianteViolado("El DataFrame de resultados no puede estar vacío.")
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado("version contiene valores inválidos.")
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El DataFrame de resultados no puede tener índices duplicados."
            )
        if not df["estado_calculo"].isin({"ok", "null_por_faltantes", "fallida"}).all():
            raise InvarianteViolado("estado_calculo contiene valores invalidos.")

        filas_ok = df["estado_calculo"] == "ok"
        if df.loc[filas_ok, "indice_replicado"].isnull().any():
            raise InvarianteViolado(
                "indice_replicado no puede ser null cuando estado_calculo es 'ok'."
            )

        filas_fallo = df["estado_calculo"] != "ok"
        if df.loc[filas_fallo, "indice_replicado"].notnull().any():
            raise InvarianteViolado(
                "indice_replicado debe ser null cuando estado_calculo no es 'ok'."
            )
        if df.loc[filas_fallo, "motivo_error"].isnull().any():
            raise InvarianteViolado(
                "motivo_error no puede ser null cuando estado_calculo no es 'ok'."
            )

        self._df = df
        self._id_corrida = id_corrida

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def id_corrida(self) -> str:
        """Devuelve el identificador de la corrida asociada al resultado."""
        return self._id_corrida

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame:
        """Devuelve el resultado en formato largo o pivoteado para visualización.

        Args:
            ancho: Si es `False`, devuelve el DataFrame interno. Si es `True`,
                pivota `indice_replicado`: `indice` como filas, periodos como columnas.

        Returns:
            El resultado en formato largo o ancho, según `ancho`.

        Ver: docs/diseño.md §5.4
        """
        if not ancho:
            return self._df
        return self._df["indice_replicado"].unstack(level="periodo")

    def _repr_html_(self) -> str:
        """Renderiza el resultado en formato largo para notebooks."""
        return self.como_tabla(ancho=False)._repr_html_()  # type: ignore[operator]
