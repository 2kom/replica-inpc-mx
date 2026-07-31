from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from replica_inpc.dominio.modelos.indice import ResultadoIndice
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import ManifestCalculo
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
    datos = graficador._aplanar_resultado_indice(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert grafica.mapping["color"] == "indice"


def test_construir_grafica_incluye_hline_si_100_en_rango() -> None:
    r = _resultado([(_P1, "INPC", 90.0, "ok"), (_P2, "INPC", 110.0, "ok")])
    datos = graficador._aplanar_resultado_indice(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_hline" in _geoms(grafica)


def test_construir_grafica_sin_hline_si_100_fuera_de_rango() -> None:
    r = _resultado([(_P1, "INPC", 120.0, "ok"), (_P2, "INPC", 150.0, "ok")])
    datos = graficador._aplanar_resultado_indice(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_hline" not in _geoms(grafica)


def test_construir_grafica_anota_texto_con_una_sola_serie() -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok"), (_P2, "INPC", 110.0, "ok")])
    datos = graficador._aplanar_resultado_indice(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_text" in _geoms(grafica)


def test_construir_grafica_no_anota_texto_con_varias_series() -> None:
    r = _resultado([(_P1, "cat_a", 90.0, "ok"), (_P1, "cat_b", 110.0, "ok")], tipo="CCIF DIVISION")
    datos = graficador._aplanar_resultado_indice(r)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert "geom_text" not in _geoms(grafica)


def test_construir_grafica_titulo_junta_tipos_de_resultado_y_comparacion() -> None:
    r = _resultado([(_P1, "cat_a", 90.0, "ok")], tipo="CCIF DIVISION")
    comparacion = _resultado([(_P1, "INPC", 100.0, "ok")])
    datos = graficador._aplanar_resultado_indice(r, comparacion)
    grafica = graficador._construir_grafica_linea(datos, r)
    assert grafica.labels.title == "CCIF DIVISION + INPC"


# --------------------------------------------------------------------------- _graficas_linea


def test_graficas_linea_una_sola_imagen_bajo_capacidad() -> None:
    r = _resultado(_n_categorias(5), tipo="CCIF DIVISION")
    graficas = graficador._graficas_linea(r)
    assert len(graficas) == 1


def test_graficas_linea_particiona_en_varias_imagenes() -> None:
    r = _resultado(_n_categorias(13), tipo="CCIF DIVISION")
    graficas = graficador._graficas_linea(r)
    assert len(graficas) == 2


def test_graficas_linea_recorta_tramo_antes_de_graficar() -> None:
    p3 = PeriodoQuincenal(2018, 2, 1)
    r = _resultado(
        [(_P1, "INPC", 100.0, "ok"), (_P2, "INPC", 105.0, "ok"), (p3, "INPC", 110.0, "ok")]
    )
    graficas = graficador._graficas_linea(r, desde=_P2)
    assert set(graficas[0].data["periodo"]) == {_P2, p3}


# --------------------------------------------------------------------------- graficar_indice


def test_graficar_indice_dibuja_cada_grafica(mocker: Any) -> None:
    r = _resultado([(_P1, "INPC", 100.0, "ok")])
    grafica_falsa = mocker.Mock()
    mocker.patch.object(graficador, "_graficas_linea", return_value=[grafica_falsa, grafica_falsa])
    graficador.graficar_indice(r)
    assert grafica_falsa.draw.call_count == 2
    grafica_falsa.draw.assert_called_with(show=True)


def test_graficar_indice_tipo_invalido_no_lanza(capsys: Any) -> None:
    graficador.graficar_indice("no es un ResultadoIndice")  # type: ignore[arg-type]
    assert "Error" in capsys.readouterr().out
