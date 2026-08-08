from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

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


def _resultado(
    filas: list[tuple[Any, str, float, str]],
    version: int = 2018,
    tipo: str = "INPC",
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
    return ResultadoIndice(df, [_manifiesto(version, tipo)], reporte, diag)


_P1 = PeriodoQuincenal(2018, 1, 1)
_P2 = PeriodoQuincenal(2018, 1, 2)


def _geoms(grafica: Any) -> list[str]:
    return [type(layer.geom).__name__ for layer in grafica.layers]


def _n_categorias(n: int) -> list[tuple[Any, str, float, str]]:
    return [(_P1, f"cat{i:02d}", float(i), "ok") for i in range(n)]


# --------------------------------------------------------------------------- _construir_grafica_linea


def test_construir_grafica_agrupa_por_indice_no_tipo() -> None:
    r = _resultado([(_P1, "cat_a", 90.0, "ok"), (_P1, "cat_b", 110.0, "ok")], tipo="CCIF DIVISION")
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert grafica.mapping["color"] == "indice"


def test_construir_grafica_incluye_geom_point_en_tramo_corto() -> None:
    r = _resultado([(_P1, "INPC", 90.0, "ok"), (_P2, "INPC", 110.0, "ok")])
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_point" in _geoms(grafica)


def _quincenas(n: int) -> list[PeriodoQuincenal]:
    return [PeriodoQuincenal(2018 + i // 24, (i % 24) // 2 + 1, i % 2 + 1) for i in range(n)]


def test_construir_grafica_sin_geom_point_en_tramo_largo() -> None:
    # Pasando el año, un punto por periodo satura la línea: la capa no se
    # agrega en absoluto (no basta con que quede vacía).
    r = _resultado([(p, "INPC", 100.0 + i, "ok") for i, p in enumerate(_quincenas(48))])
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_point" not in _geoms(grafica)


def test_construir_grafica_renderiza_punto_de_serie_solitaria_en_tramo_largo() -> None:
    # Tramo largo: sin puntos generales, pero la categoría que aparece en un
    # único periodo sí lo lleva -- geom_line no dibuja nada con un solo punto
    # por grupo, así que sin esto la categoría quedaría invisible.
    periodos = _quincenas(48)
    filas = [(p, "INPC", 100.0 + i, "ok") for i, p in enumerate(periodos)]
    r = _resultado([*filas, (periodos[10], "rara", 95.0, "ok")], tipo="CCIF DIVISION")
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_point" in _geoms(grafica)
    figura = grafica.draw()
    try:
        assert len(figura.axes[0].collections) > 0, "el punto de la serie solitaria no se dibujó"
    finally:
        import matplotlib.pyplot as plt

        plt.close(figura)


def test_construir_grafica_renderiza_puntos_con_un_solo_dato_por_serie() -> None:
    # Reproduce la forma de variacion_desde(): una fila por índice, sin
    # segundo punto para que geom_line trace una línea -- antes de agregar
    # geom_point, esto renderizaba 0 líneas y 0 puntos (chart vacío).
    r = _resultado([(_P1, "A", 90.0, "ok"), (_P1, "B", 110.0, "ok")], tipo="CCIF DIVISION")
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    figura = grafica.draw()
    try:
        ejes = figura.axes[0]
        assert len(ejes.collections) > 0, "geom_point no dibujó nada con 1 dato por serie"
    finally:
        import matplotlib.pyplot as plt

        plt.close(figura)


def test_construir_grafica_incluye_hline_si_100_en_rango() -> None:
    r = _resultado([(_P1, "INPC", 90.0, "ok"), (_P2, "INPC", 110.0, "ok")])
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_hline" in _geoms(grafica)


def test_construir_grafica_sin_hline_si_100_fuera_de_rango() -> None:
    r = _resultado([(_P1, "INPC", 120.0, "ok"), (_P2, "INPC", 150.0, "ok")])
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_hline" not in _geoms(grafica)


def test_construir_grafica_anota_texto_con_una_sola_serie() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok"), (_P2, "INPC", 110.0, "ok")])
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_text" in _geoms(grafica)


def test_construir_grafica_no_anota_texto_con_varias_series() -> None:
    r = _resultado([(_P1, "cat_a", 90.0, "ok"), (_P1, "cat_b", 110.0, "ok")], tipo="CCIF DIVISION")
    datos = graficador._aplanar_resultado(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_text" not in _geoms(grafica)


def test_construir_grafica_titulo_junta_tipos_de_resultado_y_comparacion() -> None:
    r = _resultado([(_P1, "cat_a", 90.0, "ok")], tipo="CCIF DIVISION")
    comparacion = _resultado([(_P1, "INPC", 100.0, "ok")])
    datos = graficador._aplanar_resultado(r, comparacion)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert grafica.labels.title == "CCIF DIVISION + INPC"


# --------------------------------------------------------------------------- graficar (índices)


def test_graficar_indice_una_sola_imagen_bajo_capacidad(mocker: Any) -> None:
    r = _resultado(_n_categorias(5), tipo="CCIF DIVISION")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_linea", return_value=grafica_falsa)
    graficador.graficar(r)
    grafica_falsa.draw.assert_called_once_with(show=True)


def test_graficar_indice_particiona_en_varias_imagenes(mocker: Any) -> None:
    r = _resultado(_n_categorias(13), tipo="CCIF DIVISION")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_linea", return_value=grafica_falsa)
    graficador.graficar(r)
    assert grafica_falsa.draw.call_count == 2
    grafica_falsa.draw.assert_called_with(show=True)


def test_graficar_indice_recorta_tramo_antes_de_graficar(mocker: Any) -> None:
    p3 = PeriodoQuincenal(2018, 2, 1)
    r = _resultado(
        [(_P1, "INPC", 100.0, "ok"), (_P2, "INPC", 105.0, "ok"), (p3, "INPC", 110.0, "ok")]
    )
    construir = mocker.patch.object(
        graficador, "_construir_grafica_linea", return_value=mocker.Mock()
    )
    graficador.graficar(r, desde=_P2)
    datos_recibidos = construir.call_args[0][0]
    assert set(datos_recibidos["periodo"]) == {_P2, p3}


def test_graficar_dibuja_cada_grafica_para_indice(mocker: Any) -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    grafica_falsa = mocker.Mock()
    construir = mocker.patch.object(
        graficador, "_construir_grafica_linea", return_value=grafica_falsa
    )
    graficador.graficar(r)
    grafica_falsa.draw.assert_called_once_with(show=True)
    construir.assert_called_once_with(mocker.ANY, r)


def test_graficar_tipo_invalido_no_lanza(mocker: Any, capsys: Any) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_linea")
    graficador.graficar("no es un ResultadoIndice ni ResultadoVariacion")  # type: ignore[arg-type]
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_comparacion_de_otro_tipo_no_lanza(mocker: Any, capsys: Any) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_linea")
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    graficador.graficar(r, comparacion=rv)  # type: ignore[arg-type]
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_comparacion_periodicidad_distinta_no_lanza(mocker: Any, capsys: Any) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_linea")
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    comparacion = _resultado([(PeriodoMensual(2018, 1), "INPC", 100.0, "ok")])
    graficador.graficar(r, comparacion=comparacion)
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


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


def _n_categorias_variacion(n: int) -> list[tuple[Any, str, float, str]]:
    return [(_P1, f"cat{i:02d}", float(i) / 100.0, "ok") for i in range(n)]


def _construir_grafica_variacion(datos: pd.DataFrame, resultado: ResultadoVariacion) -> Any:
    """Helper de test: `_construir_grafica_linea` con los kwargs que usa `_graficar_variacion`."""
    return graficador._construir_grafica_linea(
        datos,
        resultado,
        columna_valor="variacion_pp",
        valor_base=0.0,
        etiqueta_y="Variación (pp)",
    )


# --------------------------------------------------------------------------- _construir_grafica_linea (variaciones)


def test_construir_grafica_variacion_mapea_y_a_variacion_pp() -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert grafica.mapping["y"] == "variacion_pp"


def test_construir_grafica_variacion_incluye_hline_si_0_en_rango() -> None:
    rv = _resultado_variacion([(_P1, "INPC", -1.0, "ok"), (_P2, "INPC", 1.0, "ok")])
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert "geom_hline" in _geoms(grafica)


def test_construir_grafica_variacion_sin_hline_si_0_fuera_de_rango() -> None:
    rv = _resultado_variacion([(_P1, "INPC", 5.0, "ok"), (_P2, "INPC", 8.0, "ok")])
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert "geom_hline" not in _geoms(grafica)


def test_construir_grafica_variacion_anota_texto_con_una_sola_serie() -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok"), (_P2, "INPC", 1.5, "ok")])
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert "geom_text" in _geoms(grafica)


def test_construir_grafica_variacion_no_anota_texto_con_varias_series() -> None:
    rv = _resultado_variacion(
        [(_P1, "cat_a", -0.5, "ok"), (_P1, "cat_b", 0.5, "ok")], tipo="CCIF DIVISION"
    )
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert "geom_text" not in _geoms(grafica)


def test_construir_grafica_variacion_etiqueta_y() -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    datos = graficador._aplanar_resultado(rv)
    grafica = _construir_grafica_variacion(datos, rv)
    assert grafica.labels.y == "Variación (pp)"


def test_construir_grafica_variacion_titulo_junta_tipos_de_resultado_y_comparacion() -> None:
    principal = _resultado_variacion([(_P1, "cat", 0.5, "ok")], tipo="CCIF DIVISION")
    comparacion = _resultado_variacion([(_P1, "INPC", 0.3, "ok")])
    datos = graficador._aplanar_resultado(principal, comparacion)
    grafica = _construir_grafica_variacion(datos, principal)
    assert grafica.labels.title == "CCIF DIVISION + INPC"


# --------------------------------------------------------------------------- graficar (variaciones)


def test_graficar_variacion_una_sola_imagen_bajo_capacidad(mocker: Any) -> None:
    rv = _resultado_variacion(_n_categorias_variacion(5), tipo="CCIF DIVISION")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_linea", return_value=grafica_falsa)
    graficador.graficar(rv)
    grafica_falsa.draw.assert_called_once_with(show=True)


def test_graficar_variacion_particiona_en_varias_imagenes(mocker: Any) -> None:
    rv = _resultado_variacion(_n_categorias_variacion(13), tipo="CCIF DIVISION")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_linea", return_value=grafica_falsa)
    graficador.graficar(rv)
    assert grafica_falsa.draw.call_count == 2
    grafica_falsa.draw.assert_called_with(show=True)


def test_graficar_variacion_recorta_tramo_antes_de_graficar(mocker: Any) -> None:
    p3 = PeriodoQuincenal(2018, 2, 1)
    rv = _resultado_variacion(
        [(_P1, "INPC", 0.1, "ok"), (_P2, "INPC", 0.2, "ok"), (p3, "INPC", 0.3, "ok")]
    )
    construir = mocker.patch.object(
        graficador, "_construir_grafica_linea", return_value=mocker.Mock()
    )
    graficador.graficar(rv, desde=_P2)
    datos_recibidos = construir.call_args[0][0]
    assert set(datos_recibidos["periodo"]) == {_P2, p3}


def test_graficar_dibuja_cada_grafica_para_variacion(mocker: Any) -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    grafica_falsa = mocker.Mock()
    construir = mocker.patch.object(
        graficador, "_construir_grafica_linea", return_value=grafica_falsa
    )
    graficador.graficar(rv)
    grafica_falsa.draw.assert_called_once_with(show=True)
    # Si _graficar_variacion alguna vez olvida estos kwargs (ej. reusa el
    # camino de índice por error), el mock los revela: sin esta aserción el
    # test seguiría verde con la etiqueta/base/columna de índice.
    construir.assert_called_once_with(
        mocker.ANY,
        rv,
        columna_valor="variacion_pp",
        valor_base=0.0,
        etiqueta_y="Variación (pp)",
    )


def test_graficar_variacion_comparacion_con_otra_clase_no_lanza(mocker: Any, capsys: Any) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_linea")
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")], clase="periodica_mensual")
    comparacion = _resultado_variacion([(_P1, "INPC", 0.3, "ok")], clase="periodica_trimestral")
    graficador.graficar(rv, comparacion=comparacion)
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_variacion_comparacion_periodicidad_distinta_no_lanza(
    mocker: Any, capsys: Any
) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_linea")
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")])
    comparacion = _resultado_variacion([(PeriodoMensual(2018, 1), "INPC", 0.3, "ok")])
    graficador.graficar(rv, comparacion=comparacion)
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_variacion_comparacion_misma_clase_dibuja(mocker: Any) -> None:
    rv = _resultado_variacion([(_P1, "INPC", 0.5, "ok")], clase="periodica_mensual")
    comparacion = _resultado_variacion([(_P1, "INPC", 0.3, "ok")], clase="periodica_mensual")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_linea", return_value=grafica_falsa)
    graficador.graficar(rv, comparacion=comparacion)
    grafica_falsa.draw.assert_called_once_with(show=True)


# --------------------------------------------------------------------------- helpers incidencias


def _resultado_incidencia(
    filas: list[tuple[Any, str, float, str]],
    tipo: str = "COG",
    clase: str = "periodica_anual",
) -> ResultadoIncidencia:
    """filas = list of (periodo, indice, incidencia_pp, estado)."""
    registros = [
        {
            "periodo": p,
            "indice": i,
            "tipo": tipo,
            "clase_incidencia": clase,
            "incidencia_pp": v,
            "estado_calculo": e,
        }
        for p, i, v, e in filas
    ]
    df = pd.DataFrame(registros)
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


_M1 = PeriodoMensual(2024, 1)
_M2 = PeriodoMensual(2024, 2)


def _barras_y_linea() -> tuple[pd.DataFrame, pd.DataFrame]:
    incidencia = _resultado_incidencia(
        [
            (_M1, "cat_a", 2.0, "ok"),
            (_M1, "cat_b", -0.5, "ok"),
            (_M2, "cat_a", 1.0, "ok"),
            (_M2, "cat_b", 0.5, "ok"),
        ]
    )
    variacion = _resultado_variacion(
        [(_M1, "INPC", 1.5, "ok"), (_M2, "INPC", 1.5, "ok")], clase="periodica_anual"
    )
    return graficador._aplanar_resultado(incidencia), graficador._aplanar_resultado(variacion)


# --------------------------------------------------------------------------- _construir_grafica_barras


def test_construir_barras_usa_geom_col_y_linea_base() -> None:
    datos, _ = _barras_y_linea()
    grafica = graficador._construir_grafica_barras(datos)
    assert "geom_col" in _geoms(grafica)
    assert "geom_hline" in _geoms(grafica)


def test_construir_barras_sin_linea_no_agrega_geom_line() -> None:
    datos, _ = _barras_y_linea()
    assert "geom_line" not in _geoms(graficador._construir_grafica_barras(datos))


def test_construir_barras_con_linea_agrega_geom_line() -> None:
    datos, linea = _barras_y_linea()
    assert "geom_line" in _geoms(graficador._construir_grafica_barras(datos, linea))


def test_construir_barras_agrupa_relleno_por_indice() -> None:
    datos, _ = _barras_y_linea()
    grafica = graficador._construir_grafica_barras(datos)
    capa = next(c for c in grafica.layers if type(c.geom).__name__ == "geom_col")
    assert capa.mapping["fill"] == "indice"


def test_construir_barras_respeta_el_orden_de_apilado_pedido() -> None:
    datos, _ = _barras_y_linea()
    grafica = graficador._construir_grafica_barras(datos, orden=["cat_b", "cat_a"])
    capa = next(c for c in grafica.layers if type(c.geom).__name__ == "geom_col")
    # `layer._data` esta tipado como union laxa (Callable/None/convertible);
    # aca siempre es el DataFrame que se le paso a geom_col.
    datos_capa = cast(pd.DataFrame, capa._data)
    assert list(datos_capa["indice"].cat.categories) == ["cat_b", "cat_a"]


def test_construir_barras_renderiza_segmentos_de_ambos_signos() -> None:
    # Render real: geom_col produce una PolyCollection (no ax.patches, y no la
    # primera coleccion del eje -- esa es la LineCollection de geom_hline), con
    # un path por segmento. Periodo 1: +2.0 y -0.5, asi que el techo es 2.0 y
    # el piso -0.5; el NETO de ese periodo es 1.5 y no corresponde a ningun
    # borde dibujado.
    datos, linea = _barras_y_linea()
    figura = graficador._construir_grafica_barras(datos, linea).draw()
    try:
        from matplotlib.collections import PolyCollection

        coleccion = next(c for c in figura.axes[0].collections if isinstance(c, PolyCollection))
        # `Path.vertices` esta tipado como union de convertibles a array; en
        # tiempo de ejecucion siempre es un ndarray (N, 2).
        alturas = [np.asarray(p.vertices)[:, 1] for p in coleccion.get_paths()]
        topes = [float(y.max()) for y in alturas]
        pisos = [float(y.min()) for y in alturas]
        assert max(topes) == pytest.approx(2.0)
        assert min(pisos) == pytest.approx(-0.5)
    finally:
        import matplotlib.pyplot as plt

        plt.close(figura)


def test_construir_barras_eje_y_cubre_el_apilado_no_el_valor_individual() -> None:
    # Periodo 2: 1.0 + 0.5 apilados = 1.5, ninguno de los dos valores llega
    # ahi por si solo. Con el rango calculado sobre la columna, un apilado que
    # supere al mayor valor individual quedaria fuera del panel.
    datos, _ = _barras_y_linea()
    datos = datos[datos["periodo"] == _M2]
    figura = graficador._construir_grafica_barras(datos).draw()
    try:
        piso, techo = figura.axes[0].get_ylim()
        assert techo >= 1.5
        assert piso <= 0.0
    finally:
        import matplotlib.pyplot as plt

        plt.close(figura)


# --------------------------------------------------------------------------- _graficar_incidencia


def test_graficar_incidencia_una_sola_imagen(mocker: Any) -> None:
    # Sin particionado: cada particion mostraria una suma parcial y la linea de
    # referencia no cerraria con ninguna.
    ri = _resultado_incidencia([(_M1, f"cat{i:02d}", float(i), "ok") for i in range(12)])
    grafica_falsa = mocker.Mock()
    construir = mocker.patch.object(
        graficador, "_construir_grafica_barras", return_value=grafica_falsa
    )
    graficador._graficar_incidencia(ri, None, None, None)
    construir.assert_called_once()
    grafica_falsa.draw.assert_called_once_with(show=True)


def test_graficar_incidencia_recorta_barras_y_linea(mocker: Any) -> None:
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok"), (_M2, "cat_a", 2.0, "ok")])
    rv = _resultado_variacion(
        [(_M1, "INPC", 1.0, "ok"), (_M2, "INPC", 2.0, "ok")], clase="periodica_anual"
    )
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    graficador._graficar_incidencia(ri, rv, _M2, None)
    datos, linea = construir.call_args[0]
    assert set(datos["periodo"]) == {_M2}
    assert set(linea["periodo"]) == {_M2}


def test_graficar_incidencia_sin_comparacion_pasa_none(mocker: Any) -> None:
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")])
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    graficador._graficar_incidencia(ri, None, None, None)
    assert construir.call_args[0][1] is None


# --------------------------------------------------------------------------- graficar() con incidencias


def test_graficar_despacha_incidencia_a_barras(mocker: Any) -> None:
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")])
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_barras", return_value=grafica_falsa)
    graficador.graficar(ri)
    grafica_falsa.draw.assert_called_once_with(show=True)


def test_graficar_incidencia_comparacion_de_otra_incidencia_no_lanza(
    mocker: Any, capsys: Any
) -> None:
    # Superponer dos incidencias no dice nada: las barras SON la descomposicion
    # de la linea, asi que la comparacion tiene que ser un ResultadoVariacion.
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")])
    graficador.graficar(ri, comparacion=_resultado_incidencia([(_M1, "cat_b", 1.0, "ok")]))  # type: ignore[arg-type]
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_incidencia_comparacion_periodicidad_distinta_no_lanza(
    mocker: Any, capsys: Any
) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")])
    rv = _resultado_variacion([(_P1, "INPC", 1.0, "ok")], clase="periodica_anual")
    graficador.graficar(ri, comparacion=rv)
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_incidencia_comparacion_de_otra_clase_no_lanza(mocker: Any, capsys: Any) -> None:
    construir = mocker.patch.object(graficador, "_construir_grafica_barras")
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")], clase="periodica_anual")
    rv = _resultado_variacion([(_M1, "INPC", 1.0, "ok")], clase="periodica_mensual")
    graficador.graficar(ri, comparacion=rv)
    assert "Error" in capsys.readouterr().out
    construir.assert_not_called()


def test_graficar_incidencia_comparacion_valida_dibuja(mocker: Any) -> None:
    ri = _resultado_incidencia([(_M1, "cat_a", 1.0, "ok")], clase="periodica_anual")
    rv = _resultado_variacion([(_M1, "INPC", 1.0, "ok")], clase="periodica_anual")
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_construir_grafica_barras", return_value=grafica_falsa)
    graficador.graficar(ri, comparacion=rv)
    grafica_falsa.draw.assert_called_once_with(show=True)
