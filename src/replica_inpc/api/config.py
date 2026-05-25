"""Configuración global de la API: token INEGI, tolerancias y timeout.

Las tres variables configurables (`tolerancia_indice`, `tolerancia_derivados`,
`timeout_api`) son la fuente de verdad; `replica_inpc/__init__.py` instala un
proxy de módulo para que `rep.tolerancia_indice = X` las actualice aquí.
"""

from __future__ import annotations

import os

from replica_inpc.dominio.errores import ErrorConfiguracion
from replica_inpc.infraestructura.inegi.fuente_validacion_api import FuenteValidacionApi

_token: str | None = None

# Variables configurables — ver api.md §config.py.
tolerancia_indice: float = 0.0009
tolerancia_derivados: float = 0.009
timeout_api: int = 10


def set_token(token: str) -> None:
    """Almacena el token INEGI para la sesión actual.

    La validez del token se verifica al llamar `validar_*`, no aquí.
    """
    global _token
    _token = token


def get_token() -> str:
    """Devuelve el token INEGI configurado (uso interno).

    Busca primero la variable de entorno `INEGI_TOKEN` y, si no existe, el
    valor fijado con `set_token` — ver api.md §D2.

    Raises:
        ErrorConfiguracion: Si no hay token por ninguna de las dos vías.
    """
    token = os.environ.get("INEGI_TOKEN") or _token
    if not token:
        raise ErrorConfiguracion(
            "No hay token INEGI configurado. Usa rep.set_token('...') o exporta "
            "la variable de entorno INEGI_TOKEN."
        )
    return token


def reset_config() -> None:
    """Restaura tolerancias y timeout a sus valores por defecto."""
    global tolerancia_indice, tolerancia_derivados, timeout_api
    tolerancia_indice = 0.0009
    tolerancia_derivados = 0.009
    timeout_api = 10


def mostrar_config() -> None:
    """Imprime el estado actual de la configuración en stdout."""
    import os

    if os.environ.get("INEGI_TOKEN"):
        estado_token = "configurado (INEGI_TOKEN)"
    elif _token:
        estado_token = "configurado (set_token)"
    else:
        estado_token = "no configurado"
    n = len(FuenteValidacionApi._cache)
    print(
        f"tolerancia_indice:    {tolerancia_indice}\n"
        f"tolerancia_derivados: {tolerancia_derivados}\n"
        f"timeout_api:          {timeout_api}\n"
        f"token INEGI:          {estado_token}\n"
        f"cache:                {n} indicador{'es' if n != 1 else ''}"
    )


def limpiar_cache() -> None:
    """Vacía el cache de respuestas INEGI.

    La siguiente llamada a `validar_*` vuelve a consultar la API.
    """
    FuenteValidacionApi._cache.clear()
