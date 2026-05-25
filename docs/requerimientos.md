# Análisis de requerimientos — replica-inpc-mx

## 1. Objetivo

El sistema replica el INPC general a partir de:

- las **series publicadas por el INEGI** de los índices superiores nacionales de los genéricos;
- las **canastas y ponderadores publicados por el INEGI**, previamente extraídos a CSV.

El sistema no busca:

- replicar el levantamiento de precios;
- replicar índices elementales;
- replicar el proceso institucional completo del INEGI.

## 2. Alcance de v2

v2 permite:

- importar canastas de cualquier versión soportada;
- importar series de genéricos;
- calcular índices para uno o varios tramos históricos;
- combinar tramos en una serie histórica continua;
- calcular variaciones e incidencias sobre los índices;
- validar los resultados contra lo publicado por el INEGI;
- configurar tolerancias y token de sesión.

### 2.1 Historial de alcance por versión

| Versión | Alcance acumulado |
|---------|-------------------|
| v1.0.0  | INPC general (canasta 2018) + validación contra API INEGI |
| v1.0.1  | v1.0.0 + guías de descarga + herramienta de acondicionamiento de ponderadores |
| v1.1.0  | v1.0.1 + subíndices por clasificación de canasta (COG, CCIF, inflación, SCIAN, durabilidad) |
| v1.1.1  | v1.1.0 + documentación pública + demo ejecutable |
| v1.2.0  | v1.1.1 + canasta 2024 + Laspeyres encadenado + imputación de faltantes + combinación de tramos |
| v1.2.1  | v1.2.0 + tabla de renombres cross-versión |
| v1.2.2  | v1.2.1 + variaciones periódicas, acumuladas y desde período base |
| v1.2.3  | v1.2.2 + conversión a frecuencia mensual + validaciones quincenal y mensual |
| v1.2.4  | v1.2.3 + validación de variaciones quincenal y mensual + estado fuera_de_rango_inegi |
| v1.2.5  | v1.2.4 + incidencias (multi-canasta 2018+2024) + validación de incidencias mensual |
| v1.3.0  | v1.2.5 + canastas 2010 y 2013 + historia 2010-2024 + rebase endógeno |
| v2.0.0  | Rediseño completo: arquitectura hexagonal; superficie pública unificada; historia multi-canasta en una operación; validación de índices, variaciones e incidencias |

### 2.2 Lo que el sistema no hace

- Replicar el levantamiento de precios.
- Replicar índices elementales.
- Leer archivos `.xlsx` o `.pdf` como entradas operativas.
- Persistir artefactos a disco automáticamente — el sistema opera en memoria;
  el usuario puede exportar los resultados con los medios que prefiera.

## 3. Casos de uso (v2)

Los casos de uso acordados para v2 son:

1. Importar una canasta en formato CSV.
2. Importar una serie de genéricos en formato CSV.
3. Calcular el índice de precios para un tramo histórico.
4. Combinar tramos en una serie histórica continua.
5. Reexpresar resultados a una referencia de período distinta.
6. Convertir resultados quincenales a frecuencia mensual.
7. Calcular la historia completa multi-canasta en una sola operación.
8. Calcular variaciones sobre un resultado de índice.
9. Calcular incidencias sobre un resultado de índice.
10. Validar índices replicados contra lo publicado por el INEGI.
11. Validar variaciones calculadas contra lo publicado por el INEGI.
12. Validar incidencias calculadas contra lo publicado por el INEGI.
13. Configurar tolerancias de validación y token de sesión.

## 4. Entradas

### 4.1 Canastas

Las canastas se reciben en **CSV**. Versiones soportadas: 2010, 2013, 2018, 2024.

Columnas mínimas requeridas:

- `ponderador`
- `encadenamiento`
- `COG`
- `CCIF division`
- `inflacion componente`
- `inflacion subcomponente`
- `inflacion agrupacion`
- `SCIAN sector`
- `SCIAN rama`
- `canasta basica`
- `canasta consumo minimo`

Si falta alguna de estas columnas, la importación falla.

La canasta importada preserva todos los campos de clasificación presentes en el CSV fuente,
incluyendo campos adicionales de CCIF (grupo, clase) y campos derivados (durabilidad).

### 4.2 Series de genéricos

Las series se reciben en **CSV** descargados del INEGI. El sistema soporta:

- Con o sin metadatos.
- Orientación horizontal o vertical.
- Encodings: se intentan en orden utf-8, cp1252, latin-1.

La primera columna del archivo debe llamarse `Título`.

## 5. Salidas del sistema

### 5.1 Resultado de índice

El resultado del cálculo de índices incluye:

- el índice replicado por período y tipo;
- diagnóstico de calidad por período, con estado de cálculo;
- resumen agregado del estado general de la corrida;
- acceso filtrado a períodos con estado distinto al normal;
- manifiesto de trazabilidad (fuentes de entrada, versión de canasta, tipo de índice, fecha de cálculo).

Los períodos pueden ser quincenales o mensuales.

### 5.2 Resultado de variaciones

El resultado de variaciones incluye la misma estructura de diagnóstico, resumen y manifiesto
que el resultado de índice.

Tipos de variación soportados:

| Tipo | Descripción |
|------|-------------|
| Periódica quincenal | Respecto a la quincena anterior |
| Periódica mensual | Respecto al mes anterior |
| Periódica bimestral | Respecto al bimestre anterior |
| Periódica trimestral | Respecto al trimestre anterior |
| Periódica cuatrimestral | Respecto al cuatrimestre anterior |
| Periódica semestral | Respecto al semestre anterior |
| Periódica anual | Respecto al año anterior |
| Acumulada anual | Acumulada desde inicio del año calendario |
| Desde período base | Desde un período base específico indicado por el usuario |

### 5.3 Resultado de incidencias

El resultado de incidencias tiene la misma estructura que el de variaciones.

Tipos de incidencia soportados: los mismos que los de variación (ver §5.2).

## 6. Criterios de cálculo y validación

### 6.1 Tolerancias

| Tipo de resultado | Tolerancia (error absoluto) |
|---|---|
| Índices (todas las versiones) | ≤ 0.0009 |
| Variaciones e incidencias | ≤ 0.009 puntos porcentuales |

Las tolerancias son configurables en sesión. Ver §10.

### 6.2 Ponderadores inválidos o faltantes

Si la canasta tiene ponderadores faltantes, no positivos o con suma incorrecta,
la importación falla inmediatamente. Error estructural; no hay recuperación parcial.

### 6.3 Faltantes en series

Si falta el índice de algún genérico en un período, el sistema aplica imputación
hacia atrás y luego hacia adelante por fila, y marca el estado de calidad del período resultante.

**Para el resultado de índice:**

| Situación | Estado de cálculo |
|-----------|------------------|
| Todos los genéricos presentes, sin imputación | `ok` |
| Algún genérico imputado; resultado utilizable | `rellenado` |
| Solo 1 quincena disponible para el mes al convertir a mensual | `parcial` |
| Ninguna quincena disponible para el mes | `sin_datos` |
| Cálculo intentado y fallido; sin valor replicado | `fallida` |

Orden de severidad: `ok < rellenado < parcial < sin_datos < fallida`.

**Para resultados de variaciones e incidencias:**

| Situación | Estado de cálculo |
|-----------|------------------|
| Calculado con índice fuente en `ok` o `rellenado` | `ok` |
| Calculado con índice fuente en `parcial` | `parcial` |

## 7. Prioridades no funcionales

1. **Reproducibilidad** — mismos insumos producen mismo resultado.
2. **Trazabilidad** — cada resultado lleva manifiesto con fuentes, versión, tipo y fecha.
3. **Facilidad de uso** — acceso uniforme a resultados, diagnósticos y manifiesto en todos los tipos de salida.
4. **Flexibilidad** — historia multi-canasta en una sola operación; cálculo unitario o combinado.
5. **Rendimiento** — eficiencia en cálculos sobre conjuntos grandes de datos.

## 8. Períodos

El sistema usa dos tipos de período:

- **Quincenal** — formato: `1Q Ene 2020`, `2Q Jul 2024`.
- **Mensual** — formato: `Ene 2020`.

El formato es insensible a mayúsculas. Las series de entrada son siempre quincenales;
los datos mensuales se obtienen mediante conversión explícita.

## 9. Validación

La validación contrasta resultados replicados contra lo publicado por el INEGI vía su API
pública. Requiere token INEGI configurado (ver §10).

Los tipos de índice con validación disponible son: INPC general, y por componente y
subcomponente de inflación.

Si la API del INEGI no está disponible, el error se propaga al llamador — no se produce
resultado de validación. Esta condición no afecta el resultado de cálculo ya obtenido.

### 9.1 Validación de índices

Contrasta el índice replicado contra el publicado por el INEGI por período y tipo.
Produce el valor publicado, el error absoluto y el estado de validación para cada período.

### 9.2 Validación de variaciones

Solo soporta los tipos con equivalente disponible en el INEGI:

| Tipo de variación | Equivalente INEGI |
|-------------------|-------------------|
| Periódica quincenal | Periódica |
| Periódica mensual | Periódica |
| Periódica anual | Interanual |
| Acumulada anual | Acumulada anual |

Produce el valor publicado, el error absoluto y el estado de validación para cada período.

### 9.3 Validación de incidencias

Solo soporta:

| Tipo de incidencia | Equivalente INEGI |
|--------------------|-------------------|
| Periódica mensual | Periódica |

Produce el valor publicado, el error absoluto y el estado de validación para cada período.

### 9.4 Estados del sistema

#### Estado de cálculo — índices

| Valor | Significado |
|-------|-------------|
| `ok` | Calculado completo sin imputación |
| `rellenado` | Algún genérico imputado; resultado utilizable |
| `parcial` | Solo 1 quincena disponible al convertir a mensual |
| `sin_datos` | Ninguna quincena disponible al convertir a mensual |
| `fallida` | Cálculo intentado y fallido; sin valor replicado |

#### Estado de cálculo — variaciones e incidencias

| Valor | Significado |
|-------|-------------|
| `ok` | Calculado con índice fuente en `ok` o `rellenado` |
| `parcial` | Calculado con índice fuente en `parcial` |

#### Estado de validación

| Valor | Significado |
|-------|-------------|
| `ok` | Diferencia dentro de tolerancia |
| `diferencia_detectada` | Diferencia fuera de tolerancia |
| `diferencia_por_parcial` | Diferencia asociada a período `parcial` |
| `fuera_rango_inegi` | Período fuera del rango publicado por INEGI |
| `sin_calculo` | Período sin resultado replicado comparable |
| `no_disponible` | INEGI no tiene dato para ese período |

## 10. Configuración de sesión

El sistema permite configurar tres parámetros en sesión:

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Tolerancia de índice | 0.0009 | Umbral de error absoluto para validación de índices |
| Tolerancia de derivados | 0.009 | Umbral de error absoluto para variaciones e incidencias (pp) |
| Timeout de API | 10 s | Tiempo límite para llamadas a la API del INEGI |

Las tolerancias y el timeout pueden ajustarse y restaurarse a sus valores por defecto en cualquier momento.

El token de acceso a la API del INEGI puede configurarse mediante variable de entorno
o directamente en sesión. Si no está configurado al intentar validar, la operación falla.
La caché de respuestas de la API puede vaciarse explícitamente.

## 11. Manejo general de errores

Los errores de importación y cálculo interrumpen la corrida inmediatamente.

| Condición | Comportamiento |
|-----------|---------------|
| Archivo no encontrado | Falla inmediata |
| Archivo vacío | Falla inmediata |
| Archivo corrupto o mal formado | Falla inmediata |
| Encoding no decodificable (utf-8, cp1252, latin-1) | Falla inmediata |
| Orientación de serie no detectable | Falla inmediata |
| Columnas mínimas faltantes en canasta | Falla inmediata |
| Versión de canasta no soportada | Falla inmediata |
| Ponderador inválido, no positivo o suma incorrecta | Falla inmediata |
| Período no interpretable | Falla inmediata |
| Correspondencia insuficiente entre serie y canasta | Falla inmediata |
| Serie sin filas útiles para cálculo | Falla inmediata |

Los errores de validación (API no disponible o respuesta inválida) no interrumpen el
resultado de cálculo ya obtenido, pero sí impiden producir el resultado de validación.

## 12. Exclusiones permanentes

- Replicar levantamiento de precios o índices elementales.
- Leer archivos `.xlsx` o `.pdf` como entradas operativas principales.
- Calcular índices para versiones de canasta distintas a 2010, 2013, 2018 y 2024.
- Persistir artefactos a disco automáticamente.
