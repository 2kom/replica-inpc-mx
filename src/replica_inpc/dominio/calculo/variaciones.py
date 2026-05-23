"""Cálculo de variaciones a partir de un `ResultadoIndice`.

Tres funciones producen `ResultadoVariacion`:

- `variacion_periodica` — una variación por periodo contra N periodos atrás.
- `variacion_acumulada_anual` — enero..periodo vs diciembre del año anterior.
- `variacion_desde` — variación total de un rango; una fila por índice.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd

from replica_inpc.dominio.calculo._temporal import (
    LAG_MENSUAL,
    LAG_QUINCENAL,
    Frecuencia,
    es_mensual,
    resolver_extremo,
    restar_meses,
    restar_quincenas,
)
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestDerivado

Periodo = PeriodoQuincenal | PeriodoMensual

_COLS_REPORTE = [
    "estado_calculo",
    "motivo_error",
    "periodo_lag",
    "indice_t",
    "indice_lag",
    "version_t",
    "version_lag",
    "cobertura_pct_t",
    "cobertura_pct_lag",
]
_COLS_DIAGNOSTICO = [
    "id_corrida",
    "tipo",
    "clase_variacion",
    "periodo",
    "indice",
    "estado_calculo",
    "motivo_error",
    "periodo_lag",
    "version_t",
    "version_lag",
]


def _estado_derivado(estado_t: str, estado_lag: object) -> str:
    """Estado de una fila derivada: `parcial` si el fuente en `t` o lag lo es."""
    return "parcial" if estado_t == "parcial" or estado_lag == "parcial" else "ok"


def _motivo_faltante(valor_t: float, valor_lag: float) -> str:
    if pd.isna(valor_t) and pd.isna(valor_lag):
        return "sin valor replicado en t ni en periodo base"
    if pd.isna(valor_lag):
        return "sin valor replicado en periodo base"
    return "sin valor replicado en t"


def _cobertura(reporte_fuente: pd.DataFrame) -> pd.Series | None:
    if "cobertura_genericos_pct" in reporte_fuente.columns:
        return reporte_fuente["cobertura_genericos_pct"]
    return None


def variacion_periodica(
    resultado: ResultadoIndice, frecuencia: Frecuencia
) -> ResultadoVariacion:
    """Variación de cada periodo contra N periodos anteriores según `frecuencia`."""
    largo = resultado.resultado.largo
    mensual = es_mensual(largo)
    lag_map = LAG_MENSUAL if mensual else LAG_QUINCENAL
    if frecuencia not in lag_map:
        raise InvarianteViolado(
            f"Frecuencia '{frecuencia}' no aplica a periodos "
            f"{'mensuales' if mensual else 'quincenales'}. "
            f"Válidas: {sorted(lag_map)}."
        )
    lag = lag_map[frecuencia]
    if mensual:
        def base_de(p: Periodo) -> Periodo:
            return restar_meses(p, lag)  # type: ignore[arg-type]
    else:
        def base_de(p: Periodo) -> Periodo:
            return restar_quincenas(p, lag)  # type: ignore[arg-type]

    return _calcular_con_base(resultado, base_de, f"periodica_{frecuencia}", "")


def variacion_acumulada_anual(resultado: ResultadoIndice) -> ResultadoVariacion:
    """Variación de cada periodo contra diciembre del año anterior."""
    largo = resultado.resultado.largo
    mensual = es_mensual(largo)
    if mensual:
        def base_de(p: Periodo) -> Periodo:
            return PeriodoMensual(p.año - 1, 12)
    else:
        def base_de(p: Periodo) -> Periodo:
            return PeriodoQuincenal(p.año - 1, 12, 2)

    return _calcular_con_base(resultado, base_de, "acumulada_anual", "")


def _calcular_con_base(
    resultado: ResultadoIndice,
    base_de: Callable[[Periodo], Periodo],
    clase: str,
    descripcion: str,
) -> ResultadoVariacion:
    """Núcleo de `variacion_periodica` y `variacion_acumulada_anual`.

    `base_de` mapea cada periodo `t` a su periodo base.
    """
    largo = resultado.resultado.largo
    ids = [m.id_corrida for m in resultado.manifiesto]
    tipo = str(largo["tipo"].iloc[0])

    indices_lvl = largo.index.get_level_values("indice")
    periodos_lvl = largo.index.get_level_values("periodo")
    valores = largo["indice_replicado"]

    base_periodos = [base_de(p) for p in periodos_lvl]
    base_idx = pd.MultiIndex.from_arrays(
        [base_periodos, indices_lvl], names=["periodo", "indice"]
    )
    valor_lag = pd.Series(valores.reindex(base_idx).to_numpy(), index=largo.index)
    estado_lag = pd.Series(
        largo["estado_calculo"].reindex(base_idx).to_numpy(), index=largo.index
    )
    version_lag = pd.Series(
        largo["version"].reindex(base_idx).to_numpy(), index=largo.index
    )
    periodo_lag = pd.Series(base_periodos, index=largo.index, dtype=object)

    variacion_pp = (valores / valor_lag - 1.0) * 100.0
    computable = valores.notna() & valor_lag.notna()
    derivado = pd.Series(
        [
            _estado_derivado(et, el)
            for et, el in zip(largo["estado_calculo"], estado_lag)
        ],
        index=largo.index,
    )

    df_out = pd.DataFrame(
        {
            "tipo": tipo,
            "clase_variacion": clase,
            "variacion_pp": variacion_pp,
            "estado_calculo": derivado,
            "version_t": largo["version"],
        },
        index=largo.index,
    )[computable].sort_index()
    if df_out.empty:
        raise InvarianteViolado(
            f"Sin periodos computables para clase '{clase}'. "
            "Se requieren datos suficientes en el periodo base."
        )

    reporte_df, diagnostico_df = _construir_reporte_diagnostico(
        largo,
        _cobertura(resultado.reporte),
        valores,
        valor_lag,
        version_lag,
        periodo_lag,
        base_idx,
        derivado,
        computable,
        ids,
        tipo,
        clase,
    )
    manifiesto = ManifestDerivado(
        id_corrida=ids,
        tipo=tipo,
        clase=clase,
        descripcion=descripcion,
        fecha=datetime.now(),
    )
    return ResultadoVariacion(df_out, manifiesto, reporte_df, diagnostico_df)


def _construir_reporte_diagnostico(
    largo: pd.DataFrame,
    cobertura: pd.Series | None,
    valores: pd.Series,
    valor_lag: pd.Series,
    version_lag: pd.Series,
    periodo_lag: pd.Series,
    base_idx: pd.MultiIndex,
    derivado: pd.Series,
    computable: pd.Series,
    ids: list[str],
    tipo: str,
    clase: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye `reporte_df` (todas las filas) y `diagnostico_df` (no computables)."""
    if cobertura is not None:
        cob_t = cobertura.reindex(largo.index)
        cob_lag = pd.Series(cobertura.reindex(base_idx).to_numpy(), index=largo.index)
    else:
        cob_t = pd.Series(float("nan"), index=largo.index)
        cob_lag = pd.Series(float("nan"), index=largo.index)

    estados_rep: list[str] = []
    motivos: list[object] = []
    for ok, est, vt, vl in zip(computable, derivado, valores, valor_lag):
        if ok:
            estados_rep.append(est)
            motivos.append(float("nan"))
        else:
            estados_rep.append("sin_datos")
            motivos.append(_motivo_faltante(vt, vl))

    reporte_df = pd.DataFrame(
        {
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
            "periodo_lag": periodo_lag,
            "indice_t": valores.to_numpy(),
            "indice_lag": valor_lag.to_numpy(),
            "version_t": largo["version"].to_numpy(),
            "version_lag": version_lag.to_numpy(),
            "cobertura_pct_t": cob_t.to_numpy(),
            "cobertura_pct_lag": cob_lag.to_numpy(),
        },
        index=largo.index,
        columns=_COLS_REPORTE,
    ).sort_index()

    no_computable = ~computable
    diagnostico_df = pd.DataFrame(
        {
            "id_corrida": ",".join(ids),
            "tipo": tipo,
            "clase_variacion": clase,
            "periodo": largo.index.get_level_values("periodo"),
            "indice": largo.index.get_level_values("indice"),
            "estado_calculo": estados_rep,
            "motivo_error": motivos,
            "periodo_lag": periodo_lag.to_numpy(),
            "version_t": largo["version"].to_numpy(),
            "version_lag": version_lag.to_numpy(),
        },
        index=largo.index,
        columns=_COLS_DIAGNOSTICO,
    )[no_computable].reset_index(drop=True)

    return reporte_df, diagnostico_df


def variacion_desde(
    resultado: ResultadoIndice,
    desde: Periodo,
    hasta: Periodo | None = None,
    incluir_parciales: bool = True,
) -> ResultadoVariacion:
    """Variación total del rango `[desde, hasta]`; una fila por índice.

    Con `incluir_parciales=True`, un índice sin dato exacto en `desde`/`hasta`
    usa el primer/último periodo válido del rango; el periodo real usado se
    registra en `indices_parciales`.
    """
    largo = resultado.resultado.largo
    ids = [m.id_corrida for m in resultado.manifiesto]
    tipo = str(largo["tipo"].iloc[0])

    periodos_todos = sorted(set(largo.index.get_level_values("periodo")))
    if desde not in periodos_todos:
        raise InvarianteViolado(
            f"El periodo 'desde' ({desde}) no existe en el resultado."
        )
    hasta_efectivo: Periodo = hasta if hasta is not None else periodos_todos[-1]
    if hasta is not None and hasta not in periodos_todos:
        raise InvarianteViolado(
            f"El periodo 'hasta' ({hasta}) no existe en el resultado."
        )
    if hasta_efectivo < desde:  # type: ignore[operator]
        raise InvarianteViolado(
            f"'hasta' ({hasta_efectivo}) no puede ser anterior a 'desde' ({desde})."
        )

    rango = [p for p in periodos_todos if desde <= p <= hasta_efectivo]
    valores = largo["indice_replicado"]
    estados = largo["estado_calculo"]
    versiones = largo["version"]
    cobertura = _cobertura(resultado.reporte)
    indices = sorted(set(largo.index.get_level_values("indice")))
    id_corrida_str = ",".join(ids)

    filas_df: list[dict[str, object]] = []
    filas_rep: list[dict[str, object]] = []
    filas_diag: list[dict[str, object]] = []
    filas_parciales: list[dict[str, object]] = []

    for indice in indices:
        validos = [p for p in rango if pd.notna(valores.get((p, indice)))]
        desde_real = resolver_extremo(desde, validos, incluir_parciales, primero=True)
        hasta_real = resolver_extremo(
            hasta_efectivo, validos, incluir_parciales, primero=False
        )

        if desde_real is None or hasta_real is None:
            valor_lag = float(valores.get((desde, indice), float("nan")))
            valor_t = float(valores.get((hasta_efectivo, indice), float("nan")))
            motivo = _motivo_faltante(valor_t, valor_lag)
            filas_rep.append(
                _fila_reporte(
                    hasta_efectivo, indice, desde, "sin_datos", motivo,
                    valor_t, valor_lag, versiones, cobertura,
                    hasta_efectivo, desde,
                )
            )
            filas_diag.append(
                {
                    "id_corrida": id_corrida_str,
                    "tipo": tipo,
                    "clase_variacion": "desde",
                    "periodo": hasta_efectivo,
                    "indice": indice,
                    "estado_calculo": "sin_datos",
                    "motivo_error": motivo,
                    "periodo_lag": desde,
                    "version_t": versiones.get((hasta_efectivo, indice), float("nan")),
                    "version_lag": versiones.get((desde, indice), float("nan")),
                }
            )
            continue

        valor_desde = float(valores.at[(desde_real, indice)])  # type: ignore[arg-type]
        valor_hasta = float(valores.at[(hasta_real, indice)])  # type: ignore[arg-type]
        variacion_pp = (valor_hasta / valor_desde - 1.0) * 100.0
        estado = _estado_derivado(
            str(estados.at[(hasta_real, indice)]),
            str(estados.at[(desde_real, indice)]),
        )
        # incluir_parciales=False excluye índices con estado derivado parcial.
        if incluir_parciales or estado != "parcial":
            filas_df.append(
                {
                    "periodo": hasta_real,
                    "indice": indice,
                    "tipo": tipo,
                    "clase_variacion": "desde",
                    "variacion_pp": variacion_pp,
                    "estado_calculo": estado,
                    "version_t": int(versiones.at[(hasta_real, indice)]),  # type: ignore[arg-type]
                }
            )
        filas_rep.append(
            _fila_reporte(
                hasta_real, indice, desde_real, estado, float("nan"),
                valor_hasta, valor_desde, versiones, cobertura,
                hasta_real, desde_real,
            )
        )
        if desde_real != desde or hasta_real != hasta_efectivo:
            filas_parciales.append(
                {
                    "indice": indice,
                    "periodo_desde_real": desde_real,
                    "periodo_hasta_real": hasta_real,
                }
            )

    if not filas_df:
        raise InvarianteViolado(
            f"Ningún índice tiene datos computables en el rango "
            f"[{desde}, {hasta_efectivo}]."
        )

    df_out = pd.DataFrame(filas_df).set_index(["periodo", "indice"]).sort_index()
    reporte_df = (
        pd.DataFrame(filas_rep, columns=["periodo", "indice", *_COLS_REPORTE])
        .set_index(["periodo", "indice"])
        .sort_index()
    )
    diagnostico_df = pd.DataFrame(filas_diag, columns=_COLS_DIAGNOSTICO)
    indices_parciales = pd.DataFrame(
        filas_parciales,
        columns=["indice", "periodo_desde_real", "periodo_hasta_real"],
    ).set_index("indice")

    manifiesto = ManifestDerivado(
        id_corrida=ids,
        tipo=tipo,
        clase="desde",
        descripcion=f"desde {desde} hasta {hasta_efectivo}",
        fecha=datetime.now(),
    )
    return ResultadoVariacion(
        df_out, manifiesto, reporte_df, diagnostico_df, indices_parciales
    )


def _fila_reporte(
    periodo: Periodo,
    indice: str,
    periodo_lag: Periodo,
    estado: str,
    motivo: object,
    indice_t: float,
    indice_lag: float,
    versiones: pd.Series,
    cobertura: pd.Series | None,
    periodo_t_cob: Periodo,
    periodo_lag_cob: Periodo,
) -> dict[str, object]:
    """Construye una fila del `reporte_df` de `variacion_desde`."""
    def cob(p: Periodo) -> float:
        if cobertura is None:
            return float("nan")
        try:
            return float(cobertura.at[(p, indice)])  # type: ignore[arg-type]
        except KeyError:
            return float("nan")

    return {
        "periodo": periodo,
        "indice": indice,
        "estado_calculo": estado,
        "motivo_error": motivo,
        "periodo_lag": periodo_lag,
        "indice_t": indice_t,
        "indice_lag": indice_lag,
        "version_t": versiones.get((periodo_t_cob, indice), float("nan")),
        "version_lag": versiones.get((periodo_lag_cob, indice), float("nan")),
        "cobertura_pct_t": cob(periodo_t_cob),
        "cobertura_pct_lag": cob(periodo_lag_cob),
    }
