# Rediseño api/

## Capa api/

### Decisiones generales

- Distribución: pip + CLI. No exposición HTTP pública
- Estilo: flat, pandas-like. `import replica_inpc as rep` → `rep.<func>(...)`
- Sin clases fachada en superficie pública

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

### Convención de naming (módulos)

- Sustantivos en plural (excepto `config.py`).
- Describen el dominio o el tipo de objeto que gestionan.

### Convención de naming (funciones públicas)

- `verbo_objeto`: `cargar_canasta`, `calcular_indice`, `cargar_serie`
- `objeto_modificador`: `variacion_periodica`, `incidencia_desde`
- Verbo solo para transformaciones: `empalmar`, `rebasar`, `a_mensual`
- `validar_*` + qué se valida
- Español obligatorio
- Prohibido: `obtener_*`, `crear_*`, `procesar_*`, inglés, sufijo `_csv` en pública

### Encadenamiento

- Funciones libres = API principal
- `Resultado*` exponen método `.pipe(fn, *args, **kwargs)` para chain estilo pandas

### Manejo de periodos — decisión v2

- Funciones públicas aceptan `str | PeriodoMensual | PeriodoQuincenal` en parámetros de periodo.
- `api/` convierte strings con `periodo_desde_str` antes de pasar a dominio.
- Dominio recibe solo objetos `Periodo*` — nunca strings.
- Formatos válidos: `"1Q Ene 2015"`, `"2Q Jul 2018"`, `"Ene 2015"`, `"Dic 2024"`.

### Acoplamiento — decisión v2

- **Hoy:** `api/` llama `infraestructura/csv/` directo. Pragmático, suficiente para v2.
- **Futuro:** migrar a puertos + DI (`aplicacion/puertos/`) cuando se agreguen fuentes distintas (SQL, HTTP, etc.). `config.py` inyectará el adaptador concreto al arrancar. Los modelos de dominio no cambian — solo se agrega el adaptador nuevo.

### Pendientes generales (pre-discutir antes de cerrar api/)

- `config.py`: env var vs singleton vs híbrido
- Inyección de dependencias para tests
- Re-export de errores tipados (`rep.errores`)
- Re-export de `Periodo*` y factory `periodo_desde_str` — decisión: SÍ

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

### insumos.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `cargar_canasta` — carga canasta desde archivo
- `cargar_serie` — carga serie desde archivo

Funciones diferidas (tal vez, no implementadas):

- `normalizar_ponderadores` — asegura que los ponderadores de una canasta sumen 100

Notas:

- Versión: explícita siempre. NO auto-detect (riesgo de cálculo silencioso
  erróneo; ej. canastas 2010 y 2013 tienen genéricos idénticos)
- Delega a `infraestructura/csv/`
- Devuelve modelos de dominio

#### Ejemplos — notebook — insumos.py

```python
import replica_inpc as rep

canasta = rep.cargar_canasta("canasta_2018.csv", version=2018)
serie   = rep.cargar_serie("serie_2018.csv", version=2018)
```

Nota: `cargar_canasta` y `cargar_serie` son funciones Python — no tienen comando CLI propio.
Los insumos se pasan como argumentos al comando `calcular` de `indices.py`.

### indices.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `calcular_indice` — cálculo de índices para una canasta
- `empalmar` — une tramos de una misma referencia base
- `rebasar` — reexpresa índices a nueva referencia (una función, dos usos: intra-canasta y cross-canasta)
- `a_mensual` — conversión quincenal → mensual

Funciones diferidas (tal vez, no implementadas):

- `desencadenar` — remoción de factores de encadenamiento para recuperar Laspeyres crudo

Notas:

- `calcular_indice`: una canasta a la vez. Historia completa = varias llamadas + `empalmar`.
- `empalmar`: solo une series de misma referencia base. NO hace rebase automático.
- `rebasar`: mecánica idéntica para ambos usos — `valor / valor_en_periodo_base × 100`.
- `empalmar` reemplaza a `combinar`.

#### Ejemplos — notebook — indices.py

Tramo único:

```python
import replica_inpc as rep

canasta = rep.cargar_canasta("canasta_2018.csv", version=2018)
serie   = rep.cargar_serie("serie_2018.csv", version=2018)
indice  = rep.calcular_indice(canasta, serie)
mensual = rep.a_mensual(indice)
```

Historia completa (2Q Dic 2010 → actual, base 2018=100):

```python
import replica_inpc as rep

versiones  = [2010, 2013, 2018, 2024]
canastas   = [rep.cargar_canasta(f"c{v}.csv", version=v) for v in versiones]
series     = [rep.cargar_serie(f"s{v}.csv",   version=v) for v in versiones]
resultados = [rep.calcular_indice(c, s) for c, s in zip(canastas, series)]

hist_2010    = rep.empalmar(resultados[:2])
hist_rebased = rep.rebasar(hist_2010, periodo_base="2Q Jul 2018")
historico    = rep.empalmar([hist_rebased] + resultados[2:])
```

#### Ejemplos — CLI — indices.py

```bash
replica-inpc calcular --version 2018 --canasta canasta_2018.csv --serie serie_2018.csv
```

Nota: historia completa vía CLI → ver `flujos.py`.

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

- `incidencia_periodica(resultado, frecuencia)` — incidencia periodo a periodo por genérico
- `incidencia_acumulada_anual(resultado)` — acumulado ene→actual; suma de todos los genéricos = variación anual acumulada
- `incidencia_desde(resultado, desde, hasta, incluir_parciales)` — incidencia entre dos periodos
- `incidencia_en(resultado, periodo)` — incidencia de todos los genéricos en un periodo → Series
- `incidencia_acumulada(resultado, desde, hasta)` — incidencia acumulada por genérico → Series

Funciones públicas (escalares):

- `mayor_incidencia(resultado, periodo)` — → (genérico, float)
- `menor_incidencia(resultado, periodo)` — → (genérico, float)

Notas:

- Firmas provisionales — parámetro `canasta` pendiente hasta replanteo de contratos de dominio.
- Incidencia requiere índice del genérico en `t` y `t-1` + ponderador. Si `ResultadoCalculo` no embebe la canasta, `canasta` será parámetro explícito.
- `incidencia_acumulada_anual`: propiedad matemática — suma de incidencias de todos los genéricos = variación anual acumulada.
- `incluir_parciales` en `incidencia_desde`: diferido.

#### Ejemplos — notebook — incidencias.py

```python
import replica_inpc as rep

# serie de incidencias mensuales
inc_mensual = rep.incidencia_periodica(indice, frecuencia="mensual")

# genérico con mayor incidencia en un periodo
generico, valor = rep.mayor_incidencia(indice, periodo="Dic 2024")

# incidencia acumulada por genérico 2015–2024
rep.incidencia_acumulada(indice, desde="Ene 2015", hasta="Dic 2024")
```

#### Ejemplos — CLI — incidencias.py

```bash
replica-inpc incidencia --frecuencia mensual --indice resultado.csv
replica-inpc mayor-incidencia --periodo 2024-12 --indice resultado.csv
```

### validaciones.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `validar_mensual(resultado)` — valida series + variaciones (periódica/interanual/acumulada) + incidencias contra INEGI
- `validar_quincenal(resultado)` — valida series + variaciones (periódica/interanual/acumulada) contra INEGI; sin incidencias

Notas:

- Cada función itera los 3 tipos disponibles: `"inpc"`, `"inflacion componente"`, `"inflacion subcomponente"`.
- Delega a `FuenteValidacionApi` — auto-detecta frecuencia por tipo de periodo en `resultado`.
- Devuelve `ResultadoValidacion` (estructura pendiente de replanteo de contratos de dominio).
- Pendiente: parámetro `tipos` opcional para control granular de qué se valida (series/variaciones/incidencias).

#### Ejemplos — notebook — validaciones.py

```python
import replica_inpc as rep

reporte = rep.validar_mensual(indice)
reporte = rep.validar_quincenal(indice)
```

#### Ejemplos — CLI — validaciones.py

```bash
replica-inpc validar --indice resultado.csv
```

### flujos.py — RESUELTO (firmas provisionales)

Funciones públicas:

- `calcular_historia(canastas, series)` — múltiples canastas → serie completa empalmada y rebased
- `calcular_variacion(canastas, series, frecuencia)` — calcula índice + devuelve variaciones
- `calcular_incidencia(canastas, series, frecuencia)` — calcula índice + devuelve incidencias
- `verificar(canastas, series)` — calcula + variaciones + incidencias + valida contra INEGI (requiere token)
- `exportar(resultado, path)` — guarda cualquier resultado a archivo

Notas:

- Re-exporta desde `aplicacion/casos_uso/`. La lógica de orquestación vive ahí, no en `api/`.
- `calcular_variacion` / `calcular_incidencia`: cálculo puro, sin token, sin INEGI.
- `verificar`: requiere token INEGI configurado vía `config.set_token` o `INEGI_TOKEN` env var.

#### Ejemplos — notebook — flujos.py

```python
import replica_inpc as rep

# historia completa de una vez
historico = rep.calcular_historia(canastas, series)

# calcula + variaciones directo
variaciones = rep.calcular_variacion(canastas, series, frecuencia="mensual")

# flujo completo con validación
rep.set_token("mi-token")
reporte = rep.verificar(canastas, series)
```

#### Ejemplos — CLI — flujos.py

```bash
replica-inpc calcular-historia --config historia.toml
replica-inpc verificar --config historia.toml
replica-inpc exportar --resultado resultado.csv --salida output.xlsx
```
