"""Jerarquía de excepciones propias del dominio y la aplicación.

Todas las excepciones del sistema heredan de `ReplicaInpcError` y se importan
desde este módulo. Las capas superiores no dependen de excepciones concretas de
infraestructura o de librerías externas.

Ver: docs/diseño.md §9.1, §9.2, §9.3
"""


class ReplicaInpcError(Exception):
    """Clase base de todas las excepciones del sistema."""

    pass


class ErrorImportacion(ReplicaInpcError):
    """Error de importación de datos que falla la corrida inmediatamente.

    Ver: docs/diseño.md §9.1, §9.2, §9.3
    """

    pass


class ArchivoNoEncontrado(ErrorImportacion):
    """No se encontró un archivo de entrada requerido."""

    pass


class ArchivoVacio(ErrorImportacion):
    """El archivo de entrada existe pero no contiene datos."""

    pass


class ArchivoCorrupto(ErrorImportacion):
    """El archivo de entrada no puede interpretarse con el formato esperado."""

    pass


class EncodingNoLegible(ErrorImportacion):
    """No se pudo decodificar el archivo con los encodings soportados."""

    pass


class OrientacionNoDetectable(ErrorImportacion):
    """No se pudo inferir la orientación válida del archivo de series."""

    pass


class ColumnasMinFaltantes(ErrorImportacion):
    """Faltan columnas mínimas requeridas en el archivo de entrada."""

    pass


class CanastaNoSoportada(ErrorImportacion):
    """La canasta importada no corresponde a una versión soportada."""

    pass


class PeriodoNoInterpretable(ErrorImportacion):
    """No se pudo parsear un texto de periodo al formato del dominio."""

    pass


class VersionNoCoincide(ErrorImportacion):
    """La versión esperada no coincide con la detectada en los datos importados."""

    pass


class SerieVacia(ErrorImportacion):
    """La serie importada no contiene filas útiles para el cálculo."""

    pass


class PeriodosInsuficientes(ErrorImportacion):
    """La serie no cubre suficientes periodos válidos para ejecutar la corrida."""

    pass


class ErrorDominio(ReplicaInpcError):
    """Error del dominio al construir o validar un contrato interno.

    Ver: docs/diseño.md §9.1, §9.2
    """

    pass


class InvarianteViolado(ErrorDominio):
    """Se violó una invariante de un modelo o contrato del dominio."""

    pass


class ErrorCalculo(ReplicaInpcError):
    """Error durante el cálculo del índice que falla la corrida.

    Ver: docs/diseño.md §9.1, §9.2
    """

    pass


class CorrespondenciaInsuficiente(ErrorCalculo):
    """Faltan genéricos de la canasta en la serie normalizada.

    Args:
        faltantes: Lista de genéricos de la canasta que no tuvieron
            correspondencia en la serie.

    Attributes:
        faltantes: Genéricos faltantes que detonaron el error.
    """

    def __init__(self, faltantes: list[str]) -> None:
        super().__init__(f"Genericos sin serie: {faltantes}")
        self.faltantes = faltantes


class PonderadorFaltante(ErrorCalculo):
    """Falta un ponderador requerido para completar el cálculo."""

    pass


class CanastaSinGenericos(ErrorCalculo):
    """La canasta no contiene genéricos utilizables para el cálculo."""

    pass


class ErrorValidacion(ReplicaInpcError):
    """Error durante la validación que no falla la corrida.

    Ver: docs/diseño.md §9.1, §9.2
    """

    pass


class FuenteNoDisponible(ErrorValidacion):
    """La fuente externa de validación no estuvo disponible."""

    pass


class RespuestaInvalida(ErrorValidacion):
    """La fuente externa respondió con un formato o contenido inválido."""

    pass


class ErrorConfiguracion(ReplicaInpcError):
    """El sistema fue ensamblado o invocado con una configuración inválida.

    Ver: docs/diseño.md §9.1
    """

    pass


class ErrorPersistencia(ReplicaInpcError):
    """Falló la lectura o escritura de artefactos internos.

    Ver: docs/diseño.md §9.1
    """

    pass


class ArtefactoNoEncontrado(ErrorPersistencia):
    """No se encontró un artefacto persistido solicitado."""

    pass
