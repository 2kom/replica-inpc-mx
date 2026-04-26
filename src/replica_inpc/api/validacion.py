from __future__ import annotations

from replica_inpc.dominio.conversion import a_mensual
from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.dominio.modelos.incidencia import ResultadoIncidencia
from replica_inpc.dominio.modelos.resultado import ResultadoCalculo
from replica_inpc.dominio.modelos.validacion import (
    DiagnosticoFaltantes,
    ReporteDetalladoValidacion,
    ReporteValidacionIncidencias,
    ReporteValidacionVariaciones,
    ResumenValidacion,
)
from replica_inpc.dominio.modelos.variacion import ResultadoVariacion
from replica_inpc.dominio.periodos import PeriodoMensual, PeriodoQuincenal
from replica_inpc.dominio.validar_incidencias import validar_incidencias as _validar_incidencias
from replica_inpc.dominio.validar_inpc import (
    validar_mensual as _validar_mensual,
)
from replica_inpc.dominio.validar_inpc import (
    validar_quincenal_resultado as _validar_quincenal_resultado,
)
from replica_inpc.dominio.validar_variaciones import validar_variaciones as _validar_variaciones
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

_FRECUENCIAS_INEGI = {"mensual": "periodica", "anual": "interanual"}

_FRECUENCIAS_INEGI_QUINCENAL = {"quincenal": "periodica", "anual": "interanual"}


def validar_variaciones_mensual(
    rv: ResultadoVariacion,
    token: str,
) -> ReporteValidacionVariaciones:
    """Valida una variación mensual calculada contra series publicadas por el INEGI.

    Soporta variaciones de clase 'periodica' (frecuencias 'mensual' o 'anual') y
    'acumulada_anual'. Lanza ErrorConfiguracion si la clase es 'desde' o si la
    frecuencia de 'periodica' no es mensual ni anual.
    Ver docs/diseño.md §6.3.
    """
    clase = rv.clase_variacion

    if clase == "desde":
        raise ErrorConfiguracion(
            "La variación 'desde' no tiene indicadores INEGI disponibles. "
            "Solo se pueden validar variaciones 'periodica' (mensual o anual) y 'acumulada_anual'."
        )

    periodos = rv.df.index.get_level_values("periodo")
    if not isinstance(periodos[0], PeriodoMensual):
        raise ErrorConfiguracion(
            "validar_variaciones_mensual requiere periodos mensuales (PeriodoMensual). "
            "Calcula la variación sobre un ResultadoCalculo mensual o aplica a_mensual() antes."
        )

    if clase == "periodica":
        frecuencia = rv.descripcion
        if frecuencia not in _FRECUENCIAS_INEGI:
            raise ErrorConfiguracion(
                f"INEGI solo publica variación periódica mensual e interanual. "
                f"Frecuencia '{frecuencia}' no está disponible. "
                f"Frecuencias válidas: {list(_FRECUENCIAS_INEGI)}."
            )
        tipo_variacion_inegi = _FRECUENCIAS_INEGI[frecuencia]
    else:
        tipo_variacion_inegi = "acumulada_anual"

    periodos_lista = list(periodos.unique())
    fuente = FuenteValidacionApi(token=token, tipo=rv.tipo)
    inegi = fuente.obtener_variaciones(periodos_lista, tipo_variacion_inegi)  # type: ignore[arg-type]
    return _validar_variaciones(rv, tipo_variacion_inegi, inegi)  # type: ignore[arg-type]


def validar_variaciones_quincenal(
    rv: ResultadoVariacion,
    token: str,
) -> ReporteValidacionVariaciones:
    """Valida una variación quincenal calculada contra series publicadas por el INEGI.

    Soporta variaciones de clase 'periodica' (frecuencias 'quincenal' o 'anual') y
    'acumulada_anual'. Lanza ErrorConfiguracion si la clase es 'desde', si la
    frecuencia de 'periodica' no es quincenal ni anual, o si los periodos no son
    PeriodoQuincenal. Ver docs/diseño.md §6.3.
    """
    clase = rv.clase_variacion

    if clase == "desde":
        raise ErrorConfiguracion(
            "La variación 'desde' no tiene indicadores INEGI disponibles. "
            "Solo se pueden validar variaciones 'periodica' (quincenal o anual) y 'acumulada_anual'."
        )

    periodos = rv.df.index.get_level_values("periodo")
    if not isinstance(periodos[0], PeriodoQuincenal):
        raise ErrorConfiguracion(
            "validar_variaciones_quincenal requiere periodos quincenales (PeriodoQuincenal). "
            "Calcula la variación sobre un ResultadoCalculo quincenal."
        )

    if clase == "periodica":
        frecuencia = rv.descripcion
        if frecuencia not in _FRECUENCIAS_INEGI_QUINCENAL:
            raise ErrorConfiguracion(
                f"INEGI solo publica variación periódica quincenal e interanual. "
                f"Frecuencia '{frecuencia}' no está disponible. "
                f"Frecuencias válidas: {list(_FRECUENCIAS_INEGI_QUINCENAL)}."
            )
        tipo_variacion_inegi = _FRECUENCIAS_INEGI_QUINCENAL[frecuencia]
    else:
        tipo_variacion_inegi = "acumulada_anual"

    periodos_lista = list(periodos.unique())
    fuente = FuenteValidacionApi(token=token, tipo=rv.tipo)
    inegi = fuente.obtener_variaciones(periodos_lista, tipo_variacion_inegi)  # type: ignore[arg-type]
    return _validar_variaciones(rv, tipo_variacion_inegi, inegi)  # type: ignore[arg-type]


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
    return _validar_mensual(resultado, inegi)  # type: ignore[arg-type]


def validar_incidencias_mensual(
    ri: ResultadoIncidencia,
    token: str,
) -> ReporteValidacionIncidencias:
    """Valida incidencias mensuales calculadas contra series publicadas por el INEGI.

    Solo soporta clase_incidencia='periodica' con frecuencia='mensual'.
    Lanza ErrorConfiguracion para clases 'desde', 'acumulada_anual' o frecuencias
    distintas de 'mensual'. Ver docs/diseño.md §6.4.
    """
    clase = ri.clase_incidencia

    if clase == "desde":
        raise ErrorConfiguracion(
            "La incidencia 'desde' no tiene indicadores INEGI disponibles. "
            "Solo se puede validar incidencia 'periodica' con frecuencia 'mensual'."
        )
    if clase == "acumulada_anual":
        raise ErrorConfiguracion(
            "La incidencia 'acumulada_anual' no está disponible en la API INEGI para incidencias. "
            "Solo se puede validar incidencia 'periodica' con frecuencia 'mensual'."
        )
    if ri.frecuencia != "mensual":
        raise ErrorConfiguracion(
            f"INEGI solo publica incidencia periódica mensual. "
            f"Frecuencia '{ri.frecuencia}' no está disponible. Usa frecuencia='mensual'."
        )

    periodos = ri.df.index.get_level_values("periodo")
    if not isinstance(periodos[0], PeriodoMensual):
        raise ErrorConfiguracion(
            "validar_incidencias_mensual requiere periodos mensuales (PeriodoMensual). "
            "Calcula la incidencia sobre un ResultadoCalculo mensual o aplica a_mensual() antes."
        )

    periodos_lista = list(periodos.unique())
    fuente = FuenteValidacionApi(token=token, tipo=ri.tipo)
    inegi = fuente.obtener_incidencias(periodos_lista, "periodica")  # type: ignore[arg-type]
    return _validar_incidencias(ri, "periodica", inegi)  # type: ignore[arg-type]


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
    return _validar_quincenal_resultado(resultado, inegi)  # type: ignore[arg-type]
