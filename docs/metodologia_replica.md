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

## Correspondencia genérico <-> serie

Los nombres de los genéricos en la canasta y en las series provienen de fuentes distintas y pueden tener diferencias tipográficas (tildes, espacios, mayúsculas). El proyecto normaliza ambos conjuntos antes de emparejarlos: elimina tildes, convierte a minúsculas y colapsa espacios múltiples.

Solo los genéricos que aparecen en ambas fuentes participan en el cálculo. Los genéricos sin correspondencia se reportan en el diagnóstico de faltantes.

## Cálculo del INPC general con canastas directas

Con los genéricos alineados, el proyecto aplica la fórmula de Laspeyres directamente sobre los índices publicados:

$$INPC_t = \frac{\displaystyle\sum_{k=1}^{N} w_k \cdot I_k^t}{100}$$

Donde:

- $I_k^t$: índice nacional del genérico $k$ en el periodo $t$, publicado por el INEGI.
- $w_k$: ponderador del genérico $k$, extraído de la canasta.
- $N$: número de genéricos con correspondencia (hasta 299 para la canasta 2018).

**Nota sobre los ponderadores**: los ponderadores de la canasta suman 100 (no 1 como en el manual del INEGI). La división entre 100 en la fórmula es el ajuste equivalente; el resultado es idéntico al Laspeyres del manual donde $\omega_k = w_k / 100$ y $\sum \omega_k = 1$.

Este cálculo directo aplica a las canastas 2010 y 2018. La canasta 2010 opera en
la referencia original `2Q Dic 2010 = 100`.

## Cálculo de subíndices

Para calcular subíndices por clasificador (por ejemplo, inflación componente, CCIF, COG), el proyecto agrupa los genéricos según la categoría de clasificación y aplica Laspeyres a cada grupo por separado:

$$Subíndice_h^t = \frac{\displaystyle\sum_{k \in h} w_k \cdot I_k^t}{\displaystyle\sum_{k \in h} w_k}$$

Donde $h$ es el conjunto de genéricos que pertenecen a la categoría. Los ponderadores originales $w_k$ se usan directamente — **no se renormalizan**. El denominador $\sum_{k \in h} w_k$ es la suma de ponderadores del subgrupo (menor que 100), lo que produce una media ponderada correcta de los índices de ese subgrupo.

El resultado es un índice por categoría y periodo, con la misma escala que el INPC (base = 100 en el periodo de referencia de la canasta).

## Cálculo del INPC encadenado

El proyecto usa `LaspeyresEncadenado` para canastas con columna
`encadenamiento` poblada: 2013 y 2024. En ambos casos se divide cada serie por
su factor de genérico antes de agregar:

$$INPC_t = f_h \cdot \frac{\displaystyle\sum_{k=1}^{N} w_k \cdot \dfrac{I_k^t}{f_k}}{\displaystyle\sum_{k=1}^{N} w_k}$$

Donde:

- $I_k^t$: índice nacional del genérico $k$ en el periodo $t$, publicado por el INEGI.
- $f_k$: factor del genérico $k$, tomado de la columna `encadenamiento` de la canasta.
- $w_k$: ponderador del genérico $k$.
- $f_h$: factor de encadenamiento del índice superior $h$ en el traslape.

### Canasta 2013

La canasta 2013 usa las mismas series BIE que 2010, todavía en la referencia
`2Q Dic 2010 = 100`. El factor `encadenamiento` de `ponderadores_2013.csv` no se
usa para convertir a una base 100 estilo 2024; se usa como factor de alineación
por genérico:

$$I_k^{\text{alineado}}[t] = \frac{I_k^{\text{pub}}[t]}{f_k}$$

Después se aplica Laspeyres con ponderadores 2013 y se empalma contra el valor
replicado con canasta 2010 en el traslape real `2Q Mar 2013`:

$$f_h^{2013} = \frac{INPC_{2010}^{2Q\,Mar\,2013}}{INPC_{2013,\text{alineado}}^{2Q\,Mar\,2013}}$$

Esta variante fue la que reprodujo la fila oficial `Total` de la serie BIE en la
escala vieja antes del rebase.

### Canasta 2024

Para la canasta 2024, los índices de genéricos publicados están en base
`2Q Jul 2018 = 100`, pero los ponderadores 2024 corresponden al traslape
`2Q Jul 2024`. En este caso, `f_k` equivale a
$I_k^{2Q\,\text{Jul}\,2024} / 100$.

**Cómo se obtiene $f_h$:** el valor correcto es el INPC calculado con la canasta
2018 en el periodo de traslape, dividido entre 100. El proyecto lo extrae del
`resultado_referencia` que el usuario pasa al ejecutar la corrida 2024:

```python
resultado_2024 = corrida.ejecutar(
    ..., version=2024, resultado_referencia=resultado_2018.resultado
)
```

Sin `resultado_referencia`, el proyecto usa como fallback $f_h = \sum_k w_k f_k / \sum_k w_k$ (media ponderada de los factores individuales con ponderadores 2024). Este fallback introduce un error sistemático de ~0.72 puntos de índice porque los ponderadores 2018 y 2024 difieren. Ver §11.20 de `docs/diseño.md`.

**No aditividad:** los subíndices encadenados calculados por el proyecto no son aditivos al INPC encadenado después del traslape. Cada índice superior se encadena de forma independiente, igual que en la metodología oficial.

**Serie histórica continua:** para obtener una serie continua que abarque los
tramos 2010, 2013, 2018 y 2024, la fachada `Corrida` ofrece
`ejecutar_historico`:

```python
historico = corrida.ejecutar_historico(
    "data/inputs/ponderadores_2010.csv",
    "data/inputs/series2010_horizontal_metadata.CSV",
    "data/inputs/ponderadores_2013.csv",
    "data/inputs/series2010_horizontal_metadata.CSV",
    "data/inputs/ponderadores_2018.csv",
    "data/inputs/series2018_horizontal_metadata.CSV",
    "data/inputs/ponderadores_2024.csv",
    "data/inputs/series2024_horizontal_metadata.CSV",
    tipo="inpc",
)
```

Internamente, el proyecto combina 2010+2013, rebasa ese bloque de forma endógena
a `2Q Jul 2018 = 100` usando su propio valor replicado en ese periodo, y después
concatena con 2018+2024.

Para obtener una serie continua manual de los tramos 2018 y 2024:

```python
from replica_inpc import combinar
resultado_completo = combinar([resultado_2018.resultado, resultado_2024.resultado])
```

`combinar` excluye del tramo anterior los periodos ya cubiertos por el posterior. Para clasificadores con cambios de nombre entre canastas, normaliza automáticamente los renombres 1:1 definidos en `RENOMBRES_INDICES`. Las categorías nuevas, eliminadas, splits o fusiones aparecen solo en los periodos donde existen — ver `docs/diseño.md` §12.10.

## Cálculo de variaciones

Con un `ResultadoCalculo` disponible, el proyecto ofrece tres funciones para calcular variaciones:

$$\text{variación}_{a:t} = \frac{I_t}{I_a} - 1$$

El resultado se expresa como fracción (no porcentaje). Para obtener el porcentaje, multiplicar por 100.

### variacion_periodica

Calcula la variación de cada índice respecto a un lag fijo de quincenas:

```python
rv = variacion_periodica(resultado, "mensual")   # lag = 2 quincenas
rv = variacion_periodica(resultado, "anual")     # lag = 24 quincenas
```

Frecuencias soportadas: `quincenal` (1), `mensual` (2), `bimestral` (4), `trimestral` (6), `cuatrimestral` (8), `semestral` (12), `anual` (24).

**Regla drop/keep:** si el índice base $I_a$ es NaN (quincena sin dato), la variación no puede calcularse y la fila se elimina. Si el índice corriente $I_t$ es NaN pero existe su base, la fila se conserva con variación NaN — para no ocultar periodos sin dato.

### variacion_desde

Calcula la variación acumulada desde un periodo base hasta cada quincena del rango:

```python
rv = variacion_desde(resultado, "1Q Ene 2024")
rv = variacion_desde(resultado, "1Q Ene 2024", hasta="2Q Jun 2024")
```

La base es la quincena **inmediatamente anterior** a `desde`. Para un índice con dato en esa quincena base, la variación en `desde` refleja el cambio respecto al cierre del periodo anterior.

Para índices que no tienen dato en la quincena base (índices parciales), el parámetro `incluir_parciales=True` los incluye usando como base su primer dato disponible dentro del rango, con variación 0 en ese primer periodo.

### variacion_acumulada_anual

Calcula la variación de cada quincena respecto a la 2Q diciembre del año anterior:

```python
rv = variacion_acumulada_anual(resultado)
```

Equivale a `variacion_desde` con `desde = "1Q Ene <año>"` pero usando como base fija `2Q Dic <año-1>` para todas las quincenas del año. Los periodos del primer año disponible se eliminan porque no existe su base anual.

### Advertencia para resultados encadenados (canasta 2024)

Por la no aditividad del encadenamiento, la variación del INPC general encadenado no coincide con la suma ponderada de las variaciones de sus subíndices. Calcular variaciones directamente sobre el `ResultadoCalculo` de la corrida (o sobre el resultado combinado) produce el valor correcto. No reconstruir el INPC desde componentes para luego calcular variación.

## Validación

Al terminar el cálculo, el proyecto consulta la API de indicadores del INEGI para obtener los valores oficiales publicados y los compara con los valores replicados.

Para el INPC general y los clasificadores con indicadores disponibles en la API,
se calcula el error absoluto y el error relativo por periodo. La tolerancia
vigente para las canastas 2010, 2013, 2018 y 2024 es `<= 0.0009` en error
absoluto. El resultado global de la validación puede ser:

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

## Documentación relacionada

- [`docs/metodologia_inegi.md`](metodologia_inegi.md) — metodología oficial de cálculo del INPC según el INEGI.
- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
