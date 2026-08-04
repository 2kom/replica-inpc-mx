from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo, ManifestDerivado
from replica_inpc.infraestructura.graficacion import _prepocesamiento as pp

# --------------------------------------------------------------------------- helpers


def _manifiesto(version: int = 2018, tipo: str = "INPC") -> ManifestCalculo:
    return ManifestCalculo(
        version=version,  # type: ignore[arg-type]
        tipo=tipo,
        calculador="LaspeyresDirecto",
        fecha=datetime(2024, 1, 1),
    )


def _resultado(
    filas: list[tuple[Any, str, float, str]],
    version: int = 2018,
    tipo: str = "INPC",
    periodo_referencia: Any = None,
) -> ResultadoIndice:
    """filas = list of (periodo, indice, valor, estado)."""
    registros = [
        {
            "periodo": p,
            "indice": i,
            "version": version,
            "tipo": tipo,
            "indice_replicado": v,
            "estado_calculo": e,
            "motivo_error": None,
        }
        for p, i, v, e in filas
    ]
    df = pd.DataFrame(registros)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = df[[]].copy()
    diag = pd.DataFrame(
        columns=["periodo", "generico", "nivel_faltante", "tipo_faltante", "detalle"]
    )
    return ResultadoIndice(
        df, [_manifiesto(version, tipo)], reporte, diag, periodo_referencia=periodo_referencia
    )


_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)
_P3 = PeriodoQuincenal(2018, 2, 1)


def _datos_n_categorias(n: int, con_inpc: bool = False) -> pd.DataFrame:
    filas = [(_P1, f"cat{i:02d}", float(i), "ok") for i in range(n)]
    if con_inpc:
        filas.append((_P1, "INPC", 100.0, "ok"))
    r = _resultado(filas, tipo="CCIF DIVISION")
    return pp._aplanar_resultado(r)


# --------------------------------------------------------------------------- _titulo


def test_titulo_una_sola_tipo() -> None:
    datos = pd.DataFrame({"tipo": ["INPC", "INPC"]})
    assert pp._titulo(datos) == "INPC"


def test_titulo_varios_tipos_unidos_con_mas() -> None:
    datos = pd.DataFrame({"tipo": ["CCIF DIVISION", "CCIF DIVISION", "INPC"]})
    assert pp._titulo(datos) == "CCIF DIVISION + INPC"


# --------------------------------------------------------------------------- _aplanar_resultado


def test_aplanar_sin_comparacion_linetype_solid() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    datos = pp._aplanar_resultado(r)
    assert len(datos) == 1
    assert datos["linetype"].tolist() == ["solid"]
    assert "periodo_ts" in datos.columns


def test_aplanar_con_comparacion_concatena_y_marca_linetype() -> None:
    principal = _resultado([(_P1, "CCIF DIVISION", 90.0, "ok")], tipo="CCIF DIVISION")
    comparacion = _resultado([(_P1, "INPC", 100.0, "ok")])
    datos = pp._aplanar_resultado(principal, comparacion)
    assert len(datos) == 2
    linetypes = dict(zip(datos["indice"], datos["linetype"], strict=True))
    assert linetypes == {"CCIF DIVISION": "solid", "INPC": "dashed"}


# --------------------------------------------------------------------------- _recortar_tramo


def _datos_tres_periodos() -> pd.DataFrame:
    r = _resultado(
        [
            (_P1, "INPC", 100.0, "ok"),
            (_P2, "INPC", 101.0, "ok"),
            (_P3, "INPC", 102.0, "ok"),
        ]
    )
    return pp._aplanar_resultado(r)


def test_recortar_tramo_sin_limites_no_cambia_nada() -> None:
    datos = _datos_tres_periodos()
    assert len(pp._recortar_tramo(datos, None, None)) == 3


def test_recortar_tramo_desde_excluye_anteriores() -> None:
    datos = _datos_tres_periodos()
    recortado = pp._recortar_tramo(datos, _P2, None)
    assert set(recortado["periodo"]) == {_P2, _P3}


def test_recortar_tramo_hasta_excluye_posteriores() -> None:
    datos = _datos_tres_periodos()
    recortado = pp._recortar_tramo(datos, None, _P2)
    assert set(recortado["periodo"]) == {_P1, _P2}


def test_recortar_tramo_desde_mayor_a_hasta_falla() -> None:
    datos = _datos_tres_periodos()
    with pytest.raises(InvarianteViolado):
        pp._recortar_tramo(datos, _P3, _P1)


def test_recortar_tramo_sin_datos_en_rango_falla() -> None:
    datos = _datos_tres_periodos()
    fuera = PeriodoQuincenal(2030, 1, 1)
    with pytest.raises(InvarianteViolado):
        pp._recortar_tramo(datos, fuera, fuera)


# --------------------------------------------------------------------------- _particionar_series


def test_particionar_series_bajo_capacidad_no_parte() -> None:
    datos = _datos_n_categorias(5)
    particiones = pp._particionar_series(datos, capacidad=8)
    assert len(particiones) == 1
    assert len(particiones[0]) == 5


def test_particionar_series_reparte_parejo() -> None:
    # 13 categorías, capacidad 8 -> 7 y 6, no 8 y 5 (evita imagen casi vacía).
    datos = _datos_n_categorias(13)
    particiones = pp._particionar_series(datos, capacidad=8)
    assert len(particiones) == 2
    assert sorted(len(p) for p in particiones) == [6, 7]


def test_particionar_series_inpc_no_cuenta_y_se_repite_en_cada_particion() -> None:
    datos = _datos_n_categorias(13, con_inpc=True)
    particiones = pp._particionar_series(datos, capacidad=8)
    assert len(particiones) == 2
    for parte in particiones:
        assert "INPC" in set(parte["indice"])


# --------------------------------------------------------------------------- _ordenar_series_dibujo


def test_ordenar_series_dibujo_inpc_al_final() -> None:
    valores = pd.Series(["INPC", "cat_b", "cat_a"])
    categorico = pp._ordenar_series_dibujo(valores)
    assert list(categorico.categories) == ["cat_b", "cat_a", "INPC"]


def test_ordenar_series_dibujo_sin_inpc_mantiene_orden_aparicion() -> None:
    valores = pd.Series(["cat_b", "cat_a", "cat_b"])
    categorico = pp._ordenar_series_dibujo(valores)
    assert list(categorico.categories) == ["cat_b", "cat_a"]


# --------------------------------------------------------------------------- _breaks_y_etiquetas_x


def test_breaks_x_incluye_siempre_primero_y_ultimo() -> None:
    periodos = [PeriodoQuincenal(2018, m, q) for m in range(1, 13) for q in (1, 2)]
    r = _resultado([(p, "INPC", 100.0 + i, "ok") for i, p in enumerate(periodos)])
    datos = pp._aplanar_resultado(r)
    breaks, _ = pp._breaks_y_etiquetas_x(datos)
    assert breaks[0] == datos["periodo_ts"].min()
    assert breaks[-1] == datos["periodo_ts"].max()


# --------------------------------------------------------------------------- _breaks_y / _etiqueta_y_indice


def test_breaks_y_incluye_minimo_y_maximo_reales() -> None:
    r = _resultado([(_P1, "INPC", 80.0, "ok"), (_P2, "INPC", 120.0, "ok")])
    datos = pp._aplanar_resultado(r)
    breaks = pp._breaks_y(datos, "indice_replicado", pp._VALOR_BASE)
    assert breaks[0] == 80.0
    assert breaks[-1] == 120.0


def test_breaks_y_incluye_100_si_esta_en_rango() -> None:
    r = _resultado([(_P1, "INPC", 80.0, "ok"), (_P2, "INPC", 120.0, "ok")])
    datos = pp._aplanar_resultado(r)
    breaks = pp._breaks_y(datos, "indice_replicado", pp._VALOR_BASE)
    assert 100.0 in breaks


def test_breaks_y_no_agrega_100_fuera_de_rango() -> None:
    r = _resultado([(_P1, "INPC", 120.0, "ok"), (_P2, "INPC", 150.0, "ok")])
    datos = pp._aplanar_resultado(r)
    breaks = pp._breaks_y(datos, "indice_replicado", pp._VALOR_BASE)
    assert 100.0 not in breaks


def test_etiqueta_y_sin_periodo_referencia() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    assert pp._etiqueta_y_indice(r) == "Indice"


def test_etiqueta_y_con_periodo_referencia() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok")], periodo_referencia=_P1)
    assert pp._etiqueta_y_indice(r) == f"Indice ({_P1} = 100)"


# --------------------------------------------------------------------------- _colores_y_etiquetas


def test_colores_inpc_siempre_negro() -> None:
    colores, _ = pp._colores_y_etiquetas(["cat_a", "INPC", "cat_b"])
    assert colores["INPC"] == "black"


def test_colores_no_inpc_toman_paleta_en_orden_aparicion() -> None:
    colores, _ = pp._colores_y_etiquetas(["cat_a", "cat_b"])
    assert colores["cat_a"] == pp._PALETA_OTROS_TIPOS[0]
    assert colores["cat_b"] == pp._PALETA_OTROS_TIPOS[1]


def test_colores_inpc_no_consume_turno_de_paleta() -> None:
    # INPC en medio de la lista no debe correr el color de las categorías siguientes.
    colores, _ = pp._colores_y_etiquetas(["cat_a", "INPC", "cat_b"])
    assert colores["cat_a"] == pp._PALETA_OTROS_TIPOS[0]
    assert colores["cat_b"] == pp._PALETA_OTROS_TIPOS[1]


def test_etiquetas_nombre_corto_no_se_trunca() -> None:
    _, etiquetas = pp._colores_y_etiquetas(["INPC"])
    assert etiquetas["INPC"] == "INPC"


def test_etiquetas_nombre_largo_se_trunca_con_puntos() -> None:
    nombre = "22 generacion transmision distribucion y comercializacion de energia"
    _, etiquetas = pp._colores_y_etiquetas([nombre])
    assert len(etiquetas[nombre]) == pp._MAX_CARACTERES_LEYENDA
    assert etiquetas[nombre].endswith("...")


def test_etiquetas_limite_exacto_no_se_trunca() -> None:
    nombre = "x" * pp._MAX_CARACTERES_LEYENDA
    _, etiquetas = pp._colores_y_etiquetas([nombre])
    assert etiquetas[nombre] == nombre


# --------------------------------------------------------------------------- _primero_y_ultimo_para_anotar


def test_primero_ultimo_none_si_hay_mas_de_una_serie() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok"), (_P1, "otra", 90.0, "ok")], tipo="CCIF DIVISION")
    datos = pp._aplanar_resultado(r)
    assert pp._primero_y_ultimo_para_anotar(datos, ["INPC", "otra"]) is None


def test_primero_ultimo_none_si_resultado_y_comparacion_comparten_indice() -> None:
    # Mismo "indice" (INPC) en resultado y comparacion -> 2 grupos visuales
    # (solid/dashed), aunque `series` (solo por indice) reporte 1. Antes de
    # la guardia por (indice, linetype), esto mezclaba el primer punto de un
    # grupo con el último del otro.
    principal = _resultado([(_P1, "INPC", 100.0, "ok"), (_P2, "INPC", 105.0, "ok")])
    comparacion = _resultado([(_P1, "INPC", 200.0, "ok"), (_P2, "INPC", 210.0, "ok")])
    datos = pp._aplanar_resultado(principal, comparacion)
    assert pp._primero_y_ultimo_para_anotar(datos, ["INPC"]) is None


def test_primero_ultimo_devuelve_extremos_con_una_sola_serie() -> None:
    r = _resultado(
        [
            (_P1, "INPC", 100.0, "ok"),
            (_P2, "INPC", 105.0, "ok"),
            (_P3, "INPC", 110.0, "ok"),
        ]
    )
    datos = pp._aplanar_resultado(r)
    resultado = pp._primero_y_ultimo_para_anotar(datos, ["INPC"])
    assert resultado is not None
    primero, ultimo = resultado
    assert primero["indice_replicado"] == 100.0
    assert ultimo["indice_replicado"] == 110.0


# --------------------------------------------------------------------------- helpers variaciones


def _manifiesto_variacion(tipo: str = "INPC", clase: str = "periodica_mensual") -> ManifestDerivado:
    return ManifestDerivado(
        versiones=[2018],  # type: ignore[list-item]
        tipo=tipo,
        clase=clase,
        descripcion="",
        fecha=datetime(2024, 1, 1),
    )


def _resultado_variacion(
    filas: list[tuple[Any, str, float, str]],
    tipo: str = "INPC",
    clase: str = "periodica_mensual",
) -> ResultadoVariacion:
    """filas = list of (periodo, indice, variacion_pp, estado)."""
    registros = [
        {
            "periodo": p,
            "indice": i,
            "tipo": tipo,
            "clase_variacion": clase,
            "variacion_pp": v,
            "estado_calculo": e,
        }
        for p, i, v, e in filas
    ]
    df = pd.DataFrame(registros)
    df.index = pd.MultiIndex.from_arrays(
        [df.pop("periodo"), df.pop("indice")], names=["periodo", "indice"]
    )
    reporte = df[[]].copy()
    diag = pd.DataFrame(columns=["periodo", "indice", "estado_calculo", "motivo_error"])
    return ResultadoVariacion(df, _manifiesto_variacion(tipo, clase), reporte, diag)


# --------------------------------------------------------------------------- _aplanar_resultado (variaciones)


def test_aplanar_variacion_sin_comparacion_linetype_solid() -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    datos = pp._aplanar_resultado(rv)
    assert len(datos) == 1
    assert datos["variacion_pp"].tolist() == [0.5]
    assert datos["linetype"].tolist() == ["solid"]
    assert "periodo_ts" in datos.columns


def test_aplanar_variacion_con_comparacion_marca_linetype() -> None:
    principal = _resultado_variacion([(_P1, "cat", 0.5, "ok")], tipo="CCIF DIVISION")
    comparacion = _resultado_variacion([(_P1, "INPC", 0.3, "ok")])
    datos = pp._aplanar_resultado(principal, comparacion)
    assert len(datos) == 2
    linetypes = dict(zip(datos["indice"], datos["linetype"], strict=True))
    assert linetypes == {"cat": "solid", "INPC": "dashed"}


# --------------------------------------------------------------------------- _breaks_y (variaciones)


def test_breaks_y_variacion_incluye_minimo_maximo_y_cero() -> None:
    datos = pd.DataFrame({"variacion_pp": [-2.0, 3.0]})
    breaks = pp._breaks_y(datos, "variacion_pp", pp._VALOR_BASE_VARIACION)
    assert breaks[0] == -2.0
    assert breaks[-1] == 3.0
    assert 0.0 in breaks


def test_breaks_y_variacion_no_agrega_cero_fuera_de_rango() -> None:
    datos = pd.DataFrame({"variacion_pp": [5.0, 10.0]})
    breaks = pp._breaks_y(datos, "variacion_pp", pp._VALOR_BASE_VARIACION)
    assert 0.0 not in breaks
    assert breaks[0] == 5.0
    assert breaks[-1] == 10.0
