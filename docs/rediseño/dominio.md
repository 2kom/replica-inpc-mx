# Rediseño dominio/

## Alcance

- Cubre contratos de datos y funciones puras de `dominio/`.
- Excluye IO, infraestructura, orquestación y API pública.
- Excluye strings de periodos; dominio recibe solo `Periodo*`.
- Material transitorio removido de esta sección vive temporalmente en `transiscion.md`.

## Decisiones generales

- `ResultadoCalculo` **eliminado** — renombrado a `ResultadoIndice`.
- `ResultadoIndice` **no** embebe canasta — canasta es parámetro explícito donde se requiere.
- `ResultadoIndice` agrega atributo `periodo_referencia: PeriodoQuincenal | PeriodoMensual | None`.
- `empalmar` verifica `periodo_referencia` compatible entre inputs y propaga `reporte`, `diagnostico` y `resumen`.
- `ResumenValidacionVariaciones` eliminado — absorbido por `ValidacionVariacion`.
- Jerarquía separada en dos bases: `Resultado` y `ResultadoValidacion`.
- `ValidacionX` contiene un `ResultadoX` vía composición; no hereda de `Resultado`.
- Invariantes lanzan `InvarianteViolado`, nunca `ValueError`.

---

## Semántica compartida

### Semántica compartida global — CERRADO

Comparte semántica entre `Resultado*` y `Validacion*`.

#### Mapa de propiedades compartidas

| propiedad | existe en | tipo | significado |
|---|---|---|---|
| `.resumen` | `Resultado*`, `Validacion*` | `pd.DataFrame` | vista compacta; esquema propio de cada subclase |
| `.reporte` | `Resultado*`, `Validacion*` | `pd.DataFrame` | detalle; esquema propio de cada subclase |
| `.diagnostico` | `Resultado*`, `Validacion*` | `pd.DataFrame` | anomalías, faltantes o cobertura; esquema propio de cada subclase |

#### Semántica de propiedades compartidas

- `.resumen` = vista agregada para inspección rápida del estado del contrato.
- `.reporte` = vista detallada de la unidad de análisis relevante para el contrato.
- `.diagnostico` = vista accionable de anomalías, faltantes o combinaciones no verificables.

#### Catálogos

##### `estado_calculo` en `ResultadoIndice` — `.df`, `.resultado.largo`, `.reporte`

| valor | significado |
|---|---|
| `ok` | todas las quincenas disponibles; cálculo completo |
| `parcial` | solo una quincena disponible para el periodo; cálculo procede con calidad reducida |
| `sin_datos` | sin datos de entrada para esta combinación `(periodo, indice)` |
| `fallida` | cálculo intentado y fallido por error interno |

##### `estado_calculo` en resultados derivados — `.df`, `.resultado.largo`, `.reporte`, `.diagnostico`

Aplica en `ResultadoVariacion` y `ResultadoIncidencia`.

| valor | significado |
|---|---|
| `ok` | todos los periodos fuente tenían `estado_calculo = ok` |
| `parcial` | al menos un periodo fuente tenía `estado_calculo = parcial`; hereda degradación de calidad |

Invariante: `sin_datos` y `fallida` del fuente producen filas **ausentes** en el derivado — el NaN es implícito en `.resultado.ancho`.

##### `estado_calculo` en `.resumen` de cualquier contrato

Peor estado entre todas las filas del resultado. Orden de severidad: `fallida` > `sin_datos` > `parcial` > `ok`.

| clase | valores posibles |
|---|---|
| `ResultadoIndice` | `ok`, `parcial`, `sin_datos`, `fallida` |
| `ResultadoVariacion`, `ResultadoIncidencia` | `ok`, `parcial` |

#### Contrato NaN global — CERRADO

| clase | `.df` incluye filas `sin_datos`/`fallida` | NaN en columna calculada |
|---|---|---|
| `ResultadoIndice` | sí — todas las combinaciones intentadas | explícito; columna calculada `=NaN` cuando `sin_datos` o `fallida` |
| `ResultadoVariacion`, `ResultadoIncidencia` | no — solo combinaciones computables | implícito en `.resultado.ancho` via unstack |

`ResultadoIndice` conoce qué combinaciones intentó — el calculador conoce los genéricos esperados por canasta. Un intento fallido merece fila, con NaN marcando el fallo. Los derivados no intentan nada con `sin_datos`/`fallida` — simplemente no existe fila computable.

#### Asimetrías de `Validacion*` respecto a `Resultado*`

`Validacion*` preserva `.resumen`, `.reporte` y `.diagnostico` con la misma semántica. Las asimetrías son explícitas y están documentadas en `Semántica compartida de Validacion`:

- sin `.df` — validaciones no tienen columna calculada mínima.
- sin `.pipe()` — validaciones son terminales; no se encadenan.

### Semántica compartida de `Resultado` — CERRADO

Comparte semántica entre `ResultadoIndice`, `ResultadoVariacion` y `ResultadoIncidencia`.

#### Mapa de propiedades de `Resultado`

| propiedad | tipo | significado |
|---|---|---|
| `.df` | `pd.DataFrame` | resultado mínimo en formato largo |
| `.resultado` | `Vista` | resultado completo con metadata; expone formato largo y ancho |
| `.pipe(fn, *args, **kwargs)` | callable | encadenamiento estilo pandas sobre objeto resultado |
| `_repr_html_()` | HTML | representación rica para notebooks |

#### Semántica de propiedades de `Resultado`

- `.df` = resultado mínimo; contiene solo columna calculada en formato largo.
- `.resultado` = resultado completo; conserva metadata y expone `.largo` y `.ancho`.
- `.resultado.largo` = DataFrame completo con metadata en formato largo.
- `.resultado.ancho` = columnas clave pivoteadas por `periodo`; `Resultado*` produce filas=indice, cols=periodo; `Validacion*` produce filas=MultiIndex(indice, metrica), cols=periodo.
- `.pipe(fn, *args, **kwargs)` = encadenamiento estilo pandas sobre objeto resultado.
- `_repr_html_()` = representación rica para notebooks.

#### Vista compartida de resultados

`Vista` envuelve un `pd.DataFrame` con MultiIndex `(periodo, X)` y agrega acceso uniforme a formato largo y ancho.

- `.resultado` devuelve `Vista`, no `pd.DataFrame` plano.
- `.resultado.largo` devuelve DataFrame completo en formato largo con metadata.
- `.resultado.ancho` pivota por `periodo`; comportamiento según número de columnas en `Vista.columnas`: 1 columna → filas=indice (Resultado*); N columnas → filas=MultiIndex(indice, metrica) (Validacion*).
- `Vista` usa `unstack("periodo")`; `periodo` se asume como primer nivel del MultiIndex.

```python
import pandas as pd

class Vista:
    def __init__(self, df: pd.DataFrame, columnas: list[str]) -> None:
        self._df = df
        self._columnas = columnas

    def _repr_html_(self) -> str:
        return self._df._repr_html_()  # type: ignore[operator]

    @property
    def largo(self) -> pd.DataFrame:
        return self._df

    @property
    def ancho(self) -> pd.DataFrame:
        if len(self._columnas) == 1:
            return self._df[self._columnas[0]].unstack("periodo")
        return self._df[self._columnas].stack().unstack("periodo")
        # 1 columna → filas=indice, cols=periodo (Resultado*)
        # N columnas → filas=MultiIndex(indice, metrica), cols=periodo (Validacion*)
```

#### Asimetrías dentro de `Resultado*`

`ResultadoIndice` y los derivados NO comparten exactamente la misma semántica en `.resultado.largo`: `ResultadoIndice` conserva filas con NaN cuando `estado_calculo = sin_datos` o `fallida`; los derivados omiten esas combinaciones del largo. La asimetría está documentada en `Semántica compartida de resultados derivados`.

### Semántica compartida de resultados derivados — CERRADO

Comparte semántica entre `ResultadoVariacion` y `ResultadoIncidencia`.

#### Asimetría respecto a `ResultadoIndice`

- `.resultado.largo` contiene solo filas computables.
- combinaciones `(periodo, indice)` no computables quedan ausentes del largo.
- el NaN de esas combinaciones aparece implícito en `.resultado.ancho`.

#### Invariantes compartidos

- `df` no vacío -> `InvarianteViolado` si no.
- `df` usa MultiIndex `(periodo, indice)` -> `InvarianteViolado` si no.
- `estado_calculo` solo admite `ok` y `parcial` en `df` -> `InvarianteViolado` si contiene `sin_datos` o `fallida`.
- columna calculada no contiene NaN en filas presentes -> `InvarianteViolado` si no.
- `manifiesto.id_corrida`, `.tipo`, `.descripcion` no vacíos -> `InvarianteViolado` si no.
- `manifiesto.tipo == df["tipo"].iloc[0]` -> `InvarianteViolado` si no.
- no existe `empalmar` para resultados derivados; primero se empalma `ResultadoIndice`.

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| formato | largo mínimo heredado de `Resultado` |
| filas | solo combinaciones computables |

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| largo/ancho | ver `Semántica compartida de Resultado` |

##### `.resultado.ancho`

| aspecto | contrato |
|---|---|
| filas | índices |
| columnas | periodos |
| NaN implícito | combinaciones ausentes por cálculo no computable |

#### `.indices_parciales`

Esquema de columnas compartido. Condición de existencia: ver contrato de cada clase.

| columna | tipo | notas |
|---|---|---|
| `periodo_desde_real` | `PeriodoQuincenal \| PeriodoMensual` | base real usada |
| `periodo_hasta_real` | `PeriodoQuincenal \| PeriodoMensual` | cierre real usado |

#### `.resumen`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero (`0`) |
| granularidad | una fila; derivados son terminales |
| cálculo | calculado bajo demanda; no se almacena |

#### `.reporte`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| cobertura | incluye combinaciones computables y no computables |

#### `.diagnostico`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero |
| semántica | subconjunto accionable de `.reporte` con combinaciones no computables |

### Semántica compartida de `Validacion` — CERRADO

Comparte semántica entre `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia`.

#### Mapa de propiedades de `Validacion`

| propiedad | tipo | significado |
|---|---|---|
| `.resultado` | `Vista` | comparación entre resultado replicado e INEGI; covariante según subclase |
| `_repr_html_()` | HTML | representación rica para notebooks; cada subclase decide qué mostrar |

#### Semántica de propiedades de `Validacion`

- `.resultado` = `Vista` con columnas del `ResultadoX` de entrada más columnas de comparación INEGI; expone `.largo` y `.ancho`.
- `.df` = no aplica; validaciones no tienen columna calculada mínima.
- `.pipe()` = no aplica; validaciones son terminales, no se encadenan.
- `_repr_html_()` = abstracto en la base; cada subclase define su representación en notebook.

---

## Contratos de datos

### Resultado (base) — NUEVO — CERRADO

Clase base abstracta compartida por `ResultadoIndice`, `ResultadoVariacion` y `ResultadoIncidencia`.

#### Constructor + invariantes

```python
from abc import ABC, abstractmethod
import pandas as pd

class Resultado(ABC):
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df
```

- `df` usa MultiIndex `(periodo, indice)` -> contrato base de resultados.
- `df` contiene solo columna calculada -> metadata adicional vive en `.resultado.largo`.
- subclase llama `super().__init__(df[["columna_calculada"]])`; base almacena solo la columna calculada, no el df completo.

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| columnas | una sola columna calculada |
| formato | largo |
| NaN | ver `Semántica compartida global` y `Semántica compartida de Resultado` |

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| existencia | abstracta en la clase base |
| responsabilidad de subclase | definir DataFrame completo y columna calculada |
| largo/ancho | ver `Semántica compartida de Resultado` |

#### `.resumen`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

#### `.reporte`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

#### `.diagnostico`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

### ManifestUnidad — NUEVO — CERRADO

Dataclass de manifiesto para `ResultadoIndice`. Representa un tramo elemental de cálculo y es combinable vía `empalmar`.

> **Asimetría respecto a `ManifestDerivado`:** `ManifestUnidad` es combinable y conserva metadatos de cálculo por tramo. `ManifestDerivado` es terminal y resume el origen ya calculado.

#### Constructor + invariantes

```python
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

- un elemento representa una corrida elemental sobre una sola canasta.
- `empalmar` concatena listas de `ManifestUnidad` sin colapsarlas.
- `tipo`, `version`, `ruta_canasta` y `ruta_series` no son decorativos: forman parte de la trazabilidad del cálculo.

#### Campos

| campo | tipo | contrato |
|---|---|---|
| `id_corrida` | str | identificador único de la corrida elemental |
| `version` | `VersionCanasta` | versión de canasta usada en el tramo |
| `tipo` | str | tipo de índice calculado |
| `calculador` | literal | variante concreta del calculador usada en el tramo |
| `ruta_canasta` | `Path` | origen físico de la canasta usada |
| `ruta_series` | `Path` | origen físico de las series usadas |
| `fecha` | `datetime` | marca temporal de la corrida |

#### Uso en contratos

| aspecto | contrato |
|---|---|
| dueño | `ResultadoIndice.manifiesto` |
| cardinalidad | `list[ManifestUnidad]` |
| resumen | `ResultadoIndice.resumen` recalcula una fila por entrada de manifiesto |
| empalme | concatena listas y preserva trazabilidad por tramo |

### ManifestDerivado — NUEVO — CERRADO

Dataclass de manifiesto para `ResultadoVariacion` y `ResultadoIncidencia`. Resume el origen de un resultado derivado y no es combinable.

> **Asimetría respecto a `ManifestUnidad`:** `ManifestDerivado` no representa tramos elementales ni conserva rutas o calculador; resume el resultado ya derivado y se trata como terminal.

#### Constructor + invariantes

```python
@dataclass
class ManifestDerivado:
    id_corrida: list[str]
    tipo: str
    descripcion: str
    fecha: datetime
    inpc_ids: list[str] | None = None
    clasificacion_ids: list[str] | None = None
```

- `id_corrida` = IDs de todas las corridas origen; para incidencias = `inpc_ids + clasificacion_ids`.
- `(inpc_ids is None) == (clasificacion_ids is None)` → `InvarianteViolado` si no.
- `inpc_ids` y `clasificacion_ids` solo se populan para `ResultadoIncidencia`; para variaciones quedan `None`.
- no existe operación de `empalmar` sobre resultados derivados.
- `descripcion` expresa la clase o rango analizado: `"mensual"`, `"desde Ene 2015 hasta Dic 2024"`, etc.

#### Campos

| campo | tipo | contrato |
|---|---|---|
| `id_corrida` | `list[str]` | ids de todas las corridas origen |
| `tipo` | str | tipo de índice derivado |
| `descripcion` | str | descripción legible del derivado |
| `fecha` | `datetime` | marca temporal del derivado |
| `inpc_ids` | `list[str] \| None` | IDs de corridas de `inpc`; solo para `ResultadoIncidencia` |
| `clasificacion_ids` | `list[str] \| None` | IDs de corridas de `clasificacion`; solo para `ResultadoIncidencia` |

#### Uso en contratos

| aspecto | contrato |
|---|---|
| dueño | `ResultadoVariacion.manifiesto`, `ResultadoIncidencia.manifiesto` |
| cardinalidad | una instancia por resultado derivado |
| resumen | `.resumen` produce una fila por `ManifestDerivado` |
| empalme | no aplica; derivados son terminales |


### ResultadoIndice — MODIFICADO — CERRADO

Renombrado desde `ResultadoCalculo`. Hereda de `Resultado`.

> **Asimetría respecto a resultados derivados:** `ResultadoIndice.resultado.largo` conserva filas con `indice_replicado=NaN` cuando `estado_calculo` es `sin_datos` o `fallida`. En derivados, esas combinaciones tienden a quedar ausentes del largo y el NaN aparece implícito en `.resultado.ancho`.

#### Constructor + invariantes

```python
def __init__(
    self,
    df: pd.DataFrame,
    manifiesto: list[ManifestUnidad],
    reporte_df: pd.DataFrame,
    diagnostico_df: pd.DataFrame,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual | None = None,
) -> None:
```

- `df` usa MultiIndex `(periodo, indice)` -> `InvarianteViolado` si no.
- `df` contiene columna `indice_replicado` -> `InvarianteViolado` si no.
- `reporte_df` y `diagnostico_df` se pasan al constructor -> no se reconstruyen desde `df` después del cálculo.
- `manifiesto` no vacío -> `InvarianteViolado` si no.
- acceso a `id_corrida` ocurre vía `.manifiesto`; no existe property única para resultados empalmados.

#### `.manifiesto`

| aspecto | contrato |
|---|---|
| tipo | `list[ManifestUnidad]` |
| cardinalidad | un elemento por canasta; `empalmar` concatena listas |
| semántica | trazabilidad completa del cálculo por tramo |

#### `.periodo_referencia`

| aspecto | contrato |
|---|---|
| tipo | `PeriodoQuincenal \| PeriodoMensual \| None` |
| semántica | periodo en el que los valores del índice son 100 |
| origen | parámetro directo del constructor; `rebasar` lo setea en el resultado devuelto |
| `None` | resultado no rebsado explícitamente; escala natural del cálculo |

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| columnas | `indice_replicado` |
| formato | largo mínimo heredado de `Resultado` |
| NaN | `indice_replicado=NaN` cuando `estado_calculo = sin_datos` o `fallida`; filas presentes para todos los intentos |

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| columnas | `["indice_replicado"]` |
| largo/ancho | ver `Semántica compartida de Resultado` |

##### `.resultado.largo`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| `version` | int | nunca | versión de canasta |
| `tipo` | str | nunca | `"inpc"`, `"inflacion componente"`, etc. |
| `indice_replicado` | float | `estado_calculo` = `sin_datos` o `fallida` | |
| `estado_calculo` | str | nunca | `ok`, `parcial`, `sin_datos`, `fallida` |
| `motivo_error` | str | `estado_calculo` = `ok` o `parcial` | |

##### `.resultado.ancho`

| aspecto | contrato |
|---|---|
| filas | índices |
| columnas | periodos |
| valores | `indice_replicado` |
| NaN | explícito; `indice_replicado=NaN` cuando `estado_calculo` = `sin_datos` o `fallida` |

#### `.resumen`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | `id_corrida` |
| granularidad | una fila por `ManifestUnidad` |
| cálculo | calculado bajo demanda; no se almacena |

| columna | tipo |
|---|---|
| `version` | int |
| `tipo` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` |

#### `.reporte`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |

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

#### `.diagnostico`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero |
| compatibilidad | mismo schema que `DiagnosticoFaltantes` v1; concatenable con `pd.concat` |

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `version` | int |
| `tipo` | str |
| `periodo` | `PeriodoQuincenal`/NaN |
| `generico` | str |
| `nivel_faltante` | str |
| `tipo_faltante` | str |
| `detalle` | str |

### ResultadoVariacion — MODIFICADO — CERRADO

Hereda de `Resultado`. Mueve de `dominio/modelos/variacion.py` a `dominio/calculo/variacion.py`.

> **Asimetría respecto a `ResultadoIndice`:** `.resultado.largo` no contiene `motivo_error`. En derivados, `estado_calculo` solo admite `ok` y `parcial`; las combinaciones no computables del fuente quedan **ausentes** del largo. Si se requiere `motivo_error`, ver `.reporte`.

#### Constructor + invariantes

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

- `df` contiene columnas `tipo`, `clase_variacion`, `variacion_pp`, `estado_calculo` -> `InvarianteViolado` si no.
- `clase_variacion` es homogénea y pertenece a `{"periodica", "acumulada_anual", "desde"}` -> `InvarianteViolado` si no.

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| columnas | `variacion_pp` |
| formato | largo |
| filas | solo combinaciones computables |

#### `.resultado`

| aspecto | contrato |
|---|---|
| columnas | `["variacion_pp"]` |

##### `.resultado.largo`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| `tipo` | str | nunca | tipo de índice |
| `clase_variacion` | str | nunca | `periodica`, `acumulada_anual`, `desde` |
| `variacion_pp` | float | nunca | siempre válido en filas presentes |
| `estado_calculo` | str | nunca | `ok`, `parcial` |
| `version_t` | int | nunca | versión de canasta del periodo `t` |

##### `.resultado.ancho`

| aspecto | contrato |
|---|---|
| filas | índices |
| columnas | periodos |
| valores | `variacion_pp` |
| NaN implícito | combinaciones ausentes del `.df` |

#### `.indices_parciales`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame \| None` |
| existe cuando | `clase_variacion == "desde"` y hubo ajustes de periodos |
| índice | `indice` |

Esquema de columnas: ver `Semántica compartida de resultados derivados`.

Invariante: `indices_parciales is not None` si y solo si `clase_variacion == "desde"` -> `InvarianteViolado` si no.

#### `.resumen`

| columna | tipo |
|---|---|
| `tipo` | str |
| `clase_variacion` | str |
| `descripcion` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` |

#### `.reporte`

| columna | tipo |
|---|---|
| `estado_calculo` | str |
| `motivo_error` | str/NaN |
| `periodo_lag` | `PeriodoQuincenal \| PeriodoMensual`/NaN |
| `indice_t` | float/NaN |
| `indice_lag` | float/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |
| `cobertura_pct_t` | float/NaN |
| `cobertura_pct_lag` | float/NaN |

#### `.diagnostico`

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `tipo` | str |
| `clase_variacion` | str |
| `periodo` | `PeriodoQuincenal \| PeriodoMensual` |
| `indice` | str |
| `estado_calculo` | str |
| `motivo_error` | str |
| `periodo_lag` | `PeriodoQuincenal \| PeriodoMensual`/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |

### ResultadoIncidencia — MODIFICADO — CERRADO

Hereda de `Resultado`. Mueve de `dominio/modelos/incidencia.py` a `dominio/calculo/incidencia.py`.

> **Asimetría respecto a `ResultadoIndice`:** `.resultado.largo` no contiene `motivo_error`. En derivados, `estado_calculo` solo admite `ok` y `parcial`; las combinaciones no computables del fuente quedan **ausentes** del largo. Si se requiere `motivo_error`, ver `.reporte`.

#### Constructor + invariantes

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

- `df` contiene columnas `tipo`, `clase_incidencia`, `incidencia_pp`, `estado_calculo` -> `InvarianteViolado` si no.
- `clase_incidencia` es homogénea y pertenece a `{"periodica", "acumulada_anual", "desde"}` -> `InvarianteViolado` si no.

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| columnas | `incidencia_pp` |
| formato | largo |
| filas | solo combinaciones computables |

#### `.resultado`

| aspecto | contrato |
|---|---|
| columnas | `["incidencia_pp"]` |

##### `.resultado.largo`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| `tipo` | str | nunca | tipo de índice |
| `clase_incidencia` | str | nunca | `periodica`, `acumulada_anual`, `desde` |
| `incidencia_pp` | float | nunca | siempre válido en filas presentes |
| `estado_calculo` | str | nunca | `ok`, `parcial` |
| `version_t` | int | nunca | versión de canasta del periodo `t` |

##### `.resultado.ancho`

| aspecto | contrato |
|---|---|
| filas | índices |
| columnas | periodos |
| valores | `incidencia_pp` |
| NaN implícito | combinaciones ausentes del `.df` |

#### `.indices_parciales`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame \| None` |
| existe cuando | `clase_incidencia == "desde"` y hubo ajustes de periodos |
| índice | `indice` |

Esquema de columnas: ver `Semántica compartida de resultados derivados`.

Invariante: `indices_parciales is not None` si y solo si `clase_incidencia == "desde"` -> `InvarianteViolado` si no.

#### `.resumen`

| columna | tipo |
|---|---|
| `tipo` | str |
| `clase_incidencia` | str |
| `descripcion` | str |
| `estado_calculo` | str |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` |

#### `.reporte`

| columna | tipo |
|---|---|
| `estado_calculo` | str |
| `motivo_error` | str/NaN |
| `periodo_lag` | `PeriodoQuincenal \| PeriodoMensual`/NaN |
| `indice_t` | float/NaN |
| `indice_lag` | float/NaN |
| `ponderador_t` | float/NaN |
| `ponderador_lag` | float/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |
| `cobertura_pct_t` | float/NaN |
| `cobertura_pct_lag` | float/NaN |

#### `.diagnostico`

| columna | tipo |
|---|---|
| `id_corrida` | str |
| `tipo` | str |
| `clase_incidencia` | str |
| `periodo` | `PeriodoQuincenal \| PeriodoMensual` |
| `indice` | str |
| `estado_calculo` | str |
| `motivo_error` | str |
| `periodo_lag` | `PeriodoQuincenal \| PeriodoMensual`/NaN |
| `version_t` | int/NaN |
| `version_lag` | int/NaN |

### Validacion (base) — NUEVO — CERRADO

Clase base abstracta compartida por `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia`. Análoga a `Resultado`, pero para comparaciones contra series publicadas por INEGI.

#### Constructor + invariantes

```python
from abc import ABC, abstractmethod

class Validacion(ABC):
    ...
```

- `.resultado` es abstracto -> cada subclase devuelve `Vista` con comparación INEGI.
- `.resumen`, `.reporte`, `.diagnostico` y `_repr_html_()` son abstractos -> cada subclase define su esquema propio.
- sin `.df` — validaciones no tienen columna calculada mínima.
- sin `.pipe()` — validaciones son terminales; no se encadenan.

#### `.resultado`

| aspecto | contrato |
|---|---|
| existencia | abstracta en la clase base |
| tipo | `Vista` |
| semántica | ver `Semántica compartida de Validacion` |

#### `.resumen`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

#### `.reporte`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

#### `.diagnostico`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| existencia | abstracta en la clase base |
| semántica | ver `Semántica compartida global` |

#### `_repr_html_()`

| aspecto | contrato |
|---|---|
| existencia | abstracta en la clase base |
| semántica | cada subclase define qué propiedad expone en notebook |

### ValidacionIndice — NUEVO — CERRADO

Hereda de `Validacion`. Compara un `ResultadoIndice` contra series publicadas por INEGI.

#### Constructor + invariantes

- `resultado.manifiesto[i].tipo not in TIPOS_CON_VALIDACION` → `InvarianteViolado`; solo `"inpc"`, `"inflacion componente"` e `"inflacion subcomponente"` tienen series INEGI comparables.

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| columnas | `["indice_replicado", "indice_inegi", "error_absoluto", "estado_validacion"]` |
| construcción | `Vista(resultado_largo_df, columnas=[...])` |

- `ResultadoIndice` subyacente no tiene acceso externo; toda la información está expuesta vía `.resultado`, `.resumen`, `.reporte` y `.diagnostico`.

##### `.resultado.largo`

Hereda columnas de `ResultadoIndice.resultado.largo` y agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `version` | int | nunca |
| `tipo` | str | nunca |
| `indice_replicado` | float/NaN | `estado_calculo = sin_datos` o `fallida` |
| `estado_calculo` | str | nunca |
| `motivo_error` | str/NaN | `estado_calculo = ok` o `parcial` |
| `indice_inegi` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto` | float/NaN | mismo que `indice_inegi` |
| `estado_validacion` | str | nunca |

##### `.resultado.ancho`

Pivota las cuatro columnas de `Vista.columnas` por periodo:

| aspecto | contrato |
|---|---|
| filas | MultiIndex `(indice, metrica)` |
| columnas | periodos |
| valores | valor de cada metrica en ese `(indice, periodo)` |

> Mismo patrón en `ValidacionVariacion` (`["variacion_pp", "variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"]`) y `ValidacionIncidencia` (`["incidencia_pp", "incidencia_inegi_pp", "error_absoluto_pp", "estado_validacion"]`).

#### `.resumen`

Extiende `ResultadoIndice.resumen`. Mismo índice `id_corrida`, misma granularidad (una fila por `ManifestUnidad`). Agrega columnas de validación:

| columna | tipo | notas |
|---|---|---|
| `version` | int | de `ManifestUnidad` |
| `tipo` | str | de `ManifestUnidad` |
| `estado_calculo` | str | peor estado del tramo |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` | |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` | |
| `n_comparables` | int | filas con comparación INEGI disponible (`ok`, `diferencia_detectada`, `diferencia_por_parcial`) |
| `n_fuera_rango_inegi` | int | periodos sin publicación INEGI para ese indicador |
| `n_no_disponibles` | int | periodos en rango publicado pero sin valor |
| `n_diferencia_por_parcial` | int | periodos con diferencia atribuible a datos parciales; `0` para resultados quincenales |
| `n_sin_calculo` | int | filas con `estado_calculo = sin_datos` o `fallida`; comparación imposible desde nuestro lado |
| `error_absoluto_max` | float / NaN | NaN si `n_comparables == 0` |
| `estado_validacion_global` | str | `ok`, `diferencia_detectada`, `sin_calculo`, `diferencia_por_parcial`, `no_disponible`; `fuera_rango_inegi` no afecta el estado global |

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | `id_corrida` |
| cálculo | bajo demanda; no se almacena |

#### `.reporte`

Extiende `ResultadoIndice.reporte`. Mismo índice `(periodo, indice)`. Agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `version` | int | nunca |
| `estado_calculo` | str | nunca |
| `motivo_error` | str/NaN | `estado_calculo = ok` o `parcial` |
| `genericos_esperados` | int | nunca |
| `genericos_con_indice` | int | nunca |
| `genericos_sin_indice` | int | nunca |
| `cobertura_genericos_pct` | float | nunca |
| `ponderador_esperado` | float | nunca |
| `ponderador_cubierto` | float | nunca |
| `indice_replicado` | float/NaN | `estado_calculo = sin_datos` o `fallida` |
| `indice_inegi` | float/NaN | `estado_validacion in {fuera_rango_inegi, no_disponible, sin_calculo}` |
| `error_absoluto` | float/NaN | mismo que `indice_inegi` |
| `estado_validacion` | str | nunca |

Valores de `estado_validacion`: `ok`, `diferencia_detectada`, `diferencia_por_parcial`, `sin_calculo`, `no_disponible`, `fuera_rango_inegi`.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| cálculo | bajo demanda; no se almacena |

#### `.diagnostico`

Subconjunto de `.reporte` donde `estado_validacion != ok`: incluye `diferencia_detectada`, `diferencia_por_parcial`, `sin_calculo`, `no_disponible` y `fuera_rango_inegi`.

| columna | tipo | NaN cuando |
|---|---|---|
| `id_corrida` | str | nunca |
| `version` | int | nunca |
| `tipo` | str | nunca |
| `periodo` | `PeriodoQuincenal \| PeriodoMensual` | nunca |
| `indice` | str | nunca |
| `estado_validacion` | str | nunca |
| `estado_calculo` | str | nunca |
| `indice_replicado` | float/NaN | `estado_calculo = sin_datos` o `fallida` |
| `indice_inegi` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi, sin_calculo}` |
| `error_absoluto` | float/NaN | mismo que `indice_inegi` |

`estado_calculo` da contexto adicional para filas `diferencia_detectada`: si `estado_calculo = ok`, la diferencia no tiene causa conocida y merece mayor atención.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero |
| cálculo | bajo demanda; no se almacena |

### ValidacionVariacion — NUEVO — CERRADO

Hereda de `Validacion`. Compara un `ResultadoVariacion` contra series publicadas por INEGI.

#### Constructor + invariantes

- `resultado.manifiesto.tipo not in TIPOS_CON_VALIDACION` → `InvarianteViolado`; solo `"inpc"`, `"inflacion componente"` e `"inflacion subcomponente"` tienen series INEGI comparables.

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| columnas | `["variacion_pp", "variacion_inegi_pp", "error_absoluto_pp", "estado_validacion"]` |
| construcción | `Vista(resultado_largo_df, columnas=[...])` |

- `ResultadoVariacion` subyacente no tiene acceso externo; toda la información está expuesta vía `.resultado`, `.resumen`, `.reporte` y `.diagnostico`.

##### `.resultado.largo`

Hereda columnas de `ResultadoVariacion.resultado.largo` y agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `tipo` | str | nunca |
| `clase_variacion` | str | nunca |
| `variacion_pp` | float | nunca en filas presentes |
| `estado_calculo` | str | nunca |
| `version_t` | int | nunca |
| `variacion_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `variacion_inegi_pp` |
| `estado_validacion` | str | nunca |

##### `.resultado.ancho`

Pivota las cuatro columnas de `Vista.columnas` por periodo:

| aspecto | contrato |
|---|---|
| filas | MultiIndex `(indice, metrica)` |
| columnas | periodos |
| valores | valor de cada metrica en ese `(indice, periodo)` |

#### `.resumen`

Extiende `ResultadoVariacion.resumen`. Mismo índice `0`, misma granularidad (una fila; derivados son terminales). Agrega columnas de validación:

| columna | tipo | notas |
|---|---|---|
| `tipo` | str | de `ResultadoVariacion` |
| `clase_variacion` | str | de `ResultadoVariacion` |
| `descripcion` | str | de `ResultadoVariacion` |
| `estado_calculo` | str | de `ResultadoVariacion` |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` | de `ResultadoVariacion` |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` | de `ResultadoVariacion` |
| `n_comparables` | int | filas con comparación INEGI disponible (`ok`, `diferencia_detectada`, `diferencia_por_parcial`) |
| `n_fuera_rango_inegi` | int | filas sin publicación INEGI para ese indicador/periodo |
| `n_no_disponibles` | int | filas en rango publicado pero sin valor INEGI |
| `n_diferencia_por_parcial` | int | filas con diferencia atribuible a datos parciales; `0` para resultados quincenales |
| `error_absoluto_max_pp` | float/NaN | NaN si `n_comparables == 0` |
| `estado_validacion_global` | str | `ok`, `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible`; `fuera_rango_inegi` no afecta el estado global |

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero (`0`) |
| cálculo | bajo demanda; no se almacena |

#### `.reporte`

Extiende `ResultadoVariacion.reporte`. Mismo índice `(periodo, indice)`. Agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `estado_calculo` | str | nunca |
| `motivo_error` | str/NaN | `estado_calculo = ok` o `parcial` |
| `periodo_lag` | `Periodo*`/NaN | base no existe |
| `indice_t` | float/NaN | base no existe |
| `indice_lag` | float/NaN | base no existe |
| `version_t` | int/NaN | base no existe |
| `version_lag` | int/NaN | base no existe |
| `cobertura_pct_t` | float/NaN | base no existe |
| `cobertura_pct_lag` | float/NaN | base no existe |
| `variacion_pp` | float | nunca en filas presentes |
| `variacion_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `variacion_inegi_pp` |
| `estado_validacion` | str | nunca |

Valores de `estado_validacion`: `ok`, `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible`, `fuera_rango_inegi`.

`estado_calculo` da contexto adicional para filas `diferencia_detectada`: si `estado_calculo = ok`, la diferencia no tiene causa conocida y merece mayor atención.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| cálculo | bajo demanda; no se almacena |

#### `.diagnostico`

Subconjunto de `.reporte` donde `estado_validacion != ok`: incluye `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible` y `fuera_rango_inegi`.

| columna | tipo | NaN cuando |
|---|---|---|
| `tipo` | str | nunca |
| `clase_variacion` | str | nunca |
| `periodo` | `PeriodoQuincenal \| PeriodoMensual` | nunca |
| `indice` | str | nunca |
| `version_t` | int | nunca |
| `estado_validacion` | str | nunca |
| `estado_calculo` | str | nunca |
| `variacion_pp` | float | nunca en filas presentes |
| `variacion_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `variacion_inegi_pp` |

`estado_calculo` da contexto para `diferencia_detectada`: si `estado_calculo = ok`, la diferencia no tiene causa conocida y merece mayor atención.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero |
| cálculo | bajo demanda; no se almacena |

### ValidacionIncidencia — NUEVO — CERRADO

Hereda de `Validacion`. Compara un `ResultadoIncidencia` contra series publicadas por INEGI.

#### Constructor + invariantes

- `resultado.manifiesto.tipo not in TIPOS_CON_VALIDACION` → `InvarianteViolado`; solo `"inpc"`, `"inflacion componente"` e `"inflacion subcomponente"` tienen series INEGI comparables.

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| columnas | `["incidencia_pp", "incidencia_inegi_pp", "error_absoluto_pp", "estado_validacion"]` |
| construcción | `Vista(resultado_largo_df, columnas=[...])` |

- `ResultadoIncidencia` subyacente no tiene acceso externo; toda la información está expuesta vía `.resultado`, `.resumen`, `.reporte` y `.diagnostico`.

##### `.resultado.largo`

Hereda columnas de `ResultadoIncidencia.resultado.largo` y agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `tipo` | str | nunca |
| `clase_incidencia` | str | nunca |
| `incidencia_pp` | float | nunca en filas presentes |
| `estado_calculo` | str | nunca |
| `version_t` | int | nunca |
| `incidencia_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `incidencia_inegi_pp` |
| `estado_validacion` | str | nunca |

##### `.resultado.ancho`

Pivota las cuatro columnas de `Vista.columnas` por periodo:

| aspecto | contrato |
|---|---|
| filas | MultiIndex `(indice, metrica)` |
| columnas | periodos |
| valores | valor de cada metrica en ese `(indice, periodo)` |

#### `.resumen`

Extiende `ResultadoIncidencia.resumen`. Mismo índice `0`, misma granularidad (una fila; derivados son terminales). Agrega columnas de validación:

| columna | tipo | notas |
|---|---|---|
| `tipo` | str | de `ResultadoIncidencia` |
| `clase_incidencia` | str | de `ResultadoIncidencia` |
| `descripcion` | str | de `ResultadoIncidencia` |
| `estado_calculo` | str | de `ResultadoIncidencia` |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` | de `ResultadoIncidencia` |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` | de `ResultadoIncidencia` |
| `n_comparables` | int | filas con comparación INEGI disponible (`ok`, `diferencia_detectada`, `diferencia_por_parcial`) |
| `n_fuera_rango_inegi` | int | filas sin publicación INEGI para ese indicador/periodo |
| `n_no_disponibles` | int | filas en rango publicado pero sin valor INEGI |
| `n_diferencia_por_parcial` | int | filas con diferencia atribuible a datos parciales; `0` para resultados quincenales |
| `error_absoluto_max_pp` | float/NaN | NaN si `n_comparables == 0` |
| `estado_validacion_global` | str | `ok`, `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible`; `fuera_rango_inegi` no afecta el estado global |

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero (`0`) |
| cálculo | bajo demanda; no se almacena |

#### `.reporte`

Extiende `ResultadoIncidencia.reporte`. Mismo índice `(periodo, indice)`. Agrega columnas de comparación INEGI:

| columna | tipo | NaN cuando |
|---|---|---|
| `estado_calculo` | str | nunca |
| `motivo_error` | str/NaN | `estado_calculo = ok` o `parcial` |
| `periodo_lag` | `Periodo*`/NaN | base no existe |
| `indice_t` | float/NaN | base no existe |
| `indice_lag` | float/NaN | base no existe |
| `ponderador_t` | float/NaN | base no existe |
| `ponderador_lag` | float/NaN | base no existe |
| `version_t` | int/NaN | base no existe |
| `version_lag` | int/NaN | base no existe |
| `cobertura_pct_t` | float/NaN | base no existe |
| `cobertura_pct_lag` | float/NaN | base no existe |
| `incidencia_pp` | float | nunca en filas presentes |
| `incidencia_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `incidencia_inegi_pp` |
| `estado_validacion` | str | nunca |

Valores de `estado_validacion`: `ok`, `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible`, `fuera_rango_inegi`.

`estado_calculo` da contexto adicional para filas `diferencia_detectada`: si `estado_calculo = ok`, la diferencia no tiene causa conocida y merece mayor atención.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| cálculo | bajo demanda; no se almacena |

#### `.diagnostico`

Subconjunto de `.reporte` donde `estado_validacion != ok`: incluye `diferencia_detectada`, `diferencia_por_parcial`, `no_disponible` y `fuera_rango_inegi`.

| columna | tipo | NaN cuando |
|---|---|---|
| `tipo` | str | nunca |
| `clase_incidencia` | str | nunca |
| `periodo` | `PeriodoQuincenal \| PeriodoMensual` | nunca |
| `indice` | str | nunca |
| `version_t` | int | nunca |
| `estado_validacion` | str | nunca |
| `estado_calculo` | str | nunca |
| `incidencia_pp` | float | nunca en filas presentes |
| `incidencia_inegi_pp` | float/NaN | `estado_validacion in {no_disponible, fuera_rango_inegi}` |
| `error_absoluto_pp` | float/NaN | mismo que `incidencia_inegi_pp` |

`estado_calculo` da contexto para `diferencia_detectada`: si `estado_calculo = ok`, la diferencia no tiene causa conocida y merece mayor atención.

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | entero |
| cálculo | bajo demanda; no se almacena |

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
- Regla de `periodo_referencia`:
  - todos `None` → resultado `None`
  - mezcla `None` + un único valor explícito → resultado hereda ese valor explícito
  - `forzar=False` (default): dos valores explícitos **distintos** → `InvarianteViolado`
  - `forzar=True`: dos valores explícitos distintos → permitido + `UserWarning` describiendo qué `periodo_referencia` tiene cada input
- Concatena `.manifiesto` de cada input
- Aplica `RENOMBRES_INDICES` (`correspondencia_canastas.py`) para normalizar nombres de categorías entre versiones
- Propaga `.resumen`, `.reporte`, `.diagnostico` (merge automático)

> **Restricción:** solo para `ResultadoIndice`. No existe `empalmar` para `ResultadoVariacion` ni `ResultadoIncidencia` — siempre se empalma el `ResultadoIndice` fuente antes de calcular variaciones o incidencias.

> **Nota:** para normalización manual de categorías antes de empalmar, ver `normalizar_categorias` en `api/indices.py` — pendiente de agregar.

#### rebasar

```python
def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual,
    valor_base: float = 100.0,
) -> ResultadoIndice:
```

Sin cambio de lógica respecto a v1. Setea `.periodo_referencia` en el `ResultadoIndice` devuelto. Ver diseño.md §5.13.1.

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

#### Precondición compartida

`inpc.periodo_referencia == clasificacion.periodo_referencia` → `InvarianteViolado` si no.

Ambos deben estar en la misma escala de referencia. Si ambos son `None`, se asume misma escala — responsabilidad del llamador.

#### Proveniencia en `ManifestDerivado`

`id_corrida` concatena IDs de los manifiestos de `inpc` y `clasificacion`:
`inpc.manifiesto[*].id_corrida + clasificacion.manifiesto[*].id_corrida`.

| Función | Descripción | Referencia |
|---|---|---|
| `incidencia_periodica(inpc, clasificacion, canastas, frecuencia)` | incidencia periodo a periodo | diseño.md §5.17 |
| `incidencia_acumulada_anual(inpc, clasificacion, canastas)` | acumulado ene→actual | diseño.md §5.17 |
| `incidencia_desde(inpc, clasificacion, canastas, desde, hasta, incluir_parciales)` | incidencia entre dos periodos | diseño.md §5.17 |

---

### Validación interna

Privadas — llamadas solo desde `api/validaciones.py`. Lógica sin cambio; tipo de retorno actualizado: objetos sueltos → `ValidacionX` correspondiente.

| Función | Archivo | Devuelve | Referencia |
|---|---|---|---|
| `validar_inpc` | `dominio/validar_inpc.py` | `ValidacionIndice` | diseño.md §5.11 |
| `validar_variaciones` | `dominio/validar_variaciones.py` | `ValidacionVariacion` | diseño.md §5.16 |
| `validar_incidencias` | `dominio/validar_incidencias.py` | `ValidacionIncidencia` | diseño.md §5.20 |

---

## Decisiones

Sección de referencia. Aquí deben vivir explicaciones de diseño y decisiones de estructura que hoy siguen dispersas o estacionadas en `transiscion.md`. No usar esta sección para schemas, invariantes operativos ni tablas de columnas.

### D1. Separación entre resultados de cálculo y resultados de validación

Referencia: explicar por qué `Resultado*` y `Validacion*` forman jerarquías separadas, y qué frontera conceptual resuelve esa separación.

### D2. Composición de `ValidacionX` sobre `ResultadoX`

Referencia: explicar por qué `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia` contienen un `ResultadoX` internamente (no expuesto como atributo público) en vez de heredar de `Resultado`. `.resultado` expone una `Vista` de comparación INEGI, no el `ResultadoX` subyacente.

### D3. Asimetría estructural entre `ResultadoIndice` y resultados derivados

Referencia: explicar por qué `ResultadoIndice` conserva filas no computables en `.resultado.largo`, mientras `ResultadoVariacion` y `ResultadoIncidencia` tratan esas combinaciones como ausentes del largo y NaN implícito en ancho.

### D4. Separación entre `ManifestUnidad` y `ManifestDerivado`

Referencia: explicar por qué existen dos contratos de manifiesto, qué problema resuelve cada uno y por qué uno es combinable mientras el otro es terminal.

### D5. Adopción de `periodo_referencia` como contrato explícito

Referencia: explicar por qué `periodo_referencia` vive como atributo explícito de `ResultadoIndice`, y cómo gobierna `rebasar`, `empalmar` e incidencias.

### D6. Reubicación de variaciones e incidencias a `dominio/calculo/`

Referencia: explicar por qué `variaciones.py` e `incidencias.py` se mueven fuera de `dominio/` raíz y qué estructura de responsabilidad expresa ese cambio.

### D7. Absorción, renombre y eliminación de contratos v1

Referencia: explicar solo los cambios no triviales de `v1 -> v2`, por ejemplo:

- `ResultadoCalculo` -> `ResultadoIndice` + `Resultado`
- `ResumenValidacionVariaciones` eliminado
- reportes y resúmenes absorbidos por contratos nuevos
- aparición de `ManifestUnidad` y `ManifestDerivado`
