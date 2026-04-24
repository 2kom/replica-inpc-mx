from __future__ import annotations

from replica_inpc.dominio.conversion import a_mensual
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
    ResumenValidacion,
)
from replica_inpc.dominio.periodos import PeriodoMensual
from replica_inpc.dominio.validar_inpc import (
    validar_mensual as _validar_mensual,
)
from replica_inpc.dominio.validar_inpc import (
    validar_quincenal_resultado as _validar_quincenal_resultado,
)
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi


def validar_mensual(
    resultado: ResultadoCalculo,
    token: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:
    """Valida un ResultadoCalculo contra índices mensuales del INEGI.

    Si resultado es quincenal, aplica a_mensual() internamente.
    Detecta tipo desde el resultado — soporta inpc, inflacion componente
    e inflacion subcomponente. Ver docs/diseño.md §6.2.
    """
    periodos = resultado.df.index.get_level_values("periodo")
    if not isinstance(periodos[0], PeriodoMensual):
        resultado = a_mensual(resultado)

    tipo = resultado.df["tipo"].iloc[0]
    periodos_lista = list(resultado.df.index.get_level_values("periodo").unique())
    fuente = FuenteValidacionApi(token=token, tipo=tipo)
    inegi = fuente.obtener(periodos_lista)
    return _validar_mensual(resultado, inegi)


def validar_quincenal(
    resultado: ResultadoCalculo,
    token: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:
    """Valida un ResultadoCalculo quincenal contra índices quincenales del INEGI.

    Lanza ErrorConfiguracion si resultado es mensual.
    Ver docs/diseño.md §6.2.
    """
    periodos = resultado.df.index.get_level_values("periodo")
    if isinstance(periodos[0], PeriodoMensual):
        raise ErrorConfiguracion(
            "validar_quincenal requiere un ResultadoCalculo quincenal. "
            "Para validar resultados mensuales usa validar_mensual()."
        )

    tipo = resultado.df["tipo"].iloc[0]
    periodos_lista = list(resultado.df.index.get_level_values("periodo").unique())
    fuente = FuenteValidacionApi(token=token, tipo=tipo)
    inegi = fuente.obtener(periodos_lista)
    return _validar_quincenal_resultado(resultado, inegi)
