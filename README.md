# replica-inpc-mx

[![CI](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml)

Replicacion independiente del INPC general de Mexico a partir de insumos publicos del INEGI.

## Aviso importante

Este proyecto es una implementacion independiente y **no es un producto oficial del INEGI**.
No esta avalado, patrocinado ni apoyado por el INEGI.
Para efectos oficiales, fiscales, legales o contractuales, deben consultarse siempre las publicaciones oficiales del INEGI.

## Objetivo

El objetivo del proyecto es replicar el **INPC general** usando:

- indices superiores nacionales de genericos publicados por el INEGI;
- canastas y ponderadores publicados por el INEGI.

## Contexto

El INPC es el índice oficial de inflación de México, elaborado por el INEGI con base en los precios de una canasta representativa del consumo de los hogares. Se publica quincenalmente y tiene usos que van desde la política monetaria hasta la actualización de contratos privados.

Este proyecto replica el INPC a partir de los índices de genéricos y los ponderadores que el INEGI publica, sin acceso a los datos de campo. El objetivo es verificar de forma independiente y reproducible el índice publicado.

Para profundizar:

- [docs/contexto_inpc.md](docs/contexto_inpc.md) — qué es el INPC, usos y conceptos clave.
- [docs/metodologia_inegi.md](docs/metodologia_inegi.md) — metodología oficial de cálculo según el INEGI.
- [docs/metodologia_replica.md](docs/metodologia_replica.md) — cómo este proyecto replica el INPC.

## Alcance actual (v1.1.1)

La v1.1.1 del proyecto permite:

- importar canastas y series de genericos en formato CSV;
- calcular el INPC general mediante Laspeyres directo (canasta 2018);
- calcular subindices por clasificador (COG, CCIF, inflacion componente, inflacion subcomponente, durabilidad, entre otros);
- validar el resultado contra lo publicado por el INEGI via su API de indicadores;
- exportar resultados de calculo y validacion;
- ejecutar un demo completo con datos sinteticos (ver `demo/`).

El proyecto **no** incluye todavia:

- incidencias ni variaciones;
- calculo encadenado (canastas 2013 y 2024);
- soporte operativo para canastas 2010 y 2013.

## Politica de insumos

Este repositorio **no distribuye**:

- archivos oficiales del INEGI;
- datos publicados por el INEGI;
- transformaciones o derivados de esos datos como parte del repositorio.

El usuario debe obtener los insumos directamente desde las fuentes oficiales del INEGI.

## Fuentes oficiales

- INEGI - INPC: <https://www.inegi.org.mx/programas/inpc/>
- INEGI - API de indicadores: <https://www.inegi.org.mx/servicios/api_indicadores.html>

## Uso esperado

### 1. Obtener insumos

- Series de genéricos: ver [guias/obtener_series.md](guias/obtener_series.md).
- Ponderadores (xlsx y PDF) y generar canasta: ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md).

### 2.1 Instalar dependencias

```bash
pip install -e '.[dependencies]'
```

### 2.2 Ejecutar desde el notebook

Abrir `notebook.ipynb` y ajustar las variables de configuración:

```python
# Token del INEGI — opcional.
# Sin token el cálculo corre igual, pero la validación queda como no_disponible.
# Registro en: https://www.inegi.org.mx/app/api/denue/v1/tokenVerify.aspx
TOKEN_INEGI = None
# TOKEN_INEGI = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

CANASTA = "data/inputs/canastas/ponderadores_2018.csv"
SERIES  = "data/inputs/series/series_2018.csv"
VERSION = 2018
```

Ejecutar:

```python
from replica_inpc.api.corrida import Corrida

corrida = Corrida(token_inegi=TOKEN_INEGI)

# INPC general
resultado = corrida.ejecutar(
    canasta=CANASTA,
    series=SERIES,
    version=VERSION,
    tipo="inpc",
    persistir=False,
)

# Subindices por clasificador (ejemplo: inflacion componente)
resultado = corrida.ejecutar(
    canasta=CANASTA,
    series=SERIES,
    version=VERSION,
    tipo="inflacion componente",
    persistir=False,
)
```

El resultado incluye:

- `resultado.resumen` — estado general de la corrida
- `resultado.reporte.como_tabla()` — INPC replicado vs INEGI por periodo
- `resultado.resultado.como_tabla()` — índices calculados
- `resultado.diagnostico` — faltantes detectados

Para detalles de arquitectura y contratos, ver `docs/diseño.md`.

## Herramienta de canastas

El repositorio incluye `tools/generar_canasta.py`, una herramienta para generar los archivos CSV intermedios de canasta a partir de los insumos oficiales del INEGI (xlsx y PDF).

Para obtener el xlsx y el PDF necesarios, ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md).

Ver [tools/uso_generar_canasta.md](tools/uso_generar_canasta.md) para instrucciones de uso del script.

## Licencia

El codigo de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
