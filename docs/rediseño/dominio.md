# Rediseño dominio/

## Capa dominio/

### Decisiones generales

- Dominio puro: sin IO, sin dependencias externas, sin strings de periodos (recibe solo `Periodo*`)
- `ResultadoCalculo` **eliminado** — renombrado a `ResultadoIndice` (breaking change v2)
- `ResultadoIndice` **no** embebe canasta — canasta es parámetro explícito donde se requiere
- `ResultadoIndice` agrega atributo `periodo_base: PeriodoQuincenal | None` — `None` = escala nativa de la canasta; set por `rebasar()`
- `empalmar` verifica `periodo_base` compatible entre inputs y propaga reporte/diagnostico/resumen (merge automático)
- `ResumenValidacionVariaciones` eliminado — dead code desde v1.2.4; absorbido por `ValidacionVariacion`
- `variaciones.py` e `incidencias.py` se mueven de `dominio/` raíz → `dominio/calculo/`
- Invariantes siguen lanzando `InvarianteViolado`, nunca `ValueError`

### Jerarquía de tipos — decisión v2

Dos jerarquías paralelas, independientes:

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

`ValidacionX` **contiene** un `ResultadoX` vía composición — no hereda de `Resultado`.

**`Resultado` (base)** — mínimo compartido con semántica real:
- `.df` — DataFrame interno; escape hatch para análisis externos (scipy, networkx, etc.)
- `.pipe(fn, *args, **kwargs)` — encadenamiento estilo pandas
- `_repr_html_`
- `.como_tabla(ancho: bool = False)`
- `.resumen` — abstracto; cada subclase implementa con su propio esquema
- `.reporte` — abstracto; cada subclase implementa con su propio esquema
- `.diagnostico` — abstracto; cada subclase implementa con su propio esquema

**`ResultadoValidacion` (base)** provee:
- `.calculo` — referencia al `ResultadoX` validado
- `.resumen`
- `.reporte`
- `.diagnostico`

### Inventario de contratos v1 → v2

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

### Manifiesto por subtipo

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

### Estructura de `dominio.md`

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

### Pendientes — próxima sesión

- Esquemas nuevos de `ResultadoVariacion.resumen` / `.reporte` / `.diagnostico`
- Esquemas nuevos de `ResultadoIncidencia.resumen` / `.reporte` / `.diagnostico`
- Contratos completos: `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- Contrato de `empalmar`: compatibilidad `periodo_base=None` cross-version vs same-version
- `ResultadoVariacion` — ¿agregar `estado_calculo` en df para consistencia con `ResultadoIncidencia`?
- Actualizar `api.md`: parámetro `tipo` en `calcular_indice`; firmas completas de `api/incidencias.py`

---

## Contratos de datos

### Contratos sin cambio

Sin modificaciones en v2. Ver `docs/diseño.md` para esquema completo.

| Contrato | Archivo | Referencia |
|---|---|---|
| `CanastaCanonica` | `dominio/modelos/canasta.py` | diseño.md §5.1 |
| `SerieNormalizada` | `dominio/modelos/serie.py` | diseño.md §5.2 |
| `PeriodoQuincenal`, `PeriodoMensual`, `periodo_desde_str` | `dominio/periodos.py` | diseño.md §5.3 |
| `VersionCanasta`, `INDICE_POR_TIPO`, `RANGOS_VALIDOS` | `dominio/tipos.py` | diseño.md §5.9 |
| `CalculadorBase` (interfaz interna) | `dominio/calculo/` | diseño.md §5.8 |

---

### Vista — NUEVO

Wrapper ligero que envuelve un `pd.DataFrame` con MultiIndex `(periodo, X)` y agrega formato ancho. Usado por `.resultado` en todas las subclases de `Resultado` y `Validacion`.

**Decisión:** `Vista` no necesita saber el nombre de columna a pivotar — siempre hace `unstack("periodo")` (primer nivel del MultiIndex). El segundo nivel queda como filas. Funciona para cualquier subclase sin configuración extra.

**Decisión:** `.resultado` devuelve `Vista`, no `pd.DataFrame` plano, para permitir `inpc.resultado.ancho` sin requerir que el usuario conozca la API de pandas (`unstack`).

```python
import pandas as pd

class Vista:
    def __init__(self, df: pd.DataFrame, columna: str) -> None:
        self._df = df
        self._columna = columna

    def _repr_html_(self) -> str:
        """Muestra formato largo por default en Jupyter."""
        return self._df._repr_html_()  # type: ignore[operator]

    @property
    def largo(self) -> pd.DataFrame:
        """DataFrame completo en formato largo (MultiIndex + todas las columnas de metadata)."""
        return self._df

    @property
    def ancho(self) -> pd.DataFrame:
        """Solo la columna calculada, pivoteada: índices como filas, periodos como columnas."""
        return self._df[[self._columna]].unstack("periodo")
```

---

### Resultado (base) — NUEVO

Clase base abstracta compartida por `ResultadoIndice`, `ResultadoVariacion` y `ResultadoIncidencia`.

**Firma:**

```python
from abc import ABC, abstractmethod
import pandas as pd

class Resultado(ABC):
    def __init__(self, df: pd.DataFrame) -> None:
        """df: solo los valores calculados (indice_replicado / variacion_pp / incidencia_pp), formato largo."""
        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        """Resultado mínimo en formato largo. MultiIndex (periodo, indice), solo la columna calculada."""
        return self._df

    @property
    @abstractmethod
    def resultado(self) -> Vista:
        """Resultado completo con metadata. Largo por default; .ancho para formato pivoteado."""
        ...

    def pipe(self, fn, *args, **kwargs):
        """Encadenamiento estilo pandas."""
        return fn(self, *args, **kwargs)

    @abstractmethod
    def _repr_html_(self) -> str:
        """Display en Jupyter. Cada subclase define su propio layout."""
        ...

    @property
    @abstractmethod
    def resumen(self) -> pd.DataFrame:
        """Vista compacta — calculada desde df + manifiesto. Esquema propio de cada subclase."""
        ...

    @property
    @abstractmethod
    def reporte(self) -> pd.DataFrame:
        """Detalle de calidad por (periodo, indice). Solo el calculador lo conoce."""
        ...

    @property
    @abstractmethod
    def diagnostico(self) -> pd.DataFrame:
        """Faltantes o periodos problemáticos. Concatenable vía pd.concat."""
        ...
```

**Notas:**

- `self._df` = df mínimo: solo la columna calculada (`indice_replicado` / `variacion_pp` / `incidencia_pp`), MultiIndex `(periodo, indice)`. Se pasa en el constructor de cada subclase vía `super().__init__(df_minimo)`.
- `.df` = `self._df` — largo mínimo. Mismo dato que `.resultado.ancho` pero en formato largo.
- `.resultado` = abstracto — cada subclase devuelve `Vista(self._df_completo, columna=...)`.
- `.resultado.largo` = df completo con metadata. ≠ `.df` (tiene más columnas).
- `.resultado.ancho` = solo la columna calculada, pivoteada (índices × periodos). Mismos datos que `.df`, formato ancho.
- `.reporte` = `pd.DataFrame` con MultiIndex `(periodo, indice)`.
- `.diagnostico` = `pd.DataFrame` plano — lista de faltantes, no pivoteable.
- `.resumen` = `pd.DataFrame` plano — vista compacta agregada, no pivoteable. Se recalcula cada vez.
- Cada subclase valida sus invariantes **antes** de llamar `super().__init__(df_minimo)`.

**Responsabilidades:**

| propiedad | responde | granularidad |
|---|---|---|
| `.resumen` | ¿funcionó? ¿qué rango? ¿qué versión? | una fila por `ManifestUnidad` |
| `.resultado` | ¿cuáles son los valores calculados? | `(periodo, indice)` — largo/ancho |
| `.reporte` | ¿qué tan completo fue cada periodo? | `(periodo, indice)` — cobertura genéricos/ponderadores |
| `.diagnostico` | ¿cuáles genéricos específicamente faltaron? | fila por genérico ausente |

---

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
- `manifiesto.id_corrida`, `.tipo`, `.descripcion` no vacíos → `InvarianteViolado` si no
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
| `periodo_referencia` | `PeriodoQuincenal\|PeriodoMensual`/NaN |
| `version_t` | int/NaN |
| `version_referencia` | int/NaN |

---

**`.reporte`** — devuelve `pd.DataFrame`

Cubre todas las combinaciones `(periodo, indice)` esperadas, incluyendo no computables.

Índice: MultiIndex `(periodo, indice)`

| columna | tipo | notas |
|---|---|---|
| `estado_calculo` | str | `ok`, `parcial`, `sin_datos`, `fallida` |
| `motivo_error` | str/NaN | NaN cuando `ok`/`parcial` |
| `periodo_referencia` | `PeriodoQuincenal\|PeriodoMensual`/NaN | t-1, Dic año anterior, o `desde`; NaN cuando no computable |
| `indice_t` | float/NaN | `indice_replicado` en periodo `t` |
| `indice_referencia` | float/NaN | `indice_replicado` en periodo referencia |
| `version_t` | int/NaN | versión de canasta del periodo `t` |
| `version_referencia` | int/NaN | versión de canasta del periodo referencia |
| `cobertura_pct_t` | float/NaN | cobertura de genéricos del índice fuente en periodo `t` (de `ResultadoIndice.reporte`) |

**`estado_calculo` en reporte:**

| valor | condición |
|---|---|
| `ok` | variacion computable, fuente con datos definitivos |
| `parcial` | variacion computable, ≥1 periodo fuente era `parcial` |
| `sin_datos` | fuente tenía `sin_datos` en `t` o en referencia |
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
- `.resumen`, `.reporte`, `.diagnostico` con esquemas nuevos — pendiente de definir

**Propiedades sin cambio:** `.tipo`, `.frecuencia`, `.clase_incidencia`, `.periodos_semiok`.

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

## Funciones de dominio

### Transformaciones de ResultadoIndice

Archivo: `dominio/conversion.py`.

#### empalmar — MODIFICADO

Reemplaza a `combinar`.

```python
def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
) -> ResultadoIndice:
```

- Valida que todos los inputs tengan el mismo `tipo` (vía `manifiesto[i].tipo`) → `InvarianteViolado` si no
- `forzar=False` (default): lanza `InvarianteViolado` si `periodo_base` no es homogéneo entre inputs
- `forzar=True`: permite mezcla de escalas distintas + emite `UserWarning` describiendo qué `periodo_base` tiene cada tramo
- Concatena `.manifiesto` de cada tramo
- Aplica `RENOMBRES_INDICES` (`correspondencia_canastas.py`) para normalizar nombres de categorías entre versiones
- Propaga `.resumen`, `.reporte`, `.diagnostico` (merge automático)

> **Restricción:** solo para `ResultadoIndice`. No existe `empalmar` para `ResultadoVariacion` ni `ResultadoIncidencia` — siempre se empalma el `ResultadoIndice` fuente antes de calcular variaciones o incidencias. Tramos con escalas distintas (ej. 2Q Dic 2010 vs 2Q Jul 2018) deben rebsarse a base común antes de empalmar.

> **Nota:** para normalización manual de categorías antes de empalmar, ver `normalizar_categorias` en `api/indices.py` — pendiente de agregar.

#### rebasar

```python
def rebasar(
    resultado: ResultadoIndice,
    periodo_base: PeriodoQuincenal | PeriodoMensual,
    valor_base: float = 100.0,
) -> ResultadoIndice:
```

Sin cambio de lógica respecto a v1. Setea `.periodo_base` en el `ResultadoIndice` devuelto. Ver diseño.md §5.13.1.

#### a_mensual

```python
def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
```

Sin cambio de lógica. Tipo actualizado: `ResultadoCalculo` → `ResultadoIndice`. Ver diseño.md §5.13.

---

### Cálculo de variaciones

Mueven de `dominio/variaciones.py` → `dominio/calculo/variaciones.py`. Lógica sin cambio; tipo de `resultado` actualizado: `ResultadoCalculo` → `ResultadoIndice`.

| Función | Descripción | Referencia |
|---|---|---|
| `variacion_periodica(resultado, frecuencia)` | variación periodo a periodo | diseño.md §5.12 |
| `variacion_acumulada_anual(resultado)` | acumulado ene→actual vs dic año anterior | diseño.md §5.12 |
| `variacion_desde(resultado, desde, hasta, incluir_parciales)` | variación entre dos periodos | diseño.md §5.12 |

---

### Cálculo de incidencias

Mueven de `dominio/incidencias.py` → `dominio/calculo/incidencias.py`. Lógica sin cambio; tipos de `inpc` y `clasificacion` actualizados: `ResultadoCalculo` → `ResultadoIndice`.

| Función | Descripción | Referencia |
|---|---|---|
| `incidencia_periodica(inpc, clasificacion, canastas, frecuencia)` | incidencia periodo a periodo | diseño.md §5.17 |
| `incidencia_acumulada_anual(inpc, clasificacion, canastas)` | acumulado ene→actual | diseño.md §5.17 |
| `incidencia_desde(inpc, clasificacion, canastas, desde, hasta)` | incidencia entre dos periodos | diseño.md §5.17 |

---

### Validación interna

Privadas — llamadas solo desde `api/validaciones.py`. Lógica sin cambio; tipo de retorno actualizado: objetos sueltos → `ValidacionX` correspondiente.

| Función | Archivo | Devuelve | Referencia |
|---|---|---|---|
| `validar_inpc` | `dominio/validar_inpc.py` | `ValidacionIndice` | diseño.md §5.11 |
| `validar_variaciones` | `dominio/validar_variaciones.py` | `ValidacionVariacion` | diseño.md §5.16 |
| `validar_incidencias` | `dominio/validar_incidencias.py` | `ValidacionIncidencia` | diseño.md §5.20 |

