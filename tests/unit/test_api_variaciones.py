from __future__ import annotations

from replica_inpc.api import variaciones
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

# -- series: conversión de frontera --------------------------------------------


def test_variacion_periodica_delega(mocker) -> None:
    fn = mocker.patch.object(variaciones, "_variacion_periodica", return_value="rv")
    assert variaciones.variacion_periodica("idx", "mensual") == "rv"
    fn.assert_called_once_with("idx", "mensual")


def test_variacion_desde_convierte_desde_y_hasta(mocker) -> None:
    fn = mocker.patch.object(variaciones, "_variacion_desde", return_value="rv")

    variaciones.variacion_desde("idx", "ene 2015", "DIC 2024", incluir_parciales=False)

    fn.assert_called_once_with(
        "idx", PeriodoMensual(2015, 1), PeriodoMensual(2024, 12), False
    )


def test_variacion_desde_hasta_none_pasa_none(mocker) -> None:
    fn = mocker.patch.object(variaciones, "_variacion_desde", return_value="rv")
    variaciones.variacion_desde("idx", "2q jul 2018")
    fn.assert_called_once_with("idx", PeriodoQuincenal(2018, 7, 2), None, True)


# -- análisis: Periodo -> str en las tuplas ------------------------------------


def test_inflacion_maxima_devuelve_periodo_como_str(mocker) -> None:
    mocker.patch.object(
        variaciones._consulta,
        "inflacion_maxima",
        return_value=(PeriodoMensual(2024, 12), "INPC", 1.5),
    )
    periodo, indice, valor = variaciones.inflacion_maxima("rv")
    assert (periodo, indice, valor) == ("Dic 2024", "INPC", 1.5)
    assert isinstance(periodo, str)


def test_inflacion_minima_devuelve_periodo_como_str(mocker) -> None:
    mocker.patch.object(
        variaciones._consulta,
        "inflacion_minima",
        return_value=(PeriodoQuincenal(2020, 4, 1), "subyacente", -0.3),
    )
    periodo, indice, valor = variaciones.inflacion_minima("rv")
    assert periodo == "1Q Abr 2020"
    assert (indice, valor) == ("subyacente", -0.3)


def test_inflacion_en_parsea_periodo(mocker) -> None:
    fn = mocker.patch.object(variaciones._consulta, "inflacion_en", return_value="df")
    assert variaciones.inflacion_en("rv", "dic 2024") == "df"
    fn.assert_called_once_with("rv", PeriodoMensual(2024, 12))


def test_inflacion_acumulada_convierte_rango(mocker) -> None:
    fn = mocker.patch.object(variaciones._consulta, "inflacion_acumulada", return_value=2.0)
    variaciones.inflacion_acumulada("rv", "ene 2015", "dic 2024", indice="INPC")
    fn.assert_called_once_with(
        "rv", PeriodoMensual(2015, 1), PeriodoMensual(2024, 12), indice="INPC"
    )
