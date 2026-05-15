from __future__ import annotations

import pandas as pd
import pytest

from replica_inpc.dominio.calculo.incidencias import (
    incidencia_acumulada_anual,
    incidencia_desde,
    incidencia_periodica,
)
from replica_inpc.dominio.calculo.variaciones import variacion_periodica
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.canasta import CanastaCanonica
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.tipos import ManifestUnidad

# -- periodos ------------------------------------------------------------------

_DIC18 = PeriodoMensual(2018, 12)
_ENE = PeriodoMensual(2019, 1)
_FEB = PeriodoMensual(2019, 2)

# -- helpers -------------------------------------------------------------------


def _indice(
    data: dict[str, list[tuple[object, float | None]]],
    *,
    tipo: str,
    id_corrida: str,
    version: int = 2018,
    estados: dict[tuple[object, str], str] | None = None,
    periodo_referencia: object | None = None,
) -> ResultadoIndice:
    rows = []
    for indice, pares in data.items():
        for periodo, valor in pares:
            est = "ok" if valor is not None else "sin_datos"
            if estados and (periodo, indice) in estados:
                est = estados[(periodo, indice)]
            rows.append(
                {
                    "periodo": periodo,
                    "indice": indice,
                    "version": version,
                    "tipo": tipo,
                    "indice_replicado": float("nan") if valor is None else float(valor),
                    "estado_calculo": est,
                }
            )
    df = pd.DataFrame(rows).set_index(["periodo", "indice"])
    manifiesto = [ManifestUnidad(id_corrida, version, tipo, "LaspeyresDirecto")]  # type: ignore[arg-type]
    return ResultadoIndice(
        df, manifiesto, pd.DataFrame(), pd.DataFrame(), periodo_referencia
    )


def _inpc(estados: dict[tuple[object, str], str] | None = None) -> ResultadoIndice:
    # INPC = (60*I_A + 40*I_B) / 100 — consistente con la canasta.
    return _indice(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0), (_FEB, 104.0)]},
        tipo="inpc",
        id_corrida="ci",
        estados=estados,
    )


def _clas(estados: dict[tuple[object, str], str] | None = None) -> ResultadoIndice:
    return _indice(
        {
            "A": [(_DIC18, 100.0), (_ENE, 110.0), (_FEB, 120.0)],
            "B": [(_DIC18, 100.0), (_ENE, 90.0), (_FEB, 80.0)],
        },
        tipo="inflacion componente",
        id_corrida="cc",
        estados=estados,
    )


def _clas_b_sin_dic() -> ResultadoIndice:
    """Clasificación donde el genérico 'B' no tiene dato en `_DIC18`."""
    return _indice(
        {
            "A": [(_DIC18, 100.0), (_ENE, 110.0), (_FEB, 120.0)],
            "B": [(_DIC18, None), (_ENE, 90.0), (_FEB, 80.0)],
        },
        tipo="inflacion componente",
        id_corrida="cc",
    )


def _canasta(version: int = 2018) -> CanastaCanonica:
    df = pd.DataFrame(
        {
            "ponderador": ["60.0", "40.0"],
            "encadenamiento": [float("nan"), float("nan")],
            "inflacion componente": ["A", "B"],
        },
        index=pd.Index(["gen_a", "gen_b"], name="generico"),
    )
    return CanastaCanonica(df, version)  # type: ignore[arg-type]


def _canastas() -> dict[int, CanastaCanonica]:
    return {2018: _canasta()}


# -- incidencia_periodica ------------------------------------------------------


def test_periodica_retorna_resultado_incidencia() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert isinstance(r, ResultadoIncidencia)


def test_periodica_clase_embebe_frecuencia() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.manifiesto.clase == "periodica_mensual"
    assert (r.resultado.largo["clase_incidencia"] == "periodica_mensual").all()


def test_periodica_suma_igual_variacion_inpc() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    var = variacion_periodica(_inpc(), "mensual")
    for periodo in (_ENE, _FEB):
        suma = r.df.xs(periodo, level="periodo")["incidencia_pp"].sum()
        esperada = var.df.loc[(periodo, "INPC"), "variacion_pp"]
        assert suma == pytest.approx(esperada)


def test_periodica_indices_parciales_none() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.indices_parciales is None


def test_periodica_manifiesto_ids() -> None:
    r = incidencia_periodica(_inpc(), _clas(), _canastas(), "mensual")
    assert r.manifiesto.inpc_ids == ["ci"]
    assert r.manifiesto.clasificacion_ids == ["cc"]
    assert r.manifiesto.id_corrida == ["ci", "cc"]


def test_periodica_estado_parcial_propagado() -> None:
    clas = _clas(estados={(_FEB, "A"): "parcial"})
    r = incidencia_periodica(_inpc(), clas, _canastas(), "mensual")
    assert r.resultado.largo.loc[(_FEB, "A"), "estado_calculo"] == "parcial"
    assert r.resultado.largo.loc[(_FEB, "B"), "estado_calculo"] == "ok"


def test_periodica_frecuencia_invalida_falla() -> None:
    with pytest.raises(InvarianteViolado):
        incidencia_periodica(_inpc(), _clas(), _canastas(), "decenal")  # type: ignore[arg-type]


# -- incidencia_acumulada_anual ------------------------------------------------


def test_acumulada_suma_igual_variacion_inpc() -> None:
    r = incidencia_acumulada_anual(_inpc(), _clas(), _canastas())
    suma = r.df.xs(_FEB, level="periodo")["incidencia_pp"].sum()
    # variacion acumulada FEB vs DIC18 = (104/100 - 1) * 100
    assert suma == pytest.approx(4.0)


# -- validaciones de entrada ---------------------------------------------------


def test_periodo_referencia_distinto_falla() -> None:
    inpc = _inpc()
    clas = _indice(
        {"A": [(_DIC18, 100.0), (_ENE, 110.0)], "B": [(_DIC18, 100.0), (_ENE, 90.0)]},
        tipo="inflacion componente",
        id_corrida="cc",
        periodo_referencia=_DIC18,
    )
    with pytest.raises(InvarianteViolado):
        incidencia_periodica(inpc, clas, _canastas(), "mensual")


def test_tipo_inpc_invalido_falla() -> None:
    falso_inpc = _indice(
        {"INPC": [(_DIC18, 100.0), (_ENE, 102.0)]},
        tipo="inflacion componente",
        id_corrida="ci",
    )
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(falso_inpc, _clas(), _canastas(), "mensual")


def test_tipo_clasificacion_invalido_falla() -> None:
    clas = _indice(
        {"A": [(_DIC18, 100.0), (_ENE, 110.0)]},
        tipo="categoria inventada",
        id_corrida="cc",
    )
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(_inpc(), clas, _canastas(), "mensual")


def test_falta_canasta_para_version_falla() -> None:
    with pytest.raises(ErrorConfiguracion):
        incidencia_periodica(_inpc(), _clas(), {2024: _canasta(2024)}, "mensual")


# -- incidencia_desde ----------------------------------------------------------


def test_desde_una_fila_por_generico() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas(), desde=_DIC18, hasta=_FEB)
    assert len(r.df) == 2
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}
    assert (r.df.index.get_level_values("periodo") == _FEB).all()


def test_desde_con_none_usa_extremos() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas())
    assert len(r.df) == 2
    assert r.manifiesto.clase == "desde"


def test_desde_indices_parciales_dataframe_vacio() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas())
    assert r.indices_parciales is not None
    assert r.indices_parciales.empty


def test_desde_suma_igual_variacion_inpc() -> None:
    r = incidencia_desde(_inpc(), _clas(), _canastas(), desde=_DIC18, hasta=_FEB)
    assert r.df["incidencia_pp"].sum() == pytest.approx(4.0)


def test_desde_incluir_parciales_ajusta_periodo() -> None:
    r = incidencia_desde(
        _inpc(), _clas_b_sin_dic(), _canastas(),
        desde=_DIC18, hasta=_FEB, incluir_parciales=True,
    )
    assert set(r.df.index.get_level_values("indice")) == {"A", "B"}
    assert r.indices_parciales.loc["B", "periodo_desde_real"] == _ENE
    assert r.indices_parciales.loc["B", "periodo_hasta_real"] == _FEB
    assert (_FEB, "B") in r.df.index


def test_desde_sin_parciales_excluye_generico() -> None:
    # 'B' no tiene dato exacto en `_DIC18`; sin parciales queda excluido.
    r = incidencia_desde(
        _inpc(), _clas_b_sin_dic(), _canastas(),
        desde=_DIC18, hasta=_FEB, incluir_parciales=False,
    )
    assert set(r.df.index.get_level_values("indice")) == {"A"}
    assert r.indices_parciales.empty


def test_desde_sin_parciales_excluye_generico_con_estado_parcial() -> None:
    # 'A' tiene extremos exactos pero estado parcial en `_FEB`.
    clas = _clas(estados={(_FEB, "A"): "parcial"})
    r_con = incidencia_desde(
        _inpc(), clas, _canastas(), desde=_DIC18, hasta=_FEB, incluir_parciales=True
    )
    assert set(r_con.df.index.get_level_values("indice")) == {"A", "B"}
    r_sin = incidencia_desde(
        _inpc(), clas, _canastas(), desde=_DIC18, hasta=_FEB, incluir_parciales=False
    )
    assert set(r_sin.df.index.get_level_values("indice")) == {"B"}
