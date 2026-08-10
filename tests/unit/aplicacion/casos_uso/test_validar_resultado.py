from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from replica_inpc.aplicacion.casos_uso import validar_resultado as modulo
from replica_inpc.aplicacion.casos_uso.validar_resultado import ValidarResultado
from replica_inpc.dominio.errores import ErrorConfiguracion, InvarianteViolado
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo, ManifestDerivado

_Q1 = PeriodoQuincenal(2024, 1, 1)
_Q2 = PeriodoQuincenal(2024, 1, 2)
_M1 = PeriodoMensual(2024, 1)
_M2 = PeriodoMensual(2024, 2)
_M3 = PeriodoMensual(2024, 3)

# -- helpers -------------------------------------------------------------------


def _r_indice(*tipos: str) -> ResultadoIndice:
    filas = [
        {
            "periodo": periodo,
            "indice": tipo,
            "version": 2024,
            "tipo": tipo,
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        }
        for tipo in tipos
        for periodo in (_Q1, _Q2)
    ]
    df = pd.DataFrame(filas).set_index(["periodo", "indice"])
    reporte = pd.DataFrame({"cobertura_genericos_pct": [100.0] * len(df)}, index=df.index)
    manifiesto = [ManifestCalculo(2024, tipo, "LaspeyresDirecto") for tipo in tipos]  # type: ignore[arg-type]
    return ResultadoIndice(df, manifiesto, reporte, pd.DataFrame())


def _manifiesto(tipo: str, clase: str) -> ManifestDerivado:
    return ManifestDerivado(
        versiones=[2024],
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )


def _reporte(periodos: list[Any], indice: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"estado_calculo": ["ok"] * len(periodos), "version_t": [2024] * len(periodos)},
        index=pd.MultiIndex.from_tuples(
            [(p, indice) for p in periodos], names=["periodo", "indice"]
        ),
    )


def _r_variacion(
    *,
    tipo: str = "INPC",
    clase: str = "periodica_mensual",
    periodos_largo: list[Any] | None = None,
    reporte: pd.DataFrame | None = None,
) -> ResultadoVariacion:
    periodos = periodos_largo if periodos_largo is not None else [_M1]
    df = pd.DataFrame(
        [
            {
                "periodo": p,
                "indice": "INPC",
                "tipo": tipo,
                "clase_variacion": clase,
                "variacion_pp": 1.0,
                "estado_calculo": "ok",
                "version_t": 2024,
            }
            for p in periodos
        ]
    ).set_index(["periodo", "indice"])
    rep = reporte if reporte is not None else _reporte(periodos, "INPC")
    return ResultadoVariacion(df, _manifiesto(tipo, clase), rep, pd.DataFrame())


def _r_incidencia(
    *,
    tipo: str = "INFLACION COMPONENTE",
    clase: str = "periodica_mensual",
    periodos_largo: list[Any] | None = None,
    reporte: pd.DataFrame | None = None,
) -> ResultadoIncidencia:
    periodos = periodos_largo if periodos_largo is not None else [_M1]
    df = pd.DataFrame(
        [
            {
                "periodo": p,
                "indice": "subyacente",
                "tipo": tipo,
                "clase_incidencia": clase,
                "incidencia_pp": 1.0,
                "estado_calculo": "ok",
                "version_t": 2024,
            }
            for p in periodos
        ]
    ).set_index(["periodo", "indice"])
    rep = reporte if reporte is not None else _reporte(periodos, "subyacente")
    return ResultadoIncidencia(df, _manifiesto(tipo, clase), rep, pd.DataFrame())


def _crear_fuente_explota(tipo: str) -> Any:
    # El doble correcto para fail-fast es una FABRICA que explota: una fuente
    # que explota en el metodo solo probaria que no se llamo el metodo, ya
    # habiendo construido la dependencia (y pedido el token).
    raise AssertionError(f"la fuente no debe construirse (tipo={tipo!r})")


class _FuenteEspia:
    """Registra qué se le pidió y devuelve siempre el mismo mapa."""

    def __init__(self, mapa: dict) -> None:
        self._mapa = mapa
        self.llamadas: list[tuple[str, list[Any], str | None]] = []

    def obtener_indices(self, periodos: list) -> dict:
        self.llamadas.append(("obtener_indices", list(periodos), None))
        return self._mapa

    def obtener_variaciones(self, periodos: list, tipo_variacion: str) -> dict:
        self.llamadas.append(("obtener_variaciones", list(periodos), tipo_variacion))
        return self._mapa

    def obtener_incidencias(self, periodos: list, tipo_incidencia: str) -> dict:
        self.llamadas.append(("obtener_incidencias", list(periodos), tipo_incidencia))
        return self._mapa


# -- fail-fast: nada debe construir la fuente ----------------------------------


def test_indice_con_varios_tipos_validos_falla_sin_construir_la_fuente() -> None:
    # Dos tipos VALIDOS: el rechazo debe ser por multiplicidad, no por tipo no
    # comparable, que es un motivo distinto y ocurre después.
    resultado = _r_indice("INPC", "INFLACION COMPONENTE")

    with pytest.raises(ErrorConfiguracion, match="varios tipos"):
        ValidarResultado(_crear_fuente_explota).validar_indice(resultado)


def test_indice_con_tipo_no_comparable_falla_sin_construir_la_fuente() -> None:
    resultado = _r_indice("COG")

    with pytest.raises(ErrorConfiguracion, match="no es comparable"):
        ValidarResultado(_crear_fuente_explota).validar_indice(resultado)


@pytest.mark.parametrize(
    "constructor, metodo",
    [(_r_variacion, "validar_variacion"), (_r_incidencia, "validar_incidencia")],
)
def test_tipo_no_comparable_en_derivados_falla_sin_construir_la_fuente(
    constructor, metodo: str
) -> None:
    resultado = constructor(tipo="COG")

    with pytest.raises(ErrorConfiguracion, match="no es comparable"):
        getattr(ValidarResultado(_crear_fuente_explota), metodo)(resultado)


@pytest.mark.parametrize(
    "constructor, metodo, clase",
    [
        (_r_variacion, "validar_variacion", "periodica_bimestral"),
        (_r_incidencia, "validar_incidencia", "periodica_quincenal"),
    ],
)
def test_clase_no_publicada_falla_sin_construir_la_fuente(
    constructor, metodo: str, clase: str
) -> None:
    resultado = constructor(clase=clase)

    with pytest.raises(ErrorConfiguracion, match="no es comparable"):
        getattr(ValidarResultado(_crear_fuente_explota), metodo)(resultado)


# -- reporte vacío -------------------------------------------------------------

# Los modelos aceptan reporte vacío con DOS índices distintos y hoy se comportan
# distinto: con MultiIndex vacío la validación llegaba al adaptador y devolvía un
# resultado degenerado; con RangeIndex escapaba un KeyError de pandas. El caso de
# uso unifica ambos en el mismo InvarianteViolado.
_REPORTE_VACIO_RANGE = pd.DataFrame()
_REPORTE_VACIO_MULTI = pd.DataFrame(
    {"estado_calculo": pd.Series(dtype="object"), "version_t": pd.Series(dtype="int64")},
    index=pd.MultiIndex.from_tuples([], names=["periodo", "indice"]),
)


@pytest.mark.parametrize("reporte_vacio", [_REPORTE_VACIO_RANGE, _REPORTE_VACIO_MULTI])
@pytest.mark.parametrize(
    "constructor, metodo",
    [(_r_variacion, "validar_variacion"), (_r_incidencia, "validar_incidencia")],
)
def test_reporte_vacio_falla_sin_construir_la_fuente(
    constructor, metodo: str, reporte_vacio: pd.DataFrame
) -> None:
    resultado = constructor(reporte=reporte_vacio)

    with pytest.raises(InvarianteViolado) as exc:
        getattr(ValidarResultado(_crear_fuente_explota), metodo)(resultado)

    assert metodo in str(exc.value)
    assert "resultado.reporte" in str(exc.value)


# -- de dónde salen los periodos ----------------------------------------------


@pytest.mark.parametrize(
    "constructor, metodo, comparador, indice, esperado_tipo",
    [
        (_r_variacion, "validar_variacion", "validar_variaciones", "INPC", "periodica"),
        (
            _r_incidencia,
            "validar_incidencia",
            "validar_incidencias",
            "subyacente",
            "periodica",
        ),
    ],
)
def test_derivados_piden_los_periodos_del_reporte_no_los_del_largo(
    mocker, constructor, metodo: str, comparador: str, indice: str, esperado_tipo: str
) -> None:
    # _M3 existe SOLO en el reporte (fila no computable). Si el caso de uso
    # extrajera del largo, _M3 no llegaría a la fuente y este test pasaría igual
    # con la implementación equivocada — de ahí la asimetría deliberada.
    reporte = _reporte([_M1, _M2, _M3], indice)
    resultado = constructor(periodos_largo=[_M1, _M2], reporte=reporte)
    mapa = {indice: {_M1: 1.0, _M2: 1.0, _M3: 1.0}}
    fuente = _FuenteEspia(mapa)
    espia_comparador = mocker.patch.object(modulo, comparador, return_value="val")

    salida = getattr(ValidarResultado(lambda tipo: fuente), metodo)(resultado)

    assert salida == "val"
    # Una sola consulta, al método correcto, con la lista exacta y ordenada.
    assert len(fuente.llamadas) == 1
    nombre, periodos, tipo_pedido = fuente.llamadas[0]
    assert nombre == f"obtener_{comparador.removeprefix('validar_')}"
    assert periodos == [_M1, _M2, _M3]
    assert tipo_pedido == esperado_tipo
    # El mapa llega intacto al comparador.
    assert espia_comparador.call_args[0][1] is mapa


def test_indice_pide_los_periodos_del_largo(mocker) -> None:
    resultado = _r_indice("INPC")
    mapa = {"INPC": {_Q1: 100.0, _Q2: 100.0}}
    fuente = _FuenteEspia(mapa)
    espia_comparador = mocker.patch.object(modulo, "validar_indices", return_value="val")

    salida = ValidarResultado(lambda tipo: fuente).validar_indice(resultado)

    assert salida == "val"
    assert fuente.llamadas == [("obtener_indices", [_Q1, _Q2], None)]
    assert espia_comparador.call_args[0][1] is mapa


def test_la_fabrica_recibe_el_tipo_del_resultado() -> None:
    resultado = _r_variacion(tipo="INFLACION SUBCOMPONENTE")
    tipos_pedidos: list[str] = []

    def crear(tipo: str) -> Any:
        tipos_pedidos.append(tipo)
        return _FuenteEspia({"INPC": {_M1: 1.0}})

    ValidarResultado(crear).validar_variacion(resultado)

    assert tipos_pedidos == ["INFLACION SUBCOMPONENTE"]


def test_la_tolerancia_llega_al_comparador(mocker) -> None:
    resultado = _r_variacion()
    espia = mocker.patch.object(modulo, "validar_variaciones", return_value="val")

    ValidarResultado(lambda tipo: _FuenteEspia({"INPC": {_M1: 1.0}})).validar_variacion(
        resultado, 0.5
    )

    assert espia.call_args[0][2] == 0.5
