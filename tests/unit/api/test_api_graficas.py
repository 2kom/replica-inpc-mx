from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from replica_inpc.api import graficas
from replica_inpc.dominio.errores import InvarianteViolado, PeriodoNoDisponible
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo, ManifestDerivado
from replica_inpc.infraestructura.graficacion import graficador

# --------------------------------------------------------------------------- helpers


def _manifiesto(version: int = 2018, tipo: str = "INPC") -> ManifestCalculo:
    return ManifestCalculo(
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador="LaspeyresDirecto",
        fecha=datetime(2024, 1, 1),
    )


def _resultado(periodos: list[Any], version: int = 2018, tipo: str = "INPC") -> ResultadoIndice:
    filas = [
        {
            "periodo": p,
            "indice": "INPC" if tipo == "INPC" else "cat",
            "version": version,
            "tipo": tipo,
            "indice_replicado": 100.0,
            "estado_calculo": "ok",
            "motivo_error": None,
        }
        for p in periodos
    ]
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = df[[]].copy()
    diag = pd.DataFrame(
        columns=["periodo", "generico", "nivel_faltante", "tipo_faltante", "detalle"]
    )
    return ResultadoIndice(df, [_manifiesto(version, tipo)], reporte, diag)


_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)
_P3 = PeriodoQuincenal(2018, 2, 1)


# --------------------------------------------------------------------------- helpers variaciones


def _resultado_variacion(
    periodos: list[Any], tipo: str = "INPC", clase: str = "periodica_mensual"
) -> ResultadoVariacion:
    filas = [
        {
            "periodo": p,
            "indice": "INPC" if tipo == "INPC" else "cat",
            "tipo": tipo,
            "clase_variacion": clase,
            "variacion_pp": 0.5,
            "estado_calculo": "ok",
        }
        for p in periodos
    ]
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = df[[]].copy()
    diag = pd.DataFrame(columns=["periodo", "indice", "estado_calculo", "motivo_error"])
    manifiesto = ManifestDerivado(
        versiones=[2018],  # type: ignore[list-item]
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    return ResultadoVariacion(df, manifiesto, reporte, diag)


# --------------------------------------------------------------------------- delegación
#
# Parametrizado por tipo (indice/variacion): ambos pasan por el mismo
# graficas.graficar() y delegan al mismo graficas._graficar -- es justamente
# lo que unifica la API, no dos funciones públicas separadas por tipo.


def _construir(tipo_resultado: str, periodos: list[Any], tipo: str = "INPC"):
    if tipo_resultado == "indice":
        return _resultado(periodos, tipo=tipo)
    return _resultado_variacion(periodos, tipo=tipo)


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_sin_tramo_delega_sin_validar_periodos(mocker, tipo_resultado) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1, _P2])
    graficas.graficar(r)
    fn.assert_called_once_with(r, None, None, None)


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_convierte_desde_y_hasta(mocker, tipo_resultado) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1, _P2, _P3])
    graficas.graficar(r, desde="1Q Ene 2018", hasta="1Q Feb 2018")
    fn.assert_called_once_with(r, None, _P1, _P3)


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_pasa_comparacion(mocker, tipo_resultado) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1])
    comparacion = _construir(tipo_resultado, [_P1], tipo="CCIF DIVISION")
    graficas.graficar(r, comparacion=comparacion)
    fn.assert_called_once_with(r, comparacion, None, None)


# --------------------------------------------------------------------------- validación de tramo


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_desde_ausente_lanza_periodo_no_disponible(mocker, tipo_resultado) -> None:
    mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1, _P2])
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(r, desde="1Q Ene 2030")


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_hasta_ausente_lanza_periodo_no_disponible(mocker, tipo_resultado) -> None:
    mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1, _P2])
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(r, hasta="1Q Ene 2030")


@pytest.mark.parametrize("tipo_resultado", ["indice", "variacion"])
def test_graficar_desde_presente_solo_en_comparacion_no_lanza(mocker, tipo_resultado) -> None:
    # el periodo pedido puede venir de resultado O de comparacion -- la
    # union de ambos es lo que realmente termina en el panel.
    fn = mocker.patch.object(graficas, "_graficar")
    r = _construir(tipo_resultado, [_P1], tipo="CCIF DIVISION")
    comparacion = _construir(tipo_resultado, [_P1, _P3])
    graficas.graficar(r, comparacion=comparacion, desde="1Q Feb 2018")
    fn.assert_called_once_with(r, comparacion, _P3, None)


# --------------------------------------------------------------------------- _periodos_disponibles


def test_periodos_disponibles_sin_comparacion() -> None:
    r = _resultado([_P1, _P2])
    assert graficas._periodos_disponibles(r, None) == {_P1, _P2}


def test_periodos_disponibles_union_con_comparacion() -> None:
    r = _resultado([_P1])
    comparacion = _resultado([_P2], tipo="CCIF DIVISION")
    assert graficas._periodos_disponibles(r, comparacion) == {_P1, _P2}


# --------------------------------------------------------------------------- periodicidad de desde/hasta


def _resultado_mensual() -> ResultadoIndice:
    return _resultado([PeriodoMensual(2018, 1), PeriodoMensual(2018, 2)])


@pytest.mark.parametrize("es_desde", [True, False])
def test_graficar_periodo_quincenal_contra_resultado_mensual_falla(mocker, es_desde: bool) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    quincenal = "1Q Ene 2018"
    with pytest.raises(InvarianteViolado, match="quincenal.*mensual"):
        if es_desde:
            graficas.graficar(_resultado_mensual(), desde=quincenal)
        else:
            graficas.graficar(_resultado_mensual(), hasta=quincenal)
    fn.assert_not_called()


@pytest.mark.parametrize("es_desde", [True, False])
def test_graficar_periodo_mensual_contra_resultado_quincenal_falla(mocker, es_desde: bool) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    with pytest.raises(InvarianteViolado, match="mensual.*quincenal"):
        if es_desde:
            graficas.graficar(_resultado([_P1, _P2]), desde="Ene 2018")
        else:
            graficas.graficar(_resultado([_P1, _P2]), hasta="Ene 2018")
    fn.assert_not_called()


def test_graficar_periodicidad_se_valida_antes_que_disponibilidad(mocker) -> None:
    # Un periodo quincenal jamas puede estar en datos mensuales: reportar
    # "no está presente" ocultaria el problema real, que es el tipo.
    mocker.patch.object(graficas, "_graficar")
    with pytest.raises(InvarianteViolado):
        graficas.graficar(_resultado_mensual(), desde="1Q Ene 1990")


def test_graficar_periodicidad_correcta_pero_ausente_sigue_lanzando_no_disponible(mocker) -> None:
    mocker.patch.object(graficas, "_graficar")
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(_resultado_mensual(), desde="Ene 1990")


def test_graficar_periodicidad_coincidente_delega(mocker) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    graficas.graficar(_resultado_mensual(), desde="Ene 2018", hasta="Feb 2018")
    fn.assert_called_once()


# --------------------------------------------------------------------------- incidencias


def _resultado_incidencia(
    periodos: list[Any], tipo: str = "COG", clase: str = "periodica_anual"
) -> ResultadoIncidencia:
    filas = [
        {
            "periodo": p,
            "indice": "cat",
            "tipo": tipo,
            "clase_incidencia": clase,
            "incidencia_pp": 0.5,
            "estado_calculo": "ok",
        }
        for p in periodos
    ]
    df = pd.DataFrame(filas)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    manifiesto = ManifestDerivado(
        versiones=[2018],  # type: ignore[list-item]
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )
    return ResultadoIncidencia(df, manifiesto, df[[]].copy(), pd.DataFrame())


_MES1, _MES2, _MES3 = PeriodoMensual(2024, 1), PeriodoMensual(2024, 2), PeriodoMensual(2024, 3)


def test_graficar_incidencia_delega(mocker) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    graficas.graficar(_resultado_incidencia([_MES1, _MES2]))
    fn.assert_called_once()


def test_graficar_incidencia_desde_solo_en_la_comparacion_lanza(mocker) -> None:
    # Un limite que solo cubre la linea de referencia deja las barras vacias:
    # una grafica de incidencias sin barras no es una grafica de incidencias.
    # Antes pasaba la validacion y reventaba mas abajo, en el recorte, con un
    # InvarianteViolado que hablaba del rango y no del parametro.
    fn = mocker.patch.object(graficas, "_graficar")
    incidencia = _resultado_incidencia([_MES1, _MES2])
    comparacion = _resultado_variacion([_MES1, _MES2, _MES3], clase="periodica_anual")
    with pytest.raises(PeriodoNoDisponible):
        graficas.graficar(incidencia, comparacion, desde="Mar 2024")
    fn.assert_not_called()


def test_graficar_incidencia_desde_presente_en_la_incidencia_delega(mocker) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    incidencia = _resultado_incidencia([_MES1, _MES2])
    comparacion = _resultado_variacion([_MES1, _MES2, _MES3], clase="periodica_anual")
    graficas.graficar(incidencia, comparacion, desde="Feb 2024")
    fn.assert_called_once()


def test_graficar_indice_desde_solo_en_la_comparacion_sigue_delegando(mocker) -> None:
    # En lineas ambos resultados se concatenan en un solo panel, asi que un
    # limite presente solo en la comparacion sigue recortando algo real.
    fn = mocker.patch.object(graficas, "_graficar")
    graficas.graficar(_resultado([_P1]), _resultado([_P1, _P2]), desde="2Q Ene 2018")
    fn.assert_called_once()


def test_graficar_incidencia_periodo_quincenal_contra_incidencia_mensual_falla(mocker) -> None:
    fn = mocker.patch.object(graficas, "_graficar")
    with pytest.raises(InvarianteViolado):
        graficas.graficar(_resultado_incidencia([_MES1, _MES2]), desde="1Q Ene 2024")
    fn.assert_not_called()


@pytest.mark.parametrize(
    ("es_desde", "limite", "periodos_comparacion"),
    [(True, "Mar 2024", [_MES1]), (False, "Ene 2024", [_MES3])],
    ids=["desde", "hasta"],
)
def test_graficar_incidencia_limite_deja_la_comparacion_vacia_no_lanza(
    mocker, es_desde: bool, limite: str, periodos_comparacion: list[Any]
) -> None:
    # El limite existe en la incidencia (que es lo que la API valida) pero deja
    # la comparacion sin filas. Antes pasaba la validacion y reventaba abajo,
    # en el recorte, con un InvarianteViolado sobre el rango.
    #
    # Se mockea `_construir_grafica_barras` y NO `_graficar`: con el mock
    # arriba, `_graficar_incidencia` -- que es donde vive el arreglo -- nunca
    # corre, y el test pasaria igual contra la implementacion rota.
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    incidencia = _resultado_incidencia([_MES1, _MES2, _MES3])
    comparacion = _resultado_variacion(periodos_comparacion, clase="periodica_anual")

    if es_desde:
        graficas.graficar(incidencia, comparacion, desde=limite)
    else:
        graficas.graficar(incidencia, comparacion, hasta=limite)

    construir.assert_called_once()
    assert construir.call_args[0][1] is None  # barras dibujadas, sin linea


@pytest.mark.parametrize("es_desde", [True, False], ids=["desde", "hasta"])
def test_graficar_incidencia_limite_con_comparacion_en_rango_dibuja_linea(
    mocker, es_desde: bool
) -> None:
    # Contraparte del anterior: si la comparacion si alcanza el tramo, la linea
    # se dibuja. Sin este caso, un fix que dejara SIEMPRE la linea en None
    # pasaria el test de arriba.
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    incidencia = _resultado_incidencia([_MES1, _MES2, _MES3])
    comparacion = _resultado_variacion([_MES1, _MES2, _MES3], clase="periodica_anual")

    if es_desde:
        graficas.graficar(incidencia, comparacion, desde="Mar 2024")
    else:
        graficas.graficar(incidencia, comparacion, hasta="Ene 2024")

    assert construir.call_args[0][1] is not None
