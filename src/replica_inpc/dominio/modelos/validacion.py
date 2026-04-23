from __future__ import annotations

import pandas as pd

from replica_inpc.dominio.errores import InvarianteViolado


class ResumenValidacion:
    """Representa el resumen agregado de una corrida y su validación.

    Args:
        df: DataFrame con índice `id_corrida` y métricas agregadas de cálculo,
            cobertura y comparación contra INEGI.

    Raises:
        InvarianteViolado: Si el DataFrame está vacío, si el índice tiene
            duplicados, si `version`, `estado_corrida` o
            `estado_validacion_global` contienen valores inválidos, si
            `total_periodos_calculados` excede `total_periodos_esperados`, si
            `total_periodos_con_null` excede `total_periodos_calculados` o si
            `periodo_inicio` es mayor que `periodo_fin`.

    Esquema del DataFrame (índice: `id_corrida`):
        version (int): versión de la canasta usada en la corrida.
        tipo (str): tipo lógico del cálculo; en v1, `"inpc"`.
        periodo_inicio (PeriodoQuincenal): primer periodo calculado.
        periodo_fin (PeriodoQuincenal): último periodo calculado.
        total_periodos_esperados (int): periodos esperados en el rango.
        total_periodos_calculados (int): periodos efectivamente calculados.
        total_periodos_con_null (int): periodos con resultado nulo por faltantes.
        error_absoluto_max (float/NaN): error absoluto máximo frente a INEGI.
        error_relativo_max (float/NaN): error relativo máximo frente a INEGI.
        total_faltantes_indice (int): cantidad de faltantes de índice.
        total_faltantes_ponderador (int): cantidad de faltantes de ponderador.
        estado_validacion_global (str): `ok`, `ok_parcial`, `diferencia_detectada` o `no_disponible`.
        estado_corrida (str): `ok`, `ok_parcial` o `fallida`.

    Example:
        DataFrame interno (`df`):
        | id     | version | tipo | inicio      | fin         | esperados | calculados | null   | err-abs | err-rel | fal-ind | fal-pon | val-gol               | est-co     |
        | ------ | ------: | ---- | ----------- | ----------- | --------: | ---------: | -----: | ------: | ------: | ------: | ------: | --------------------- | ---------- |
        | 'uuid' | 2018    | inpc | 2Q Jul 2018 | 2Q Jul 2024 | 145       | 145        | 0      | 0.002   | 0.002   | 0       | 0       | ok                    | ok         |
        | 'uuid' | 2018    | inpc | 2Q Jul 2018 | 2Q Jul 2024 | 145       | 143        | 2      | 0.018   | 0.0002  | 3       | 0       | diferencia_detectada  | ok_parcial |
        | 'uuid' | 2018    | inpc | 2Q Jul 2018 | 2Q Jul 2024 | 145       | 145        | 0      | NaN     | NaN     | 0       | 0       | ok_parcial            | ok         |
        | 'uuid' | 2018    | inpc | 2Q Jul 2018 | 2Q Jul 2024 | 145       | 145        | 145    | NaN     | NaN     | 0       | 1       | no_disponible         | fallida    |

        Abreviaciones:
        | abreviacion | descripcion                |
        | ----------- | -------------------------- |
        | id          | id_corrida                 |
        | inicio      | periodo_inicio             |
        | fin         | periodo_fin                |
        | esperados   | total_periodos_esperados   |
        | calculados  | total_periodos_calculados  |
        | null        | total_periodos_con_null    |
        | err-abs     | error_absoluto_max         |
        | err-rel     | error_relativo_max         |
        | fal-ind     | total_faltantes_indice     |
        | fal-pon     | total_faltantes_ponderador |
        | val-gol     | estado_validacion_global   |
        | est-co      | estado_corrida             |

    Ver: docs/diseño.md §5.5
    """

    def __init__(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise InvarianteViolado("El DataFrame de resumen de validación no puede estar vacío.")
        if df.index.duplicated().any():
            raise InvarianteViolado(
                "El DataFrame de resumen de validación no puede tener índices duplicados."
            )
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["estado_corrida"].isin({"ok", "ok_parcial", "fallida"}).all():
            raise InvarianteViolado(
                "La columna 'estado_corrida' debe contener solo los valores 'ok', 'ok_parcial' o 'fallida'."
            )
        if "estado_validacion_global" in df.columns and (
            not df["estado_validacion_global"]
            .isin({"ok", "ok_parcial", "diferencia_detectada", "no_disponible"})
            .all()
        ):
            raise InvarianteViolado(
                "La columna 'estado_validacion_global' debe contener solo los valores 'ok', 'ok_parcial', 'diferencia_detectada' o 'no_disponible'."
            )
        if (df["total_periodos_calculados"] > df["total_periodos_esperados"]).any():
            raise InvarianteViolado(
                "La columna 'total_periodos_calculados' no puede tener más valores que 'total_periodos_esperados'."
            )
        if (df["total_periodos_con_null"] > df["total_periodos_calculados"]).any():
            raise InvarianteViolado(
                "La columna 'total_periodos_con_null' no puede tener más valores que 'total_periodos_calculados'."
            )
        if (df["periodo_inicio"] > df["periodo_fin"]).any():
            raise InvarianteViolado("periodo_inicio no puede ser mayor que periodo_fin.")

        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        """Renderiza el resumen como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]


class ReporteDetalladoValidacion:
    """Representa el detalle por periodo del cálculo y su validación.

    Args:
        df: DataFrame con índice compuesto `(periodo, indice)` y métricas
            detalladas de cálculo, validación y cobertura por periodo.
        id_corrida: Identificador de la corrida a la que pertenece el reporte.

    Raises:
        InvarianteViolado: Si el DataFrame está vacío, si el índice tiene
            duplicados, si `version`, `estado_calculo` o `estado_validacion`
            contienen valores inválidos, si `indice_replicado` es nulo cuando
            `estado_calculo == "ok"` o si `indice_replicado` no es nulo cuando
            `estado_calculo != "ok"`.

    Esquema del DataFrame (índice: `periodo`, `indice`):
        version (int): versión de la canasta usada en el cálculo.
        tipo (str): tipo lógico del cálculo; en v1, `"inpc"`.
        indice_replicado (float/NaN): valor replicado del índice por periodo.
        indice_inegi (float/NaN): valor oficial usado para validación.
        error_absoluto (float/NaN): diferencia absoluta contra INEGI.
        error_relativo (float/NaN): diferencia relativa contra INEGI.
        estado_calculo (str): `ok`, `null_por_faltantes` o `fallida`.
        motivo_error (str/NaN): detalle del fallo cuando aplica.
        estado_validacion (str): `ok`, `diferencia_detectada` o `no_disponible`.
        total_genericos_esperados (int): genéricos esperados por la canasta.
        total_genericos_con_indice (int): genéricos con dato en el periodo.
        total_genericos_sin_indice (int): genéricos sin dato en el periodo.
        cobertura_genericos_pct (float): cobertura porcentual del periodo.
        ponderador_total_esperado (float): suma total esperada de ponderadores.
        ponderador_total_cubierto (float): suma de ponderadores cubiertos.

    Example:
        Vista larga (`como_tabla(False)`):
        | (periodo, indice)          | ver  | tipo | inpc_rep | inegi   | err_abs | err_rel | est_calc            | mot_err   | est_val               | gen_esp | gen_con | gen_sin | cob_pct | pon_esp | pon_cub |
        | -------------------------- | ---: | ---- | -------: | ------: | ------: | ------: | ------------------- | --------- | --------------------- | ------: | ------: | ------: | ------: | ------: | ------: |
        | (PeriodoQuincenal(2018, 7, 2), INPC)| 2018 | inpc | 100.000  | 100.002 | 0.002   | 0.00002 | ok                  | NaN       | ok                    | 299     | 299     | 0       | 100.0   | 100.0   | 100.0   |
        | (PeriodoQuincenal(2018, 8, 1), INPC)| 2018 | inpc | NaN      | NaN     | NaN     | NaN     | null_por_faltantes  | faltantes | no_disponible         | 299     | 296     | 3       | 98.9967 | 100.0   | 98.7421 |
        | (PeriodoQuincenal(2018, 8, 2), INPC)| 2018 | inpc | 103.500  | 103.518 | 0.018   | 0.00017 | ok                  | NaN       | diferencia_detectada  | 299     | 299     | 0       | 100.0   | 100.0   | 100.0   |

        Vista ancha con validación INEGI (`como_tabla(True)`):
        | indice                  | 2Q Jul 2018 | 1Q Ago 2018 | 2Q Ago 2018 |
        | ----------------------- | ----------: | ----------: | ----------: |
        | INPC_calculado          | 100.000     | NaN         | 103.500     |
        | INPC_inegi              | 100.002     | NaN         | 103.518     |
        | INPC_error_absoluto     | 0.002       | NaN         | 0.018       |
        | INPC_error_relativo     | 0.00002     | NaN         | 0.00017     |
        | INPC_estado_validacion  | ok          | no_disp.    | dif_detect. |

        Abreviaciones:
        | abreviacion | descripcion                 |
        | ----------- | --------------------------- |
        | ver         | version                     |
        | inpc_rep    | indice_replicado            |
        | inegi       | indice_inegi                |
        | err_abs     | error_absoluto              |
        | err_rel     | error_relativo              |
        | est_calc    | estado_calculo              |
        | mot_err     | motivo_error                |
        | est_val     | estado_validacion           |
        | gen_esp     | total_genericos_esperados   |
        | gen_con     | total_genericos_con_indice  |
        | gen_sin     | total_genericos_sin_indice  |
        | cob_pct     | cobertura_genericos_pct     |
        | pon_esp     | ponderador_total_esperado   |
        | pon_cub     | ponderador_total_cubierto   |

    Ver: docs/diseño.md §5.6
    """

    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None:
        if df.empty:
            raise InvarianteViolado(
                "El DataFrame del reporte detallado de validación no puede estar vacío."
            )
        if df.index.duplicated().any():
            raise InvarianteViolado("El índice no puede tener valores duplicados.")
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["estado_calculo"].isin({"ok", "null_por_faltantes", "fallida"}).all():
            raise InvarianteViolado(
                "La columna 'estado_calculo' debe contener solo los valores 'ok', 'null_por_faltantes' o 'fallida'."
            )
        if "estado_validacion" in df.columns and (
            not df["estado_validacion"]
            .isin({"ok", "diferencia_detectada", "diferencia_detectada_imputado", "no_disponible"})
            .all()
        ):
            raise InvarianteViolado(
                "La columna 'estado_validacion' debe contener solo los valores "
                "'ok', 'diferencia_detectada', 'diferencia_detectada_imputado' o 'no_disponible'."
            )

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

        self._df = df
        self._id_corrida = id_corrida

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def id_corrida(self) -> str:
        """Devuelve el identificador de la corrida asociada al reporte."""
        return self._id_corrida

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame:
        """Devuelve el reporte en formato largo o pivoteado para visualización.

        Args:
            ancho: Si es `False`, devuelve el DataFrame interno. Si es `True`,
                pivota métricas clave con periodos como columnas. Con validación
                INEGI incluye `{indice}_calculado`, `{indice}_inegi`,
                `{indice}_error_absoluto`, `{indice}_error_relativo` y
                `{indice}_estado_validacion`. Sin validación incluye
                `{indice}_calculado`, `{indice}_estado_calculo`,
                `{indice}_motivo_error`, `{indice}_cobertura_pct` y
                `{indice}_ponderador_cubierto`.

        Returns:
            El reporte en formato largo o ancho, según `ancho`.

        Ver: docs/diseño.md §5.6
        """
        if not ancho:
            return self._df

        con_validacion = "estado_validacion" in self._df.columns
        indices = self._df.index.get_level_values("indice").unique()
        partes = []

        for indice in indices:
            df_ind = self._df.xs(indice, level="indice")

            if con_validacion:
                cols = {
                    "indice_replicado": f"{indice}_calculado",
                    "indice_inegi": f"{indice}_inegi",
                    "error_absoluto": f"{indice}_error_absoluto",
                    "error_relativo": f"{indice}_error_relativo",
                    "estado_validacion": f"{indice}_estado_validacion",
                }
            else:
                cols = {
                    "indice_replicado": f"{indice}_calculado",
                    "estado_calculo": f"{indice}_estado_calculo",
                    "motivo_error": f"{indice}_motivo_error",
                    "cobertura_genericos_pct": f"{indice}_cobertura_pct",
                    "ponderador_total_cubierto": f"{indice}_ponderador_cubierto",
                }

            df_sel = df_ind[list(cols.keys())].rename(columns=cols)  # type: ignore[call-overload]
            partes.append(df_sel.T)

        resultado = pd.concat(partes)
        resultado.index.name = "indice"
        return resultado

    def _repr_html_(self) -> str:
        """Renderiza el reporte en formato largo para notebooks."""
        return self.como_tabla(ancho=False)._repr_html_()  # type: ignore[operator]


class DiagnosticoFaltantes:
    """Representa el diagnóstico detallado de faltantes detectados en una corrida.

    Args:
        df: DataFrame con índice entero y filas de trazabilidad por faltante
            detectado. Puede estar vacío cuando la corrida no presenta faltantes.

    Raises:
        InvarianteViolado: Si `version`, `nivel_faltante` o `tipo_faltante`
            contienen valores inválidos, si `periodo` es nulo cuando
            `tipo_faltante == "indice"` o si `periodo` no es nulo cuando
            `tipo_faltante == "ponderador"`.

    Esquema del DataFrame (índice entero):
        id_corrida (str): identificador de la corrida.
        version (int): versión de la canasta usada en la corrida.
        tipo (str): tipo lógico del cálculo; en v1, `"inpc"`.
        periodo (PeriodoQuincenal/NaN): periodo afectado; `NaN` para faltantes de ponderador.
        generico (str): genérico afectado por el faltante.
        nivel_faltante (str): `periodo` o `estructural`.
        tipo_faltante (str): `indice` o `ponderador`.
        detalle (str): descripción textual del faltante.

    Example:
        DataFrame interno (`df`):
        | id         | ver  | tipo | per         | gen    | nivel        | tipo_fal  | detalle                                      |
        | ---------- | ---: | ---- | ----------- | ------ | ------------ | --------- | -------------------------------------------- |
        | 'uuid'     | 2018 | inpc | 1Q Ago 2018 | frijol | periodo      | indice    | Sin dato de indice para generico frijol...   |
        | 'uuid'     | 2018 | inpc | 2Q Ago 2018 | frijol | periodo      | indice    | Sin dato de indice para generico frijol...   |
        | 'uuid'     | 2018 | inpc | NaN         | huevo  | estructural  | ponderador| Sin ponderador para generico huevo           |

        Abreviaciones:
        | abreviacion | descripcion     |
        | ----------- | --------------- |
        | id          | id_corrida      |
        | ver         | version         |
        | per         | periodo         |
        | gen         | generico        |
        | nivel       | nivel_faltante  |
        | tipo_fal    | tipo_faltante   |

        También es válido un DataFrame vacío: eso significa que no se
        detectaron faltantes en la corrida.

    Ver: docs/diseño.md §5.7
    """

    def __init__(self, df: pd.DataFrame) -> None:
        if not df["version"].isin({2010, 2013, 2018, 2024}).all():
            raise InvarianteViolado(
                "La columna 'version' debe contener solo los valores 2010, 2013, 2018 o 2024."
            )
        if not df["nivel_faltante"].isin({"periodo", "estructural"}).all():
            raise InvarianteViolado(
                "La columna 'nivel_faltante' debe contener solo los valores 'periodo' o 'estructural'."
            )
        if not df["tipo_faltante"].isin({"indice", "ponderador", "indice_imputado"}).all():
            raise InvarianteViolado(
                "La columna 'tipo_faltante' debe contener solo los valores "
                "'indice', 'ponderador' o 'indice_imputado'."
            )

        filas_con_periodo = df["tipo_faltante"].isin({"indice", "indice_imputado"})
        if df.loc[filas_con_periodo, "periodo"].isnull().any():
            raise InvarianteViolado(
                "periodo no puede ser null cuando tipo_faltante es 'indice' o 'indice_imputado'."
            )

        filas_ponderador = df["tipo_faltante"] == "ponderador"
        if df.loc[filas_ponderador, "periodo"].notnull().any():
            raise InvarianteViolado("periodo debe ser null cuando tipo_faltante es 'ponderador'.")

        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        """Renderiza el diagnóstico como tabla HTML en entornos interactivos."""
        return self._df._repr_html_()  # type: ignore[operator]
