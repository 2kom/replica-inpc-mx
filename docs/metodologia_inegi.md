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

A partir de la v1.2.0, este proyecto implementa las bases **2018** y **2024**. Las secciones siguientes describen su metodología en detalle.

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

Para los genéricos con muestreo probabilístico, el INEGI considera una estructura de estratificación por tipo de mercado (moderno o tradicional) y tamaño de unidad económica según ingresos. Según la información disponible para cada genérico y área geográfica, el índice elemental se calcula en uno de tres casos:

**Caso 1** — existen ponderaciones por tipo de mercado y por tamaño de punto de venta:

$$I_{lk} = \prod_{j=1}^{2} I_{lkj}^{\omega_{lkj}}, \qquad I_{lkj} = \prod_{i=1}^{m} I_{lkji}^{\alpha_{lkji}}$$

**Caso 2** — existen ponderaciones por tipo de mercado, pero no por tamaño de punto de venta:

$$I_{lk} = \prod_{j=1}^{2} I_{lkj}^{\omega_{lkj}}$$

**Caso 3** — no existen ponderaciones por tipo de mercado ni por tamaño: el genérico completo en el área geográfica se toma como agregado elemental y $I_{lk}$ se calcula directamente.

En los tres casos, el índice de cada estrato se calcula con la fórmula de **Jevons** (media geométrica de relativos de precios):

$$I_{elem} = \left[\prod_{e \in E} \left(\frac{p_e^t}{p_e^0}\right)\right]^{1/n} \times 100$$

Donde $p_e^t$ es el precio de la especificación $e$ en el periodo corriente, $p_e^0$ es su precio en el periodo base y $n$ es el número de especificaciones. La media geométrica es adecuada cuando los productos del agregado son relativamente homogéneos y pueden funcionar como sustitutos cercanos.

#### Genéricos no probabilísticos (51 genéricos)

Para los genéricos con muestreo no probabilístico, el índice elemental se calcula con una media geométrica no ponderada de relativos de precios:

$$I_{lk} = \left(\prod_{e=1}^{n_{lk}} r_{lke}\right)^{1/n_{lk}}$$

Donde $r_{lke}$ es el relativo de precio de la especificación $e$ del genérico $k$ en el área $l$.

Estos genéricos requieren tratamiento especial porque corresponden a tarifas reguladas, servicios con pocos oferentes o fuentes no aptas para muestreo probabilístico convencional.

### Etapa 2 — Índices superiores

Un índice superior es un índice agregado por encima del nivel elemental. En el INPC los índices superiores se calculan con la fórmula de Laspeyres, como exige el Código Fiscal de la Federación:

$$P^L_{0:t} = \sum_{i=1}^{n} \left(\frac{p_i^t}{p_i^0}\right) \omega_i^0, \qquad \omega_i^0 = \frac{p_i^0 \, q_i^0}{\sum_{i=1}^{n} p_i^0 \, q_i^0}$$

El supuesto central es que las cantidades de la canasta permanecen fijas en las del periodo base, de modo que las variaciones del índice reflejan cambios de precios y no cambios en las cantidades consumidas.

#### Índice nacional por genérico

El índice nacional del genérico $k$ se obtiene agregando los índices del genérico en las 55 áreas geográficas:

$$I_k = \sum_{l=1}^{55} \omega_{lk} \, I_{lk}, \qquad \sum_{l=1}^{55} \omega_{lk} = 1$$

Este paso convierte los índices por área geográfica en un índice nacional para cada genérico.

#### INPC nacional

El INPC nacional es la media aritmética ponderada de los índices nacionales de los 299 genéricos:

$$INPC = \sum_{k=1}^{299} \omega_k \, I_k, \qquad \sum_{k=1}^{299} \omega_k = 1$$

La variación porcentual entre dos periodos se interpreta como inflación:

$$\text{Inflación}_{a:t} = \left(\frac{INPC_t}{INPC_a} - 1\right) \times 100$$

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

Estructura idéntica a la base 2018 (Jevons, estratificación por tipo de mercado). Las diferencias son numéricas: 235 genéricos probabilísticos (vs. 248 en 2018) y 57 no probabilísticos (vs. 51 en 2018). Ver Manual INPC 2024 §9.1.

### Etapa 2 — Índices superiores (2024)

Misma fórmula Laspeyres de la base 2018, aplicada a los 292 genéricos con ponderadores ENIGH Estacional 2022. Los ponderadores fueron alineados al 2Q jul. 2024 vía precios relativos, por lo que el resultado de esta etapa tiene como referencia interna el 2Q jul. 2024 = 100 — no el 2Q jul. 2018 = 100.

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

**Ejemplo numérico (INPC agosto 2024, Manual INPC 2024, Cuadro 28):**

| Índice | $\omega$ | $f_h$ | $\theta$ | Jul 2024 | Ago 2024 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Subyacente | 0.7718 | 1.33524 | 0.74893 | 133.524 | 134.112 |
| No subyacente | 0.2282 | 1.35738 | 0.73671 | 135.738 | 135.521 |
| **INPC** | **1.0000** | **1.34065** | — | **134.065** | **134.471** |

Aplicando el procedimiento: $I_{\text{Sub},E22}^{\text{Ago}} = 0.74893 \times 134.112 = 100.440$; $I_{\text{Nosub},E22}^{\text{Ago}} = 0.73671 \times 135.521 = 99.840$; $I_{\text{INPC},E22}^{\text{Ago}} = 0.7718 \times 100.440 + 0.2282 \times 99.840 = 100.303$; $I_{\text{INPC},E}^{\text{Ago}} = 1.34065 \times 100.303 = 134.471$ ✓

#### No aditividad

El encadenamiento rompe la aditividad: después del traslape, los subíndices encadenados publicados no se reconstruyen exactamente como sumas ponderadas de sus componentes publicados. Esta propiedad es documentada por el INEGI como consecuencia esperada del método. La pérdida es evidente en el ejemplo anterior: $0.7718 \times 134.112 + 0.2282 \times 135.521 = 134.434 \neq 134.471$.

## Fuentes

El contenido de este documento está basado en los manuales metodológicos oficiales del INEGI:

- INEGI. *Índice Nacional de Precios al Consumidor. Documento metodológico. Base segunda quincena de julio de 2018.* Disponible en: <https://www.inegi.org.mx/programas/inpc/2018/>
- INEGI. *Índice Nacional de Precios al Consumidor. Base segunda quincena de julio de 2018=100. Documento metodológico.* Disponible en: <https://www.inegi.org.mx/programas/inpc/2018a/>

Los manuales de las bases 2010 y 2013 se incorporarán como referencia cuando el proyecto implemente soporte para esas versiones.

## Documentación relacionada

- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
- [`docs/metodologia_replica.md`](metodologia_replica.md) — cómo este proyecto replica el INPC a partir de los insumos públicos del INEGI.
