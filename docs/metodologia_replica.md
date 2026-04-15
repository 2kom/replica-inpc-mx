# Cómo este proyecto replica el INPC

Este documento describe cómo el proyecto replica el Índice Nacional de Precios al Consumidor (INPC) a partir de los insumos públicos del INEGI.

Para la metodología oficial del INEGI, ver [`docs/metodologia_inegi.md`](metodologia_inegi.md).
Para contexto general sobre el INPC, ver [`docs/contexto_inpc.md`](contexto_inpc.md).

## Punto de entrada

La metodología del INEGI calcula el INPC en dos etapas:

1. **Índices elementales**: a partir de cotizaciones individuales de especificaciones en puntos de venta.
2. **Índices superiores**: agregación de índices elementales con ponderadores de gasto mediante Laspeyres.

Este proyecto **no replica la Etapa 1**. El INEGI publica directamente los resultados de esa etapa como series de índices nacionales por genérico. Esas series son el insumo de este proyecto; el cálculo propio comienza en la Etapa 2.

## Insumos

El proyecto requiere dos archivos CSV:

- **Series de genéricos**: índices nacionales por genérico publicados por el INEGI, en formato quincenal. Cada columna es un periodo; cada fila es un genérico. Ver [guias/obtener_series.md](../guias/obtener_series.md) para obtenerlos.
- **Canasta con ponderadores**: tabla de genéricos con sus ponderadores y clasificaciones. Ver [guias/obtener_ponderadores.md](../guias/obtener_ponderadores.md) para generarla.

## Correspondencia genérico↔serie

Los nombres de los genéricos en la canasta y en las series provienen de fuentes distintas y pueden tener diferencias tipográficas (tildes, espacios, mayúsculas). El proyecto normaliza ambos conjuntos antes de emparejarlos: elimina tildes, convierte a minúsculas y colapsa espacios múltiples.

Solo los genéricos que aparecen en ambas fuentes participan en el cálculo. Los genéricos sin correspondencia se reportan en el diagnóstico de faltantes.

## Cálculo del INPC general

Con los genéricos alineados, el proyecto aplica la fórmula de Laspeyres directamente sobre los índices publicados:

$$INPC_t = \frac{\displaystyle\sum_{k=1}^{N} w_k \cdot I_k^t}{100}$$

Donde:

- $I_k^t$: índice nacional del genérico $k$ en el periodo $t$, publicado por el INEGI.
- $w_k$: ponderador del genérico $k$, extraído de la canasta.
- $N$: número de genéricos con correspondencia (hasta 299 para la canasta 2018).

**Nota sobre los ponderadores**: los ponderadores de la canasta suman 100 (no 1 como en el manual del INEGI). La división entre 100 en la fórmula es el ajuste equivalente; el resultado es idéntico al Laspeyres del manual donde $\omega_k = w_k / 100$ y $\sum \omega_k = 1$.

## Cálculo de subíndices

Para calcular subíndices por clasificador (por ejemplo, inflación componente, CCIF, COG), el proyecto agrupa los genéricos según la categoría de clasificación y aplica Laspeyres a cada grupo por separado.

Dentro de cada grupo, los ponderadores se re-normalizan para que sumen 100:

$$w_k^{(h)} = \frac{w_k}{\displaystyle\sum_{j \in h} w_j} \times 100$$

Donde $h$ es el conjunto de genéricos que pertenecen a la categoría. Esto garantiza que el subíndice de cada categoría sea una media ponderada correcta de sus genéricos, independiente del peso relativo de esa categoría en el INPC general.

El resultado es un índice por categoría y periodo, con la misma escala que el INPC (base = 100 en el periodo de referencia de la canasta).

## Validación

Al terminar el cálculo, el proyecto consulta la API de indicadores del INEGI para obtener los valores oficiales publicados y los compara con los valores replicados.

Para el INPC general y los clasificadores con indicadores disponibles en la API, se calcula el error absoluto y el error relativo por periodo. La tolerancia para la canasta 2018 es `<= 0.0009` en error absoluto. El resultado global de la validación puede ser:

- `ok`: todos los periodos dentro de la tolerancia numérica.
- `ok_parcial`: algunos periodos fuera de tolerancia o sin dato oficial.
- `diferencia_detectada`: diferencias sistemáticas fuera de tolerancia.
- `no_disponible`: la API no devolvió datos (sin token o indicador no disponible).

La validación produce tres artefactos: un **resumen** con el estado global de la corrida, un **reporte detallado** con los valores por periodo y un **diagnóstico de faltantes** con los genéricos sin correspondencia o sin dato.

El pipeline puede correr completamente en memoria (`persistir=False`, útil para exploración en notebooks) o escribir todos los artefactos a disco (`persistir=True`). La validación es opcional: sin token de la API del INEGI el cálculo corre igual y el estado de validación queda como `no_disponible`.

## Limitaciones

Este proyecto no replica:

- **La Etapa 1 del INEGI**: el cálculo de índices elementales desde cotizaciones individuales. Los índices por genérico se toman directamente de las series publicadas.
- **Los índices por área geográfica**: el proyecto trabaja con los índices nacionales por genérico, no con los índices desagregados por ciudad o región.
- **El tratamiento de faltantes del INEGI**: cuando el INEGI detecta un precio faltante aplica procedimientos de imputación propios. Este proyecto marca el periodo como `null_por_faltantes` si algún genérico no tiene dato.
- **Índices encadenados**: el cálculo encadenado para las canastas 2013 y 2024 no está implementado en la versión actual.

## Documentación relacionada

- [`docs/metodologia_inegi.md`](metodologia_inegi.md) — metodología oficial de cálculo del INPC según el INEGI.
- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
