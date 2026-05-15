from __future__ import annotations

from replica_inpc.api import incidencias
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

# -- series: conversión de frontera --------------------------------------------


def test_incidencia_periodica_delega(mocker) -> None:
    fn = mocker.patch.object(incidencias, "_incidencia_periodica", return_value="ri")
    assert incidencias.incidencia_periodica("inpc", "clas", {2024: "c"}, "mensual") == "ri"
    fn.assert_called_once_with("inpc", "clas", {2024: "c"}, "mensual")


def test_incidencia_desde_convierte_desde_y_hasta(mocker) -> None:
    fn = mocker.patch.object(incidencias, "_incidencia_desde", return_value="ri")

    incidencias.incidencia_desde(
        "inpc", "clas", {2024: "c"}, "ene 2024", "DIC 2024", incluir_parciales=False
    )

    fn.assert_called_once_with(
        "inpc", "clas", {2024: "c"}, PeriodoMensual(2024, 1), PeriodoMensual(2024, 12), False
    )


def test_incidencia_desde_extremos_none(mocker) -> None:
    fn = mocker.patch.object(incidencias, "_incidencia_desde", return_value="ri")
    incidencias.incidencia_desde("inpc", "clas", {2024: "c"})
    fn.assert_called_once_with("inpc", "clas", {2024: "c"}, None, None, True)


# -- análisis: Periodo -> str en las tuplas ------------------------------------


def test_mayor_incidencia_devuelve_periodo_como_str(mocker) -> None:
    mocker.patch.object(
        incidencias._consulta,
        "mayor_incidencia",
        return_value=(PeriodoMensual(2024, 6), "Alimentos", 0.42),
    )
    periodo, indice, valor = incidencias.mayor_incidencia("ri")
    assert (periodo, indice, valor) == ("Jun 2024", "Alimentos", 0.42)
    assert isinstance(periodo, str)


def test_menor_incidencia_devuelve_periodo_como_str(mocker) -> None:
    mocker.patch.object(
        incidencias._consulta,
        "menor_incidencia",
        return_value=(PeriodoQuincenal(2021, 9, 2), "energeticos", -0.1),
    )
    periodo, indice, valor = incidencias.menor_incidencia("ri")
    assert periodo == "2Q Sep 2021"
    assert (indice, valor) == ("energeticos", -0.1)


def test_incidencia_en_parsea_periodo(mocker) -> None:
    fn = mocker.patch.object(incidencias._consulta, "incidencia_en", return_value="df")
    assert incidencias.incidencia_en("ri", "dic 2024") == "df"
    fn.assert_called_once_with("ri", PeriodoMensual(2024, 12))
