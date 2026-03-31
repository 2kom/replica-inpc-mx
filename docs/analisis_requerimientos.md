# Analisis de requerimientos

## 1. Objetivo

La primera version del proyecto busca **replicar el INPC general** a partir de:

- las **series publicadas por el INEGI** de los indices superiores nacionales de los genericos;
- las **canastas y ponderadores publicados por el INEGI**, previamente extraidos a CSV.

El proyecto **no** busca, en esta etapa:

- replicar el levantamiento de precios;
- replicar indices elementales;
- replicar el proceso institucional completo del INEGI;
- usar directamente los archivos crudos `.xlsx` y `.pdf` de canastas como interfaz principal de uso.

## 2. Alcance de la version 1

La `v1` debe permitir:

- importar canastas;
- importar series de genericos;
- calcular el **INPC general**;
- validar el resultado contra lo publicado por el INEGI;
- exportar resultados.

### 2.1 Alcance temporal por etapas

El desarrollo se plantea de forma incremental:

1. iniciar con la canasta `2018`;
2. despues incorporar la canasta `2024`;
3. posteriormente considerar las canastas `2010` y `2013`.

## 3. Casos de uso de la version 1

Los casos de uso acordados para la `v1` son:

1. importar una canasta en formato CSV;
2. importar una serie de genericos en formato CSV;
3. calcular el INPC general a partir de la canasta y la serie importadas;
4. validar el INPC replicado contra lo publicado por el INEGI por medio de su API;
5. exportar los resultados del calculo y la validacion.

## 4. Entradas oficiales soportadas en la version 1

### 4.1 Canastas

Las canastas se recibirán en **CSV**.

Estos CSV provienen de un proceso previo de extraccion desde los archivos oficiales del INEGI. En esta etapa:

- el `.xlsx` oficial es parte del proceso de preparacion de insumos;
- el `.pdf` del manual se usa para contraste y validacion de la extraccion;
- pero la interfaz principal del sistema en `v1` recibira **CSV de canastas**.

En `v1`, ese CSV corresponde a la **canasta_intermedia**. A partir de ella, el sistema debe construir la **canasta_canonica** antes de realizar el calculo.

### 4.2 Series de genericos

Las series se recibirán en **CSV** descargados del INEGI.

El sistema debe contemplar que estos archivos pueden venir:

- con o sin metadatos;
- en orientacion horizontal o vertical;
- con `encoding cp1252`.

La capa de importacion debe encargarse de resolver esas variantes y producir un formato interno estable.

## 5. Salida minima esperada de la version 1

La salida minima del calculo y validacion del INPC general debe incluir una tabla con:

- `periodo`
- `inpc_replicado`
- `inpc_inegi`
- `error_absoluto`
- `error_relativo`
- `estado_calculo`
- `motivo_error`

El sistema debe permitir exportar esta salida al menos en:

- `CSV`

## 6. Criterios de validez del calculo

### 6.1 Criterio general

La replicacion debe coincidir con lo publicado por el INEGI, salvo diferencias atribuibles a redondeo.

La tolerancia es configurable por version:

| Version | Tolerancia (`error_absoluto`) |
| --- | --- |
| 2018 | `<= 0.0005` |
| 2024 | `<= 0.005` |

### 6.2 Faltantes en ponderadores

Si falta el ponderador de algun generico requerido por la canasta:

- el calculo completo del indice **falla**.

Esto se considera un error estructural global.

### 6.3 Faltantes en series

Si para una fecha o periodo especifico falta el valor del indice de algun generico requerido:

- el calculo del INPC para ese periodo **falla**;
- el valor resultante para ese periodo debe quedar como `null`;
- los demas periodos pueden seguir calculandose si tienen cobertura completa.

Esto se considera un error local por periodo.

## 7. Persistencia deseada en la version 1

El objetivo de esta seccion es declarar unicamente que artefactos deben persistirse en la `v1`.

Se acordó persistir unicamente los **artefactos computados** por el pipeline:

- el **resultado del calculo** (`ResultadoCalculo`);
- los **artefactos de validacion** definidos formalmente en la seccion 11 (`ResumenValidacion`, `ReporteDetalladoValidacion`, `DiagnosticoFaltantes`).

La trazabilidad de los insumos queda cubierta por las rutas registradas en `ManifestCorrida`. No se persisten copias de los archivos fuente porque el flujo de uso esperado es local: el usuario gestiona sus propios archivos y los reemplaza cuando hay actualizaciones.

La persistencia es **opcional por corrida**. El caso de uso acepta un parametro `persistir: bool`. Cuando `persistir=False`, el pipeline corre completo en memoria y devuelve `ResultadoCorrida` sin escribir nada a disco — util para exploracion en notebooks. Cuando `persistir=True`, se escriben todos los artefactos y metadatos a disco.

## 8. Prioridades no funcionales de la version 1

Las prioridades no funcionales acordadas para la `v1` son:

1. **reproducibilidad**
2. **trazabilidad**
3. **facilidad de uso**
4. **flexibilidad**
5. **velocidad**

### 8.1 Interpretacion en este contexto

- **Reproducibilidad**: con los mismos insumos, el sistema debe producir el mismo resultado.
- **Trazabilidad**: debe ser posible identificar que archivo se uso, que pasos se aplicaron y por que un periodo fallo o quedo en `null`.
- **Facilidad de uso**: el flujo de importacion, calculo y validacion debe ser claro para el usuario.
- **Flexibilidad**: el sistema debe poder crecer despues hacia otras canastas, sin que esa necesidad domine la `v1`.
- **Velocidad**: es deseable, pero no es la prioridad principal en esta etapa.

## 9. Serie normalizada minima

La normalizacion de series, en esta etapa, se entiende como:

- limpiar el archivo descargado;
- eliminar texto y metadatos que no aportan al calculo;
- dejar la informacion en un formato estable para el sistema.

### 9.1 Metadatos que pueden venir en los archivos crudos

Cuando el archivo se descarga **con metadatos**, puede incluir:

- `titulo`
- `periodo disponible`
- `cifra`
- `unidad`
- `base`
- `aviso`
- `tipo de informacion`
- `serie`
- valores numericos de las series

Cuando se descarga **sin metadatos**, puede incluir:

- `titulo`
- `cifra`
- `serie`
- valores numericos de las series

En ambos casos, la normalizacion debe quedarse solo con lo necesario para calcular.

### 9.2 Forma conceptual del dato elemental

Sin importar si el archivo viene horizontal o vertical, el dato elemental que interesa al sistema es:

- un generico;
- un periodo;
- un valor de indice.

### 9.3 Formato normalizado minimo acordado

La `SerieNormalizada` usa formato **ancho**:

- `generico_limpio` como índice del DataFrame;
- una columna por periodo (objetos `Periodo`);
- valores `float64` o `NaN` cuando falta el índice.

El dato elemental (generico + periodo + valor) está implícito en la estructura: cada celda `[generico_limpio, Periodo]` contiene el valor de índice correspondiente.

Este formato fue elegido sobre el formato largo (columnas `generico_limpio`, `periodo`, `indice`) porque hace el cálculo Laspeyres eficiente — la agregación es una multiplicación matricial directa entre ponderadores y la matriz de índices.

`generico_original` no es una columna del DataFrame. Vive en `serie.mapeo` como `dict[str, str]` (`generico_limpio → generico_original`), disponible para trazabilidad cuando se necesita reconstruir el nombre original.

En este contexto, `generico_limpio` representa el texto util derivado de la columna `Título` del archivo de series una vez removido el contenido contextual que no aporta al calculo, conservando solo la parte necesaria para identificar el generico.

### 9.4 Alcance de `periodo`

El campo `periodo` no es un string sino un objeto `Periodo` con atributos `año`, `mes` y `quincena`. Se representa como etiqueta legible:

- `1Q Ene 2020`
- `2Q Jul 2024`

Es decir:

- `1Q` o `2Q`: primera o segunda quincena;
- mes;
- año.

El tipo propio permite sorting natural, uso como clave de diccionario y conversión a `pd.Timestamp` para graficación.

## 10. Canastas del sistema

En el sistema deben distinguirse dos artefactos relacionados con las canastas:

- `canasta_intermedia`
- `canasta_canonica`

### 10.1 Canasta intermedia

La `canasta_intermedia` es un artefacto de preparacion de insumos.

Su funcion es:

- conservar el resultado del pipeline de extraccion y rectificacion;
- servir como punto de trazabilidad entre los archivos oficiales del INEGI y la representacion final usada por el sistema;
- documentar el paso previo a la construccion de la canasta usada por el calculo.

La `canasta_intermedia`:

- se obtiene a partir de archivos oficiales, principalmente `.xlsx`;
- se contrasta y rectifica con los manuales publicados por el INEGI;
- es la entrada operativa de canasta para la `v1`;
- **no** es la entrada final del motor de calculo.

En esta etapa del analisis de requerimientos, la `canasta_intermedia` se declara como artefacto existente, pero **no** se fija formalmente su esquema como contrato estable del sistema.

### 10.2 Canasta canonica

La `canasta_canonica` es la representacion interna estable de una canasta ya lista para ser usada por el calculo.

Su objetivo es:

- dar al sistema un formato unico y predecible para trabajar;
- evitar que el motor de calculo dependa del formato de extraccion;
- separar la preparacion de insumos del calculo del indice.

La `canasta_canonica` **si** constituye un contrato del sistema.

En `v1`, la `canasta_canonica` debe construirse a partir de la `canasta_intermedia` antes de que el sistema realice el calculo.

### 10.3 Esquema de la canasta canonica

La `canasta_canonica` debe manejar un **esquema unico comun** para todas las versiones de canasta.

Cuando una columna no aplique a una version especifica, su valor debe quedar en `null`.

Para el calculo del `INPC general` en la `v1`, las columnas minimas necesarias de la `canasta_canonica` son:

- `version`
- `generico`
- `ponderador`

Las demas columnas se conservan como parte del contrato canonico del sistema, aunque no sean estrictamente necesarias para el calculo del `INPC general` en esta etapa.

Las columnas acordadas son:

- `version`
- `generico`
- `ponderador`
- `encadenamiento`
- `COG`
- `CCIF`
- `inflacion_1`
- `inflacion_2`
- `inflacion_3`
- `SCIAN_sector`
- `SCIAN_sector_numero`
- `SCIAN_rama`
- `SCIAN_rama_numero`
- `canasta_basica`
- `canasta_consumo_minimo`

### 10.4 Reglas de contenido y tipos de la canasta canonica

- `version`
  - entero
  - valores esperados: `2010`, `2013`, `2018`, `2024`

- `generico`
  - texto
  - se asume ya limpio y listo para ser usado en el sistema

- `ponderador`
  - texto decimal exacto
  - se conserva asi para respetar la precision extraida del archivo oficial

- `encadenamiento`
  - texto decimal exacto o `null`
  - se conserva asi por la misma razon que `ponderador`

- `COG`
  - texto

- `CCIF`
  - texto

- `inflacion_1`
  - texto

- `inflacion_2`
  - texto

- `inflacion_3`
  - texto

- `SCIAN_sector`
  - texto
  - debe conservar el numero y el nombre del sector en una sola columna

- `SCIAN_sector_numero`
  - texto
  - conserva solo el codigo del sector

- `SCIAN_rama`
  - texto
  - conserva el codigo y el nombre de la rama en una sola columna

- `SCIAN_rama_numero`
  - texto
  - conserva solo el codigo de la rama

- `canasta_basica`
  - booleano

- `canasta_consumo_minimo`
  - booleano o `null`

### 10.5 Criterios adicionales

- `generico_original` **no** forma parte de la canasta canonica.
- `SCIAN_sector_nombre` no se considera necesario si `SCIAN_sector` ya incluye numero y nombre.
- `SCIAN_rama_nombre` no se considera necesario si `SCIAN_rama` ya incluye codigo y nombre.
- el campo `generico` de la canasta canonica representa el mismo concepto que `generico_limpio` en la serie normalizada: un identificador textual ya depurado y listo para usarse en la correspondencia entre ambos insumos.

## 11. Validacion

La validacion del sistema debe contrastar el `INPC` replicado por el proyecto contra lo publicado por el INEGI.

Esta seccion constituye la definicion formal de los artefactos, estados y reglas de comportamiento asociados a la validacion del sistema.

En esta etapa, se acuerda que:

- la validacion se realiza usando la API del INEGI;
- la validacion es un componente distinto del calculo;
- un fallo en la obtencion de datos de validacion **no** invalida automaticamente el calculo del INPC.

### 11.1 Artefactos de validacion

Se definen tres artefactos de validacion:

- `resumen_validacion`
- `reporte_detallado_validacion`
- `diagnostico_faltantes`

### 11.2 Resumen de validacion

El `resumen_validacion` debe ser:

- compacto;
- una fila por corrida;
- util para evaluar rapidamente el resultado general de la corrida.

Las columnas acordadas son:

- `version`
- `total_periodos_esperados`
- `total_periodos_calculados`
- `total_periodos_con_null`
- `error_absoluto_max`
- `error_relativo_max`
- `total_faltantes_indice`
- `total_faltantes_ponderador`
- `estado_validacion_global`
- `estado_corrida`

### 11.3 Reporte detallado de validacion

El `reporte_detallado_validacion` debe contener una fila por periodo y servir para diagnostico fino del calculo y la comparacion.

Las columnas acordadas son:

- `periodo`
- `version`
- `inpc_replicado`
- `inpc_inegi`
- `error_absoluto`
- `error_relativo`
- `estado_calculo`
- `motivo_error`
- `estado_validacion`
- `total_genericos_esperados`
- `total_genericos_con_indice`
- `total_genericos_sin_indice`
- `cobertura_genericos_pct`
- `ponderador_total_esperado`
- `ponderador_total_cubierto`

### 11.4 Diagnostico de faltantes

El `diagnostico_faltantes` debe contener una fila por faltante detectado y permitir trazabilidad de la corrida mediante un identificador propio.

En esta etapa, `id_corrida` se entiende como un identificador de la ejecucion a la que pertenece el artefacto, sin implicar todavia la existencia de un artefacto separado de registro de corridas en la `v1`.

Las columnas acordadas son:

- `id_corrida`
- `version`
- `periodo`
- `generico`
- `nivel_faltante`
- `tipo_faltante`
- `detalle`

Reglas para su uso:

- si falta un indice:
  - `periodo` lleva el periodo afectado;
  - `nivel_faltante = periodo`;
  - `tipo_faltante = indice`.

- si falta un ponderador:
  - `periodo = null`;
  - `nivel_faltante = estructural`;
  - `tipo_faltante = ponderador`.

### 11.5 Estados del sistema asociados a validacion

#### Estado de calculo

Los valores acordados para `estado_calculo` son:

- `ok`
- `null_por_faltantes`
- `fallida`

#### Estado de validacion

Los valores acordados para `estado_validacion` son:

- `ok`
- `diferencia_detectada`
- `no_disponible`

#### Estado de validacion global

El campo `estado_validacion_global` representa el resultado global de la validacion contra lo publicado por el INEGI a nivel corrida.

Los valores acordados para `estado_validacion_global` son:

- `ok`
- `diferencia_detectada`
- `no_disponible`

Su interpretacion es la siguiente:

- `ok`
  - cuando la validacion contra el INEGI estuvo disponible y no se detectaron diferencias.

- `diferencia_detectada`
  - cuando la validacion contra el INEGI estuvo disponible y se detectaron diferencias.

- `no_disponible`
  - cuando no fue posible obtener los datos de validacion desde la API del INEGI.

#### Estado de corrida

Los valores acordados para `estado_corrida` son:

- `ok`
- `parcial`
- `fallida`

Su interpretacion es la siguiente:

- `ok`
  - cuando la corrida produce resultados completos y utilizables, sin faltantes estructurales ni periodos en `null`.

- `parcial`
  - cuando la corrida produce resultados utilizables, pero con periodos en `null`, o con validacion no disponible, o con diferencias detectadas.

- `fallida`
  - cuando la corrida no puede producir un resultado utilizable, por ejemplo por faltantes estructurales o por errores generales de importacion o preparacion de insumos.

### 11.6 Falla de la API del INEGI

Si la obtencion de datos de validacion desde la API del INEGI falla:

- la corrida **continua**;
- el calculo del INPC **si se entrega**;
- la validacion se considera **no disponible**.

En ese caso, el sistema debe producir:

- `inpc_inegi = null`
- `error_absoluto = null`
- `error_relativo = null`
- `estado_validacion = no_disponible`

## 12. Manejo general de errores

Ademas de las reglas de faltantes en ponderadores y series ya definidas en la seccion de validez del calculo, la `v1` debe contemplar errores generales de importacion y preparacion de insumos.

En todos los casos listados a continuacion, la corrida debe **fallar inmediatamente**.

### 12.1 Archivo no encontrado

Si el archivo de series o el archivo de canasta no existe:

- la corrida falla inmediatamente.

### 12.2 Archivo vacio

Si el archivo existe pero no contiene datos utiles:

- la corrida falla inmediatamente.

### 12.3 Archivo corrupto o mal formado

Si el archivo no puede ser interpretado como un CSV estructuralmente valido para el sistema:

- la corrida falla inmediatamente.

Para `v1` no se acuerdan recuperaciones parciales sobre archivos dudosos mas alla del comportamiento normal esperado por el lector.

### 12.4 Encoding no legible

Para los archivos de series del INEGI, el sistema debe:

1. intentar lectura con `cp1252`;
2. intentar un fallback controlado como `latin-1`.

Si aun asi no se puede leer el archivo:

- la corrida falla inmediatamente.

### 12.5 Orientacion no detectable

Si el sistema no puede determinar si el archivo de series esta en formato horizontal o vertical:

- la corrida falla inmediatamente.

### 12.6 Columnas minimas faltantes

Si faltan columnas minimas requeridas por el proceso:

- la corrida falla inmediatamente.

En el caso de las series, una de las columnas esperadas en el archivo crudo es literalmente:

- `Título`

### 12.7 Canasta no soportada

Si se solicita una version de canasta fuera del conjunto soportado por el sistema:

- la corrida falla inmediatamente.

En esta etapa, las versiones previstas por el sistema son:

- `2010`
- `2013`
- `2018`
- `2024`

No obstante, no todas forman parte del alcance operativo de la `v1`. Ese alcance se define en las secciones `2` y `13`.

### 12.8 Periodo no interpretable

Si el sistema detecta una etiqueta temporal que no puede interpretar como un periodo valido del tipo esperado:

- la corrida falla inmediatamente.

### 12.9 Correspondencia insuficiente entre serie y canasta

Antes del calculo, el sistema debe poder establecer una correspondencia valida entre:

- los genericos de la serie;
- y los genericos de la canasta.

Si esa correspondencia no produce una base minima valida para calcular el INPC:

- la corrida falla inmediatamente.

En esta etapa del analisis de requerimientos, esta regla se expresa como una necesidad de correspondencia valida entre ambos insumos, sin fijar todavia el mecanismo tecnico especifico que se usara para implementarla.

## 13. Exclusiones explicitas de la version 1

Con el fin de fijar expectativas y evitar ambiguedades, se establece explicitamente que la `v1` **no** incluye todavia los siguientes alcances:

### 13.1 Subindices

La `v1` no incluye:

- calculo de subindices;
- calculo de clasificaciones agregadas por encima del INPC general.

### 13.2 Incidencias y variaciones

La `v1` no incluye:

- incidencias;
- variaciones.

### 13.3 Operacion sobre canastas 2010 y 2013

Aunque las canastas `2010` y `2013` se contemplan como parte del horizonte futuro del proyecto:

- la `v1` no incluye operacion completa sobre esas canastas.

El alcance operativo inicial de la `v1` se concentra en:

- `2018`

y posteriormente se extendera a:

- `2024`

### 13.4 Uso directo de archivos oficiales `.xlsx` y `.pdf`

La `v1` no incluye el uso directo de:

- archivos `.xlsx`;
- archivos `.pdf`;

como entradas operativas principales del sistema.

Esos archivos siguen siendo fuentes oficiales de informacion, pero en esta etapa pertenecen al proceso de preparacion de insumos previo al uso principal del sistema.
