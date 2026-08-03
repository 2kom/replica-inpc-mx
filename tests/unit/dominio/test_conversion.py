from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import pandas as pd
import pytest

from replica_inpc.dominio.conversion import a_mensual, empalmar, rebasar
from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo

# --------------------------------------------------------------------------- helpers


def _manifiesto(
    version: int = 2018,
    tipo: str = "INPC",
    calculador: str = "LaspeyresDirecto",
) -> ManifestCalculo:
    return ManifestCalculo(
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador=calculador,  # type: ignore[arg-type]
        fecha=datetime(2024, 1, 1),
    )


def _resultado(
    rows: list[tuple[Any, str, float | None, str, str | None]],
    version: int = 2018,
    tipo: str = "INPC",
    periodo_referencia: Any = None,
    frontera: pd.DataFrame | None = None,
) -> ResultadoIndice:
    """rows = list of (periodo, indice, valor, estado, motivo)."""
    filas = []
    for periodo, indice, valor, estado, motivo in rows:
        filas.append(
            {
                "periodo": periodo,
                "indice": indice,
                "version": version,
                "tipo": tipo,
                "indice_replicado": valor,
                "estado_calculo": estado,
                "motivo_error": motivo,
            }
        )
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = pd.DataFrame(
        {"version": version, "estado_calculo": [estado for _, _, _, estado, _ in rows]},
        index=df.index,
    )
    diag = pd.DataFrame(
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
    return ResultadoIndice(
        df,
        [_manifiesto(version=version, tipo=tipo)],
        reporte,
        diag,
        periodo_referencia=periodo_referencia,
        frontera=frontera,
    )


# --------------------------------------------------------------------------- empalmar

_p1 = PeriodoQuincenal(2018, 7, 2)
_p2 = PeriodoQuincenal(2018, 8, 1)
_p3 = PeriodoQuincenal(2024, 7, 2)  # traslape
_p4 = PeriodoQuincenal(2024, 8, 1)


def test_empalmar_requiere_minimo_dos() -> None:
    r = _resultado([(_p1, "INPC", 100.0, "ok", None)])
    with pytest.raises(InvarianteViolado):
        empalmar([r])


def test_empalmar_construccion_valida_concatena_manifiestos() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    out = empalmar([r_2018, r_2024])
    assert len(out.manifiesto) == 2


def test_empalmar_sin_frontera_compartida_falla() -> None:
    # r_2010 y r_2024 no comparten ningún periodo — sin frontera válida.
    r_2010 = _resultado([(_p1, "INPC", 100.0, "ok", None)], version=2010)
    r_2024 = _resultado([(_p4, "INPC", 110.0, "ok", None)], version=2024)
    with pytest.raises(InvarianteViolado, match="no comparte ningún periodo"):
        empalmar([r_2010, r_2024])


def test_empalmar_pares_con_frontera_aceptados() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    out = empalmar([r_2018, r_2024])
    assert len(out.manifiesto) == 2


def test_empalmar_tres_versiones_en_una_llamada_ok() -> None:
    # Tres versiones en una sola llamada: renombre transitivo 2010→2013→2018.
    pa = PeriodoQuincenal(2010, 12, 2)
    pb = PeriodoQuincenal(2013, 3, 2)
    pc = PeriodoQuincenal(2018, 7, 2)
    pd_ = PeriodoQuincenal(2018, 8, 1)
    r_2010 = _resultado(
        [(pa, "INPC", 100.0, "ok", None), (pb, "INPC", 103.0, "ok", None)], version=2010
    )
    r_2013 = _resultado(
        [(pb, "INPC", 103.0, "ok", None), (pc, "INPC", 108.0, "ok", None)], version=2013
    )
    r_2018 = _resultado(
        [(pc, "INPC", 110.0, "ok", None), (pd_, "INPC", 112.0, "ok", None)], version=2018
    )
    out = empalmar([r_2010, r_2013, r_2018], forzar=True)
    assert len(out.manifiesto) == 3
    periodos = list(out.df.index.get_level_values("periodo"))
    assert periodos == sorted(periodos)


def test_empalmar_cadena_pares_con_fronteras() -> None:
    # Cada tramo incluye la frontera con el siguiente para formar topología PATH.
    pa = PeriodoQuincenal(2010, 12, 2)
    pb = PeriodoQuincenal(2013, 3, 2)
    pc = PeriodoQuincenal(2018, 7, 2)
    pd_ = PeriodoQuincenal(2024, 7, 2)
    r_2010 = _resultado(
        [(pa, "INPC", 100.0, "ok", None), (pb, "INPC", 103.0, "ok", None)], version=2010
    )
    r_2013 = _resultado(
        [(pb, "INPC", 103.0, "ok", None), (pc, "INPC", 108.0, "ok", None)], version=2013
    )
    r_2018 = _resultado(
        [(pc, "INPC", 110.0, "ok", None), (pd_, "INPC", 118.0, "ok", None)], version=2018
    )
    pe = PeriodoQuincenal(2024, 8, 1)
    r_2024 = _resultado(
        [(pd_, "INPC", 120.0, "ok", None), (pe, "INPC", 122.0, "ok", None)], version=2024
    )

    intermedio_a = empalmar([r_2010, r_2013])
    intermedio_b = empalmar([intermedio_a, r_2018], forzar=True)
    final = empalmar([intermedio_b, r_2024])

    assert len(final.manifiesto) == 4
    periodos = list(final.df.index.get_level_values("periodo"))
    assert periodos == sorted(periodos)


def test_empalmar_tipo_distinto_falla() -> None:
    r_inpc = _resultado([(_p1, "INPC", 100.0, "ok", None)], tipo="INPC")
    r_cog = _resultado([(_p3, "Alimentos", 100.0, "ok", None)], tipo="COG")
    with pytest.raises(InvarianteViolado):
        empalmar([r_inpc, r_cog])


def test_empalmar_periodo_referencia_distintos_sin_forzar_falla() -> None:
    r_2018 = _resultado([(_p1, "INPC", 100.0, "ok", None)], periodo_referencia=_p1)
    r_2024 = _resultado([(_p3, "INPC", 110.0, "ok", None)], periodo_referencia=_p3)
    with pytest.raises(InvarianteViolado):
        empalmar([r_2018, r_2024])


def test_empalmar_periodo_referencia_distintos_con_forzar_warning() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)], periodo_referencia=_p1
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], periodo_referencia=_p3
    )
    with pytest.warns(UserWarning):
        out = empalmar([r_2018, r_2024], forzar=True)
    # último cronológico es r_2024 con _p3
    assert out.periodo_referencia == _p3


def test_empalmar_mezcla_none_con_valor_hereda_valor() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)],
        periodo_referencia=None,
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], periodo_referencia=_p3
    )
    out = empalmar([r_2018, r_2024])
    assert out.periodo_referencia == _p3


def test_empalmar_todos_none_resulta_none() -> None:
    r_2018 = _resultado([(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)])
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    out = empalmar([r_2018, r_2024])
    assert out.periodo_referencia is None


def test_empalmar_ordena_cronologicamente() -> None:
    r_2018 = _resultado(
        [
            (_p1, "INPC", 100.0, "ok", None),
            (_p2, "INPC", 101.0, "ok", None),
            (_p3, "INPC", 108.0, "ok", None),
        ]
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    out = empalmar([r_2024, r_2018])  # orden inverso
    periodos = list(out.df.index.get_level_values("periodo"))
    assert periodos == sorted(periodos)


def test_empalmar_traslape_queda_en_anterior() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 105.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 999.0, "ok", None), (_p4, "INPC", 110.0, "ok", None)], version=2024
    )
    out = empalmar([r_2018, r_2024])
    # En _p3 prevalece r_2018 (valor 105, version 2018) — el valor de r_2024
    # en el traslape es derivado de r_2018 por construcción.
    fila_largo = out.resultado.largo.loc[cast(Any, (_p3, "INPC"))]
    assert fila_largo["version"] == 2018
    assert fila_largo["indice_replicado"] == 105.0


def test_empalmar_normalizacion_aplica_a_df_y_reporte() -> None:
    # CCIF division: "comunicaciones" (2018) → "informacion y comunicacion" (2024)
    r_2018 = _resultado(
        [(_p1, "comunicaciones", 100.0, "ok", None), (_p3, "comunicaciones", 108.0, "ok", None)],
        version=2018,
        tipo="CCIF DIVISION",
    )
    r_2024 = _resultado(
        [
            (_p3, "informacion y comunicacion", 110.0, "ok", None),
            (_p4, "informacion y comunicacion", 112.0, "ok", None),
        ],
        version=2024,
        tipo="CCIF DIVISION",
    )
    out = empalmar([r_2018, r_2024])  # version_nombres=None → max=2024
    indices_df = set(out.df.index.get_level_values("indice"))
    indices_rep = set(out.reporte.index.get_level_values("indice"))
    assert indices_df == {"informacion y comunicacion"}
    assert indices_rep == indices_df  # reporte sincronizado


def test_empalmar_version_nombres_explicito_2024() -> None:
    # Caller pide nomenclatura 2024 explícita.
    r_2018 = _resultado(
        [(_p1, "comunicaciones", 100.0, "ok", None), (_p3, "comunicaciones", 108.0, "ok", None)],
        version=2018,
        tipo="CCIF DIVISION",
    )
    r_2024 = _resultado(
        [
            (_p3, "informacion y comunicacion", 110.0, "ok", None),
            (_p4, "informacion y comunicacion", 112.0, "ok", None),
        ],
        version=2024,
        tipo="CCIF DIVISION",
    )
    out = empalmar([r_2024, r_2018], version_nombres=2024)
    assert set(out.df.index.get_level_values("indice")) == {"informacion y comunicacion"}


def test_empalmar_version_nombres_explicito_2018_invierte() -> None:
    # version_nombres=2018: r_2024 tramo se invierte (2024 -> 2018).
    r_2018 = _resultado(
        [(_p1, "comunicaciones", 100.0, "ok", None), (_p3, "comunicaciones", 108.0, "ok", None)],
        version=2018,
        tipo="CCIF DIVISION",
    )
    r_2024 = _resultado(
        [
            (_p3, "informacion y comunicacion", 110.0, "ok", None),
            (_p4, "informacion y comunicacion", 112.0, "ok", None),
        ],
        version=2024,
        tipo="CCIF DIVISION",
    )
    out = empalmar([r_2018, r_2024], version_nombres=2018)
    assert set(out.df.index.get_level_values("indice")) == {"comunicaciones"}


def test_empalmar_bloques_preempalmados_ok() -> None:
    # Escenario real: dos bloques pre-empalmados con span>1 entre sus max_versions.
    # pre_r = empalmar([r_2010, r_2013]) → max_version=2013
    # inpc_pos = empalmar([r_2018, r_2024]) → max_version=2024
    # empalmar([pre_r, inpc_pos]): renombre transitivo 2013→2018→2024.
    pa = PeriodoQuincenal(2010, 12, 2)
    pb = PeriodoQuincenal(2013, 3, 2)
    pc = PeriodoQuincenal(2018, 7, 2)
    pd_ = PeriodoQuincenal(2024, 7, 2)
    pe = PeriodoQuincenal(2024, 8, 1)
    r_2010 = _resultado(
        [(pa, "INPC", 100.0, "ok", None), (pb, "INPC", 103.0, "ok", None)], version=2010
    )
    r_2013 = _resultado(
        [(pb, "INPC", 103.0, "ok", None), (pc, "INPC", 108.0, "ok", None)], version=2013
    )
    r_2018 = _resultado(
        [(pc, "INPC", 110.0, "ok", None), (pd_, "INPC", 118.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(pd_, "INPC", 120.0, "ok", None), (pe, "INPC", 122.0, "ok", None)], version=2024
    )
    pre_r = empalmar([r_2010, r_2013])
    inpc_pos = empalmar([r_2018, r_2024])
    final = empalmar([pre_r, inpc_pos])
    assert len(final.manifiesto) == 4
    periodos = list(final.df.index.get_level_values("periodo"))
    assert periodos == sorted(periodos)


def test_empalmar_version_nombres_fuera_de_rango_falla() -> None:
    # inputs 2018+2024, pide 2010 como destino: fuera del rango [2018, 2024].
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    with pytest.raises(InvarianteViolado, match="fuera del rango"):
        empalmar([r_2018, r_2024], version_nombres=2010)


def test_empalmar_input_multiversion_usa_nomenclatura_max() -> None:
    # Caso: input ya-empalmado tiene filas con version=2010 y version=2013, pero
    # su nomenclatura es 2013 (max manifests). El siguiente empalmar con r_2018
    # debe aplicar mapa 2013->2018 a TODO el tramo, no usar version per-fila.
    # Como no hay mapa 2010<->2013 catalogado, simulamos con tipo cuyo mapa
    # actualizado 2018->2024 existe. Construimos input ya-empalmado entre 2018 y 2024:
    r_2018 = _resultado(
        [(_p1, "comunicaciones", 100.0, "ok", None), (_p3, "comunicaciones", 108.0, "ok", None)],
        version=2018,
        tipo="CCIF DIVISION",
    )
    r_2024 = _resultado(
        [
            (_p3, "informacion y comunicacion", 110.0, "ok", None),
            (_p4, "informacion y comunicacion", 112.0, "ok", None),
        ],
        version=2024,
        tipo="CCIF DIVISION",
    )
    intermedio = empalmar([r_2018, r_2024])
    # Después de empalmar, nomenclatura=2024. Todas las filas tienen índice
    # "informacion y comunicacion" (las del tramo 2018 fueron renombradas).
    assert set(intermedio.df.index.get_level_values("indice")) == {"informacion y comunicacion"}
    # El manifiesto tiene dos versions (2018, 2024) pero la nomenclatura es max=2024.
    assert {m.version for m in intermedio.manifiesto} == {2018, 2024}


def test_empalmar_inpc_no_afectado_por_normalizacion() -> None:
    r_2018 = _resultado(
        [(_p1, "INPC", 100.0, "ok", None), (_p3, "INPC", 108.0, "ok", None)], version=2018
    )
    r_2024 = _resultado(
        [(_p3, "INPC", 110.0, "ok", None), (_p4, "INPC", 112.0, "ok", None)], version=2024
    )
    out = empalmar([r_2018, r_2024])
    assert set(out.df.index.get_level_values("indice")) == {"INPC"}


def test_empalmar_mensual_emite_warning() -> None:
    r1 = _resultado(
        [
            (PeriodoMensual(2024, 1), "INPC", 100.0, "ok", None),
            (PeriodoMensual(2024, 2), "INPC", 101.0, "ok", None),
        ],
        version=2018,
    )
    r2 = _resultado(
        [
            (PeriodoMensual(2024, 2), "INPC", 101.5, "ok", None),
            (PeriodoMensual(2024, 3), "INPC", 102.0, "ok", None),
        ],
        version=2024,
    )
    with pytest.warns(UserWarning):
        empalmar([r1, r2])


# --------------------------------------------------------------------------- rebasar

_r1 = PeriodoQuincenal(2018, 6, 2)
_r2 = PeriodoQuincenal(2018, 7, 2)
_r3 = PeriodoQuincenal(2018, 8, 1)


def test_rebasar_periodo_referencia_queda_en_100() -> None:
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 133.112, "ok", None),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    rb = rebasar(r, _r2)
    assert rb.df.at[(_r2, "INPC"), "indice_replicado"] == pytest.approx(100.0)


def test_rebasar_proporcional() -> None:
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 133.112, "ok", None),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    rb = rebasar(r, _r2)
    assert rb.df.at[(_r1, "INPC"), "indice_replicado"] == pytest.approx(120.0 * 100.0 / 133.112)
    assert rb.df.at[(_r3, "INPC"), "indice_replicado"] == pytest.approx(135.0 * 100.0 / 133.112)


def test_rebasar_periodo_inexistente_falla() -> None:
    # periodo_referencia no existe para NINGÚN índice → toda la operación falla
    # (antes devolvía el resultado sin reescalar con periodo_referencia seteado,
    # un estado engañoso: ver hallazgo de auditoría 2026-08-03).
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r3, "INPC", 135.0, "ok", None)])
    with pytest.raises(InvarianteViolado, match="ningún índice tiene dato"):
        rebasar(r, _r2)


def test_rebasar_indice_sin_referencia_emite_warning_y_no_rebase() -> None:
    # 2 índices: "INPC" sí tiene dato en periodo_referencia, "COG" no → "COG"
    # queda sin rebasar (warning), "INPC" sí se reescala normal.
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 133.112, "ok", None),
            (_r3, "INPC", 135.0, "ok", None),
            (_r1, "COG", 50.0, "ok", None),
            (_r3, "COG", 55.0, "ok", None),
        ]
    )
    with pytest.warns(UserWarning, match="COG"):
        rb = rebasar(r, _r2)
    assert rb.df.at[(_r2, "INPC"), "indice_replicado"] == pytest.approx(100.0)
    assert rb.df.at[(_r1, "COG"), "indice_replicado"] == pytest.approx(50.0)
    assert rb.df.at[(_r3, "COG"), "indice_replicado"] == pytest.approx(55.0)


def test_rebasar_frontera_indice_sin_referencia_queda_intacta() -> None:
    # "COG" no tiene dato en periodo_referencia (huérfano) pero SÍ tiene ancla de
    # junta válida en _frontera — no debe pisarse con NaN (ver hallazgo de
    # auditoría 2026-08-03: antes multiplicaba por factores.get(i, NaN)).
    frontera_in = pd.DataFrame(
        {
            "version_old": [2018, 2018],
            "version_new": [2024, 2024],
            "indice_incidencia_old": [99.5, 48.0],
            "indice_replicado_old": [99.5, 48.0],
        },
        index=pd.MultiIndex.from_arrays([[_r3, _r3], ["INPC", "COG"]], names=["periodo", "indice"]),
    )
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 133.112, "ok", None),
            (_r3, "INPC", 135.0, "ok", None),
            (_r3, "COG", 55.0, "ok", None),
        ],
        frontera=frontera_in,
    )
    with pytest.warns(UserWarning, match="COG"):
        rb = rebasar(r, _r2)
    assert rb._frontera is not None
    assert rb._frontera.at[(_r3, "COG"), "indice_replicado_old"] == pytest.approx(48.0)
    factor_inpc = 100.0 / 133.112
    assert rb._frontera.at[(_r3, "INPC"), "indice_replicado_old"] == pytest.approx(
        99.5 * factor_inpc
    )


def test_rebasar_sin_datos_en_referencia_falla() -> None:
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", None, "sin_datos", "faltantes"),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    with pytest.raises(InvarianteViolado):
        rebasar(r, _r2)


def test_rebasar_nan_con_estado_ok_inconsistente_falla() -> None:
    # estado_calculo=ok pero indice_replicado=NaN → inconsistente (no debería
    # ocurrir con datos reales, pero rebasar debe detectarlo si pasa).
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r2, "INPC", None, "ok", None)])
    with pytest.raises(InvarianteViolado, match="NaN"):
        rebasar(r, _r2)


def test_rebasar_cero_en_referencia_falla() -> None:
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 0.0, "ok", None),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    with pytest.raises(InvarianteViolado, match="0"):
        rebasar(r, _r2)


def test_rebasar_valor_base_distinto_de_100() -> None:
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r2, "INPC", 130.0, "ok", None)])
    rb = rebasar(r, _r2, valor_base=200.0)
    assert rb.df.at[(_r2, "INPC"), "indice_replicado"] == pytest.approx(200.0)
    assert rb.df.at[(_r1, "INPC"), "indice_replicado"] == pytest.approx(120.0 * 200.0 / 130.0)


@pytest.mark.parametrize(
    "valor_base", [float("nan"), float("inf"), float("-inf"), 0.0, -100.0], ids=str
)
def test_rebasar_valor_base_invalido_falla(valor_base: float) -> None:
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r2, "INPC", 130.0, "ok", None)])
    with pytest.raises(InvarianteViolado, match="valor_base"):
        rebasar(r, _r2, valor_base=valor_base)


def test_rebasar_setea_periodo_referencia() -> None:
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r2, "INPC", 130.0, "ok", None)])
    rb = rebasar(r, _r2)
    assert rb.periodo_referencia == _r2


def test_rebasar_propaga_manifiesto() -> None:
    r = _resultado([(_r1, "INPC", 120.0, "ok", None), (_r2, "INPC", 130.0, "ok", None)])
    rb = rebasar(r, _r2)
    assert rb.manifiesto == r.manifiesto


def test_rebasar_referencia_parcial_acepta() -> None:
    # estado "parcial" en periodo_referencia (solo 1 quincena disponible en el
    # mes) trae valor real → se acepta como base, igual que "ok"/"rellenado".
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 130.0, "parcial", None),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    rb = rebasar(r, _r2)
    assert rb.df.at[(_r2, "INPC"), "indice_replicado"] == pytest.approx(100.0)


def test_rebasar_referencia_fallida_falla() -> None:
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", None, "fallida", "error interno"),
            (_r3, "INPC", 135.0, "ok", None),
        ]
    )
    with pytest.raises(InvarianteViolado):
        rebasar(r, _r2)


def test_rebasar_filas_sin_datos_y_fallida_fuera_de_referencia_preservadas() -> None:
    # Filas con estado sin_datos/fallida en OTROS periodos (no el de referencia)
    # no se tocan. Valores centinela FINITOS (999.0/888.0, no NaN real — situación
    # que no ocurre con datos reales, ver test_rebasar_nan_con_estado_ok_inconsistente_falla
    # para el caso inverso) para que el assert distinga "la máscara excluyó la fila"
    # de "la fila era NaN de por sí y multiplicar por cualquier factor sigue dando NaN".
    r = _resultado(
        [
            (_r1, "INPC", 999.0, "sin_datos", "faltantes"),
            (_r2, "INPC", 130.0, "ok", None),
            (_r3, "INPC", 888.0, "fallida", "error interno"),
        ]
    )
    rb = rebasar(r, _r2)
    fila_sin_datos = rb.resultado.largo.loc[cast(Any, (_r1, "INPC"))]
    assert fila_sin_datos["indice_replicado"] == pytest.approx(999.0)
    assert fila_sin_datos["estado_calculo"] == "sin_datos"
    assert fila_sin_datos["motivo_error"] == "faltantes"
    fila_fallida = rb.resultado.largo.loc[cast(Any, (_r3, "INPC"))]
    assert fila_fallida["indice_replicado"] == pytest.approx(888.0)
    assert fila_fallida["estado_calculo"] == "fallida"
    assert fila_fallida["motivo_error"] == "error interno"


def test_rebasar_acepta_referencia_rellenado() -> None:
    # periodo_referencia con estado "rellenado" tiene valor → debe rebasar sin error
    r = _resultado(
        [
            (_r1, "INPC", 120.0, "ok", None),
            (_r2, "INPC", 125.0, "rellenado", None),
            (_r3, "INPC", 130.0, "ok", None),
        ]
    )
    rb = rebasar(r, _r2)
    fila = rb.resultado.largo.loc[cast(Any, (_r2, "INPC"))]
    assert fila["indice_replicado"] == pytest.approx(100.0)
    assert fila["estado_calculo"] == "rellenado"


# --------------------------------------------------------------------------- a_mensual

_q1 = PeriodoQuincenal(2024, 1, 1)
_q2 = PeriodoQuincenal(2024, 1, 2)
_q3 = PeriodoQuincenal(2024, 2, 1)
_q4 = PeriodoQuincenal(2024, 2, 2)


def test_a_mensual_ambas_quincenas_ok() -> None:
    r = _resultado([(_q1, "INPC", 100.0, "ok", None), (_q2, "INPC", 102.0, "ok", None)])
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "ok"
    assert fila["indice_replicado"] == pytest.approx(101.0)
    assert isinstance(rm.df.index.get_level_values("periodo")[0], PeriodoMensual)


@pytest.mark.parametrize("periodo,valor", [(_q1, 100.0), (_q2, 102.0)])
def test_a_mensual_una_quincena_es_parcial(periodo: PeriodoQuincenal, valor: float) -> None:
    r = _resultado([(periodo, "INPC", valor, "ok", None)])
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "parcial"
    assert fila["indice_replicado"] == pytest.approx(valor)


def test_a_mensual_ambas_sin_datos() -> None:
    r = _resultado(
        [
            (_q1, "INPC", None, "sin_datos", "faltantes"),
            (_q2, "INPC", None, "sin_datos", "faltantes"),
        ]
    )
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "sin_datos"
    assert pd.isna(fila["indice_replicado"])


def test_a_mensual_una_fallida_propaga() -> None:
    r = _resultado(
        [
            (_q1, "INPC", 100.0, "ok", None),
            (_q2, "INPC", None, "fallida", "error de calculo"),
        ]
    )
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "fallida"
    assert pd.isna(fila["indice_replicado"])
    assert fila["motivo_error"] == "error de calculo"


def test_a_mensual_version_de_2q_preferida() -> None:
    # Construir manualmente df con versiones distintas en q1 y q2
    df = pd.DataFrame(
        [
            {
                "periodo": _q1,
                "indice": "INPC",
                "version": 2018,
                "tipo": "INPC",
                "indice_replicado": 100.0,
                "estado_calculo": "ok",
                "motivo_error": None,
            },
            {
                "periodo": _q2,
                "indice": "INPC",
                "version": 2024,
                "tipo": "INPC",
                "indice_replicado": 102.0,
                "estado_calculo": "ok",
                "motivo_error": None,
            },
        ]
    )
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = pd.DataFrame(
        {"version": [2018, 2024], "estado_calculo": ["ok", "ok"]}, index=df.index
    )
    diag = pd.DataFrame(
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
    r = ResultadoIndice(df, [_manifiesto(version=2018), _manifiesto(version=2024)], reporte, diag)
    rm = a_mensual(r)
    assert rm.resultado.largo["version"].iloc[0] == 2024


def test_a_mensual_multiples_meses() -> None:
    r = _resultado(
        [
            (_q1, "INPC", 100.0, "ok", None),
            (_q2, "INPC", 102.0, "ok", None),
            (_q3, "INPC", 104.0, "ok", None),
            (_q4, "INPC", 106.0, "ok", None),
        ]
    )
    rm = a_mensual(r)
    assert len(rm.df) == 2
    periodos = list(rm.df.index.get_level_values("periodo"))
    assert periodos[0] == PeriodoMensual(2024, 1)
    assert periodos[1] == PeriodoMensual(2024, 2)


def test_a_mensual_input_mensual_falla() -> None:
    r = _resultado([(PeriodoMensual(2024, 1), "INPC", 100.0, "ok", None)])
    with pytest.raises(InvarianteViolado, match="quincenal"):
        a_mensual(r)


def test_a_mensual_propaga_manifiesto() -> None:
    r = _resultado([(_q1, "INPC", 100.0, "ok", None), (_q2, "INPC", 102.0, "ok", None)])
    rm = a_mensual(r)
    assert rm.manifiesto == r.manifiesto


def test_a_mensual_periodo_referencia_convierte_a_mensual() -> None:
    r = _resultado(
        [(_q1, "INPC", 100.0, "ok", None), (_q2, "INPC", 102.0, "ok", None)],
        periodo_referencia=_q1,
    )
    rm = a_mensual(r)
    assert rm.periodo_referencia == PeriodoMensual(_q1.año, _q1.mes)


def test_a_mensual_sin_periodo_referencia_queda_none() -> None:
    r = _resultado(
        [(_q1, "INPC", 100.0, "ok", None), (_q2, "INPC", 102.0, "ok", None)],
        periodo_referencia=None,
    )
    rm = a_mensual(r)
    assert rm.periodo_referencia is None


def test_a_mensual_ambas_rellenado_produce_rellenado() -> None:
    r = _resultado(
        [(_q1, "INPC", 100.0, "rellenado", None), (_q2, "INPC", 102.0, "rellenado", None)],
        version=2024,
    )
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "rellenado"
    assert fila["indice_replicado"] == pytest.approx(101.0)


def test_a_mensual_una_rellenado_produce_rellenado() -> None:
    # 1Q rellenado + 2Q ok → mensual rellenado (dato aproximado presente)
    r = _resultado(
        [(_q1, "INPC", 100.0, "rellenado", None), (_q2, "INPC", 102.0, "ok", None)], version=2024
    )
    rm = a_mensual(r)
    fila = rm.resultado.largo.iloc[0]
    assert fila["estado_calculo"] == "rellenado"
    assert fila["indice_replicado"] == pytest.approx(101.0)


def test_a_mensual_reporte_tiene_periodo_mensual() -> None:
    r = _resultado([(_q1, "INPC", 100.0, "ok", None), (_q2, "INPC", 102.0, "ok", None)])
    rm = a_mensual(r)
    periodos_rep = rm.reporte.index.get_level_values("periodo")
    assert all(isinstance(p, PeriodoMensual) for p in periodos_rep)
    assert rm.reporte["version"].iloc[0] == 2018
    assert rm.reporte["estado_calculo"].iloc[0] == "ok"
