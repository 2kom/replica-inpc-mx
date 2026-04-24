from __future__ import annotations

import uuid

import pandas as pd
import pytest

from replica_inpc.api.validacion import validar_mensual, validar_quincenal
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_ID = str(uuid.uuid4())
_TOKEN = "token-test"

_PQ1 = PeriodoQuincenal(2018, 8, 1)
_PQ2 = PeriodoQuincenal(2018, 8, 2)
_PM1 = PeriodoMensual(2018, 8)
_PM2 = PeriodoMensual(2018, 9)


def _resultado_quincenal(periodos, tipo="inpc"):
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    return ResultadoCalculo(
        pd.DataFrame(
            {
                "version": [2018] * len(periodos),
                "tipo": tipo,
                "indice_replicado": pd.array([103.5] * len(periodos), dtype="Float64"),
                "estado_calculo": ["ok"] * len(periodos),
                "motivo_error": [None] * len(periodos),
            },
            index=idx,
        ),
        _ID,
    )


def _resultado_mensual(periodos, tipo="inpc"):
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    return ResultadoCalculo(
        pd.DataFrame(
            {
                "version": [2018] * len(periodos),
                "tipo": tipo,
                "indice_replicado": pd.array([103.5] * len(periodos), dtype="Float64"),
                "estado_calculo": ["ok"] * len(periodos),
                "motivo_error": [None] * len(periodos),
            },
            index=idx,
        ),
        _ID,
    )


class TestValidarMensual:
    def test_acepta_resultado_mensual(self, mocker):
        mock_fuente = mocker.MagicMock()
        mock_fuente.obtener.return_value = {"INPC": {_PM1: 103.5}}
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)

        r = _resultado_mensual([_PM1])
        resumen, reporte, diag = validar_mensual(r, _TOKEN)

        assert resumen is not None
        assert reporte is not None
        assert diag is not None

    def test_acepta_resultado_quincenal_convierte(self, mocker):
        mock_fuente = mocker.MagicMock()
        mock_fuente.obtener.return_value = {"INPC": {_PM1: 103.5}}
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)

        r = _resultado_quincenal([_PQ1, _PQ2])
        resumen, _, _ = validar_mensual(r, _TOKEN)

        periodos_validados = resumen.df.loc[_ID, "periodo_inicio"]
        assert isinstance(periodos_validados, PeriodoMensual)

    def test_construye_fuente_con_token_y_tipo(self, mocker):
        mock_cls = mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi")
        mock_cls.return_value.obtener.return_value = {"INPC": {_PM1: 103.5}}

        r = _resultado_mensual([_PM1], tipo="inpc")
        validar_mensual(r, _TOKEN)

        mock_cls.assert_called_once_with(token=_TOKEN, tipo="inpc")

    def test_pasa_periodos_a_obtener(self, mocker):
        mock_fuente = mocker.MagicMock()
        mock_fuente.obtener.return_value = {"INPC": {_PM1: 103.5, _PM2: 104.0}}
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)

        r = _resultado_mensual([_PM1, _PM2])
        validar_mensual(r, _TOKEN)

        periodos_pasados = mock_fuente.obtener.call_args[0][0]
        assert set(periodos_pasados) == {_PM1, _PM2}


class TestValidarQuincenal:
    def test_acepta_resultado_quincenal(self, mocker):
        mock_fuente = mocker.MagicMock()
        mock_fuente.obtener.return_value = {"INPC": {_PQ1: 103.5}}
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)

        r = _resultado_quincenal([_PQ1])
        resumen, reporte, diag = validar_quincenal(r, _TOKEN)

        assert resumen is not None
        assert reporte is not None
        assert diag is not None

    def test_rechaza_resultado_mensual(self, mocker):
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi")

        r = _resultado_mensual([_PM1])
        with pytest.raises(ErrorConfiguracion):
            validar_quincenal(r, _TOKEN)

    def test_construye_fuente_con_token_y_tipo(self, mocker):
        mock_cls = mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi")
        mock_cls.return_value.obtener.return_value = {"INPC": {_PQ1: 103.5}}

        r = _resultado_quincenal([_PQ1], tipo="inpc")
        validar_quincenal(r, _TOKEN)

        mock_cls.assert_called_once_with(token=_TOKEN, tipo="inpc")

    def test_pasa_periodos_quincenales_a_obtener(self, mocker):
        mock_fuente = mocker.MagicMock()
        mock_fuente.obtener.return_value = {"INPC": {_PQ1: 103.5, _PQ2: 104.0}}
        mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)

        r = _resultado_quincenal([_PQ1, _PQ2])
        validar_quincenal(r, _TOKEN)

        periodos_pasados = mock_fuente.obtener.call_args[0][0]
        assert set(periodos_pasados) == {_PQ1, _PQ2}
