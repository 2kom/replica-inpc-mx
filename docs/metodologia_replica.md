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

El proyecto usa Laspeyres encadenado para canastas con columna
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
resultado de la versión 2018 que el usuario pasa como referencia al calcular 2024:

```python
import replica_inpc as rep

i2018 = rep.calcular_indice(c2018, s2018, tipo="inpc")
i2024 = rep.calcular_indice(c2024, s2024, tipo="inpc", referencia=i2018)
```

Sin `referencia`, el proyecto usa como fallback $f_h = \sum_k w_k f_k / \sum_k w_k$ (media ponderada de los factores individuales con ponderadores 2024). Este fallback introduce un error sistemático de ~0.72 puntos de índice porque los ponderadores 2018 y 2024 difieren.

**No aditividad:** los subíndices encadenados calculados por el proyecto no son aditivos al INPC encadenado después del traslape. Cada índice superior se encadena de forma independiente, igual que en la metodología oficial.

**Serie histórica continua:** para obtener una serie continua que abarque los
tramos 2010, 2013, 2018 y 2024, el modo automático orquesta carga, cálculo,
empalme, conversión y rebase en una sola llamada:

```python
import replica_inpc as rep

insumos = [
    (2010, "data/ponderadores_2010.csv", "data/series_2010.csv"),
    (2013, "data/ponderadores_2013.csv", "data/series_2013.csv"),
    (2018, "data/ponderadores_2018.csv", "data/series_2018.csv"),
    (2024, "data/ponderadores_2024.csv", "data/series_2024.csv"),
]
inpc = rep.calcular_historia(insumos, tipo="inpc")
```

Internamente, el proyecto combina 2010+2013, rebasa ese bloque de forma endógena
a `2Q Jul 2018 = 100` usando su propio valor replicado en ese periodo, y después
empalma con 2018+2024.

Para empalmar manualmente tramos individuales ya calculados:

```python
import replica_inpc as rep

hist   = rep.empalmar([i2018, i2024])
hist_m = rep.a_mensual(hist)
inpc   = rep.rebasar(hist_m, "Jul 2018")
```

`empalmar` excluye del tramo anterior los periodos ya cubiertos por el posterior. Para clasificadores con cambios de nombre entre canastas, normaliza automáticamente los renombres 1:1 entre versiones de canasta. Las categorías nuevas, eliminadas, splits o fusiones aparecen solo en los periodos donde existen.

## Cálculo de variaciones

Con un resultado de índice disponible, el proyecto ofrece tres funciones para calcular variaciones:

$$\text{variación}_{a:t} = \left(\frac{I_t}{I_a} - 1\right) \times 100$$

El resultado se expresa en puntos porcentuales.

### variacion_periodica

Calcula la variación de cada índice respecto a un lag fijo de quincenas:

```python
import replica_inpc as rep

rv_m = rep.variacion_periodica(inpc, frecuencia="mensual")   # lag = 2 quincenas
rv_a = rep.variacion_periodica(inpc, frecuencia="anual")     # lag = 24 quincenas
```

Frecuencias soportadas: `quincenal` (1), `mensual` (2), `bimestral` (4), `trimestral` (6), `cuatrimestral` (8), `semestral` (12), `anual` (24).

**Regla drop/keep:** si el índice base $I_a$ es NaN (quincena sin dato), la variación no puede calcularse y la fila se elimina. Si el índice corriente $I_t$ es NaN pero existe su base, la fila se conserva con variación NaN — para no ocultar periodos sin dato.

### variacion_desde

Calcula la variación acumulada desde un periodo base hasta cada quincena del rango:

```python
rv = rep.variacion_desde(inpc, desde="1Q Ene 2024")
rv = rep.variacion_desde(inpc, desde="1Q Ene 2024", hasta="2Q Jun 2024")
```

La base es la quincena **inmediatamente anterior** a `desde`. Para un índice con dato en esa quincena base, la variación en `desde` refleja el cambio respecto al cierre del periodo anterior.

Para índices que no tienen dato en la quincena base (índices parciales), el parámetro `incluir_parciales=True` los incluye usando como base su primer dato disponible dentro del rango, con variación 0 en ese primer periodo.

### variacion_acumulada_anual

Calcula la variación de cada quincena respecto a la 2Q diciembre del año anterior:

```python
rv = rep.variacion_acumulada_anual(inpc)
```

Equivale a `variacion_desde` con `desde = "1Q Ene <año>"` pero usando como base fija `2Q Dic <año-1>` para todas las quincenas del año. Los periodos del primer año disponible se eliminan porque no existe su base anual.

### Advertencia para resultados encadenados (canasta 2024)

Por la no aditividad del encadenamiento, la variación del INPC general encadenado no coincide con la suma ponderada de las variaciones de sus subíndices. Calcular variaciones directamente sobre el resultado de índice (o sobre el resultado empalmado) produce el valor correcto. No reconstruir el INPC desde componentes para luego calcular variación.

## Validación

La validación contrasta los valores replicados contra los publicados por el INEGI vía su API. Se calcula el error absoluto por periodo. Las tolerancias vigentes son ≤ 0.0009 para índices y ≤ 0.009 pp para variaciones e incidencias.

El estado de validación por fila puede ser:

- `ok`: diferencia dentro de tolerancia.
- `diferencia_detectada`: diferencia fuera de tolerancia.
- `diferencia_por_parcial`: diferencia asociada a un periodo con solo 1 quincena disponible.
- `fuera_rango_inegi`: periodo fuera del rango publicado por INEGI.
- `sin_calculo`: periodo sin resultado replicado comparable.
- `no_disponible`: INEGI no tiene dato para ese periodo.

La validación es opcional: sin token de la API del INEGI el cálculo corre igual. El resultado incluye el valor publicado, el error absoluto y el estado de validación para cada periodo.

## Limitaciones

Este proyecto no replica:

- **La Etapa 1 del INEGI**: el cálculo de índices elementales desde cotizaciones individuales. Los índices por genérico se toman directamente de las series publicadas.
- **Los índices por área geográfica**: el proyecto trabaja con los índices nacionales por genérico, no con los índices desagregados por ciudad o región.
- **El tratamiento de faltantes del INEGI**: cuando el INEGI detecta un precio faltante aplica procedimientos de imputación propios. Este proyecto aplica imputación bfill/ffill y marca el periodo con estado `rellenado` o `sin_datos` según la disponibilidad de datos.

## Documentación relacionada

- [`docs/metodologia_inegi.md`](metodologia_inegi.md) — metodología oficial de cálculo del INPC según el INEGI.
- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
