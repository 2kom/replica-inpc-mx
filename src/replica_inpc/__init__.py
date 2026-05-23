"""replica_inpc — réplica del INPC de México.

Superficie pública flat estilo pandas: `import replica_inpc as rep` y luego
`rep.<func>(...)`. Ver `docs/rediseño/api.md`.
"""

from __future__ import annotations

import sys
from types import ModuleType

from replica_inpc.api import config as _config
from replica_inpc.api.config import limpiar_cache, set_token
from replica_inpc.api.flujos import calcular_historia
from replica_inpc.api.incidencias import (
    incidencia_acumulada,
    incidencia_acumulada_anual,
    incidencia_desde,
    incidencia_en,
    incidencia_periodica,
    incidencia_promedio,
    mayor_incidencia,
    menor_incidencia,
)
from replica_inpc.api.indices import a_mensual, calcular_indice, empalmar, rebasar
from replica_inpc.api.insumos import cargar_canasta, cargar_serie
from replica_inpc.api.validaciones import (
    TIPOS_CON_VALIDACION,
    validar_incidencia,
    validar_indice,
    validar_variacion,
)
from replica_inpc.api.variaciones import (
    inflacion_acumulada,
    inflacion_en,
    inflacion_maxima,
    inflacion_minima,
    inflacion_promedio,
    variacion_acumulada_anual,
    variacion_desde,
    variacion_periodica,
)
from replica_inpc.dominio.errores import (
    ArchivoCorrupto,
    ArchivoNoEncontrado,
    ArchivoVacio,
    ArtefactoNoEncontrado,
    CanastaNoSoportada,
    CanastaSinGenericos,
    ColumnasMinFaltantes,
    CorrespondenciaInsuficiente,
    EncodingNoLegible,
    ErrorCalculo,
    ErrorConfiguracion,
    ErrorDominio,
    ErrorImportacion,
    ErrorPersistencia,
    ErrorValidacion,
    FuenteNoDisponible,
    InvarianteViolado,
    OrientacionNoDetectable,
    PeriodoNoInterpretable,
    PeriodosInsuficientes,
    PonderadorFaltante,
    ReplicaInpcError,
    RespuestaInvalida,
    SerieVacia,
    VersionNoCoincide,
)
from replica_inpc.dominio.periodos import (
    PeriodoMensual,
    PeriodoQuincenal,
    periodo_desde_str,
)
from replica_inpc.dominio.tipos import VersionCanasta

__all__ = [
    # tipos de periodo
    "PeriodoMensual",
    "PeriodoQuincenal",
    "VersionCanasta",
    "periodo_desde_str",
    # config
    "limpiar_cache",
    "set_token",
    # insumos
    "cargar_canasta",
    "cargar_serie",
    # indices
    "a_mensual",
    "calcular_indice",
    "empalmar",
    "rebasar",
    # variaciones
    "inflacion_acumulada",
    "inflacion_en",
    "inflacion_maxima",
    "inflacion_minima",
    "inflacion_promedio",
    "variacion_acumulada_anual",
    "variacion_desde",
    "variacion_periodica",
    # incidencias
    "incidencia_acumulada",
    "incidencia_acumulada_anual",
    "incidencia_desde",
    "incidencia_en",
    "incidencia_periodica",
    "incidencia_promedio",
    "mayor_incidencia",
    "menor_incidencia",
    # validaciones
    "TIPOS_CON_VALIDACION",
    "validar_incidencia",
    "validar_indice",
    "validar_variacion",
    # flujos
    "calcular_historia",
    # errores
    "ArchivoCorrupto",
    "ArchivoNoEncontrado",
    "ArchivoVacio",
    "ArtefactoNoEncontrado",
    "CanastaNoSoportada",
    "CanastaSinGenericos",
    "ColumnasMinFaltantes",
    "CorrespondenciaInsuficiente",
    "EncodingNoLegible",
    "ErrorCalculo",
    "ErrorConfiguracion",
    "ErrorDominio",
    "ErrorImportacion",
    "ErrorPersistencia",
    "ErrorValidacion",
    "FuenteNoDisponible",
    "InvarianteViolado",
    "OrientacionNoDetectable",
    "PeriodoNoInterpretable",
    "PeriodosInsuficientes",
    "PonderadorFaltante",
    "ReplicaInpcError",
    "RespuestaInvalida",
    "SerieVacia",
    "VersionNoCoincide",
    # variables configurables (vía proxy de módulo)
    "tolerancia_indice",
    "tolerancia_derivados",
    "timeout_api",
]


class _ReplicaModule(ModuleType):
    """Módulo paquete con proxy de las variables configurables.

    `rep.tolerancia_indice = X` se redirige a `api/config.py` para que las
    funciones de validación lean siempre el valor vigente — un nombre
    re-exportado por valor no propagaría la reasignación.
    """

    _PROXY = ("tolerancia_indice", "tolerancia_derivados", "timeout_api")

    def __getattr__(self, name: str) -> object:
        if name in type(self)._PROXY:
            return getattr(_config, name)
        raise AttributeError(f"module 'replica_inpc' has no attribute '{name}'")

    def __setattr__(self, name: str, value: object) -> None:
        if name in type(self)._PROXY:
            setattr(_config, name, value)
        else:
            super().__setattr__(name, value)


sys.modules[__name__].__class__ = _ReplicaModule
