# aqui van las funciones pequeñas que no ameritan un archivo aparte, pero que se usan en varios lugares

import re
from pathlib import Path

import pandas as pd

from canasta_inpc.esquema import COLUMNAS_BASE, VersionCanasta

_TRANS_TILDES = str.maketrans("áéíóúüÁÉÍÓÚÜ", "aeiouuAEIOUU")
_PATRON_ESPACIOS = re.compile(r"\s+")
_PATRON_PREFIJO_NUMERICO = re.compile(r"^\d+\s+")


def normalizar_texto(texto: str) -> str:
    """Minusculas, sin tildes (conserva la ñ), sin puntuacion, espacios simples.

    Mismo estandar que usa `src/replica_inpc/infraestructura/csv/_utils.py`
    (reimplementado acá porque `tools/` es standalone y no puede importar de
    `src/`). Ver: tools/uso_generar_canasta.md §Esquema del CSV de salida.
    """
    texto = texto.translate(_TRANS_TILDES).lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    return _PATRON_ESPACIOS.sub(" ", texto).strip()


def quitar_prefijo_numerico(texto: str) -> str:
    """Quita el prefijo numerico estructural inicial (ej. "01 alimentos" -> "alimentos").

    Debe correr DESPUES de `normalizar_texto`, nunca antes: depende de que ya
    no quede puntuacion ("." ")" "-") separando el numero del resto del texto.
    Ver: tools/uso_generar_canasta.md §Esquema del CSV de salida.
    """
    return _PATRON_PREFIJO_NUMERICO.sub("", texto, count=1)


# para guardar el contenido de las columnas se siguen las siguientes reglas generales
# (estas reglas no aplican a los encabezados):
# - las columnas fijas se guardan en el mismo orden que COLUMNAS_BASE
# - todo debe estar en minusculas
# - sin acentos exceptuando la ñ
# - sin caracteres especiales (no signos de puntuación), y con espacios simples (no dobles) entre palabras ni al inicio ni al final
# - si no hay informacion de una columna, simplemente es un string vacio ""

# - genericos: sigue las reglas generales; solo se eliminan prefijos numericos estructurales, no los numeros que formen parte del nombre
# - ponderadores, encadenamiento: se guardan en str con todos los decimales que vienen en el xlsx, sin redondear ni truncar, tal cual viene en el XML crudo o str(cell.value) (si viene en notacion cientifica, asi se guarda, si viene con 20 decimales, asi se guarda), y con punto decimal (no coma)
# - COG, inflacion *, durabilidad: sigue las reglas generales; solo se eliminan prefijos numericos estructurales. ejemplo "01 alimentos" -> "alimentos"
# - CCIF *: sigue las reglas generales; sin eliminacion de prefijos numericos estructurales. ejemplo "01 alimentos ...", "01.1 alimentos ...", "01.1.1 alimentos ..."
#   esto aplica al resultado final (xlsx + pdf); el xlsx solo no trae el prefijo consistente
#   entre versiones (2010/2013/2018 sin prefijo, 2024 con prefijo, verificado en el archivo real),
#   asi que extraer_xlsx.py SIEMPRE lo quita -- el pdf lo repone consistente en las 4 versiones
# - SCIAN *: sigue las reglas generales; el codigo y el nombre se separan por un espacio simple
#   - SCIAN sector: inicia con un codigo de 2 digitos (por ejemplo, "31 industrias manufactureras")
#   - SCIAN rama: inicia con un codigo de exactamente 4 digitos (por ejemplo, "3111 elaboracion de alimentos para animales")
# - canasta *: son categorias binarias y se guardan como str: "X" si pertenece y "-" si no pertenece
#   - se asume que no hay datos faltantes dentro de una columna con informacion (sin validacion)
#   - canasta consumo minimo no tiene informacion antes de 2024, por lo que toda la columna contiene "" en 2010, 2013 y 2018


def guardar_csv(df: pd.DataFrame, ruta: Path, version: VersionCanasta) -> None:
    """Completa el esquema fijo de 15 columnas y escribe el CSV.

    Advierte (no lanza) si `df` trae columnas fuera de `COLUMNAS_BASE`: se
    descartan igual, sin validación dura (el esquema de columnas ya se
    sostiene por construcción en quien arma el df).
    Ver: tools/uso_generar_canasta.md §Esquema del CSV de salida.
    """
    sobrantes = set(df.columns) - set(COLUMNAS_BASE)
    if sobrantes:
        print(
            f"[canasta_inpc] Advertencia: columnas fuera de esquema descartadas: {sorted(sobrantes)}"
        )
    df = df.reindex(columns=COLUMNAS_BASE, fill_value="")
    df.to_csv(ruta, index=False)
