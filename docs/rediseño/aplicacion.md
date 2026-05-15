# Rediseño aplicacion/

## Alcance

- Cubre: puertos (`Protocol`) y casos de uso de `aplicacion/`.
- Excluye: adaptadores concretos (`infraestructura/`), firmas públicas de `api/` (ver `api.md`), contratos de dominio (ver `dominio.md`).
- Fuente de verdad: este archivo para contratos de puertos y casos de uso.

## Decisiones generales

- Coupling vive solo en `api/` — dominio y casos de uso reciben puertos, nunca adaptadores concretos.
- `api/` crea los adaptadores e inyecta al caso de uso o pasa al dominio.
- Sin casos de uso para funciones manuales (`cargar_*`, `validar_*`) — `api/` orquesta directamente.
- `EjecutarCorrida` eliminado — reemplazado por `CalcularHistoria` + `api/flujos.py`.
- Puertos eliminados vs v1: `AlmacenArtefactos`, `EscritorResultados`, `RepositorioCorridas`.

## Estructura de archivos

| archivo v1 | v2 | notas |
|---|---|---|
| `puertos/lector_canasta.py` | sin cambio | — |
| `puertos/lector_series.py` | sin cambio | — |
| `puertos/fuente_validacion.py` | modificado | agrega `obtener_variaciones` y `obtener_incidencias` |
| `puertos/almacen_artefactos.py` | **eliminado** | solo lo usaba `EjecutarCorrida` |
| `puertos/escritor_resultados.py` | **eliminado** | tipos v1 eliminados |
| `puertos/repositorio_corridas.py` | **eliminado** | `ManifestCorrida` eliminado en v2 |
| `casos_uso/ejecutar_corrida.py` | **eliminado** | reemplazado por `CalcularHistoria` |
| `casos_uso/calcular_historia.py` | **nuevo** | orquesta carga + cálculo + empalme + rebase |

---

## Puertos

### LectorCanasta — SIN CAMBIO — CERRADO

#### Responsabilidad

Carga un archivo CSV de canasta y devuelve una `CanastaCanonica` validada.

#### Protocolo

```python
class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

#### Métodos

##### `leer`

| parámetro | tipo | contrato |
|---|---|---|
| `ruta` | `Path` | ruta al archivo CSV; existencia no garantizada por el puerto |
| `version` | `VersionCanasta` | versión de canasta; requerida para validar e interpretar el CSV |

| aspecto | contrato |
|---|---|
| retorno | `CanastaCanonica` — índice = `generico`; columnas `ponderador` y `encadenamiento` como `str` |

| condición | lanza |
|---|---|
| `ruta` no existe | `ArchivoNoEncontrado` |
| archivo vacío | `ArchivoVacio` |
| CSV no parseable | `ArchivoCorrupto` |
| columnas requeridas ausentes | `ColumnasMinFaltantes` |
| `version` inválida | `InvarianteViolado` |

#### Invariantes del implementador

- `version` explícita siempre — sin auto-detect; canastas 2010 y 2013 tienen genéricos idénticos

#### Usado por

- `CalcularHistoria` — para cargar cada canasta de la lista de insumos

#### Implementado por

- `infraestructura/csv/lector_canasta_csv.py` — `LectorCanastaCsv`

---

### LectorSeries — SIN CAMBIO — CERRADO

#### Responsabilidad

Carga un archivo CSV de series de genéricos y devuelve una `SerieNormalizada`.

#### Protocolo

```python
class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

#### Métodos

##### `leer`

| parámetro | tipo | contrato |
|---|---|---|
| `ruta` | `Path` | ruta al archivo CSV; existencia no garantizada por el puerto |

| aspecto | contrato |
|---|---|
| retorno | `SerieNormalizada` — índice = `generico_limpio`; columnas = `PeriodoQuincenal` |

| condición | lanza |
|---|---|
| `ruta` no existe | `ArchivoNoEncontrado` |
| archivo vacío | `ArchivoVacio` |
| CSV no parseable | `ArchivoCorrupto` |
| orientación de columnas no detectable | `OrientacionNoDetectable` |
| ninguna fila útil tras normalización | `SerieVacia` |

#### Invariantes del implementador

- siempre quincenal — datos mensuales se obtienen vía `a_mensual(resultado)`, nunca cargando CSV mensuales
- soporta formato BIE jerárquico (2010/2013) y formato estándar (2018/2024)
- `version` no es parámetro — el filtrado por rango válido de periodos lo hace `CalcularHistoria`

#### Usado por

- `CalcularHistoria` — para cargar cada serie de la lista de insumos

#### Implementado por

- `infraestructura/csv/lector_series_csv.py` — `LectorSeriesCsv`

---

### FuenteValidacion — MODIFICADO — CERRADO

#### Responsabilidad

Obtiene series publicadas por INEGI para tres tipos de dato distintos: niveles de índice, variaciones y incidencias.

#### Protocolo

```python
class FuenteValidacion(Protocol):
    def obtener_indices(
        self,
        periodos: list[PeriodoQuincenal | PeriodoMensual],
    ) -> dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]: ...

    def obtener_variaciones(
        self,
        periodos: list[PeriodoQuincenal | PeriodoMensual],
        tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    ) -> dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]: ...

    def obtener_incidencias(
        self,
        periodos: list[PeriodoMensual],
        tipo_incidencia: Literal["periodica"],
    ) -> dict[str, dict[PeriodoMensual, float | None]]: ...
```

> **Modificación vs v1:** v1 solo declaraba `obtener`. v2 agrega `obtener_variaciones` y `obtener_incidencias` para soportar `dominio/validacion/variaciones.py` y `dominio/validacion/incidencias.py`.

#### Esquema de retorno compartido

Todos los métodos devuelven `dict[str, dict[Periodo, float | None]]`:

| nivel | clave | significado |
|---|---|---|
| exterior | nombre del índice | ej. `"INPC"`, `"subyacente"`, `"mercancias"` |
| interior | `Periodo` | el periodo consultado |
| interior valor | `float` | valor publicado por INEGI |
| interior valor | `None` | INEGI tiene el periodo en rango pero sin dato (`no_disponible`) |
| interior ausente | — | periodo antes del inicio del histórico INEGI (`fuera_rango_inegi`) |

#### Tipos válidos por método

| tipo (`str`) | `obtener_indices` | `obtener_variaciones` | `obtener_incidencias` |
|---|---|---|---|
| `"inpc"` | ✓ | ✓ | ✓ |
| `"inflacion componente"` | ✓ | ✓ | ✓ |
| `"inflacion subcomponente"` | ✓ | ✓ | ✓ |

El `tipo` se fija en el constructor del implementador, no en el método.

#### Métodos

##### `obtener_indices`

Niveles de índice publicados por INEGI (series BIE de nivel).

| parámetro | tipo | contrato |
|---|---|---|
| `periodos` | `list[PeriodoQuincenal \| PeriodoMensual]` | lista homogénea; detección de frecuencia por `type(periodos[0])` |

**Frecuencias soportadas:** quincenal y mensual.

**Claves de retorno por tipo:**

| tipo | claves del dict exterior |
|---|---|
| `"inpc"` | `"INPC"` |
| `"inflacion componente"` | `"subyacente"`, `"no subyacente"` |
| `"inflacion subcomponente"` | `"mercancias"`, `"servicios"`, `"agropecuarios"`, `"energeticos y tarifas autorizadas por el gobierno"` |

| condición | lanza |
|---|---|
| `len(periodos) == 0` | `InvarianteViolado` |
| `tipo` sin indicador INEGI disponible | `ErrorConfiguracion` |
| API no responde / HTTP error | `FuenteNoDisponible` |
| respuesta INEGI con formato inesperado | `RespuestaInvalida` |

##### `obtener_variaciones`

Series de variación publicadas por INEGI.

| parámetro | tipo | contrato |
|---|---|---|
| `periodos` | `list[PeriodoQuincenal \| PeriodoMensual]` | lista homogénea; detección de frecuencia por `type(periodos[0])` |
| `tipo_variacion` | `Literal["periodica", "interanual", "acumulada_anual"]` | clase de variación |

**Frecuencias soportadas:** quincenal y mensual para los tres `tipo_variacion`.

**Claves de retorno:** mismas que `obtener_indices` según `tipo`.

| condición | lanza |
|---|---|
| `len(periodos) == 0` | `InvarianteViolado` |
| `tipo_variacion` inválido | `ErrorConfiguracion` |
| `tipo` sin indicadores de variación para `tipo_variacion` | `ErrorConfiguracion` |
| API no responde / HTTP error | `FuenteNoDisponible` |
| respuesta INEGI con formato inesperado | `RespuestaInvalida` |

##### `obtener_incidencias`

Series de incidencia publicadas por INEGI.

| parámetro | tipo | contrato |
|---|---|---|
| `periodos` | `list[PeriodoMensual]` | solo mensuales — INEGI no publica incidencias quincenales |
| `tipo_incidencia` | `Literal["periodica"]` | único tipo publicado por INEGI |

**Frecuencias soportadas:** solo mensual.

**Claves de retorno:** mismas que `obtener_indices` según `tipo`.

| condición | lanza |
|---|---|
| `len(periodos) == 0` | `InvarianteViolado` |
| `tipo_incidencia` inválido | `ErrorConfiguracion` |
| `tipo` sin indicadores de incidencia | `ErrorConfiguracion` |
| API no responde / HTTP error | `FuenteNoDisponible` |
| respuesta INEGI con formato inesperado | `RespuestaInvalida` |

#### Invariantes del implementador

- cache de clase compartido entre instancias — primera llamada descarga histórico completo; siguientes reutilizan sin requests adicionales
- detección de frecuencia (quincenal vs mensual) por `type(periodos[0])`; lista vacía → comportamiento indefinido
- `tipo` fijo en constructor; no cambia entre llamadas

#### Mapeo desde contratos de dominio

Puente entre los valores de `clase_variacion`/`clase_incidencia` del dominio y los parámetros del puerto. Usado por `dominio/validacion/` para traducir antes de llamar al puerto.

**`obtener_variaciones` — mapeo de `clase_variacion` a `tipo_variacion`:**

| `clase_variacion` | `tipo_variacion` | notas |
|---|---|---|
| `"periodica_quincenal"` | `"periodica"` | `periodos` son `PeriodoQuincenal` |
| `"periodica_mensual"` | `"periodica"` | `periodos` son `PeriodoMensual` |
| `"periodica_bimestral"`, `"periodica_trimestral"`, `"periodica_cuatrimestral"`, `"periodica_semestral"` | — | INEGI no publica → `ErrorConfiguracion` |
| `"periodica_anual"` | `"interanual"` | — |
| `"acumulada_anual"` | `"acumulada_anual"` | — |
| `"desde"` | — | no comparable → `ErrorConfiguracion` |

**`obtener_incidencias` — mapeo de `clase_incidencia` a `tipo_incidencia`:**

| `clase_incidencia` | `tipo_incidencia` | notas |
|---|---|---|
| `"periodica_mensual"` | `"periodica"` | único caso comparable; `periodos` son `PeriodoMensual` |
| cualquier otro valor | — | INEGI no publica → `ErrorConfiguracion` |

---

#### Usado por

- `dominio/validacion/indices.py` — llama `fuente.obtener_indices`
- `dominio/validacion/variaciones.py` — llama `fuente.obtener_variaciones`
- `dominio/validacion/incidencias.py` — llama `fuente.obtener_incidencias`
- `api/validaciones.py` — crea `FuenteValidacionApi(token, tipo)` e inyecta al dominio

#### Implementado por

- `infraestructura/inegi/fuente_validacion_api.py` — `FuenteValidacionApi`

---

## Casos de uso

### CalcularHistoria — NUEVO — CERRADO

#### Responsabilidad

Orquesta carga, cálculo, empalme, rebase y conversión de frecuencia para producir un `ResultadoIndice` histórico a partir de una lista de insumos por versión de canasta.

#### Constructor

```python
class CalcularHistoria:
    def __init__(
        self,
        lector_canasta: LectorCanasta,
        lector_series: LectorSeries,
    ) -> None:
```

| parámetro | tipo | contrato |
|---|---|---|
| `lector_canasta` | `LectorCanasta` | adaptador para cargar canastas |
| `lector_series` | `LectorSeries` | adaptador para cargar series |

#### `ejecutar`

```python
def ejecutar(
    self,
    insumos: list[tuple[VersionCanasta, Path, Path]],
    tipo: str,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual,
    periodicidad: Literal["quincenal", "mensual"],
) -> ResultadoIndice:
```

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `insumos` | `list[tuple[VersionCanasta, Path, Path]]` | orden cronológico; cada elemento = `(version, ruta_canasta, ruta_series)`; mínimo 1; sin versiones duplicadas |
| `tipo` | `str` | tipo de índice a calcular; debe existir en todas las canastas |
| `periodo_referencia` | `PeriodoQuincenal \| PeriodoMensual` | periodo para `rebasar`; debe existir en el resultado empalmado |
| `periodicidad` | `Literal["quincenal", "mensual"]` | frecuencia del resultado final |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | resultado empalmado, rebased, en `periodicidad` indicada; `.periodo_referencia` seteado |

##### Orquestación interna

Pasos en orden; el llamador no tiene acceso a resultados intermedios:

1. Por cada `(version, ruta_canasta, ruta_series)` en `insumos`: `lector_canasta.leer` + `lector_series.leer`
2. `calcular_indice` por versión con encadenamiento automático entre versiones consecutivas
3. Si `len(insumos) > 1`: `empalmar` por pares vecinos (fold-left), `version_nombres` de la versión más reciente de cada par
4. Si `periodicidad="mensual"`: `a_mensual`
5. `rebasar` al `periodo_referencia` — sobre el resultado ya en la periodicidad final

> **Orden `a_mensual` → `rebasar`:** `a_mensual` devuelve `periodo_referencia=None`; si se rebaseara antes, la conversión a mensual anularía el rebase. Además, con `periodicidad="mensual"` el `periodo_referencia` es `PeriodoMensual` y `rebasar` requiere que exista en el resultado, lo que solo ocurre tras `a_mensual`.

##### Errores

| condición | lanza |
|---|---|
| `insumos` vacío | `InvarianteViolado` |
| versión duplicada en `insumos` | `InvarianteViolado` |
| versión encadenada sin su versión base en `insumos` | `InvarianteViolado` |
| `tipo` no presente en alguna canasta | `InvarianteViolado` |
| `periodo_referencia` no existe en resultado empalmado | `InvarianteViolado` |
| error de IO en carga | propaga errores de `LectorCanasta` / `LectorSeries` |

#### Usado por

- `api/flujos.py` — `calcular_historia` crea `CalcularHistoria(LectorCanastaCsv(), LectorSeriesCsv())` y llama `ejecutar`

---

## Decisiones

### §D1. Eliminación de puertos de persistencia

PENDIENTE: documentar por qué `AlmacenArtefactos`, `EscritorResultados` y `RepositorioCorridas` se eliminan en v2. En resumen: `EjecutarCorrida` era el único consumidor y se reemplaza por `calcular_historia`; la persistencia de artefactos es responsabilidad del notebook o del usuario, no del sistema.

### §D2. `FuenteValidacion` con tres métodos en lugar de uno

PENDIENTE: documentar por qué el puerto expone `obtener_indices`, `obtener_variaciones` y `obtener_incidencias` por separado en lugar de un método genérico unificado.
