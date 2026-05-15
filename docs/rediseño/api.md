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

### config.py — RESUELTO (firmas completas)

#### set_token — RESUELTO

##### Firma

```python
def set_token(token: str) -> None:
```

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `token` | `str` | token INEGI; almacenado en memoria para la sesión; cualquier string aceptado |

##### Retorno

`None`

##### Errores

Ninguno. La validez del token se verifica al llamar `validar_*`, no aquí.

##### Notas

- Token híbrido: `get_token()` (interno) busca `INEGI_TOKEN` en env var primero, luego valor seteado con `set_token`. Lanza `ErrorConfiguracion` si ninguno está disponible.
- CLI: usar env var `INEGI_TOKEN`; `set_token` no aplica en CLI.

##### Ejemplo

```python
rep.set_token("mi-token-inegi")
```

```bash
export INEGI_TOKEN="mi-token-inegi"
```

#### limpiar_cache — RESUELTO

##### Firma

```python
def limpiar_cache() -> None:
```

##### Retorno

`None`

##### Errores

Ninguno.

##### Notas

- Limpia el cache de respuestas INEGI (`FuenteValidacionApi._cache`). La siguiente llamada a `validar_*` vuelve a consultar la API.
- Útil en notebooks de larga duración donde los datos INEGI pueden haber cambiado.

##### Ejemplo

```python
rep.limpiar_cache()
```

#### Variables configurables — RESUELTO

| variable | tipo | default | descripción |
|---|---|---|---|
| `tolerancia_indice` | `float` | `0.0009` | diferencia absoluta máxima aceptable en validación de índices; aplica a todas las versiones |
| `tolerancia_derivados` | `float` | `0.009` | diferencia absoluta máxima aceptable en validación de variaciones e incidencias (pp) |
| `timeout_api` | `int` | `10` | timeout en segundos para llamadas a la API INEGI |

##### Ejemplo

```python
rep.tolerancia_indice = 0.001
rep.tolerancia_derivados = 0.01
rep.timeout_api = 30
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
    tipo: str,
    referencia: ResultadoIndice | None = None,
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `canasta` | `CanastaCanonica` | canasta ya cargada; versión determinada por el objeto |
| `serie` | `SerieNormalizada` | serie ya cargada; debe corresponder a la misma versión que `canasta` |
| `tipo` | `str` | tipo de índice a calcular; valores válidos en `INDICE_POR_TIPO ∪ COLUMNAS_CLASIFICACION` (ej. `"inpc"`, `"inflacion componente"`, `"durabilidad"`) |
| `referencia` | `ResultadoIndice \| None` | resultado del tramo anterior; requerido para versiones encadenadas (2013 → base 2010, 2024 → base 2018); `None` para versiones base (2010, 2018); ver §`VersionCanasta` en `dominio.md` |

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
| `tipo` no en `INDICE_POR_TIPO ∪ COLUMNAS_CLASIFICACION` | `InvarianteViolado` |

##### Notas

- una canasta a la vez; historia completa = varias llamadas + `empalmar`
- `referencia` requerido para versiones encadenadas (2013, 2024); `None` para versiones base (2010, 2018)

##### Ejemplo

```python
canasta = rep.cargar_canasta("canasta_2018.csv", version=2018)
serie   = rep.cargar_serie("serie_2018.csv", version=2018)
indice  = rep.calcular_indice(canasta, serie, tipo="inpc")
```

#### empalmar — RESUELTO

##### Firma

```python
def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: Literal[2010, 2013, 2018, 2024] | None = None,
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `resultados` | `list[ResultadoIndice]` | tramos a unir; orden cronológico; al menos dos elementos |
| `forzar` | `bool` | si `True`, permite empalmar resultados con `periodo_referencia` distintos emitiendo `UserWarning` |
| `version_nombres` | `Literal[2010, 2013, 2018, 2024] \| None` | versión de referencia para nombres de categorías; debe estar en el rango de las nomenclaturas de los inputs (± 1 paso adyacente en `(2010, 2013, 2018, 2024)`); `None` = versión más reciente de los inputs (`max(versions)`) |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | resultado unificado; `manifiesto` concatenado; `reporte` y `diagnostico` mergeados; nombres de categorías normalizados según `version_nombres` |

##### Errores

| condición | error |
|---|---|
| lista vacía o con un solo elemento | `InvarianteViolado` |
| `tipo` distinto entre resultados | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=False` | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=True` | `UserWarning` |
| nomenclaturas (inputs + `version_nombres`) con span > 1 paso adyacente en `(2010, 2013, 2018, 2024)` | `InvarianteViolado` |

##### Notas

- solo une tramos del mismo `tipo`; no hace rebase automático
- `None` + valor explícito → resultado hereda el valor explícito (no requiere `forzar`)
- renombrado de categorías lo aplica `empalmar` de dominio vía `RENOMBRES_INDICES` en `correspondencia_canastas.py`; `version_nombres` selecciona qué convención usar
- `version_nombres=None` → versión más reciente de los inputs (`max(versions)`)
- `version_nombres=X` → dominio usa X como versión canónica contra `RENOMBRES_INDICES`; si no existe mapa para ese `(tipo, X)`, los índices de ese tramo no se renombran (no-op silencioso a nivel de mapa faltante; el span entre nomenclaturas sigue restringido por la invariante de errores)
- las correspondencias de nombres solo están catalogadas entre pares vecinos `2010↔2013`, `2013↔2018`, `2018↔2024`; saltos no contiguos no se pueden expresar en una sola llamada — el caller debe encadenar `empalmar` por pares vecinos

##### Ejemplo

```python
# inputs 2018+2024; nombres quedan con convención 2024 (más reciente)
hist = rep.empalmar([indice_2018, indice_2024])

# inputs 2018+2024; forzar convención 2018 (reverse del mapa 2018↔2024)
hist = rep.empalmar([indice_2018, indice_2024], version_nombres=2018)

# Cadena explícita 2010 → 2024 (encadenar por pares vecinos)
intermedio_a = rep.empalmar([indice_2010, indice_2013])      # nomenclatura 2013
intermedio_b = rep.empalmar([intermedio_a, indice_2018])     # nomenclatura 2018
hist = rep.empalmar([intermedio_b, indice_2024])             # nomenclatura 2024

# FALLA: salto 2010 → 2024 directo (span 3 pasos)
rep.empalmar([indice_2010, indice_2024])  # InvarianteViolado

# FALLA: version_nombres fuera del rango adyacente de los inputs
rep.empalmar([indice_2018, indice_2024], version_nombres=2010)  # InvarianteViolado
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
- `normalizar_categorias(resultado, version_nombres)` — renombrado manual de categorías antes de empalmar; diferida; `empalmar` lo hace internamente vía `version_nombres`

### variaciones.py — RESUELTO (firmas completas)

#### Grupo: variaciones (series) — RESUELTO

##### Funciones (series)

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `variacion_periodica` | `variacion_periodica(resultado, frecuencia)` | `ResultadoVariacion` | una variación por periodo según `frecuencia` |
| `variacion_acumulada_anual` | `variacion_acumulada_anual(resultado)` | `ResultadoVariacion` | ene→periodo_actual vs dic_año_anterior; una fila por periodo |
| `variacion_desde` | `variacion_desde(resultado, desde, hasta, incluir_parciales)` | `ResultadoVariacion` | variación total del rango; una fila por índice |

##### Parámetros comunes

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | resultado de índices; quincenal o mensual |

##### Diferencias por función

| función | parámetro específico | tipo | contrato |
|---|---|---|---|
| `variacion_periodica` | `frecuencia` | `Literal["quincenal", "mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual"]` | quincenal=1Q, mensual=1M, bimestral=2M, trimestral=3M, cuatrimestral=4M, semestral=6M, anual=12M anteriores |
| `variacion_desde` | `desde` | `str` | periodo inicial del rango; ver §Manejo de periodos |
| `variacion_desde` | `hasta` | `str \| None` | periodo final; `None` = último disponible |
| `variacion_desde` | `incluir_parciales` | `bool = True` | si `False`, excluye periodos con `estado_calculo = parcial` |

##### Errores comunes

| condición | error |
|---|---|
| `frecuencia` fuera del conjunto válido | `InvarianteViolado` |
| `frecuencia="quincenal"` con resultado mensual | `InvarianteViolado` |
| `desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |
| `desde` o `hasta` no existe en resultado | `InvarianteViolado` |
| `desde` posterior a `hasta` | `InvarianteViolado` |

##### Ejemplos

```python
vars_mensual = rep.variacion_periodica(indice, frecuencia="mensual")
acum_anual   = rep.variacion_acumulada_anual(indice)
rango        = rep.variacion_desde(indice, desde="Ene 2015", hasta="Dic 2024")
```

#### Grupo: inflación (análisis) — RESUELTO

##### Funciones de análisis

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `inflacion_en` | `inflacion_en(resultado, periodo)` | `pd.DataFrame` | índice=indice, col=`variacion_pp`; todas las categorías en el periodo |
| `inflacion_acumulada` | `inflacion_acumulada(resultado, desde, hasta, indice)` | `float` | variación total del rango para el índice especificado |
| `inflacion_promedio` | `inflacion_promedio(resultado, desde, hasta, indice, metodo)` | `float` | TCAC o promedio simple para el índice especificado |
| `inflacion_maxima` | `inflacion_maxima(resultado, desde, hasta, indice)` | `tuple[str, str, float]` | (periodo, indice, valor) del máximo en el rango |
| `inflacion_minima` | `inflacion_minima(resultado, desde, hasta, indice)` | `tuple[str, str, float]` | (periodo, indice, valor) del mínimo en el rango |

##### Parámetros comunes

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoVariacion` | resultado de variaciones ya calculado |

##### Diferencias por función

| función | parámetro específico | tipo | contrato |
|---|---|---|---|
| `inflacion_en` | `periodo` | `str` | ver §Manejo de periodos |
| `inflacion_acumulada` | `desde` | `str` | periodo inicial; ver §Manejo de periodos |
| `inflacion_acumulada` | `hasta` | `str \| None` | `None` = último disponible |
| `inflacion_acumulada` | `indice` | `str` | índice a consultar; debe existir en resultado |
| `inflacion_promedio` | `desde` | `str \| None` | `None` = primer disponible |
| `inflacion_promedio` | `hasta` | `str \| None` | `None` = último disponible |
| `inflacion_promedio` | `indice` | `str` | índice a consultar |
| `inflacion_promedio` | `metodo` | `Literal["tcac", "simple"] = "tcac"` | `tcac` = tasa de crecimiento anual compuesta; `simple` = media aritmética |
| `inflacion_maxima` | `desde` | `str \| None` | `None` = sin límite inferior |
| `inflacion_maxima` | `hasta` | `str \| None` | `None` = sin límite superior |
| `inflacion_maxima` | `indice` | `str \| None = None` | `None` = máximo global entre todos los índices y periodos |
| `inflacion_minima` | `desde` | `str \| None` | `None` = sin límite inferior |
| `inflacion_minima` | `hasta` | `str \| None` | `None` = sin límite superior |
| `inflacion_minima` | `indice` | `str \| None = None` | `None` = mínimo global entre todos los índices y periodos |

##### Errores comunes

| condición | error |
|---|---|
| `periodo`/`desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |
| `periodo` no existe en resultado | `InvarianteViolado` |
| `desde` o `hasta` no existe en resultado | `InvarianteViolado` |
| `desde` posterior a `hasta` | `InvarianteViolado` |
| `indice` no existe en resultado | `InvarianteViolado` |

##### Notas

- `inflacion_acumulada` e `inflacion_promedio` operan sobre `variacion_pp` fila a fila; solo tienen sentido si `resultado` fue calculado con `variacion_periodica` — con `variacion_desde` o `variacion_acumulada_anual` los valores ya son totales y sumarlos sería incorrecto

##### Ejemplos

```python
variaciones = rep.variacion_periodica(indice, frecuencia="mensual")

en          = rep.inflacion_en(variaciones, periodo="Dic 2024")
acum        = rep.inflacion_acumulada(variaciones, desde="Ene 2015", hasta="Dic 2024", indice="inpc")
prom        = rep.inflacion_promedio(variaciones, desde="Ene 2015", hasta="Dic 2024", indice="inpc")
p, i, v     = rep.inflacion_maxima(variaciones)
p, i, v     = rep.inflacion_maxima(variaciones, indice="Alimentos")
```

### incidencias.py — RESUELTO (firmas completas)

#### Grupo: incidencias (series) — RESUELTO

##### Funciones (series)

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `incidencia_periodica` | `incidencia_periodica(inpc, clasificacion, canastas, frecuencia)` | `ResultadoIncidencia` | incidencia periodo a periodo por genérico |
| `incidencia_acumulada_anual` | `incidencia_acumulada_anual(inpc, clasificacion, canastas)` | `ResultadoIncidencia` | ene→periodo_actual; propiedad: suma de genéricos = variación anual acumulada del INPC |
| `incidencia_desde` | `incidencia_desde(inpc, clasificacion, canastas, desde, hasta, incluir_parciales)` | `ResultadoIncidencia` | incidencia total del rango; una fila por genérico |

##### Parámetros comunes

| parámetro | tipo api | contrato |
|---|---|---|
| `inpc` | `ResultadoIndice` | resultado de índice INPC global |
| `clasificacion` | `ResultadoIndice` | resultado de clasificación (componentes o subcomponentes); mismo `periodo_referencia` que `inpc` |
| `canastas` | `dict[int, CanastaCanonica]` | canastas por versión; claves = `VersionCanasta` |

##### Diferencias por función

| función | parámetro específico | tipo | contrato |
|---|---|---|---|
| `incidencia_periodica` | `frecuencia` | `Literal["quincenal", "mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual"]` | quincenal=1Q, mensual=1M, bimestral=2M, trimestral=3M, cuatrimestral=4M, semestral=6M, anual=12M anteriores |
| `incidencia_desde` | `desde` | `str \| None` | periodo inicial; `None` = primer disponible; ver §Manejo de periodos |
| `incidencia_desde` | `hasta` | `str \| None` | periodo final; `None` = último disponible |
| `incidencia_desde` | `incluir_parciales` | `bool = True` | si `False`, excluye genéricos con `estado_calculo = parcial` |

##### Errores comunes

| condición | error |
|---|---|
| `inpc.periodo_referencia != clasificacion.periodo_referencia` | `InvarianteViolado` |
| `frecuencia` fuera del conjunto válido | `InvarianteViolado` |
| `frecuencia="quincenal"` con resultado mensual | `InvarianteViolado` |
| `desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |
| `desde` o `hasta` no existe en resultado | `InvarianteViolado` |
| `desde` posterior a `hasta` | `InvarianteViolado` |

##### Ejemplos

```python
inc_mensual = rep.incidencia_periodica(inpc, clasificacion, canastas, frecuencia="mensual")
inc_anual   = rep.incidencia_acumulada_anual(inpc, clasificacion, canastas)
rango       = rep.incidencia_desde(inpc, clasificacion, canastas, desde="Ene 2015", hasta="Dic 2024")
```

#### Grupo: incidencias (análisis) — RESUELTO

##### Funciones de análisis

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `incidencia_en` | `incidencia_en(resultado, periodo)` | `pd.DataFrame` | índice=indice, col=`incidencia_pp`; todas las categorías en el periodo |
| `incidencia_acumulada` | `incidencia_acumulada(resultado, desde, hasta, indice)` | `float` | incidencia acumulada del rango para el índice especificado |
| `incidencia_promedio` | `incidencia_promedio(resultado, desde, hasta, indice)` | `float` | promedio aritmético de `incidencia_pp` en el rango para el índice especificado |
| `mayor_incidencia` | `mayor_incidencia(resultado, desde, hasta, indice)` | `tuple[str, str, float]` | (periodo, indice, valor) del máximo en el rango |
| `menor_incidencia` | `menor_incidencia(resultado, desde, hasta, indice)` | `tuple[str, str, float]` | (periodo, indice, valor) del mínimo en el rango |

##### Parámetros comunes

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoIncidencia` | resultado de incidencias ya calculado |

##### Diferencias por función

| función | parámetro específico | tipo | contrato |
|---|---|---|---|
| `incidencia_en` | `periodo` | `str` | ver §Manejo de periodos |
| `incidencia_acumulada` | `desde` | `str` | periodo inicial; ver §Manejo de periodos |
| `incidencia_acumulada` | `hasta` | `str \| None` | `None` = último disponible |
| `incidencia_acumulada` | `indice` | `str` | índice a consultar; debe existir en resultado |
| `incidencia_promedio` | `desde` | `str \| None` | `None` = primer disponible |
| `incidencia_promedio` | `hasta` | `str \| None` | `None` = último disponible |
| `incidencia_promedio` | `indice` | `str` | índice a consultar |
| `mayor_incidencia` | `desde` | `str \| None` | `None` = sin límite inferior |
| `mayor_incidencia` | `hasta` | `str \| None` | `None` = sin límite superior |
| `mayor_incidencia` | `indice` | `str \| None = None` | `None` = máximo global entre todos los índices y periodos |
| `menor_incidencia` | `desde` | `str \| None` | `None` = sin límite inferior |
| `menor_incidencia` | `hasta` | `str \| None` | `None` = sin límite superior |
| `menor_incidencia` | `indice` | `str \| None = None` | `None` = mínimo global entre todos los índices y periodos |

##### Errores comunes

| condición | error |
|---|---|
| `periodo`/`desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |
| `periodo` no existe en resultado | `InvarianteViolado` |
| `desde` o `hasta` no existe en resultado | `InvarianteViolado` |
| `desde` posterior a `hasta` | `InvarianteViolado` |
| `indice` no existe en resultado | `InvarianteViolado` |

##### Notas

- `incidencia_acumulada` e `incidencia_promedio` operan sobre `incidencia_pp` fila a fila; solo tienen sentido si `resultado` fue calculado con `incidencia_periodica` — con `incidencia_desde` o `incidencia_acumulada_anual` los valores ya son totales y sumarlos sería incorrecto

##### Ejemplos

```python
en        = rep.incidencia_en(inc_mensual, periodo="Dic 2024")
acum      = rep.incidencia_acumulada(inc_mensual, desde="Ene 2024", hasta="Dic 2024", indice="Alimentos")
prom      = rep.incidencia_promedio(inc_mensual, desde="Ene 2024", hasta="Dic 2024", indice="Alimentos")
p, i, v   = rep.mayor_incidencia(inc_mensual)
p, i, v   = rep.mayor_incidencia(inc_mensual, indice="Alimentos")
```

### validaciones.py — RESUELTO (firmas completas)

#### Grupo: validar_* — RESUELTO

##### Funciones

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `validar_indice` | `validar_indice(resultado)` | `ValidacionIndice` | compara `ResultadoIndice` contra series INEGI |
| `validar_variacion` | `validar_variacion(resultado)` | `ValidacionVariacion` | compara `ResultadoVariacion` contra series INEGI |
| `validar_incidencia` | `validar_incidencia(resultado)` | `ValidacionIncidencia` | compara `ResultadoIncidencia` contra series INEGI |

##### Parámetros comunes

Cada función recibe un único parámetro `resultado` del tipo `ResultadoX` correspondiente. Contrato compartido:

| aspecto | contrato |
|---|---|
| `tipo` | leído del manifiesto del resultado; debe pertenecer a `TIPOS_CON_VALIDACION`; el usuario no lo pasa |
| frecuencia | auto-detectada por tipo de periodo en el resultado: `PeriodoQuincenal` → quincenal; `PeriodoMensual` → mensual |
| token INEGI | requerido; obtenido vía `get_token()` (ver `config.py §Token híbrido`) |

##### Diferencias por función

| función | tipo de `resultado` | retorno |
|---|---|---|
| `validar_indice` | `ResultadoIndice` | `ValidacionIndice` |
| `validar_variacion` | `ResultadoVariacion` | `ValidacionVariacion` |
| `validar_incidencia` | `ResultadoIncidencia` | `ValidacionIncidencia` |

##### Errores comunes

| condición | error |
|---|---|
| `tipo` del manifiesto no en `TIPOS_CON_VALIDACION` | `ErrorConfiguracion` |
| token INEGI no configurado | `ErrorConfiguracion` |
| API INEGI no responde / HTTP error | `FuenteNoDisponible` |
| respuesta INEGI con formato inesperado | `RespuestaInvalida` |

##### Notas

- `TIPOS_CON_VALIDACION = {"inpc", "inflacion componente", "inflacion subcomponente"}`.

- `validar_variacion`: comparables contra INEGI son `clase_variacion in {"periodica_mensual", "periodica_anual"}` para periodos mensuales y `{"periodica_quincenal", "periodica_anual"}` para quincenales; y `"acumulada_anual"`. `clase_variacion = "desde"` y valores fuera de los conjuntos válidos lanzan `ErrorConfiguracion`.

- `validar_incidencia`: INEGI solo publica incidencia periódica mensual. Únicamente comparable: `clase_incidencia = "periodica_mensual"`. Cualquier otro valor lanza `ErrorConfiguracion`.

##### Ejemplos

```python
import replica_inpc as rep

val_indice     = rep.validar_indice(indice)
val_variacion  = rep.validar_variacion(variacion_periodica_mensual)
val_incidencia = rep.validar_incidencia(incidencia_periodica_mensual)
```

```bash
replica-inpc validar-indice     --resultado resultado.csv
replica-inpc validar-variacion  --resultado variaciones.csv
replica-inpc validar-incidencia --resultado incidencias.csv
```

### flujos.py — RESUELTO (firmas completas)

#### calcular_historia — RESUELTO

##### Firma

```python
def calcular_historia(
    insumos: list[tuple[VersionCanasta, str, str]],
    tipo: str = "inpc",
    referencia: str = "Jul 2018",
    periodicidad: Literal["quincenal", "mensual"] = "mensual",
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `insumos` | `list[tuple[VersionCanasta, str, str]]` | orden cronológico; cada elemento = `(version, canasta_path, series_path)`; mínimo 1 elemento; sin versiones duplicadas; si contiene 2013 → debe contener 2010; si contiene 2024 → debe contener 2018 |
| `tipo` | `str` | clasificación a calcular; debe existir en todas las canastas de `insumos`; default `"inpc"` |
| `referencia` | `str` | periodo base para `rebasar`; formato `"NQ Mmm AAAA"` o `"Mmm AAAA"` — debe coincidir con `periodicidad` (el rebase se aplica tras convertir a la frecuencia final); default `"Jul 2018"` |
| `periodicidad` | `Literal["quincenal", "mensual"]` | frecuencia del resultado final; default `"mensual"` |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | resultado empalmado, rebased a `referencia`, en `periodicidad` indicada; nombres de categorías de la versión más reciente en `insumos` |

##### Orquestación interna

Pasos en orden; el usuario no tiene acceso a resultados intermedios:

1. Por cada `(version, canasta_path, series_path)` en `insumos`: `cargar_canasta` + `cargar_serie`
2. `calcular_indice` por versión con encadenamiento automático entre versiones consecutivas
3. Si `len(insumos) > 1`: `empalmar` encadenado por pares vecinos en orden cronológico hasta llegar a la versión más reciente (cada llamada a `empalmar` admite span máximo de 1 paso adyacente en `(2010, 2013, 2018, 2024)`); nomenclatura final = `max(versions)` de `insumos`
4. Si `periodicidad="mensual"`: `a_mensual`
5. `rebasar` al periodo `referencia`

`a_mensual` precede a `rebasar`: `a_mensual` devuelve `periodo_referencia=None`, por lo que rebasear antes lo anularía; además, con `periodicidad="mensual"` el `referencia` resuelto es `PeriodoMensual` y `rebasar` exige que exista en el resultado, lo que solo ocurre tras `a_mensual` (ver `transiscion.md` §`CalcularHistoria — orden`).

Para control granular sobre cualquier paso, usar las funciones manuales de `insumos.py`, `indices.py`.

##### Errores

| condición | error |
|---|---|
| `insumos` vacío | `InvarianteViolado` |
| versión duplicada en `insumos` | `InvarianteViolado` |
| versión encadenada (2013 o 2024) sin su versión base en `insumos` | `InvarianteViolado` |
| `tipo` no presente en alguna canasta | `InvarianteViolado` |
| path no encontrado | `ArchivoNoEncontrado` |
| archivo vacío | `ArchivoVacio` |
| archivo corrupto / formato inválido | `ArchivoCorrupto` |
| encoding no legible | `EncodingNoLegible` |
| columnas requeridas faltantes en canasta | `ColumnasMinFaltantes` |
| orientación no detectable en serie | `OrientacionNoDetectable` |
| sin genéricos en serie | `SerieVacia` |
| `referencia` no parseable | `ErrorConfiguracion` |

##### Ejemplo

```python
import replica_inpc as rep

insumos = [
    (2010, "ponderadores_2010.csv", "series_2010.csv"),
    (2018, "ponderadores_2018.csv", "series_2018.csv"),
    (2024, "ponderadores_2024.csv", "series_2024.csv"),
]
historico = rep.calcular_historia(insumos)
```

```bash
replica-inpc calcular-historia --config historia.toml
```

#### Funciones diferidas

- `calcular_variacion` — diferida; `calcular_historia` + `variacion_periodica` cubre el caso con una línea adicional
- `calcular_incidencia` — diferida; mismo argumento que `calcular_variacion`
- `verificar` — diferida; orquestación completa requiere más diseño (firma compleja por `clasificacion`)
- `exportar` — diferida; pandas ya expone `to_csv`/`to_excel`

---

## Decisiones

### §D1. Acoplamiento api/ → infraestructura/

`api/` llama directamente a `infraestructura/csv/` e `infraestructura/inegi/` —
instancia `LectorCanastaCsv`, `LectorSeriesCsv` y `FuenteValidacionApi` sin
inyección de dependencias. Pragmático y suficiente para v2: solo existe una
fuente de cada tipo (CSV local, API INEGI).

La migración a puertos + DI (`aplicacion/puertos/`) se difiere a cuando se
agreguen fuentes alternativas (SQL, HTTP, etc.); entonces `config.py` inyectará
el adaptador concreto al arrancar. Los modelos de dominio no cambian — solo se
suma el adaptador nuevo.

### §D2. Token híbrido en config.py

`get_token()` busca la env var `INEGI_TOKEN` **primero** y solo después el valor
de `set_token`. El orden no es arbitrario: en CI y en la CLI el token se fija por
entorno sin escribir código, y ese contexto debe ganar sobre un `set_token`
dejado por error en una celda de notebook. En un notebook interactivo, donde no
hay env var, `set_token` sigue siendo el único mecanismo y funciona sin
fricción. Si ninguno está disponible, `get_token()` lanza `ErrorConfiguracion`.

### §D3. Versión explícita en insumos

`version` es obligatorio (no auto-detect) en `cargar_canasta` y `cargar_serie`
porque las canastas 2010 y 2013 tienen genéricos idénticos: un auto-detect no
puede distinguirlas y elegiría mal en silencio, produciendo un cálculo
erróneo sin error visible. Exigir la versión hace explícito el contrato y
traslada la decisión al usuario, que sí conoce el origen del archivo.

### §D4. Re-export de errores en `__init__.py`

Los tipos de error de `dominio/errores.py` se re-exportan a través de `api/__init__.py` y quedan disponibles como `rep.ArchivoNoEncontrado`, `rep.InvarianteViolado`, etc. El usuario no necesita importar desde rutas internas para capturar errores específicos. Consistente con el estilo flat (`import replica_inpc as rep`).
