import re

_TRANS_TILDES = str.maketrans("áéíóúüÁÉÍÓÚÜ", "aeiouuAEIOUU")


def _normalizar(nombre: str) -> str:

    nombre = nombre.translate(_TRANS_TILDES)
    nombre = re.sub(r"[^\w\s]", "", nombre)
    nombre = nombre.strip().lower()
    return nombre
