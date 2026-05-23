# Guía de uso — replica_inpc

El uso típico es desde un notebook de Jupyter (VS Code o navegador). Los flujos de esta guía asumen ese entorno.

## Setup del notebook

```python
from IPython.display import display
import replica_inpc as rep
```

`display(obj)` renderiza objetos `ResultadoIndice`, `ResultadoVariacion`, `ResultadoIncidencia` y DataFrames con formato HTML dentro del notebook. En VS Code, la extensión **Data Wrangler** permite explorar los `.df` de los resultados de forma interactiva (clic derecho sobre la variable → "Open in Data Wrangler").

Para exportar o inspeccionar fuera del notebook:

```python
resultado.df.to_csv("output/inpc.csv")
```

`import replica_inpc as rep` es el único import de la librería. No se requieren rutas internas.

---

## Flujo 1 — INPC histórico (modo automático)

El camino más corto. `calcular_historia` orquesta carga → cálculo → empalme → conversión → rebase en una sola llamada. Usar cuando no se necesita acceso a resultados intermedios por versión.

```python
import replica_inpc as rep

insumos = [
    (2010, "data/ponderadores_2010.csv", "data/series_2010.csv"),
    (2013, "data/ponderadores_2013.csv", "data/series_2013.csv"),
    (2018, "data/ponderadores_2018.csv", "data/series_2018.csv"),
    (2024, "data/ponderadores_2024.csv", "data/series_2024.csv"),
]

inpc = rep.calcular_historia(insumos)
# ResultadoIndice mensual, base Jul 2018 = 100
# nomenclatura de categorías: versión 2024 (la más reciente)

display(inpc)           # tabla HTML en el notebook
display(inpc.resumen)   # estado por tramo (estado_calculo, periodos, versión)
```

**Parámetros opcionales:**

| parámetro | default | descripción |
|---|---|---|
| `tipo` | `"inpc"` | índice a calcular; debe existir en todas las canastas de `insumos` |
| `referencia` | `"2Q Jul 2018"` | periodo base (= 100); solo formato quincenal `"NQ Mmm AAAA"`; con `periodicidad="mensual"` se convierte automáticamente a su equivalente mensual |
| `periodicidad` | `"mensual"` | frecuencia del resultado: `"mensual"` o `"quincenal"` |

**Reglas de `insumos`:**
- Si incluye 2013 → debe incluir 2010
- Si incluye 2024 → debe incluir 2018
- Sin versiones duplicadas; en orden cronológico

**Errores posibles:**

| condición | error |
|---|---|
| `insumos` vacío | `InvarianteViolado` |
| versión duplicada | `InvarianteViolado` |
| 2013 sin 2010, o 2024 sin 2018 | `InvarianteViolado` |
| `tipo` no presente en alguna canasta | `InvarianteViolado` |
| `referencia` en formato mensual | `ErrorConfiguracion` |
| path no encontrado | `ArchivoNoEncontrado` |
| archivo vacío | `ArchivoVacio` |
| CSV corrupto o formato inválido | `ArchivoCorrupto` |
| encoding no reconocible | `EncodingNoLegible` |

---

## Flujo 2 — Modo manual (control granular)

Útil cuando se necesita acceso a los resultados intermedios por versión, reutilizar canastas cargadas entre múltiples cálculos, o controlar el rebase por tramo.

### Caso base: 2 versiones (2018 + 2024)

```python
import replica_inpc as rep

# 1. Cargar insumos
c2018 = rep.cargar_canasta("data/ponderadores_2018.csv", version=2018)
s2018 = rep.cargar_serie("data/series_2018.csv", version=2018)
c2024 = rep.cargar_canasta("data/ponderadores_2024.csv", version=2024)
s2024 = rep.cargar_serie("data/series_2024.csv", version=2024)

# 2. Calcular por versión (2024 es encadenada → requiere referencia de 2018)
i2018 = rep.calcular_indice(c2018, s2018, tipo="inpc")
i2024 = rep.calcular_indice(c2024, s2024, tipo="inpc", referencia=i2018)

# 3. Empalmar → a_mensual → rebasar (orden obligatorio)
hist  = rep.empalmar([i2018, i2024])
hist_m = rep.a_mensual(hist)        # siempre antes de rebasar
inpc   = rep.rebasar(hist_m, "Jul 2018")
```

`cargar_serie` devuelve siempre periodos quincenales. `a_mensual` debe ir **antes** de `rebasar` — el orden inverso anula la referencia.

### Caso completo: 4 versiones

El bloque 2010/2013 y el bloque 2018/2024 viven en escalas naturales distintas: "2Q Jul 2018" vale ~X en el bloque 2010/2013 y vale 100 en el bloque 2018/2024. Hay que rebasar el bloque anterior a "2Q Jul 2018" antes de empalmar con el bloque 2018/2024.

```python
# Cargar (2010 y 2013 adicionales)
c2010 = rep.cargar_canasta("data/ponderadores_2010.csv", version=2010)
s2010 = rep.cargar_serie("data/series_2010.csv", version=2010)
c2013 = rep.cargar_canasta("data/ponderadores_2013.csv", version=2013)
s2013 = rep.cargar_serie("data/series_2013.csv", version=2013)

# Calcular por versión
i2010 = rep.calcular_indice(c2010, s2010, tipo="inpc")
i2013 = rep.calcular_indice(c2013, s2013, tipo="inpc", referencia=i2010)
i2018 = rep.calcular_indice(c2018, s2018, tipo="inpc")
i2024 = rep.calcular_indice(c2024, s2024, tipo="inpc", referencia=i2018)

# Empalmar bloque pre-2018 y rebasar para que "2Q Jul 2018" = 100 (igual que i2018 natural)
pre   = rep.empalmar([i2010, i2013])
pre_r = rep.rebasar(pre, "2Q Jul 2018")

# Empalmar los dos bloques — renombre transitivo aplicado automáticamente
inpc_pos = rep.empalmar([i2018, i2024])
hist     = rep.empalmar([pre_r, inpc_pos])

hist_m = rep.a_mensual(hist)
inpc   = rep.rebasar(hist_m, "Jul 2018")
```

`empalmar([pre_r, inpc_pos])` no requiere `forzar=True` porque `pre_r.periodo_referencia = "2Q Jul 2018"` coincide con la frontera entre ambos bloques.

`rebasar` acepta formato quincenal o mensual según la periodicidad del resultado — la restricción de solo quincenal aplica únicamente a `calcular_historia`. `rebasar(hist_m, "Jul 2018")` es correcto porque `hist_m` es mensual; hace `promedio(1Q Jul 2018, 2Q Jul 2018) = 100`. Es la misma convención que usa el INEGI en sus publicaciones mensuales.

**Errores posibles en `calcular_indice`:**

| condición | error |
|---|---|
| `referencia=None` para versión encadenada (2013 o 2024) | `InvarianteViolado` |
| sin genéricos con correspondencia canasta↔serie | `CorrespondenciaInsuficiente` |
| canasta sin genéricos utilizables para el `tipo` | `CanastaSinGenericos` |
| `tipo` no reconocido | `InvarianteViolado` |

**Errores posibles en `empalmar`:**

| condición | error |
|---|---|
| pares consecutivos sin periodo compartido | `InvarianteViolado` |
| `periodo_referencia` desalineada con `forzar=False` | `InvarianteViolado` |
| lista con un solo elemento | `InvarianteViolado` |
| `version_nombres` fuera del rango de versiones de los inputs | `InvarianteViolado` |

---

## Flujo 3 — Subíndices por clasificador

Mismo flujo que INPC, con `tipo` distinto. `referencia` en versiones encadenadas debe ser el resultado del **mismo tipo** de la versión base, no el INPC.

```python
# Modo automático
ccif = rep.calcular_historia(insumos, tipo="CCIF division")
cog  = rep.calcular_historia(insumos, tipo="COG")
```

```python
# Modo manual — nota: referencia es el resultado del mismo tipo en versión anterior
i2018_cog = rep.calcular_indice(c2018, s2018, tipo="COG")
i2024_cog = rep.calcular_indice(c2024, s2024, tipo="COG", referencia=i2018_cog)

cog = rep.rebasar(rep.a_mensual(rep.empalmar([i2018_cog, i2024_cog])), "Jul 2018")
```

**Tipos disponibles:**

| tipo | descripción |
|---|---|
| `"inpc"` | Índice Nacional de Precios al Consumidor |
| `"inflacion componente"` | subyacente / no subyacente |
| `"inflacion subcomponente"` | desglose de subyacente y no subyacente |
| `"COG"` | Objeto del Gasto |
| `"CCIF division"` | COICOP nivel división |
| `"CCIF grupo"` | COICOP nivel grupo |
| `"CCIF clase"` | COICOP nivel clase |
| `"SCIAN sector"` | sector SCIAN |
| `"SCIAN rama"` | rama SCIAN |
| `"durabilidad"` | bienes duraderos / semi / no duraderos / servicios |
| `"origen"` | nacionales / importados |

Los tipos disponibles en cada canasta dependen de su versión. Si un `tipo` no existe en alguna canasta de `insumos`, `calcular_historia` lanza `InvarianteViolado`.

### Múltiples subíndices en la misma sesión (reutilizando insumos cargados)

```python
# Cargar una sola vez
c2018 = rep.cargar_canasta("data/ponderadores_2018.csv", version=2018)
s2018 = rep.cargar_serie("data/series_2018.csv", version=2018)
c2024 = rep.cargar_canasta("data/ponderadores_2024.csv", version=2024)
s2024 = rep.cargar_serie("data/series_2024.csv", version=2024)

# INPC
i2018_inpc = rep.calcular_indice(c2018, s2018, tipo="inpc")
i2024_inpc = rep.calcular_indice(c2024, s2024, tipo="inpc", referencia=i2018_inpc)
inpc = rep.rebasar(rep.a_mensual(rep.empalmar([i2018_inpc, i2024_inpc])), "Jul 2018")

# COG (referencia = resultado COG de 2018, no el INPC)
i2018_cog = rep.calcular_indice(c2018, s2018, tipo="COG")
i2024_cog = rep.calcular_indice(c2024, s2024, tipo="COG", referencia=i2018_cog)
cog = rep.rebasar(rep.a_mensual(rep.empalmar([i2018_cog, i2024_cog])), "Jul 2018")
```

---

## Flujo 4 — Variaciones e inflación

Las funciones de variación operan sobre un `ResultadoIndice` ya calculado.

```python
# Variación mensual (un valor por periodo)
vars_m = rep.variacion_periodica(inpc, frecuencia="mensual")

# Variación anual (lag 12 meses, un valor por periodo)
vars_a = rep.variacion_periodica(inpc, frecuencia="anual")

# Variación acumulada anual (ene→periodo vs dic del año anterior)
acum = rep.variacion_acumulada_anual(inpc)

# Variación total de un rango (una fila por índice)
total_2024 = rep.variacion_desde(inpc, desde="Ene 2024", hasta="Dic 2024")
```

**Frecuencias válidas para `variacion_periodica`:** `"quincenal"`, `"mensual"`, `"bimestral"`, `"trimestral"`, `"cuatrimestral"`, `"semestral"`, `"anual"`. Usar `"quincenal"` con resultado mensual lanza `InvarianteViolado`.

### Análisis sobre variaciones

```python
vars_m = rep.variacion_periodica(inpc, frecuencia="mensual")

# Todos los índices en un periodo → pd.DataFrame (índice=indice, col=variacion_pp)
en_dic = rep.inflacion_en(vars_m, "Dic 2024")
display(en_dic)

# Inflación acumulada de un índice en un rango → float (pp)
acum_2024 = rep.inflacion_acumulada(vars_m, desde="Ene 2024", hasta="Dic 2024", indice="INPC")

# Promedio anual → float (pp)
prom = rep.inflacion_promedio(
    vars_m, desde="Ene 2020", hasta="Dic 2024", indice="INPC", metodo="tcac"
)
# metodo="tcac": tasa de crecimiento anual compuesta  |  metodo="simple": media aritmética

# Máximo y mínimo → tuple[periodo: str, indice: str, valor: float]
p, i, v = rep.inflacion_maxima(vars_m, desde="Ene 2022", hasta="Dic 2024")
p, i, v = rep.inflacion_minima(vars_m, indice="INPC")   # en toda la serie para ese índice
```

`inflacion_acumulada` e `inflacion_promedio` solo tienen sentido sobre `variacion_periodica` — sumar variaciones de `variacion_acumulada_anual` o `variacion_desde` produce resultados incorrectos.

**Errores posibles:**

| condición | error |
|---|---|
| `desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |
| periodo no existe en resultado | `InvarianteViolado` |
| `indice` no existe en resultado | `InvarianteViolado` |
| `desde` posterior a `hasta` | `InvarianteViolado` |

---

## Flujo 5 — Incidencias

Mide la contribución de cada categoría (genérico, componente, etc.) a la variación del INPC. Requieren el INPC global, un resultado de clasificación con el **mismo `periodo_referencia`**, y las canastas por versión.

```python
import replica_inpc as rep

# Insumos (modo manual para tener acceso a las canastas)
c2018 = rep.cargar_canasta("data/ponderadores_2018.csv", version=2018)
s2018 = rep.cargar_serie("data/series_2018.csv", version=2018)
c2024 = rep.cargar_canasta("data/ponderadores_2024.csv", version=2024)
s2024 = rep.cargar_serie("data/series_2024.csv", version=2024)

# INPC e inflacion componente con el mismo rebase (obligatorio: mismo periodo_referencia)
i2018_inpc = rep.calcular_indice(c2018, s2018, tipo="inpc")
i2024_inpc = rep.calcular_indice(c2024, s2024, tipo="inpc", referencia=i2018_inpc)
inpc = rep.rebasar(rep.a_mensual(rep.empalmar([i2018_inpc, i2024_inpc])), "Jul 2018")

i2018_comp = rep.calcular_indice(c2018, s2018, tipo="inflacion componente")
i2024_comp = rep.calcular_indice(c2024, s2024, tipo="inflacion componente", referencia=i2018_comp)
comp = rep.rebasar(rep.a_mensual(rep.empalmar([i2018_comp, i2024_comp])), "Jul 2018")

canastas = {2018: c2018, 2024: c2024}

# Incidencia periodo a periodo
inc_m = rep.incidencia_periodica(inpc, comp, canastas, frecuencia="mensual")

# Incidencia acumulada anual (propiedad: ∑ genéricos = variación anual del INPC en ese periodo)
inc_anual = rep.incidencia_acumulada_anual(inpc, comp, canastas)

# Incidencia de un rango (una fila por genérico)
inc_2024 = rep.incidencia_desde(inpc, comp, canastas, desde="Ene 2024", hasta="Dic 2024")
```

### Análisis sobre incidencias

```python
# Todas las categorías en un periodo → pd.DataFrame (índice=indice, col=incidencia_pp)
en_dic = rep.incidencia_en(inc_m, "Dic 2024")
display(en_dic)

# Incidencia acumulada de una categoría → float (pp)
acum = rep.incidencia_acumulada(
    inc_m, desde="Ene 2024", hasta="Dic 2024", indice="subyacente"
)

# Mayor y menor contribuyente → tuple[periodo: str, indice: str, valor: float]
p, i, v = rep.mayor_incidencia(inc_m, desde="Ene 2024", hasta="Dic 2024")
p, i, v = rep.menor_incidencia(inc_m)
```

**Restricciones:**
- `inpc.periodo_referencia` debe coincidir con `clasificacion.periodo_referencia` (mismo rebase)
- `canastas` debe tener una entrada por cada versión presente en `clasificacion`
- `tipo` de `clasificacion` debe estar en `COLUMNAS_CLASIFICACION`

**Errores posibles:**

| condición | error |
|---|---|
| `periodo_referencia` distinto entre INPC y clasificación | `InvarianteViolado` |
| falta `canastas[v]` para alguna versión en clasificación | `ErrorConfiguracion` |
| `tipo` de clasificación no reconocido | `ErrorConfiguracion` |
| `desde`/`hasta` con formato inválido | `PeriodoNoInterpretable` |

---

## Flujo 6 — Validación contra INEGI

Compara los resultados calculados contra los datos publicados por INEGI (BIE). Requiere token de API.

```python
import replica_inpc as rep

# Configurar token una vez por sesión
rep.set_token("mi-token-inegi")
# Alternativa sin código: export INEGI_TOKEN="mi-token-inegi"
# La variable de entorno tiene prioridad sobre set_token

# Validar índice
val_ind = rep.validar_indice(inpc)
val_ind.aprobado    # bool
val_ind.df          # DataFrame con diferencias por (periodo, índice)

# Validar variaciones (solo clase_variacion compatible con INEGI)
vars_m   = rep.variacion_periodica(inpc, frecuencia="mensual")
val_var  = rep.validar_variacion(vars_m)

# Validar incidencias (INEGI solo publica periódica mensual)
inc_m    = rep.incidencia_periodica(inpc, comp, canastas, frecuencia="mensual")
val_inc  = rep.validar_incidencia(inc_m)
```

**Tipos validables:** `"inpc"`, `"inflacion componente"`, `"inflacion subcomponente"`. Otros tipos lanzan `ErrorConfiguracion`.

**Variaciones validables:** `clase_variacion` en `{"periodica_mensual", "periodica_anual", "acumulada_anual"}` para resultado mensual; `{"periodica_quincenal", "periodica_anual"}` para quincenal. `clase_variacion="desde"` lanza `ErrorConfiguracion`.

**Tolerancias ajustables:**

```python
rep.tolerancia_indice    = 0.0009   # default; diferencia absoluta máxima en índices
rep.tolerancia_derivados = 0.009    # default; diferencia absoluta máxima en pp
rep.timeout_api          = 10       # default; segundos por llamada a INEGI
```

**Errores posibles:**

| condición | error |
|---|---|
| token no configurado | `ErrorConfiguracion` |
| `tipo` no validable | `ErrorConfiguracion` |
| `clase_variacion` no comparable con INEGI | `ErrorConfiguracion` |
| API INEGI sin respuesta | `FuenteNoDisponible` |
| respuesta INEGI con formato inesperado | `RespuestaInvalida` |

---

## Referencia rápida de errores

| error | cuándo ocurre |
|---|---|
| `ArchivoNoEncontrado` | path no existe en disco |
| `ArchivoVacio` | archivo existe pero sin datos |
| `ArchivoCorrupto` | CSV no parseable |
| `EncodingNoLegible` | encoding no reconocible |
| `ColumnasMinFaltantes` | columnas requeridas ausentes en canasta |
| `OrientacionNoDetectable` | CSV de serie sin orientación válida |
| `SerieVacia` | ninguna fila útil tras normalización |
| `CorrespondenciaInsuficiente` | sin genéricos comunes canasta↔serie |
| `CanastaSinGenericos` | canasta sin genéricos utilizables para el `tipo` |
| `PonderadorFaltante` | ponderador faltante al calcular |
| `PeriodoNoInterpretable` | string de periodo con formato inválido |
| `InvarianteViolado` | contrato de dominio roto (ver función específica) |
| `ErrorConfiguracion` | configuración inválida o faltante |
| `FuenteNoDisponible` | API INEGI no responde |
| `RespuestaInvalida` | respuesta INEGI con formato inesperado |

Todos heredan de `rep.ReplicaInpcError`. Para capturar cualquier error del paquete:

```python
try:
    inpc = rep.calcular_historia(insumos)
except rep.ReplicaInpcError as e:
    print(type(e).__name__, e)
```
