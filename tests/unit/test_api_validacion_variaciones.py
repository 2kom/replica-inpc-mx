from __future__ import annotations

import uuid

import pandas as pd
import pytest

from replica_inpc.api.validacion import validar_variaciones_mensual, validar_variaciones_quincenal
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal

_ID = str(uuid.uuid4())
_TOKEN = "token-test"

_PERIODOS_M = [PeriodoMensual(2019, m) for m in range(1, 10)]
_PERIODOS_Q = [PeriodoQuincenal(2019, m, q) for m in range(1, 6) for q in (1, 2)]


def _rv_mensual(periodos, clase="periodica", descripcion="mensual", semiok=None):
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    valores = [0.005 + i * 0.001 for i in range(len(periodos))]
    return ResultadoVariacion(
        pd.DataFrame({"variacion": pd.array(valores, dtype="Float64")}, index=idx),
        tipo="inpc",
        descripcion=descripcion,
        clase_variacion=clase,  # type: ignore[arg-type]
        periodos_semiok=frozenset(semiok) if semiok else None,
    )


def _rv_quincenal(periodos, clase="periodica", descripcion="quincenal"):
    idx = pd.MultiIndex.from_tuples([(p, "INPC") for p in periodos], names=["periodo", "indice"])
    return ResultadoVariacion(
        pd.DataFrame({"variacion": pd.array([0.005] * len(periodos), dtype="Float64")}, index=idx),
        tipo="inpc",
        descripcion=descripcion,
        clase_variacion=clase,  # type: ignore[arg-type]
    )


def _mock_fuente(mocker, periodos):
    mock_fuente = mocker.MagicMock()
    mock_fuente.obtener_variaciones.return_value = {"INPC": {p: None for p in periodos}}
    mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)
    return mock_fuente


class TestRetorno:
    def test_retorna_reporte(self, mocker):
        _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M)
        from replica_inpc.dominio.modelos.validacion import ReporteValidacionVariaciones

        assert isinstance(validar_variaciones_mensual(rv, _TOKEN), ReporteValidacionVariaciones)

    def test_periodica_mensual_ok(self, mocker):
        _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="mensual")
        result = validar_variaciones_mensual(rv, _TOKEN)
        assert result is not None

    def test_periodica_anual_ok(self, mocker):
        _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="anual")
        result = validar_variaciones_mensual(rv, _TOKEN)
        assert result is not None

    def test_acumulada_anual_ok(self, mocker):
        _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="acumulada_anual", descripcion="acumulada_anual")
        result = validar_variaciones_mensual(rv, _TOKEN)
        assert result is not None


class TestErrores:
    def test_clase_desde_lanza_error(self, mocker):
        rv = _rv_mensual(_PERIODOS_M, clase="desde", descripcion="desde 2019/01 hasta 2019/09")
        with pytest.raises(ErrorConfiguracion, match="desde"):
            validar_variaciones_mensual(rv, _TOKEN)

    def test_periodica_bimestral_lanza_error(self, mocker):
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="bimestral")
        with pytest.raises(ErrorConfiguracion, match="bimestral"):
            validar_variaciones_mensual(rv, _TOKEN)

    def test_periodica_trimestral_lanza_error(self, mocker):
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="trimestral")
        with pytest.raises(ErrorConfiguracion):
            validar_variaciones_mensual(rv, _TOKEN)

    def test_periodos_quincenales_lanza_error(self, mocker):
        rv = _rv_quincenal(_PERIODOS_Q)
        with pytest.raises(ErrorConfiguracion, match="PeriodoMensual"):
            validar_variaciones_mensual(rv, _TOKEN)


class TestLlamadasFuente:
    def test_construye_fuente_con_token_y_tipo(self, mocker):
        mock_cls = mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi")
        mock_cls.return_value.obtener_variaciones.return_value = {
            "INPC": {p: None for p in _PERIODOS_M}
        }
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="mensual")
        validar_variaciones_mensual(rv, _TOKEN)
        mock_cls.assert_called_once_with(token=_TOKEN, tipo="inpc")

    def test_llama_obtener_variaciones_una_vez(self, mocker):
        mock_fuente = _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M)
        validar_variaciones_mensual(rv, _TOKEN)
        assert mock_fuente.obtener_variaciones.call_count == 1

    def test_periodica_mensual_usa_tipo_periodica(self, mocker):
        mock_fuente = _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="mensual")
        validar_variaciones_mensual(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "periodica"

    def test_periodica_anual_usa_tipo_interanual(self, mocker):
        mock_fuente = _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="periodica", descripcion="anual")
        validar_variaciones_mensual(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "interanual"

    def test_acumulada_usa_tipo_acumulada_anual(self, mocker):
        mock_fuente = _mock_fuente(mocker, _PERIODOS_M)
        rv = _rv_mensual(_PERIODOS_M, clase="acumulada_anual", descripcion="acumulada_anual")
        validar_variaciones_mensual(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "acumulada_anual"


def _mock_fuente_q(mocker, periodos):
    mock_fuente = mocker.MagicMock()
    mock_fuente.obtener_variaciones.return_value = {"INPC": {p: None for p in periodos}}
    mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi", return_value=mock_fuente)
    return mock_fuente


class TestQuincenal:
    def test_retorna_reporte(self, mocker):
        _mock_fuente_q(mocker, _PERIODOS_Q)
        rv = _rv_quincenal(_PERIODOS_Q)
        from replica_inpc.dominio.modelos.validacion import ReporteValidacionVariaciones

        assert isinstance(validar_variaciones_quincenal(rv, _TOKEN), ReporteValidacionVariaciones)

    def test_clase_desde_lanza_error(self):
        rv = _rv_quincenal(
            _PERIODOS_Q, clase="desde", descripcion="desde 2019/01/1 hasta 2019/05/2"
        )
        with pytest.raises(ErrorConfiguracion, match="desde"):
            validar_variaciones_quincenal(rv, _TOKEN)

    def test_periodos_mensuales_lanza_error(self):
        rv = _rv_mensual(_PERIODOS_M)
        with pytest.raises(ErrorConfiguracion, match="PeriodoQuincenal"):
            validar_variaciones_quincenal(rv, _TOKEN)

    def test_periodica_quincenal_usa_periodica(self, mocker):
        mock_fuente = _mock_fuente_q(mocker, _PERIODOS_Q)
        rv = _rv_quincenal(_PERIODOS_Q, clase="periodica", descripcion="quincenal")
        validar_variaciones_quincenal(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "periodica"

    def test_periodica_anual_usa_interanual(self, mocker):
        mock_fuente = _mock_fuente_q(mocker, _PERIODOS_Q)
        rv = _rv_quincenal(_PERIODOS_Q, clase="periodica", descripcion="anual")
        validar_variaciones_quincenal(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "interanual"

    def test_acumulada_anual_usa_acumulada_anual(self, mocker):
        mock_fuente = _mock_fuente_q(mocker, _PERIODOS_Q)
        rv = _rv_quincenal(_PERIODOS_Q, clase="acumulada_anual", descripcion="acumulada_anual")
        validar_variaciones_quincenal(rv, _TOKEN)
        tipo_llamado = mock_fuente.obtener_variaciones.call_args[0][1]
        assert tipo_llamado == "acumulada_anual"

    def test_periodica_bimestral_lanza_error(self):
        rv = _rv_quincenal(_PERIODOS_Q, clase="periodica", descripcion="bimestral")
        with pytest.raises(ErrorConfiguracion, match="bimestral"):
            validar_variaciones_quincenal(rv, _TOKEN)

    def test_construye_fuente_con_token_y_tipo(self, mocker):
        mock_cls = mocker.patch("replica_inpc.api.validacion.FuenteValidacionApi")
        mock_cls.return_value.obtener_variaciones.return_value = {
            "INPC": {p: None for p in _PERIODOS_Q}
        }
        rv = _rv_quincenal(_PERIODOS_Q)
        validar_variaciones_quincenal(rv, _TOKEN)
        mock_cls.assert_called_once_with(token=_TOKEN, tipo="inpc")
