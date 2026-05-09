# Objetivo

el objetivo de este archivo es meter toda la informacion que no vaya en los documentos de las secciones dedicadas, al final este documento debe de redistriburi la informacion en sus repsectivas secciones y se eliminara

## Extraido de `dominio.md`

### Origen: `## Capa dominio/` -> `### Decisiones generales`

- `variaciones.py` e `incidencias.py` se mueven de `dominio/` raíz → `dominio/calculo/`

---

### Origen: `## Capa dominio/` -> `### Jerarquía de tipos — decisión v2`

```
Resultado  (base)
├── ResultadoIndice       ← renombrado desde ResultadoCalculo; input de variaciones/incidencias/validaciones
├── ResultadoVariacion    ← análisis; terminal
└── ResultadoIncidencia   ← análisis; terminal

ResultadoValidacion  (base)
├── ValidacionIndice      ← contiene ResultadoIndice
├── ValidacionVariacion   ← contiene ResultadoVariacion
└── ValidacionIncidencia  ← contiene ResultadoIncidencia
```

---

### Origen: `## Capa dominio/` -> `### Inventario de contratos v1 → v2`

| Contrato v1 | Destino v2 |
|---|---|
| `CanastaCanonica` | sin cambio |
| `SerieNormalizada` | sin cambio |
| `PeriodoQuincenal` / `PeriodoMensual` | sin cambio |
| `ResultadoCalculo` | → `ResultadoIndice` + base `Resultado` |
| `ResumenValidacion` | → `ResultadoIndice.resumen` (sin columnas INEGI) |
| `ReporteDetalladoValidacion` | → `ResultadoIndice.reporte` (sin columnas INEGI) |
| `DiagnosticoFaltantes` | → `ResultadoIndice.diagnostico` (sin cambio de esquema) |
| `CalculadorBase` / `LaspeyresDirecto` / `LaspeyresEncadenado` | sin cambio (internos) |
| `tipos.py` | sin cambio |
| `correspondencia.py` | sin cambio |
| `ResultadoVariacion` | sin cambio de clase; mueve a `dominio/calculo/`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionVariaciones` | **eliminado** |
| `ReporteValidacionVariaciones` | → `ValidacionVariacion.reporte` |
| `ResultadoIncidencia` | sin cambio de clase; mueve a `dominio/calculo/`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionIncidencias` | → `ValidacionIncidencia.resumen` |
| `ReporteValidacionIncidencias` | → `ValidacionIncidencia.reporte` |
| `validar_inpc.py` | sin cambio (interno — alimenta `ValidacionIndice`) |
| `validar_variaciones.py` | sin cambio (interno — alimenta `ValidacionVariacion`) |
| `validar_incidencias.py` | sin cambio (interno — alimenta `ValidacionIncidencia`) |

**Nuevos en v2:**
- `Resultado` (base abstracta)
- `ResultadoValidacion` (base) → `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- `ManifestUnidad` — dataclass embebida en `ResultadoIndice.manifiesto`
- `ManifestDerivado` — dataclass embebida en `ResultadoVariacion` / `ResultadoIncidencia`
- `DiagnosticoValidacion` — cobertura temporal de API INEGI (propuesto §12.14)

---

### Origen: `## Capa dominio/` -> `### Manifiesto por subtipo`

**`ResultadoIndice.manifiesto: list[ManifestUnidad]`** — combinable:

```python
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    periodo_base: PeriodoQuincenal | PeriodoMensual | None
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

Un elemento para canasta simple; `empalmar` concatena listas. `resumen` se recalcula desde df merged + manifiestos concatenados.

**`ResultadoVariacion.manifiesto` / `ResultadoIncidencia.manifiesto`: `ManifestDerivado`** — no combinable (terminales):

```python
@dataclass
class ManifestDerivado:
    id_corrida: list[str]   # hereda del ResultadoIndice origen
    tipo: str
    descripcion: str  # "mensual", "desde Ene 2015 hasta Dic 2024", etc.
    fecha: datetime
```

---

### Origen: `## Capa dominio/` -> `### Estructura de dominio.md`

```
## Contratos de datos
   Resultado (base)
   ResultadoIndice
   ResultadoVariacion
   ResultadoIncidencia
   ResultadoValidacion (base)
   ValidacionIndice
   ValidacionVariacion
   ValidacionIncidencia

## Funciones de dominio
   transformaciones de ResultadoIndice  (empalmar, rebasar, a_mensual)
   cálculo de variaciones               (variacion_periodica, etc.)
   cálculo de incidencias               (incidencia_periodica, etc.)
   validación interna                   (validar_inpc, validar_variaciones, validar_incidencias)
```

---

### Origen: `## Capa dominio/` -> `### Pendientes — próxima sesión`

- Esquemas nuevos de `ResultadoVariacion.resumen` / `.reporte` / `.diagnostico`
- Esquemas nuevos de `ResultadoIncidencia.resumen` / `.reporte` / `.diagnostico`
- Contratos completos: `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- Contrato de `empalmar`: compatibilidad `periodo_base=None` cross-version vs same-version
- `ResultadoVariacion` — ¿agregar `estado_calculo` en df para consistencia con `ResultadoIncidencia`?
- Actualizar `api.md`: parámetro `tipo` en `calcular_indice`; firmas completas de `api/incidencias.py`

---

### Origen: bloque previo a `## Semántica compartida` -> `### Contratos sin cambio`

Sin modificaciones en v2. Ver `docs/diseño.md` para esquema completo.

| Contrato | Archivo | Referencia |
|---|---|---|
| `CanastaCanonica` | `dominio/modelos/canasta.py` | diseño.md §5.1 |
| `SerieNormalizada` | `dominio/modelos/serie.py` | diseño.md §5.2 |
| `PeriodoQuincenal`, `PeriodoMensual`, `periodo_desde_str` | `dominio/periodos.py` | diseño.md §5.3 |
| `VersionCanasta`, `INDICE_POR_TIPO`, `RANGOS_VALIDOS` | `dominio/tipos.py` | diseño.md §5.9 |
| `CalculadorBase` (interfaz interna) | `dominio/calculo/` | diseño.md §5.8 |

---

### Origen: `## Contratos de datos`

### ResultadoIndice — MODIFICADO

Renombrado desde `ResultadoCalculo`. Hereda de `Resultado`.

**Constructor:**

```python
def __init__(
    self,
    df: pd.DataFrame,
    manifiesto: list[ManifestUnidad],
    reporte_df: pd.DataFrame,
    diagnostico_df: pd.DataFrame,
    periodo_base: PeriodoQuincenal | None = None,
) -> None:
```

**Decisión:** `reporte_df` y `diagnostico_df` se pasan al constructor porque no pueden derivarse del `df` después del cálculo — el calculador conoce la cobertura de genéricos y los faltantes en el momento de calcular. `.reporte` y `.diagnostico` los almacenan y devuelven directamente.

**Decisión:** sin property `.id_corrida` — acceso solo vía `.manifiesto[0].id_corrida`. Para resultado empalmado no existe un único `id_corrida`.

**`ManifestUnidad` (dataclass embebida):**

```python
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    periodo_base: PeriodoQuincenal | PeriodoMensual | None
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

---

**`.df`** — heredado de `Resultado`

`self._df_completo[["indice_replicado"]]` derivado en el constructor. MultiIndex `(periodo, indice)`, columna `indice_replicado`.

---

**`.resultado`** — override de `Resultado`

Devuelve `Vista(self._df_completo, columna="indice_replicado")`.

- **`.resultado.largo`** — df completo con metadata:

  Índice: MultiIndex `(periodo, indice)`

  | columna | tipo | notas |
  |---|---|---|
  | `version` | int | versión de canasta |
  | `tipo` | str | `"inpc"`, `"inflacion componente"`, etc. |
  | `indice_replicado` | float/NaN | NaN cuando `estado_calculo` es `sin_datos` o `fallida` |
  | `estado_calculo` | str | `ok`, `parcial`, `sin_datos`, `fallida` |
  | `motivo_error` | str/NaN | NaN cuando `ok`/`parcial` |

  **`estado_calculo` catálogo:**

  | valor | significado |
  |---|---|
  | `ok` | cálculo completo con datos definitivos |
  | `parcial` | mes calculado con solo 1 quincena. Solo producido por `a_mensual()` |
  | `sin_datos` | algún genérico tiene NaN en el periodo. Renombrado desde `null_por_faltantes` v1 |
  | `fallida` | fallo en el cálculo |

- **`.resultado.ancho`** — `indice_replicado` pivoteado: índices como filas, periodos como columnas. Mismos datos que `.df`, formato ancho.

---

**`.manifiesto` y `.periodo_base`**

- `.manifiesto: list[ManifestUnidad]` — un elemento por canasta; `empalmar` concatena listas
- `.periodo_base: PeriodoQuincenal | PeriodoMensual | None` — propiedad derivada del manifiesto:
  - un único valor distinto en todos los `ManifestUnidad` → devuelve ese valor
  - `None` en cualquier entrada, o valores mixtos → devuelve `None`
- `rebasar()` setea `ManifestUnidad.periodo_base` en cada entrada del manifiesto; no es atributo suelto

---

**`.resumen`**

Calculado desde `self._df_completo` + `self._manifiesto`. No se almacena.

Índice: `id_corrida` (una fila por `ManifestUnidad`)

| columna | tipo |
|---|---|
| `version` | int |
| `tipo` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal\|PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal\|PeriodoMensual` |

**`estado_calculo` en resumen:**

| valor | condición |
|---|---|
| `ok` | todos los periodos `ok` |
| `con_advertencias` | al menos un periodo `sin_datos`, ninguno `fallida` |
| `fallida` | al menos un periodo `fallida` |

---

**`.reporte`** — devuelve `pd.DataFrame`

Índice: MultiIndex `(periodo, indice)`

| columna | tipo |
|---|---|
| `version` | int |
| `estado_calculo` | str |
| `motivo_error` | str/NaN |
| `genericos_esperados` | int |
| `genericos_con_indice` | int |
| `genericos_sin_indice` | int |
| `cobertura_genericos_pct` | float |
| `ponderador_esperado` | float |
| `ponderador_cubierto` | float |

---

**`.diagnostico`** — devuelve `pd.DataFrame` plano

Mismo schema que `DiagnosticoFaltantes` v1. Concatenable con `pd.concat`.

Índice: entero

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `version` | int |
| `tipo` | str |
| `periodo` | PeriodoQuincenal/NaN |
| `generico` | str |
| `nivel_faltante` | str (`periodo`, `estructural`) |
| `tipo_faltante` | str (`indice`, `ponderador`, `indice_imputado`) |
| `detalle` | str |

---

### ResultadoVariacion — MODIFICADO

Hereda de `Resultado`. Mueve de `dominio/modelos/variacion.py` a `dominio/calculo/variacion.py`.

**Cambios respecto a v1:**

- Hereda de `Resultado` (agrega `.pipe()`, `.resumen`, `.reporte`, `.diagnostico`)
- Agrega `.manifiesto: ManifestDerivado`
- Columna `variacion` → `variacion_pp` (almacenada en pp, no fracción)
- `estado_calculo` en df: `ok`, `parcial` — NaN excluidos del largo
- `periodos_semiok` eliminado — reemplazado por `estado_calculo = "parcial"`
- `indices_parciales` rediseñado — ver abajo

**`ManifestDerivado` (dataclass embebida, compartida con `ResultadoIncidencia`):**

```python
@dataclass
class ManifestDerivado:
    id_corridas: list[str]  # uno por ManifestUnidad del ResultadoIndice fuente
    tipo: str
    descripcion: str  # "mensual", "desde Ene 2015 hasta Dic 2024", etc.
    fecha: datetime
```

**Propiedades sin cambio:** `.tipo`, `.descripcion`, `.clase_variacion`.

> **Sin `empalmar`:** siempre se empalma el `ResultadoIndice` fuente antes de calcular variaciones. Variaciones de canastas con distintas escalas no son directamente concatenables.

---

**Constructor:**

```python
def __init__(
    self,
    df: pd.DataFrame,
    manifiesto: ManifestDerivado,
    reporte_df: pd.DataFrame,
    diagnostico_df: pd.DataFrame,
    indices_parciales: pd.DataFrame | None = None,
) -> None:
```

Valida antes de `super().__init__(df[["variacion_pp"]])`:

- `df` no vacío
- `df` tiene MultiIndex `(periodo, indice)`
- `df` tiene columnas `tipo`, `clase_variacion`, `variacion_pp`, `estado_calculo`
- `clase_variacion` homogéneo — un único valor en toda la columna
- `clase_variacion` ∈ `{"periodica", "acumulada_anual", "desde"}` → `InvarianteViolado` si no
- `estado_calculo` solo `ok` o `parcial` → `InvarianteViolado` si contiene `sin_datos`/`fallida`
- `variacion_pp` sin NaN → `InvarianteViolado` si no
- `manifiesto.id_corridas`, `.tipo`, `.descripcion` no vacíos → `InvarianteViolado` si no
- `manifiesto.tipo == df["tipo"].iloc[0]` — consistencia → `InvarianteViolado` si no
- `indices_parciales` solo cuando `clase_variacion == "desde"` → `InvarianteViolado` si no

---

**`.df`** — heredado de `Resultado`

`self._df_completo[["variacion_pp"]]`. MultiIndex `(periodo, indice)`, columna `variacion_pp`. Solo filas computables.

---

**`.resultado`** — override de `Resultado`

Devuelve `Vista(self._df_completo, columna="variacion_pp")`.

`_df_completo` contiene solo las combinaciones `(periodo, indice)` donde la variacion fue computable. Periodos fuente con `sin_datos` o `fallida` en `ResultadoIndice` resultan en filas **ausentes** — no NaN en `_df_completo`. Aparecen como NaN implícito en `.resultado.ancho` y son capturados en `.reporte`.

- **`.resultado.largo`** — solo filas computables:

  Índice: MultiIndex `(periodo, indice)`

  | columna | tipo | notas |
  |---|---|---|
  | `tipo` | str | tipo de índice |
  | `clase_variacion` | str | `periodica`, `acumulada_anual`, `desde` |
  | `variacion_pp` | float | siempre válido |
  | `estado_calculo` | str | `ok`, `parcial` |
  | `version_t` | int | versión de canasta del periodo `t` |

  **`estado_calculo` catálogo:**

  | valor | significado |
  |---|---|
  | `ok` | cálculo completo con datos definitivos |
  | `parcial` | uno o ambos periodos fuente tenían solo 1 quincena disponible |

- **`.resultado.ancho`** — `variacion_pp` pivoteado: índices como filas, periodos como columnas. NaN implícito para combinaciones ausentes.

---

**`.indices_parciales`** — atributo exclusivo de `variacion_desde`

`pd.DataFrame | None`. `None` cuando `clase_variacion != "desde"` o no hay ajustes.

Registra índices cuya cobertura real no abarca el rango `[desde, hasta]` completo solicitado:

Índice: `indice` (str)

| columna | tipo | notas |
|---|---|---|
| `periodo_desde_real` | `PeriodoQuincenal\|PeriodoMensual` | base real usada (≠ `desde` solicitado) |
| `periodo_hasta_real` | `PeriodoQuincenal\|PeriodoMensual` | cierre real usado (≠ `hasta` solicitado) |

Solo aparecen índices con al menos un extremo ajustado. Motivación: `variacion_pp` es escalar — el rango real quedaría oculto sin este atributo.

---

**`.diagnostico`** — devuelve `pd.DataFrame` plano

Lista accionable de combinaciones `(periodo, indice)` no computables. Subconjunto de `.reporte` donde `estado_calculo` es `sin_datos` o `fallida`. Concatenable con `pd.concat`.

Índice: entero

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `tipo` | str |
| `clase_variacion` | str |
| `periodo` | `PeriodoQuincenal\|PeriodoMensual` |
| `indice` | str |
| `estado_calculo` | str — `sin_datos`, `fallida` |
| `motivo_error` | str |
| `periodo_lag` | `PeriodoQuincenal\|PeriodoMensual`/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |

---

**`.reporte`** — devuelve `pd.DataFrame`

Cubre todas las combinaciones `(periodo, indice)` esperadas, incluyendo no computables.

Índice: MultiIndex `(periodo, indice)`

| columna | tipo | notas |
|---|---|---|
| `estado_calculo` | str | `ok`, `parcial`, `sin_datos`, `fallida` |
| `motivo_error` | str/NaN | NaN cuando `ok`/`parcial` |
| `periodo_lag` | `PeriodoQuincenal\|PeriodoMensual`/NaN | t-1, Dic año anterior, o `desde`; NaN cuando no computable |
| `indice_t` | float/NaN | `indice_replicado` en periodo `t` |
| `indice_lag` | float/NaN | `indice_replicado` en periodo `lag` |
| `version_t` | int/NaN | versión de canasta del periodo `t` |
| `version_lag` | int/NaN | versión de canasta del periodo `lag` |
| `cobertura_pct_t` | float/NaN | cobertura de genéricos del índice fuente en periodo `t` (de `ResultadoIndice.reporte`) |
| `cobertura_pct_lag` | float/NaN | cobertura de genéricos del índice fuente en periodo `lag` (de `ResultadoIndice.reporte`) |

**`estado_calculo` en reporte:**

| valor | condición |
|---|---|
| `ok` | variacion computable, fuente con datos definitivos |
| `parcial` | variacion computable, ≥1 periodo fuente era `parcial` |
| `sin_datos` | fuente tenía `sin_datos` en `t` o en `lag` |
| `fallida` | fuente tenía `fallida` o error interno en cálculo |

---

**`.resumen`** — devuelve `pd.DataFrame`

Calculado desde `_df_completo` + `manifiesto`. No se almacena.

Índice: `id_corrida` (una fila — un solo `ManifestDerivado`)

| columna | tipo |
|---|---|
| `tipo` | str |
| `clase_variacion` | str |
| `descripcion` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal\|PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal\|PeriodoMensual` |

**`estado_calculo` en resumen:**

| valor | condición |
|---|---|
| `ok` | todos los periodos computados y `ok` |
| `con_advertencias` | ≥1 `parcial` o ≥1 periodo ausente por fuente con `sin_datos` |
| `fallida` | ≥1 error interno en cálculo de variacion |

---

### ResultadoIncidencia — MODIFICADO

Hereda de `Resultado`. Mueve de `dominio/modelos/incidencia.py` a `dominio/calculo/incidencia.py`.

**Cambios respecto a v1:**

- Hereda de `Resultado` (agrega `.pipe()`, `.resumen`, `.reporte`, `.diagnostico`)
- Agrega `.manifiesto: ManifestDerivado` (misma dataclass que `ResultadoVariacion`)
- `periodos_semiok` eliminado — reemplazado por `estado_calculo = "parcial"` (consistente con `ResultadoVariacion`)
- `indices_parciales` agregado — exclusivo de `incidencia_desde`

**Propiedades sin cambio:** `.tipo`, `.frecuencia`, `.clase_incidencia`.

**`ManifestDerivado`:** misma dataclass que `ResultadoVariacion` — ver definición allí.

> **Sin `empalmar`:** siempre se empalma el `ResultadoIndice` fuente antes de calcular incidencias.

---

**Constructor:**

```python
def __init__(
    self,
    df: pd.DataFrame,
    manifiesto: ManifestDerivado,
    reporte_df: pd.DataFrame,
    diagnostico_df: pd.DataFrame,
    indices_parciales: pd.DataFrame | None = None,
) -> None:
```

Valida antes de `super().__init__(df[["incidencia_pp"]])`:

- `df` no vacío
- `df` tiene MultiIndex `(periodo, indice)`
- `df` tiene columnas `tipo`, `clase_incidencia`, `incidencia_pp`, `estado_calculo`
- `clase_incidencia` homogéneo — un único valor en toda la columna
- `clase_incidencia` ∈ `{"periodica", "acumulada_anual", "desde"}` → `InvarianteViolado` si no
- `estado_calculo` solo `ok` o `parcial` → `InvarianteViolado` si contiene `sin_datos`/`fallida`
- `incidencia_pp` sin NaN → `InvarianteViolado` si no
- `manifiesto.id_corridas`, `.tipo`, `.descripcion` no vacíos → `InvarianteViolado` si no
- `manifiesto.tipo == df["tipo"].iloc[0]` — consistencia → `InvarianteViolado` si no
- `indices_parciales` solo cuando `clase_incidencia == "desde"` → `InvarianteViolado` si no

---

**`.df`** — heredado de `Resultado`

`self._df_completo[["incidencia_pp"]]`. MultiIndex `(periodo, indice)`, columna `incidencia_pp`. Solo filas computables.

---

**`.resultado`** — override de `Resultado`

Devuelve `Vista(self._df_completo, columna="incidencia_pp")`.

`_df_completo` contiene solo las combinaciones `(periodo, indice)` donde la incidencia fue computable. Periodos fuente con `sin_datos` o `fallida` en `ResultadoIndice` resultan en filas **ausentes** — no NaN en `_df_completo`. Aparecen como NaN implícito en `.resultado.ancho` y son capturados en `.reporte`.

- **`.resultado.largo`** — solo filas computables:

  Índice: MultiIndex `(periodo, indice)`

  | columna | tipo | notas |
  |---|---|---|
  | `tipo` | str | tipo de índice: `"inpc"`, `"inflacion componente"`, etc. |
  | `clase_incidencia` | str | `periodica`, `acumulada_anual`, `desde` |
  | `incidencia_pp` | float | siempre válido |
  | `estado_calculo` | str | `ok`, `parcial` |
  | `version_t` | int | versión de canasta del periodo `t` |

  **`estado_calculo` catálogo:**

  | valor | significado |
  |---|---|
  | `ok` | cálculo completo con datos definitivos |
  | `parcial` | uno o ambos periodos fuente tenían solo 1 quincena disponible |

- **`.resultado.ancho`** — `incidencia_pp` pivoteado: índices como filas, periodos como columnas. NaN implícito para combinaciones ausentes.

---

**`.indices_parciales`** — atributo exclusivo de `incidencia_desde`

`pd.DataFrame | None`. `None` cuando `clase_incidencia != "desde"` o no hay ajustes.

Registra índices cuya cobertura real no abarca el rango `[desde, hasta]` completo solicitado:

Índice: `indice` (str)

| columna | tipo | notas |
|---|---|---|
| `periodo_desde_real` | `PeriodoQuincenal\|PeriodoMensual` | base real usada (≠ `desde` solicitado) |
| `periodo_hasta_real` | `PeriodoQuincenal\|PeriodoMensual` | cierre real usado (≠ `hasta` solicitado) |

Solo aparecen índices con al menos un extremo ajustado. Motivación: `incidencia_pp` es escalar — el rango real quedaría oculto sin este atributo.

---

**`.resumen`** — devuelve `pd.DataFrame`

Calculado desde `_df_completo` + `manifiesto`. No se almacena.

Índice: `id_corrida` (una fila — un solo `ManifestDerivado`)

| columna | tipo |
|---|---|
| `tipo` | str |
| `clase_incidencia` | str |
| `descripcion` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal\|PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal\|PeriodoMensual` |

**`estado_calculo` en resumen:**

| valor | condición |
|---|---|
| `ok` | todos los periodos computados y `ok` |
| `con_advertencias` | ≥1 `parcial` o ≥1 periodo ausente por fuente con `sin_datos` |
| `fallida` | ≥1 error interno en cálculo de incidencia |

---

**`.reporte`** — devuelve `pd.DataFrame`

Cubre todas las combinaciones `(periodo, indice)` esperadas, incluyendo no computables.

Índice: MultiIndex `(periodo, indice)`

| columna | tipo | notas |
|---|---|---|
| `estado_calculo` | str | `ok`, `parcial`, `sin_datos`, `fallida` |
| `motivo_error` | str/NaN | NaN cuando `ok`/`parcial` |
| `periodo_lag` | `PeriodoQuincenal\|PeriodoMensual`/NaN | t-1, Dic año anterior, o `desde`; NaN cuando no computable |
| `indice_t` | float/NaN | `indice_replicado` de la clasificación en periodo `t` |
| `indice_lag` | float/NaN | `indice_replicado` de la clasificación en periodo `lag` |
| `ponderador_t` | float/NaN | ponderador de la clasificación en canasta versión `t` |
| `ponderador_lag` | float/NaN | ponderador de la clasificación en canasta versión `lag` |
| `version_t` | int/NaN | versión de canasta del periodo `t` |
| `version_lag` | int/NaN | versión de canasta del periodo `lag` |
| `cobertura_pct_t` | float/NaN | cobertura de genéricos del índice fuente en periodo `t` (de `ResultadoIndice.reporte`) |
| `cobertura_pct_lag` | float/NaN | cobertura de genéricos del índice fuente en periodo `lag` (de `ResultadoIndice.reporte`) |

**`estado_calculo` en reporte:**

| valor | condición |
|---|---|
| `ok` | incidencia computable, fuente con datos definitivos |
| `parcial` | incidencia computable, ≥1 periodo fuente era `parcial` |
| `sin_datos` | fuente tenía `sin_datos` en `t` o en `lag` |
| `fallida` | fuente tenía `fallida` o error interno en cálculo |

---

**`.diagnostico`** — devuelve `pd.DataFrame` plano

Lista accionable de combinaciones `(periodo, indice)` no computables. Subconjunto de `.reporte` donde `estado_calculo` es `sin_datos` o `fallida`. Concatenable con `pd.concat`.

Índice: entero

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `tipo` | str |
| `clase_incidencia` | str |
| `periodo` | `PeriodoQuincenal\|PeriodoMensual` |
| `indice` | str |
| `estado_calculo` | str — `sin_datos`, `fallida` |
| `motivo_error` | str |
| `periodo_lag` | `PeriodoQuincenal\|PeriodoMensual`/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |

---

### Validacion (base) — NUEVO

Clase base abstracta compartida por `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia`. Análoga a `Resultado` pero para comparaciones contra INEGI.

**Interfaz:**

- `.calculo` — abstracto; referencia al `ResultadoX` validado (retorno covariante en cada subclase)
- `.df` — escape hatch
- `.pipe(fn, *args, **kwargs)`
- `_repr_html_`
- `.como_tabla(ancho: bool = False)`
- `.resumen` — abstracto; estadísticas agregadas de la comparación
- `.reporte` — abstracto; comparación detallada periodo × índice
- `.diagnostico` — abstracto; periodos no verificables por ausencia de datos en API INEGI

---

### ValidacionIndice — NUEVO

Hereda de `Validacion`. Compara un `ResultadoIndice` contra series publicadas por INEGI.

- `.calculo: ResultadoIndice`
- `.resumen`, `.reporte`, `.diagnostico` — esquemas pendiente de definir

---

### ValidacionVariacion — NUEVO

Hereda de `Validacion`. Compara un `ResultadoVariacion` contra series publicadas por INEGI.

- `.calculo: ResultadoVariacion`
- `.resumen`, `.reporte`, `.diagnostico` — esquemas pendiente de definir

---

### ValidacionIncidencia — NUEVO

Hereda de `Validacion`. Compara un `ResultadoIncidencia` contra series publicadas por INEGI.

- `.calculo: ResultadoIncidencia`
- `.resumen`, `.reporte`, `.diagnostico` — esquemas pendiente de definir

---
