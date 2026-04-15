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

Este proyecto implementa actualmente la base **2018**. Las secciones siguientes describen su metodología en detalle.

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

## Fuentes

El contenido de este documento está basado en el manual metodológico oficial del INEGI:

- INEGI. *Índice Nacional de Precios al Consumidor. Documento metodológico. Base segunda quincena de julio de 2018.* Disponible en: <https://www.inegi.org.mx/programas/inpc/2018/>

Los manuales de las bases 2010, 2013 y 2024 se incorporarán como referencia cuando el proyecto implemente soporte para esas versiones.

## Documentación relacionada

- [`docs/contexto_inpc.md`](contexto_inpc.md) — qué es el INPC, sus usos y conceptos clave.
- [`docs/metodologia_replica.md`](metodologia_replica.md) — cómo este proyecto replica el INPC a partir de los insumos públicos del INEGI.
