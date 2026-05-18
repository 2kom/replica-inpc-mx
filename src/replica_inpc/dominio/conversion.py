from __future__ import annotations

import warnings

import pandas as pd

from replica_inpc.dominio.correspondencia_canastas import RENOMBRES_INDICES
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import VersionCanasta

_ESTADOS_CON_VALOR = frozenset({"ok", "parcial"})
_ORDEN_VERSIONES = (2010, 2013, 2018, 2024)


def _construir_mapa_renombre(
    tipo: str, version_origen: int, version_canonica: int
) -> dict[str, str]:
    if tipo not in RENOMBRES_INDICES or version_origen == version_canonica:
        return {}
    if version_origen < version_canonica:
        return dict(RENOMBRES_INDICES[tipo].get(version_origen, {}))
    mapa_forward = RENOMBRES_INDICES[tipo].get(version_canonica, {})
    return {v: k for k, v in mapa_forward.items()}


def _aplicar_renombre(df: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    if not mapa or df.empty:
        return df
    new_indice = df.index.get_level_values("indice").map(lambda x: mapa.get(x, x))
    new_periodo = df.index.get_level_values("periodo")
    df_nuevo = df.copy()
    df_nuevo.index = pd.MultiIndex.from_arrays(
        [new_periodo, new_indice], names=["periodo", "indice"]
    )
    return df_nuevo


def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: VersionCanasta | None = None,
) -> ResultadoIndice:
    """Concatena tramos del mismo `tipo` en un único `ResultadoIndice`.

    Normaliza nombres de categorías entre versiones de canasta. En traslapes,
    las filas del input anterior (cronológico) prevalecen — el valor del tramo
    posterior en el traslape es derivado del anterior por construcción.
    """
    if len(resultados) < 2:
        raise InvarianteViolado("empalmar requiere al menos 2 ResultadoIndice.")

    tipos = {m.tipo for r in resultados for m in r.manifiesto}
    if len(tipos) != 1:
        raise InvarianteViolado(
            f"empalmar requiere mismo 'tipo' entre todos los inputs; recibió {sorted(tipos)}"
        )

    # Nomenclatura por input = max(manifest.versions). Tras un empalmar previo,
    # todas las filas quedan en la nomenclatura del max de versiones; las
    # versions de cada fila reflejan origen de cálculo, no nomenclatura.
    # version_nombres (si se pasa explícito) también participa del span check:
    # no se puede pedir destino fuera del rango de un paso adyacente.
    nomenclaturas_set = {max(m.version for m in r.manifiesto) for r in resultados}
    if version_nombres is not None:
        nomenclaturas_set.add(int(version_nombres))
    nomenclaturas = sorted(nomenclaturas_set)
    idx_min = _ORDEN_VERSIONES.index(nomenclaturas[0])
    idx_max = _ORDEN_VERSIONES.index(nomenclaturas[-1])
    if idx_max - idx_min > 1:
        raise InvarianteViolado(
            f"empalmar admite a lo más un paso adyacente en {list(_ORDEN_VERSIONES)}; "
            f"nomenclaturas (inputs + version_nombres) = {nomenclaturas} "
            f"(span {idx_max - idx_min} pasos). Encadenar empalmar por pares vecinos."
        )

    refs = [r.periodo_referencia for r in resultados]
    refs_explicitas = [r for r in refs if r is not None]
    refs_distintas = set(refs_explicitas)
    if len(refs_distintas) > 1 and not forzar:
        raise InvarianteViolado(
            f"empalmar recibió periodo_referencia distintos {sorted(map(str, refs_distintas))} "
            "y forzar=False"
        )

    primer_periodo = resultados[0]._df_completo.index.get_level_values("periodo")[0]
    if not isinstance(primer_periodo, PeriodoQuincenal):
        warnings.warn(
            "empalmar recibió ResultadoIndice mensuales. El mes frontera puede perder "
            "una quincena. Usa a_mensual(empalmar([r1, r2])) en su lugar.",
            UserWarning,
            stacklevel=2,
        )

    ordenados = sorted(
        resultados,
        key=lambda r: r._df_completo.index.get_level_values("periodo").min(),
    )

    if version_nombres is None:
        vc = max(int(v) for r in ordenados for v in r._df_completo["version"].unique())
    else:
        vc = int(version_nombres)

    tipo_unico = next(iter(tipos))

    periodos_anteriores: set[object] = set()
    dfs_indice: list[pd.DataFrame] = []
    dfs_reporte: list[pd.DataFrame] = []
    dfs_diag: list[pd.DataFrame] = []
    for r in ordenados:
        df_completo = r._df_completo
        reporte = r.reporte
        periodos_propios = set(df_completo.index.get_level_values("periodo"))
        periodos_a_incluir = periodos_propios - periodos_anteriores

        df_filtrado = df_completo[
            df_completo.index.get_level_values("periodo").isin(periodos_a_incluir)
        ]
        rep_filtrado = reporte[reporte.index.get_level_values("periodo").isin(periodos_a_incluir)]

        # Nomenclatura del tramo = max(manifest.versions). Para inputs
        # ya-empalmados con múltiples versions a nivel de fila, la nomenclatura
        # del índice es uniforme (último renombre aplicado al empalmar previo).
        version_origen = max(m.version for m in r.manifiesto)
        mapa = _construir_mapa_renombre(tipo_unico, version_origen, vc)

        dfs_indice.append(_aplicar_renombre(df_filtrado, mapa))
        dfs_reporte.append(_aplicar_renombre(rep_filtrado, mapa))
        dfs_diag.append(r.diagnostico)
        periodos_anteriores |= periodos_propios

    df_combinado = pd.concat(dfs_indice)
    df_combinado.sort_index(level="periodo", sort_remaining=False, inplace=True)

    reporte_combinado = pd.concat(dfs_reporte)
    reporte_combinado.sort_index(level="periodo", sort_remaining=False, inplace=True)

    diag_combinado = pd.concat(dfs_diag, ignore_index=True)

    manifiesto_combinado = [m for r in ordenados for m in r.manifiesto]

    if len(refs_distintas) == 0:
        periodo_referencia_out = None
    elif len(refs_distintas) == 1:
        periodo_referencia_out = next(iter(refs_distintas))
    else:
        elegido = ordenados[-1].periodo_referencia
        warnings.warn(
            f"empalmar recibió periodo_referencia distintos {sorted(map(str, refs_distintas))}; "
            f"forzar=True activo; prevalece el del último input cronológico: {elegido}",
            UserWarning,
            stacklevel=2,
        )
        periodo_referencia_out = elegido

    return ResultadoIndice(
        df_combinado,
        manifiesto_combinado,
        reporte_combinado,
        diag_combinado,
        periodo_referencia=periodo_referencia_out,
    )


def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual,
    valor_base: float = 100.0,
) -> ResultadoIndice:
    """Reexpresa cada índice a una nueva referencia usando el valor replicado propio.

    Endógeno: el denominador es el valor replicado del propio resultado en
    `periodo_referencia`.
    """
    df = resultado._df_completo.copy()
    indices_unicos = df.index.get_level_values("indice").unique()

    for indice in indices_unicos:
        key = (periodo_referencia, indice)
        if key not in df.index:
            raise InvarianteViolado(
                f"periodo_referencia {periodo_referencia} no existe para índice '{indice}'."
            )
        fila_base = df.loc[key]
        estado_base = fila_base["estado_calculo"]
        if estado_base not in _ESTADOS_CON_VALOR:
            raise InvarianteViolado(
                f"El valor base de '{indice}' en {periodo_referencia} no está disponible "
                f"(estado_calculo='{estado_base}')."
            )
        base_raw = fila_base["indice_replicado"]
        if pd.isna(base_raw):
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es NaN; "
                f"estado_calculo='{estado_base}' es inconsistente."
            )
        base = float(base_raw)
        if base == 0:
            raise InvarianteViolado(
                f"indice_replicado de '{indice}' en {periodo_referencia} es 0; no rebasable."
            )

        mask_indice = df.index.get_level_values("indice") == indice
        mask_valor = df["estado_calculo"].isin(_ESTADOS_CON_VALOR)
        df.loc[mask_indice & mask_valor, "indice_replicado"] = (
            df.loc[mask_indice & mask_valor, "indice_replicado"].astype(float) * valor_base / base
        )

    return ResultadoIndice(
        df,
        resultado.manifiesto,
        resultado.reporte,
        resultado.diagnostico,
        periodo_referencia=periodo_referencia,
    )


def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
    """Convierte un ResultadoIndice quincenal a periodos mensuales.

    Promedio simple 1Q+2Q. Si solo una quincena disponible → `parcial`.
    """
    df = resultado._df_completo
    periodos = df.index.get_level_values("periodo")

    if not all(isinstance(p, PeriodoQuincenal) for p in periodos):
        raise InvarianteViolado("a_mensual requiere un ResultadoIndice quincenal")

    df_flat = df.copy()
    df_flat["_año"] = [p.año for p in periodos]
    df_flat["_mes"] = [p.mes for p in periodos]
    df_flat["_quincena"] = [p.quincena for p in periodos]
    df_flat["_indice"] = df.index.get_level_values("indice")
    df_flat = df_flat.reset_index(drop=True).set_index(["_año", "_mes", "_indice"])

    q1 = df_flat[df_flat["_quincena"] == 1]
    q2 = df_flat[df_flat["_quincena"] == 2]

    all_groups = q1.index.union(q2.index)
    q1_r = q1.reindex(all_groups)
    q2_r = q2.reindex(all_groups)

    version = q2_r["version"].fillna(q1_r["version"])
    tipo = q2_r["tipo"].fillna(q1_r["tipo"])

    v1 = q1_r["indice_replicado"]
    v2 = q2_r["indice_replicado"]
    v1_ok = v1.notna()
    v2_ok = v2.notna()
    both_ok = v1_ok & v2_ok
    one_ok = v1_ok ^ v2_ok

    fallida_q1 = (q1_r["estado_calculo"] == "fallida").fillna(False)
    fallida_q2 = (q2_r["estado_calculo"] == "fallida").fillna(False)
    any_fallida = fallida_q1 | fallida_q2
    null_mask = ~any_fallida & ~both_ok & ~one_ok

    estado_calculo = pd.Series("sin_datos", index=all_groups, dtype=object)
    estado_calculo[any_fallida] = "fallida"
    estado_calculo[~any_fallida & both_ok] = "ok"
    estado_calculo[~any_fallida & one_ok] = "parcial"

    val_avg = (v1 + v2) / 2
    val_one = v1.fillna(v2)
    indice_replicado = pd.Series(float("nan"), index=all_groups)
    indice_replicado[~any_fallida & both_ok] = val_avg[~any_fallida & both_ok]
    indice_replicado[~any_fallida & one_ok] = val_one[~any_fallida & one_ok]

    motivo_q1 = q1_r["motivo_error"]
    motivo_q2 = q2_r["motivo_error"]
    motivo_fallida_s = motivo_q1.where(fallida_q1, motivo_q2)
    motivo_faltante_s = motivo_q2.where(motivo_q2.notna(), motivo_q1)
    motivo_error = pd.Series(None, index=all_groups, dtype=object)
    motivo_error[any_fallida] = motivo_fallida_s[any_fallida]
    motivo_error[null_mask] = motivo_faltante_s[null_mask]

    años = all_groups.get_level_values("_año")
    meses = all_groups.get_level_values("_mes")
    indices = all_groups.get_level_values("_indice")
    periodos_mensuales = [PeriodoMensual(int(a), int(m)) for a, m in zip(años, meses)]

    df_result = pd.DataFrame(
        {
            "version": version.values,
            "tipo": tipo.values,
            "indice_replicado": indice_replicado.values,
            "estado_calculo": estado_calculo.values,
            "motivo_error": motivo_error.values,
        },
        index=pd.MultiIndex.from_arrays([periodos_mensuales, indices], names=["periodo", "indice"]),
    )

    df_result.sort_index(level="periodo", sort_remaining=False, inplace=True)

    # ResultadoIndice exige fila por cada manifiesto. Tras a_mensual, una version
    # puede perder todas sus filas (ej: q1=2018, q2=2024 → mensual hereda 2024 por
    # preferencia 2Q). Se descartan manifiestos huérfanos; si todos quedarían
    # huérfanos, se preserva la lista original como fallback de provenance.
    pares_presentes = set(zip(df_result["version"], df_result["tipo"]))
    manifiesto_filtrado = [
        m for m in resultado.manifiesto if (m.version, m.tipo) in pares_presentes
    ]
    if not manifiesto_filtrado:
        manifiesto_filtrado = resultado.manifiesto

    return ResultadoIndice(
        df_result,
        manifiesto_filtrado,
        resultado.reporte,
        resultado.diagnostico,
        periodo_referencia=None,
    )
