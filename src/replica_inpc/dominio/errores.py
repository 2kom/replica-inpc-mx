# Clase Base
class ReplicaInpcError(Exception):
    pass


# Clases para errores de importación de datos - falla la corrida de inmediato
class ErrorImportacion(ReplicaInpcError):
    pass


class ArchivoNoEncontrado(ErrorImportacion):
    pass


class ArchivoVacio(ErrorImportacion):
    pass


class ArchivoCorrupto(ErrorImportacion):
    pass


class EncodingNoLegible(ErrorImportacion):
    pass


class OrientacionNoDetectable(ErrorImportacion):
    pass


class ColumnasMinFaltantes(ErrorImportacion):
    pass


class CanastaNoSoportada(ErrorImportacion):
    pass


class PeriodoNoInterpretable(ErrorImportacion):
    pass


class VersionNoCoincide(ErrorImportacion):
    pass


# Errores de dominio - invariante violado al construir un contrato
class ErrorDominio(ReplicaInpcError):
    pass


class InvarianteViolado(ErrorDominio):
    pass


# Errores de calculo - fallan la corrida inmediatamente
class ErrorCalculo(ReplicaInpcError):
    pass


class CorrespondenciaInsuficiente(ErrorCalculo):
    pass


class PonderadorFaltante(ErrorCalculo):
    pass


class SerieVacia(ErrorCalculo):
    pass


class CanastaSinGenericos(ErrorCalculo):
    pass


# Errores de validacion - no fallan la corrida
class ErrorValidacion(ReplicaInpcError):
    pass


class FuenteNoDisponible(ErrorValidacion):
    pass


class RespuestaInvalida(ErrorValidacion):
    pass
