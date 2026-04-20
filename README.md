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

## Alcance actual (v1.2.0)

La v1.2.0 del proyecto permite:

- importar canastas y series de genericos en formato CSV;
- calcular el INPC general mediante Laspeyres directo (canastas 2018) o encadenado (canastas 2013 y 2024);
- calcular subindices por clasificador (COG, CCIF, inflacion componente, inflacion subcomponente, durabilidad, entre otros);
- imputar periodos faltantes en series via bfill/ffill con trazabilidad completa;
- combinar resultados de distintas corridas en un unico `ResultadoCalculo` cronologico;
- validar el resultado contra lo publicado por el INEGI via su API de indicadores;
- exportar resultados de calculo y validacion;
- ejecutar un demo completo con datos sinteticos (ver `demo/`).

El proyecto **no** incluye todavia:

- incidencias ni variaciones;
- soporte operativo para canastas 2010 y 2013;
- tabla de correspondencia CCIF/SCIAN entre canastas (gap 12.10): `combinar` funciona para `inpc`,
  `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `COG`, `durabilidad` y
  `canasta basica`, pero no para clasificadores CCIF division/grupo/clase ni SCIAN sector/rama donde
  los nombres difieren entre la canasta 2018 y la 2024.

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
```

**Canasta 2018 (Laspeyres directo):**

```python
from replica_inpc.api.corrida import Corrida

corrida = Corrida(token_inegi=TOKEN_INEGI)

resultado_2018 = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2018.csv",
    series="data/inputs/series/series_2018.csv",
    version=2018,
    tipo="inpc",
    persistir=False,
)
```

**Canasta 2024 (Laspeyres encadenado):**

```python
# resultado_referencia es la corrida 2018; provee f_h exacto del INEGI para el periodo de traslape.
resultado_2024 = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2024.csv",
    series="data/inputs/series/series_2024.csv",
    version=2024,
    tipo="inpc",
    resultado_referencia=resultado_2018.resultado,
    persistir=False,
)
```

**Combinar corridas en serie temporal continua:**

```python
from replica_inpc import combinar

resultado_completo = combinar([resultado_2018.resultado, resultado_2024.resultado])
```

> **Nota:** `combinar` funciona directamente para `tipo="inpc"`, `"inflacion componente"`,
> `"inflacion subcomponente"`, `"inflacion agrupacion"`, `"COG"`, `"durabilidad"` y `"canasta basica"`.
> Para `CCIF division/grupo/clase` y `SCIAN sector/rama` los nombres de categorías difieren entre
> canastas 2018 y 2024 — el resultado combinado tendrá categorías que aparecen solo en algunos
> periodos (ver gap 12.10 en `docs/diseño.md`).

**Subindices por clasificador:**

```python
resultado = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2018.csv",
    series="data/inputs/series/series_2018.csv",
    version=2018,
    tipo="inflacion componente",
    persistir=False,
)
```

El resultado incluye:

- `resultado.resumen` — estado general de la corrida
- `resultado.reporte.como_tabla()` — INPC replicado vs INEGI por periodo
- `resultado.resultado.como_tabla()` — índices calculados
- `resultado.diagnostico` — faltantes detectados e imputados

Para detalles de arquitectura y contratos, ver `docs/diseño.md`.

## Herramienta de canastas

El repositorio incluye `tools/generar_canasta.py`, una herramienta para generar los archivos CSV intermedios de canasta a partir de los insumos oficiales del INEGI (xlsx y PDF).

Para obtener el xlsx y el PDF necesarios, ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md).

Ver [tools/uso_generar_canasta.md](tools/uso_generar_canasta.md) para instrucciones de uso del script.

## Licencia

El codigo de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
