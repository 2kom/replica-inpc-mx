# Metodología oficial de cálculo del INPC

Este documento resume la metodología que el INEGI utiliza para calcular el Índice Nacional de Precios al Consumidor (INPC), con base en los manuales metodológicos oficiales.

Para contexto general sobre qué es el INPC, sus usos y conceptos clave, ver [`docs/contexto_inpc.md`](contexto_inpc.md).

## Visión general

El INPC se calcula en dos etapas:

1. **Índices elementales**: se calcula un índice de precios por genérico y área geográfica a partir de las cotizaciones individuales de especificaciones.
2. **Índices superiores**: los índices elementales se agregan con ponderadores de gasto mediante la fórmula de Laspeyres para obtener subíndices y el INPC nacional.

En las versiones con encadenamiento (2013 y 2024) se agrega una tercera etapa que vincula la serie nueva con la serie histórica anterior.

| | 2010 | 2013 | 2018 | 2024 |
| --- | --- | --- | --- | --- |
| Etapas | 2 | 2 + encadenamiento | 2 | 2 + encadenamiento |
| Genéricos | 283 | 283 | 299 | 292 |
| Áreas geográficas | 46 ciudades | 46 ciudades | 55 áreas | 55 áreas |
| Encadenamiento | No | Sí | No | Sí |
| Ponderadores | ENIGH 2008 | ENIGH 2010 | ENGASTO 2012-2013 / ENIGH 2014 | ENIGH Estacional 2022 |
| Base = 100 | 2a qna. dic. 2010 | 2a qna. dic. 2010 | 2a qna. jul. 2018 | 2a qna. jul. 2018 |

Este proyecto implementa las cuatro bases del INPC vigentes: **2010**, **2013**, **2018** y **2024**. Las secciones siguientes describen su metodología en detalle.

## Base 2010

### Insumos

El cálculo del INPC base 2010 combina:

- Una canasta de **283 genéricos**.
- Ponderadores derivados de la ENIGH 2008.
- Cotizaciones de precios en **46 ciudades**.

La base de comparación del índice es la **segunda quincena de diciembre de 2010**, periodo en el que el INPC se iguala a 100.

### Etapa 1 — Índices elementales

El genérico se compone de "específicos" (Figura 1 del manual: específico → genérico → subíndice → INPC). A diferencia de la base 2018 — que estratifica el cálculo elemental por tipo de mercado y tamaño de punto de venta (tres casos, según la información disponible por genérico y área) —, la base 2010 agrega los específicos de un genérico directamente con una **media geométrica no ponderada** de relativos de precios (fórmula de Jevons):

$$I_j^{b:t} = \prod_{i=1}^{n} \left(\frac{p_i^t}{p_i^b}\right)^{1/n}$$

Donde $p_i^t$ es el precio del específico $i$ en el periodo corriente, $p_i^b$ su precio en el periodo base y $n$ el número de específicos del genérico. El manual justifica la elección con el enfoque axiomático de índices de precios: la media geométrica cumple los axiomas de **reversibilidad** (intercambiar los dos periodos da el recíproco del índice original) y **transitividad** (el índice encadenado entre dos periodos debe igualar el índice directo entre los mismos periodos).

### Etapa 2 — Índices superiores

Los índices de genéricos se agregan en dos pasos — primero a subíndices, después los subíndices al INPC —, ambos con la misma fórmula: una media aritmética ponderada (Laspeyres):

$$I^{b:t} = \sum_j w_j^b \, I_j^{b:t}, \qquad \sum_j w_j^b = 1$$

Donde $w_j^b$ es el ponderador del genérico $j$ (o del subíndice, en el segundo paso), con información de gasto levantada en el periodo base $b$.

### Tratamiento de precios ante escasez y cambios de características

Dar seguimiento a una canasta fija requiere comparar, en la medida de lo posible, los mismos productos entre periodos. Dos problemas rompen esa comparación directa: la escasez temporal de un producto, y la aparición de un producto nuevo o el cambio de características de uno existente.

**Escasez temporal** — al específico no encontrado se le imputa la variación de la muestra presente del mismo genérico en la localidad ("imputación de la media global").

**Cambios de características o sustitución de producto** — el INEGI usa dos métodos, según si el cambio se puede valuar:

- **Ajuste explícito (costeo directo)**: cuando es posible valuar las características cambiantes y ajustar el precio descontando o agregando ese valor. Se aplica a los genéricos de computadoras, automóviles, servicios de educación y servicios turísticos en paquete.
- **Ajuste implícito (imputación de la media global)**: cuando no es posible valuar el cambio — se imputa al producto sustituido, solo durante el periodo de la sustitución, la variación de la media del genérico.

## Base 2013

### Insumos

El cálculo del INPC base 2013 combina:

- La misma canasta de **283 genéricos** que la base 2010.
- Ponderadores recalculados con la estructura de gasto en consumo de los hogares de **2010**, actualizados vía precios relativos a la segunda quincena de diciembre de ese mismo año.

El periodo base (segunda quincena de diciembre de 2010, donde el índice = 100) y el periodo de referencia de los ponderadores quedan fijados en la **misma quincena** — a diferencia del caso usual, donde ambos periodos difieren y las ponderaciones se actualizan vía precios relativos para alinearlos.

### Etapa 1 — Índices elementales

Misma fórmula de Jevons que la base 2010, calculada vía el relativo de corto plazo: el relativo del periodo anterior se multiplica por el cociente entre el precio promedio quincenal actual y el del periodo anterior; la media geométrica no ponderada de esos relativos en el periodo actual da el índice del genérico:

$$g = \prod_{j \in s} \left(\frac{p_j^1}{p_j^0}\right)^{1/n}$$

**Caso especial — variedades con ponderación propia.** Para dar continuidad a 18 productos que dejaron de tratarse como genéricos independientes en la canasta a partir de 2011 (cada uno con variedades que sí tienen ponderación propia dentro de él), el índice del producto se calcula como la media geométrica **ponderada** de sus variedades:

$$I_{t/0}^G = \left(I_1^{w_1} \times I_2^{w_2} \times \cdots \times I_N^{w_N}\right)^{1/w}, \qquad w = \sum_{i=1}^{N} w_i$$

### Etapa 2 — Índices superiores

Igual que en la base 2010: agregación por fórmula de tipo Laspeyres, primero de genéricos a subíndices y después de subíndices al INPC, mediante media aritmética ponderada:

$$I^{b:t} = \sum_i w_i^b \, I_i^{b:t}, \qquad \sum_i w_i^b = 1$$

Donde $w_i^b$ es el ponderador del genérico o agregado $i$, obtenido con información de gasto levantada en el periodo base $b$.

### Etapa 3 — Encadenamiento

Vincular el índice con las nuevas ponderaciones de 2010 a la serie histórica anterior requiere un **factor de encadenamiento** por cada nivel de agregación: el cociente entre el índice con los ponderadores anteriores y el índice con los ponderadores nuevos, ambos calculados en el mismo periodo de traslape (empalme). El factor se multiplica por el índice con los ponderadores nuevos, en los periodos posteriores al empalme, para darle continuidad a la serie histórica.

> "Cuando se incorporan nuevas ponderaciones, el período de referencia de los precios del nuevo índice puede ser el último período del índice anterior, con lo cual este índice y el nuevo se encadenan en este punto. Juntos, los dos índices forman un índice en cadena."

**Pasos del encadenamiento:**

i. A partir de los precios de los específicos cotizados cada quincena, se obtiene la variación de cada uno de los 283 genéricos por ciudad, con la misma metodología de Jevons de siempre.
ii. Esa variación se aplica al índice de cada genérico por ciudad — el cálculo a este nivel sigue siendo idéntico al de antes del encadenamiento. El tratamiento distinto empieza en el cálculo de los agregados de genéricos.
iii. Se calculan los índices de precios de los grupos de genéricos con los **nuevos** ponderadores y la fórmula de Laspeyres.
iv. Se obtiene el factor de encadenamiento (cociente entre los índices de la quincena de empalme con ponderadores actuales y con ponderadores nuevos) y se multiplica por los índices de transición para obtener los índices encadenados.

**Características del índice en cadena** (citadas del manual):
- Permite actualizar las ponderaciones y facilita incorporar productos y subíndices nuevos, y eliminar los obsoletos.
- Encadenar la nueva serie con la anterior requiere un periodo de superposición (empalme), en el que el índice nuevo debe calcularse con ambos conjuntos de ponderaciones.
- Los índices se encadenan para garantizar que los índices individuales, en todo nivel, manifiesten la evolución adecuada a través del tiempo.
- **Le quita a la serie su característica aditiva.** Cuando la nueva serie se encadena con la anterior, los índices de nivel superior posteriores al eslabón no se pueden obtener como las medias aritméticas ponderadas de los índices individuales utilizando las nuevas ponderaciones.

**Fórmula para replicar el índice encadenado de un agregado**, dada la pérdida de aditividad y usando los factores de encadenamiento publicados:

$$I_h = f_h \sum_{j=1}^{n} \frac{w_j \, I_j}{f_j}$$

Donde:

| Símbolo | Significado |
| --- | --- |
| $I_h$ | Índice de precios encadenado del agregado $h$ |
| $f_h$ | Factor de encadenamiento del índice de precios del agregado $h$ |
| $f_j$ | Factor de encadenamiento del índice de precios $j$, componente del agregado $h$ |
| $w_j$ | Ponderador del índice de precios $j$, componente del agregado $h$ |
| $I_j$ | Índice de precios encadenado del agregado $j$, componente del agregado $h$ |
| $n$ | Número de componentes del agregado $h$ |

### Verificación del proceso de cálculo

El INEGI valida y controla todas las etapas con herramientas sistematizadas y homogéneas que revisan la consistencia de las variaciones del periodo en estudio en todos los niveles de agregación — por producto, grupos de productos, ciudad, región, hasta el índice nacional. Además, un sistema en paralelo calcula los índices de todos los niveles de agregación y confronta los resultados entre ambos.

## Base 2018

### Insumos

El cálculo del INPC base 2018 combina:

- Una canasta de **299 genéricos**.
- Ponderadores derivados de la ENGASTO 2012-2013 y complementados con la ENIGH 2014.
- Cotizaciones de precios en **55 áreas geográficas** distribuidas en las 32 entidades federativas.
- Una muestra probabilística de puntos de venta para **248 genéricos**.
- Un esquema no probabilístico para **51 genéricos** con características especiales (tarifas reguladas, pocos oferentes, vivienda, electricidad, telefonía móvil, entre otros).

La base de comparación del índice, de los precios y de los ponderadores es la **segunda quincena de julio de 2018**, periodo en el que el INPC se iguala a 100. El INEGI alinea estos tres periodos de referencia para que el índice sea de tipo Laspeyres.

### Etapa 1 — Índices elementales

Un índice elemental es un índice de precios para un agregado elemental. En el INPC, el genérico en un área geográfica es el nivel más desagregado con ponderación propia.

#### Genéricos probabilísticos (248 genéricos)

Para los genéricos con muestreo probabilístico, el INEGI considera una estructura de estratificación por tipo de mercado ($j$: moderno o tradicional) y por tamaño de unidad económica según estrato de ingreso ($i$). Según la información disponible para cada genérico y área geográfica, el índice elemental se calcula en uno de tres casos:

**Caso 1** — existen ponderaciones por tamaño de unidad económica y por tipo de mercado:

$$I_{lk} = \prod_{j=1}^{2} I_{lkj}^{\omega_{lkj}}, \qquad \sum_{j=1}^{2} \omega_{lkj} = 1, \qquad I_{lkj} = \prod_{i=1}^{2} I_{lkji}^{\left(\text{ING}_{lkji} \big/ \sum_{i=1}^{2} \text{ING}_{lkji}\right)}$$

El exponente del segundo nivel no es un peso abstracto: es la **participación del ingreso** del estrato $i$ (dentro del genérico $k$, área $l$, tipo de mercado $j$) sobre el ingreso total de los dos estratos — $\text{ING}_{lkji}$ es el ingreso en el estrato $i$-ésimo, tipo de mercado $j$-ésimo, genérico $k$-ésimo, área geográfica $l$-ésima.

**Caso 2** — existen ponderaciones por tipo de mercado, pero no por tamaño de unidad económica:

$$I_{lk} = \prod_{j=1}^{2} I_{lkj}^{\omega_{lkj}}, \qquad \sum_{j=1}^{2} \omega_{lkj} = 1$$

**Caso 3** — no existen ponderaciones por tipo de mercado ni por tamaño de unidad económica: el genérico completo en el área geográfica se toma como agregado elemental y se pondera con la participación que tenga en el área geográfica.

Según cuál de los tres casos aplique, el índice elemental resultante es $I_{lkji}$, $I_{lkj}$ o $I_{lk}$ respectivamente. En los tres casos, ese índice elemental se calcula con la fórmula de **Jevons** (media geométrica no ponderada de relativos de precios):

$$I_{elem} = \prod_{e} \left(\frac{p_e^t}{p_e^0} \times 100\right)^{1/n}, \qquad I_{elem} \in \{I_{lkji}, I_{lkj}, I_{lk}\}$$

Donde $p_e^t$ es el precio de la especificación $e$ en el periodo corriente, $p_e^0$ es su precio en el periodo base y $n$ es el número de especificaciones del estrato.

**Por qué Jevons y no un promedio simple.** El INEGI justifica la elección por dos vías que convergen: la **axiomática** (reversibilidad y transitividad, igual que en la base 2010) y la **económica**. Bajo el enfoque económico, agregar productos homogéneos con presencia de sustitutos cercanos implica preferencias del consumidor de tipo "Cobb-Douglas"; con ellas, el Laspeyres geométrico (Jevons) da una mejor aproximación al índice teórico del costo de vida que el promedio aritmético — en la medida en que las elasticidades cruzadas de sustitución entre las especificaciones de un mismo agregado elemental se acerquen a uno.

#### Genéricos no probabilísticos (51 genéricos)

Para los genéricos con muestreo no probabilístico, el índice elemental se calcula con una media geométrica no ponderada de relativos de precios:

$$I_{lk} = \left(\prod_{e=1}^{n_{lk}} r_{lke}\right)^{1/n_{lk}}$$

Donde $r_{lke}$ es el relativo de precio de la especificación $e$ del genérico $k$ en el área $l$.

Estos genéricos requieren tratamiento especial porque corresponden a tarifas reguladas, servicios con pocos oferentes o fuentes no aptas para muestreo probabilístico convencional.

### Etapa 2 — Índices superiores

Un índice superior es un índice agregado por encima del nivel elemental. En el INPC los índices superiores se calculan con la fórmula de Laspeyres, como exige el Código Fiscal de la Federación:

$$P^L_{0:t} = \sum_{i=1}^{n} \left(\frac{p_i^t}{p_i^0}\right) \omega_i^0, \qquad \omega_i^0 = \frac{p_i^0 \, q_i^0}{\sum_{i=1}^{n} p_i^0 \, q_i^0}$$

El supuesto central es que las cantidades de la canasta permanecen fijas en las del periodo base, de modo que las variaciones del índice reflejan cambios de precios y no cambios en las cantidades consumidas. Ese supuesto implica un modelo de preferencias del consumidor de tipo **"Leontief"**: las cantidades relativas consumidas no cambian sin importar cómo se muevan los precios relativos entre sí — no hay sustitución entre genéricos, porque el modelo los trata como complementarios (elasticidades cruzadas de demanda nulas). Es el supuesto opuesto al de Jevons en la Etapa 1, donde sí se asume sustitución entre especificaciones de un mismo agregado elemental.

**Tres periodos de referencia distintos.** El INPC distingue: el **periodo de referencia de las ponderaciones** (el gasto que se usa para calcularlas), el **periodo de referencia de los precios** (el que se usa como denominador del índice) y el **periodo de referencia del índice** (donde el índice se fija en 100). Para que un índice sea del tipo Laspeyres en sentido estricto, los tres deben coincidir en el mismo periodo — en la base 2018, los tres están alineados en la 2Q de julio de ese año (ver Insumos).

#### Índice nacional por genérico

El índice nacional del genérico $k$ se obtiene agregando los índices del genérico en las 55 áreas geográficas:

$$I_k = \sum_{l=1}^{55} \omega_{lk} \, I_{lk}, \qquad \sum_{l=1}^{55} \omega_{lk} = 1$$

Este paso convierte los índices por área geográfica en un índice nacional para cada genérico.

#### INPC nacional

El INPC nacional es la media aritmética ponderada de los índices nacionales de los 299 genéricos:

$$INPC = \sum_{k=1}^{299} \omega_k \, I_k, \qquad \sum_{k=1}^{299} \omega_k = 1$$

### Variaciones e inflación (base 2018)

La variación del índice entre dos periodos se calcula como:

$$\text{Variación}_{a:t} = \left(\frac{INPC_t}{INPC_a} - 1\right) \times 100$$

Casos de uso:

- **Inflación quincenal**: `a` es la quincena inmediata anterior, `t` la quincena actual.
- **Inflación mensual**: `a` es el mes inmediato anterior, `t` el mes actual.
- **Inflación anual**: `a` es el mismo mes del año anterior, `t` el mes actual.
- **Inflación acumulada**: `a` es el periodo inicial, `t` el periodo final.

La fórmula aplica al INPC general o a cualquier índice superior (subíndice, componente, genérico), siempre que ambos valores estén en la misma base y correspondan a la misma serie.

## Base 2024

### Insumos (2024)

El cálculo del INPC base 2024 combina:

- Una canasta de **292 genéricos**.
- Ponderadores derivados de la ENIGH Estacional 2022.
- Cotizaciones en **55 áreas geográficas** (misma cobertura que 2018).
- 123,485 especificaciones (~341 mil cotizaciones mensuales).
- 235 genéricos con muestreo probabilístico y 57 con muestreo no probabilístico.

El INPC publicado **mantiene** la base segunda quincena de julio de 2018 = 100. El nuevo tramo de cálculo usa como referencia interna la **segunda quincena de julio de 2024** — el periodo de traslape entre la serie 2018 y la serie 2024.

### Etapa 1 — Índices elementales (2024)

Misma justificación económica y axiomática que la base 2018 para el uso de Jevons (Cobb-Douglas, elasticidades cruzadas cercanas a uno; ver Base 2018 § Etapa 1), y misma fórmula de agregación elemental. **La estructura de casos no es idéntica a 2018**: la base 2024 estratifica solo por tipo de mercado ($j$: moderno/tradicional) — **no** conserva el nivel adicional de estratificación por tamaño de unidad económica / estrato de ingreso que 2018 tenía en su "Caso 1". Solo hay dos casos:

**Caso uno** — existen ponderaciones por tipo de mercado:

$$I_{lk} = \prod_{j=1}^{2} I_{lkj}^{\omega_{lkj}}, \qquad \sum_{j=1}^{2} \omega_{lkj} = 1$$

**Caso dos** — no existen ponderaciones por tipo de mercado: el genérico completo en el área geográfica se toma como agregado elemental, ponderado por su participación en el área.

El índice elemental resultante es $I_{lkj}$ o $I_{lk}$ según el caso (no existe nivel $I_{lkji}$ en 2024), calculado igual que en 2018 con la fórmula de Jevons:

$$I_{elem} = \prod_{e} \left(\frac{p_e^t}{p_e^0} \times 100\right)^{1/n}, \qquad I_{elem} \in \{I_{lkj}, I_{lk}\}$$

Para los genéricos no probabilísticos, misma fórmula que 2018 — media geométrica no ponderada de relativos de precio: $I_{lk} = \prod_e \rho_{lke}^{1/n_{lk}}$.

Las diferencias numéricas frente a 2018: 235 genéricos probabilísticos (vs. 248) y 57 no probabilísticos (vs. 51).

### Etapa 2 — Índices superiores (2024)

Misma fórmula Laspeyres de la base 2018, aplicada a los 292 genéricos con ponderadores ENIGH Estacional 2022 ($I_k=\sum_{l=1}^{55}\omega_{lk}I_{lk}$, $k=1,\ldots,292$), y mismo supuesto implícito de preferencias "Leontief" (ver Base 2018 § Etapa 2). Los ponderadores fueron alineados al 2Q jul. 2024 vía precios relativos, por lo que el resultado de esta etapa tiene como referencia interna el 2Q jul. 2024 = 100 — no el 2Q jul. 2018 = 100.

### Etapa 3 — Encadenamiento (2024)

Para mantener la continuidad con la serie histórica (base 2Q jul. 2018 = 100), el INEGI encadena el resultado de la Etapa 2 con la serie anterior mediante un factor calculado en el periodo de traslape (2Q jul. 2024).

#### Factor de encadenamiento

$$f_h = \frac{I_h^{2Q\,\text{Jul}\,2024}}{100}$$

Donde $I_h^{2Q\,\text{Jul}\,2024}$ es el valor del índice $h$ en el traslape calculado con los ponderadores anteriores (ENGASTO 2012-2013 y ENIGH 2014).

#### Procedimiento para replicar a partir de series de genéricos publicadas

Los índices de genéricos publicados están en base 2Q jul. 2018 = 100. Para aplicar Laspeyres con los ponderadores nuevos, cada serie se normaliza al traslape:

i. Factor inverso por genérico: $\theta_j = \dfrac{100}{I_j^{2Q\,\text{Jul}\,2024}}$

ii. Normalizar al traslape: $I_{j,E22}^t = \theta_j \cdot I_j^t$

iii. Agregar con Laspeyres: $I_{h,E22}^t = \displaystyle\sum_j \omega_j \cdot I_{j,E22}^t$

iv. Encadenar: $I_{h,E}^t = f_h \cdot I_{h,E22}^t$

El resultado $I_{h,E}^t$ es el índice publicado con base 2Q jul. 2018 = 100.

**Características del índice encadenado** (mismas que documenta el manual 2013 para su propio encadenamiento):
- Permite actualizar las ponderaciones con mayor frecuencia y facilita incorporar productos y subíndices nuevos, y eliminar los obsoletos.
- Requiere un periodo de superposición (traslape) en el que el índice debe calcularse con ambos conjuntos de ponderaciones.
- El periodo de encadenamiento puede ser un mes o un año, con la condición de que las ponderaciones y los índices se refieran al mismo periodo.
- Le quita a la serie su característica aditiva (ver "No aditividad" abajo).

**Ejemplo numérico (INPC agosto 2024, Manual INPC 2024, Cuadro 28):**

| Índice | $\omega$ | $f_h$ | $\theta$ | Jul 2024 | Ago 2024 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Subyacente | 0.7718 | 1.33524 | 0.74893 | 133.524 | 134.112 |
| No subyacente | 0.2282 | 1.35738 | 0.73671 | 135.738 | 135.521 |
| **INPC** | **1.0000** | **1.34065** | — | **134.065** | **134.471** |

Aplicando el procedimiento: $I_{\text{Sub},E22}^{\text{Ago}} = 0.74893 \times 134.112 = 100.440$; $I_{\text{Nosub},E22}^{\text{Ago}} = 0.73671 \times 135.521 = 99.840$; $I_{\text{INPC},E22}^{\text{Ago}} = 0.7718 \times 100.440 + 0.2282 \times 99.840 = 100.303$; $I_{\text{INPC},E}^{\text{Ago}} = 1.34065 \times 100.303 = 134.471$ ✓

#### No aditividad

El encadenamiento rompe la aditividad: después del traslape, los subíndices encadenados publicados no se reconstruyen exactamente como sumas ponderadas de sus componentes publicados. Esta propiedad es documentada por el INEGI como consecuencia esperada del método. La pérdida es evidente en el ejemplo anterior: $0.7718 \times 134.112 + 0.2282 \times 135.521 = 134.434 \neq 134.471$.

### Variaciones e inflación (base 2024)

La fórmula es idéntica a la base 2018:

$$\text{Variación}_{a:t} = \left(\frac{I_t}{I_a} - 1\right) \times 100$$

Con los mismos cuatro casos de uso: quincenal, mensual, anual, acumulada.

**Restricción por no aditividad:** para periodos posteriores al traslape (2Q jul. 2024), la variación debe calcularse sobre la serie encadenada publicada del índice. No es válido reconstruir primero el INPC como suma ponderada de subíndices publicados y después calcular la variación, porque la no aditividad introduce error. Se debe usar directamente el índice general encadenado.

## Fuentes

El contenido de este documento está basado en los manuales metodológicos oficiales del INEGI disponibles en:

- INEGI. *Índice Nacional de Precios al Consumidor. Documento metodológico. Base segunda quincena de diciembre de 2010.* Disponible en: <https://www.inegi.org.mx/programas/inpc/2010/> (fuente de las bases 2010 y 2013 — 2013 reponderó sobre el mismo manual metodológico).
- INEGI. *Índice Nacional de Precios al Consumidor. Documento metodológico. Base segunda quincena de julio de 2018.* Disponible en: <https://www.inegi.org.mx/programas/inpc/2018/>
- INEGI. *Índice Nacional de Precios al Consumidor. Metodología de cálculo y procesamiento — actualización de ponderadores 2024 (base 2Q julio 2018=100, encadenada a 2Q julio 2024).* Disponible en: <https://www.inegi.org.mx/programas/inpc/2018a/>

## Documentación relacionada

- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
- [`docs/metodologia_replica.md`](metodologia_replica.md) — cómo este proyecto replica el INPC a partir de los insumos públicos del INEGI.
