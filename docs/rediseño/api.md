# Rediseño api/

## Alcance

- Cubre: firmas públicas de `api/`; tipos de parámetros y retorno visibles al usuario; errores que ve el usuario
- Excluye: contratos de dominio (ver `dominio.md`), adaptadores CSV (`infraestructura/`), casos de uso (`aplicacion/`)
- Fuente de verdad: este archivo para firmas de `api/`; `dominio.md` para contratos de los tipos que se devuelven

---

## Decisiones generales

- Distribución: pip + CLI. No exposición HTTP pública
- Estilo: flat, pandas-like. `import replica_inpc as rep` → `rep.<func>(...)`
- Sin clases fachada en superficie pública
- Funciones libres = API principal; `Resultado*` exponen `.pipe(fn, *args, **kwargs)` para chain estilo pandas

### Estructura de módulos

| Archivo | Tema |
| --- | --- |
| `insumos.py` | IO de inputs (canastas, series) |
| `indices.py` | cálculo y transformaciones de índices |
| `variaciones.py` | análisis de variaciones |
| `incidencias.py` | análisis de incidencias |
| `validaciones.py` | validaciones contra INEGI |
| `flujos.py` | flujos orquestados completos (modo automático) |
| `config.py` | configuración global |
| `__init__.py` | re-export plano con `__all__` curado |

### Convenciones de naming

#### Módulos

- Sustantivos en plural (excepto `config.py`)
- Describen el dominio o el tipo de objeto que gestionan

#### Funciones públicas

- `verbo_objeto`: `cargar_canasta`, `calcular_indice`, `cargar_serie`
- `objeto_modificador`: `variacion_periodica`, `incidencia_desde`
- Verbo solo para transformaciones: `empalmar`, `rebasar`, `a_mensual`
- `validar_*` + qué se valida
- Español obligatorio
- Prohibido: `obtener_*`, `crear_*`, `procesar_*`, inglés, sufijo `_csv` en pública

### Manejo de periodos

- Funciones públicas aceptan `str` en parámetros de periodo — sin `Periodo*` en la superficie pública.
- `api/` convierte con `periodo_desde_str` antes de pasar a dominio; detección de formato interna.
- Dominio recibe solo objetos `Periodo*` — nunca strings.
- Formatos válidos (insensible a mayúsculas):

| formato | ejemplo | tipo resultante |
|---|---|---|
| `"NQ Mmm AAAA"` | `"1Q ene 2015"`, `"2Q JUL 2018"` | `PeriodoQuincenal` |
| `"Mmm AAAA"` | `"ene 2015"`, `"DIC 2024"` | `PeriodoMensual` |

---

## Módulo por módulo

### config.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `set_token(token)` — establece token INEGI en memoria
- `limpiar_cache()` — limpia cache de `FuenteValidacionApi` (útil en notebooks de larga duración)

Variables configurables:

- `tolerancia_validacion` — umbral de diferencia aceptable en validación (default: `0.001` INPC, `0.009` pp incidencias)
- `timeout_api` — timeout en segundos para llamadas a INEGI (default: `10`)

Notas:

- Token: híbrido — `get_token()` (interno) busca `INEGI_TOKEN` en env var primero, luego valor seteado con `set_token`. Lanza `ErrorConfiguracion` si ninguno está presente.

#### Ejemplos — notebook — config.py

```python
import replica_inpc as rep

rep.set_token("mi-token-inegi")
rep.tolerancia_validacion = 0.005  # opcional
```

#### Ejemplos — CLI — config.py

```bash
export INEGI_TOKEN="mi-token-inegi"
replica-inpc validar --indice resultado.csv
```

### insumos.py — RESUELTO (firmas completas)

#### cargar_canasta — RESUELTO

##### Firma

```python
def cargar_canasta(
    ruta: str,
    version: Literal[2010, 2013, 2018, 2024],
) -> CanastaCanonica:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `ruta` | `str` | ruta al CSV; relativa o absoluta |
| `version` | `Literal[2010, 2013, 2018, 2024]` | versión de la canasta; explícita siempre — no auto-detect |

##### Retorno

| tipo | contrato |
|---|---|
| `CanastaCanonica` | índice = `generico`; columnas `ponderador` y `encadenamiento` como `str` |

##### Errores

| condición | error |
|---|---|
| `ruta` no existe | `ArchivoNoEncontrado` |
| archivo existe pero vacío | `ArchivoVacio` |
| CSV no parseable | `ArchivoCorrupto` |
| columnas requeridas ausentes | `ColumnasMinFaltantes` |
| `version` fuera de `[2010, 2013, 2018, 2024]` | `InvarianteViolado` |

##### Notas

- versión siempre explícita — canastas 2010 y 2013 tienen genéricos idénticos; auto-detect arriesga cálculo silenciosamente erróneo

##### Ejemplo

```python
canasta = rep.cargar_canasta("data/canasta_2018.csv", version=2018)
```

#### cargar_serie — RESUELTO

##### Firma

```python
def cargar_serie(
    ruta: str,
    version: Literal[2010, 2013, 2018, 2024],
) -> SerieNormalizada:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `ruta` | `str` | ruta al CSV; relativa o absoluta |
| `version` | `Literal[2010, 2013, 2018, 2024]` | versión de la canasta correspondiente |

##### Retorno

| tipo | contrato |
|---|---|
| `SerieNormalizada` | índice = `generico_limpio`; columnas = `PeriodoQuincenal` |

##### Errores

| condición | error |
|---|---|
| `ruta` no existe | `ArchivoNoEncontrado` |
| archivo existe pero vacío | `ArchivoVacio` |
| CSV no parseable | `ArchivoCorrupto` |
| orientación de columnas no detectable | `OrientacionNoDetectable` |
| ninguna fila útil tras normalización | `SerieVacia` |
| `version` fuera de `[2010, 2013, 2018, 2024]` | `InvarianteViolado` |

##### Notas

- siempre quincenal — datos mensuales se obtienen vía `a_mensual(resultado)`, nunca cargando CSV mensuales
- soporta formato BIE jerárquico (2010/2013) y formato estándar (2018/2024)

##### Ejemplo

```python
serie = rep.cargar_serie("data/serie_2018.csv", version=2018)
```

#### Funciones diferidas

- `normalizar_ponderadores(canasta)` — asegura que ponderadores sumen 100; diferida por baja prioridad en v2

### indices.py — RESUELTO (firmas completas)

#### calcular_indice — RESUELTO

##### Firma

```python
def calcular_indice(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    referencia: ResultadoIndice | None = None,
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `canasta` | `CanastaCanonica` | canasta ya cargada; versión determinada por el objeto |
| `serie` | `SerieNormalizada` | serie ya cargada; debe corresponder a la misma versión que `canasta` |
| `referencia` | `ResultadoIndice \| None` | resultado del tramo anterior; requerido para versiones 2010 y 2013 (LaspeyresEncadenado); `None` para 2018 y 2024 |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | índice calculado para el tramo de la canasta; `periodo_referencia = None` |

##### Errores

| condición | error |
|---|---|
| genéricos de `canasta` sin correspondencia en `serie` | `CorrespondenciaInsuficiente` |
| `canasta` sin genéricos utilizables | `CanastaSinGenericos` |
| ponderador faltante para el cálculo | `PonderadorFaltante` |
| `referencia=None` cuando la versión requiere encadenamiento | `InvarianteViolado` |

##### Notas

- una canasta a la vez; historia completa = varias llamadas + `empalmar`
- `referencia` requerido para versiones 2010 y 2013; ignorado para 2018 y 2024

##### Ejemplo

```python
canasta = rep.cargar_canasta("canasta_2018.csv", version=2018)
serie   = rep.cargar_serie("serie_2018.csv", version=2018)
indice  = rep.calcular_indice(canasta, serie)
```

#### empalmar — RESUELTO

##### Firma

```python
def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `resultados` | `list[ResultadoIndice]` | tramos a unir; orden cronológico; al menos dos elementos |
| `forzar` | `bool` | si `True`, permite empalmar resultados con `periodo_referencia` distintos emitiendo `UserWarning` |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | resultado unificado; `manifiesto` concatenado; `reporte` y `diagnostico` mergeados |

##### Errores

| condición | error |
|---|---|
| lista vacía o con un solo elemento | `InvarianteViolado` |
| `tipo` distinto entre resultados | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=False` | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=True` | `UserWarning` |

##### Notas

- solo une tramos del mismo `tipo`; no hace rebase automático
- `None` + valor explícito → resultado hereda el valor explícito (no requiere `forzar`)

##### Ejemplo

```python
hist = rep.empalmar([indice_2010, indice_2013])
```

#### rebasar — RESUELTO

##### Firma

```python
def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: str,
    valor_referencia: float = 100.0,
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | resultado a reexpresar |
| `periodo_referencia` | `str` | periodo en el que los índices valdrán `valor_referencia`; ver §Manejo de periodos |
| `valor_referencia` | `float` | valor al que se normaliza el periodo de referencia; default `100.0` |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | mismo contenido reescalado; `.periodo_referencia` seteado al periodo indicado |

##### Errores

| condición | error |
|---|---|
| `periodo_referencia` con formato inválido | `PeriodoNoInterpretable` |
| periodo no existe en `resultado` | `InvarianteViolado` |
| índice en `periodo_referencia` es NaN (`sin_datos` o `fallida`) | `InvarianteViolado` |

##### Notas

- mecánica: `valor / valor_en_periodo_referencia × valor_referencia`
- misma función para rebase intra-canasta y cross-canasta

##### Ejemplo

```python
rebased = rep.rebasar(hist, periodo_referencia="2Q Jul 2018")
```

#### a_mensual — RESUELTO

##### Firma

```python
def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | resultado quincenal a convertir |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | resultado mensual; índice de periodos = `PeriodoMensual`; valor = promedio simple 1Q y 2Q |

##### Errores

| condición | error |
|---|---|
| `resultado` ya tiene periodos mensuales | `InvarianteViolado` |

##### Notas

- promedio simple de 1Q y 2Q; si solo hay una quincena disponible en el mes, `estado_calculo = parcial`
- único mecanismo para obtener datos mensuales — nunca cargar CSV mensuales directamente

##### Ejemplo

```python
mensual = rep.a_mensual(indice)
```

#### Funciones diferidas

- `desencadenar(resultado)` — remoción de factores de encadenamiento para recuperar Laspeyres crudo; diferida por baja prioridad en v2

### variaciones.py — RESUELTO (firmas provisionales)

Funciones públicas (series):

- `variacion_periodica(resultado, frecuencia)` — variación periodo a periodo (quincenal/mensual/anual)
- `variacion_acumulada_anual(resultado)` — acumulado ene→actual vs dic año anterior
- `variacion_desde(resultado, desde, hasta, incluir_parciales)` — variación entre dos periodos

Funciones públicas (escalares):

- `inflacion_acumulada(resultado, desde, hasta)` — acumulado entre dos periodos → float
- `inflacion_promedio(resultado, desde, hasta)` — TCAC o promedio simple → float
- `inflacion_en(resultado, periodo)` — variación puntual en un periodo (respecto al periodo anterior) → float
- `inflacion_maxima(resultado)` — → (periodo, float)
- `inflacion_minima(resultado)` — → (periodo, float)

#### Ejemplos — notebook — variaciones.py

```python
import replica_inpc as rep

# serie de variaciones mensuales
vars_mensual = rep.variacion_periodica(indice, frecuencia="mensual")

# acumulado 2015–2024
acum = rep.inflacion_acumulada(indice, desde="Ene 2015", hasta="Dic 2024")  # → float

# máximo histórico
periodo, valor = rep.inflacion_maxima(indice)
```

#### Ejemplos — CLI — variaciones.py

```bash
replica-inpc variacion --frecuencia mensual --indice resultado.csv
replica-inpc inflacion-acumulada --desde 2015-01 --hasta 2024-12 --indice resultado.csv
```

### incidencias.py — RESUELTO (firmas provisionales)

Funciones públicas (series):

- `incidencia_periodica(resultado, canastas, frecuencia)` — incidencia periodo a periodo por genérico
- `incidencia_acumulada_anual(resultado, canastas)` — acumulado ene→actual; suma de todos los genéricos = variación anual acumulada
- `incidencia_desde(resultado, canastas, desde, hasta)` — incidencia entre dos periodos
- `incidencia_en(resultado, canastas, periodo)` — incidencia de todos los genéricos en un periodo → `pd.Series`
- `incidencia_acumulada(resultado, canastas, desde, hasta)` — incidencia acumulada por genérico → `pd.Series`

Funciones públicas (escalares):

- `mayor_incidencia(resultado, canastas, periodo)` — → `(str, float)`
- `menor_incidencia(resultado, canastas, periodo)` — → `(str, float)`

Notas:

- Todas las funciones reciben `canastas: dict[int, CanastaCanonica]` como parámetro explícito — la canasta no está embebida en el resultado.
- `incidencia_acumulada_anual`: propiedad matemática — suma de incidencias de todos los genéricos = variación anual acumulada del INPC.
- `incidencia_acumulada` devuelve `pd.Series` (un escalar por genérico); distinto de `incidencia_desde` que devuelve `ResultadoIncidencia`.
- `incluir_parciales` en `incidencia_desde`: diferido.

#### Ejemplos — notebook — incidencias.py

```python
import replica_inpc as rep

# serie de incidencias mensuales
inc_mensual = rep.incidencia_periodica(indice, canastas, frecuencia="mensual")

# genérico con mayor incidencia en un periodo
generico, valor = rep.mayor_incidencia(indice, canastas, periodo="Dic 2024")

# incidencia acumulada por genérico 2015–2024
rep.incidencia_acumulada(indice, canastas, desde="Ene 2015", hasta="Dic 2024")
```

#### Ejemplos — CLI — incidencias.py

```bash
replica-inpc incidencia --frecuencia mensual --indice resultado.csv
replica-inpc mayor-incidencia --periodo 2024-12 --indice resultado.csv
```

### validaciones.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `validar_indice(resultado)` — compara `ResultadoIndice` contra series INEGI → `ValidacionIndice`
- `validar_variacion(variacion)` — compara `ResultadoVariacion` contra series INEGI → `ValidacionVariacion`
- `validar_incidencia(incidencia)` — compara `ResultadoIncidencia` contra series INEGI → `ValidacionIncidencia`

Notas:

- Cada función acepta solo tipos con series INEGI comparables: `"inpc"`, `"inflacion componente"`, `"inflacion subcomponente"`. Otros tipos → `InvarianteViolado`.
- Auto-detecta frecuencia (quincenal/mensual) por tipo de periodo en el resultado de entrada.
- Delega a `FuenteValidacionApi` para obtener series INEGI.

#### Ejemplos — notebook — validaciones.py

```python
import replica_inpc as rep

val_indice     = rep.validar_indice(indice)        # → ValidacionIndice
val_variacion  = rep.validar_variacion(variacion)  # → ValidacionVariacion
val_incidencia = rep.validar_incidencia(incidencia) # → ValidacionIncidencia
```

#### Ejemplos — CLI — validaciones.py

```bash
replica-inpc validar-indice --resultado resultado.csv
replica-inpc validar-variacion --resultado variaciones.csv
```

### flujos.py — PROVISIONAL (firmas provisionales)

Funciones públicas:

- `calcular_historia(canastas, series)` — múltiples canastas → `ResultadoIndice` completo empalmado y rebased

Funciones pendientes de decisión:

- `calcular_variacion(canastas, series, frecuencia)` — PENDIENTE: determinar si agrega valor frente a `calcular_historia` + `variacion_periodica` manual
- `calcular_incidencia(canastas, series, frecuencia)` — PENDIENTE: mismo argumento que `calcular_variacion`
- `verificar(canastas, series)` — PENDIENTE: superfunción que orquesta cálculo + validación completa; evaluar utilidad real vs complejidad

Funciones diferidas:

- `exportar(resultado, path)` — diferida; pandas ya expone `to_csv`/`to_excel`; agregar solo si se requiere formato propio o CLI específico

Notas:

- Re-exporta desde `aplicacion/casos_uso/`. La lógica de orquestación vive ahí, no en `api/`.
- `calcular_historia`: único flujo confirmado para v2.

#### Ejemplos — notebook — flujos.py

```python
import replica_inpc as rep

# historia completa de una vez
historico = rep.calcular_historia(canastas, series)
```

#### Ejemplos — CLI — flujos.py

```bash
replica-inpc calcular-historia --config historia.toml
```

---

## Decisiones

### §D1. Acoplamiento api/ → infraestructura/

PENDIENTE: ver `transiscion.md` § "Origen: `## Capa api/` → `### Acoplamiento — decisión v2`".

### §D2. Token híbrido en config.py

PENDIENTE: documentar por qué `get_token()` busca env var primero y luego valor de `set_token`, no al revés.

### §D3. Versión explícita en insumos

PENDIENTE: documentar por qué `version` es parámetro obligatorio (no auto-detect) en `cargar_canasta` y `cargar_serie`.

### §D4. Re-export de errores en `__init__.py`

Los tipos de error de `dominio/errores.py` se re-exportan a través de `api/__init__.py` y quedan disponibles como `rep.ArchivoNoEncontrado`, `rep.InvarianteViolado`, etc. El usuario no necesita importar desde rutas internas para capturar errores específicos. Consistente con el estilo flat (`import replica_inpc as rep`).
