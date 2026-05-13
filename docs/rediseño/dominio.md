# Rediseño dominio/

## Alcance

- Cubre contratos de datos, funciones puras y estructura de módulos de `dominio/`.
- Excluye IO, infraestructura, orquestación y API pública.
- Excluye strings de periodos; dominio recibe solo `Periodo*`.
- Material transitorio removido de esta sección vive temporalmente en `transiscion.md`.

## Decisiones generales

- `ResultadoCalculo` **eliminado** — renombrado a `ResultadoIndice`.
- `ResultadoIndice` **no** embebe canasta — canasta es parámetro explícito donde se requiere.
- `ResultadoIndice` agrega atributo `periodo_referencia: PeriodoQuincenal | PeriodoMensual | None`.
- `empalmar` verifica `periodo_referencia` compatible entre inputs y propaga `reporte`, `diagnostico` y `resumen`.
- `ResumenValidacionVariaciones` eliminado — absorbido por `ValidacionVariacion`.
- Jerarquía separada en dos bases: `Resultado` y `Validacion`.
- `ValidacionX` contiene un `ResultadoX` vía composición; no hereda de `Resultado`.
- Invariantes lanzan `InvarianteViolado`, nunca `ValueError`.

---

## Estructura de archivos

### Raíz de `dominio/`

| archivo | contiene | notas |
|---|---|---|
| `periodos.py` | `PeriodoQuincenal`, `PeriodoMensual`, `periodo_desde_str` | sin cambio |
| `errores.py` | jerarquía de excepciones; `InvarianteViolado` | sin cambio |
| `tipos.py` | `VersionCanasta`, `INDICE_POR_TIPO`, `RANGOS_VALIDOS`, `ManifestUnidad`, `ManifestDerivado` | agrega `ManifestUnidad` y `ManifestDerivado`; reemplaza `ManifestCorrida` y `ResultadoCorrida` de v1 |
| `correspondencia.py` | matcheo canasta↔series por normalización de genéricos; `RENOMBRES_INDICES` | `RENOMBRES_INDICES` cubre todas las versiones: 2010↔2013↔2018↔2024 |
| `conversion.py` | `empalmar`, `rebasar`, `a_mensual` | `combinar` renombrado a `empalmar`; lógica de `rebasar` y `a_mensual` sin cambio |

### `modelos/`

Contratos de datos del dominio. Sin IO, sin lógica de cálculo.

| archivo | contiene | notas |
|---|---|---|
| `canasta.py` | `CanastaCanonica` | sin cambio |
| `serie.py` | `SerieNormalizada` | sin cambio |
| `base.py` | `Resultado` (ABC), `Validacion` (ABC), `Vista` | nuevo |
| `indice.py` | `ResultadoIndice` | renombrado desde `resultado.py`; `ResultadoCalculo` → `ResultadoIndice` |
| `variacion.py` | `ResultadoVariacion` | nuevo en v2 |
| `incidencia.py` | `ResultadoIncidencia` | sin cambio de ubicación; clase modificada en v2 |
| `validacion.py` | `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia` | reescrito; objetos sueltos v1 (`ResumenValidacion`, etc.) absorbidos por estas clases |

### `calculo/`

Funciones y calculadores que **producen** objetos `Resultado*`. Todo output es un objeto de dominio con invariantes y manifiesto.

| archivo | contiene | notas |
|---|---|---|
| `base.py` | `CalculadorBase` (Strategy) | sin cambio |
| `laspeyres_directo.py` | `LaspeyresDirecto` | sin cambio |
| `laspeyres_encadenado.py` | `LaspeyresEncadenadoT1`, `LaspeyresEncadenadoT2` | sin cambio |
| `variaciones.py` | `variacion_periodica`, `variacion_acumulada_anual`, `variacion_desde` | movido desde `dominio/variaciones.py`; tipo actualizado `ResultadoCalculo` → `ResultadoIndice` |
| `incidencias.py` | `incidencia_periodica`, `incidencia_acumulada_anual`, `incidencia_desde` | movido desde `dominio/incidencias.py`; tipos actualizados |

### `consulta/`

Funciones que **extraen información** de objetos `Resultado*` ya calculados. Output: scalars, `pd.DataFrame`, tuplas. Punto de extensión natural para cualquier tipo de análisis sobre resultados.

> **Separación de responsabilidades:** `calculo/` produce objetos de dominio. `consulta/` consulta objetos de dominio. Ambos son dominio puro — la separación es de responsabilidad, no de capa.

| archivo | contiene |
|---|---|
| `variaciones.py` | `inflacion_en`, `inflacion_acumulada`, `inflacion_promedio`, `inflacion_maxima`, `inflacion_minima` |
| `incidencias.py` | `incidencia_en`, `incidencia_acumulada`, `incidencia_promedio`, `mayor_incidencia`, `menor_incidencia` |

### `validacion/`

Privadas — llamadas solo desde `api/validaciones.py`. Cada función recibe un `ResultadoX` y una `FuenteValidacion` (Protocol definido en `aplicacion/`); devuelve el `ValidacionX` correspondiente. No tocan IO — reciben los datos INEGI ya descargados a través del puerto.

| archivo | función principal | devuelve |
|---|---|---|
| `indices.py` | `validar_indices` | `ValidacionIndice` |
| `variaciones.py` | `validar_variaciones` | `ValidacionVariacion` |
| `incidencias.py` | `validar_incidencias` | `ValidacionIncidencia` |

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

##### `VersionCanasta` — tipo de calculador

| versión | tipo | calculador | requiere `referencia` |
|---|---|---|---|
| 2010 | base | `LaspeyresDirecto` | no |
| 2013 | encadenada | `LaspeyresEncadenado*` | sí → versión 2010 |
| 2018 | base | `LaspeyresDirecto` | no |
| 2024 | encadenada | `LaspeyresEncadenado*` | sí → versión 2018 |

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
| `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia` | mismos valores que el `Resultado*` subyacente; propagado sin transformación |

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
    clase: str
    descripcion: str
    fecha: datetime
    inpc_ids: list[str] | None = None
    clasificacion_ids: list[str] | None = None
```

- `id_corrida` = IDs de todas las corridas origen; para incidencias = `inpc_ids + clasificacion_ids`.
- `clase` no vacío → `InvarianteViolado` si no.
- `(inpc_ids is None) == (clasificacion_ids is None)` → `InvarianteViolado` si no.
- `inpc_ids` y `clasificacion_ids` solo se populan para `ResultadoIncidencia`; para variaciones quedan `None`.
- no existe operación de `empalmar` sobre resultados derivados.
- `descripcion` expresa información adicional del derivado; para `"desde"`: incluye el rango de periodos; para otros: puede quedar vacío.

#### Campos

| campo | tipo | contrato |
|---|---|---|
| `id_corrida` | `list[str]` | ids de todas las corridas origen |
| `tipo` | str | tipo de índice derivado |
| `clase` | str | clase del derivado: `"periodica_quincenal"`, `"periodica_mensual"`, `"periodica_bimestral"`, `"periodica_trimestral"`, `"periodica_cuatrimestral"`, `"periodica_semestral"`, `"periodica_anual"`, `"acumulada_anual"`, `"desde"` |
| `descripcion` | str | información adicional legible del derivado; para `"desde"`: incluye el rango de periodos |
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

### ResultadoVariacion — NUEVO — CERRADO

Hereda de `Resultado`. Vive en `dominio/modelos/variacion.py`. En v1 no existía clase — variaciones retornaban `pd.DataFrame` plano.

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
- `clase_variacion` es homogénea y pertenece a `{"periodica_quincenal", "periodica_mensual", "periodica_bimestral", "periodica_trimestral", "periodica_cuatrimestral", "periodica_semestral", "periodica_anual", "acumulada_anual", "desde"}` -> `InvarianteViolado` si no.

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
| `clase_variacion` | str | nunca | `periodica_quincenal`, `periodica_mensual`, `periodica_bimestral`, `periodica_trimestral`, `periodica_cuatrimestral`, `periodica_semestral`, `periodica_anual`, `acumulada_anual`, `desde` |
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

| columna | tipo | notas |
|---|---|---|
| `tipo` | str | — |
| `clase_variacion` | str | — |
| `descripcion` | str | no vacío solo cuando `clase_variacion = "desde"`; vacío en otros casos |
| `estado_calculo` | str | — |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` | — |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` | — |

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

Hereda de `Resultado`. Permanece en `dominio/modelos/incidencia.py`.

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
- `clase_incidencia` es homogénea y pertenece a `{"periodica_quincenal", "periodica_mensual", "periodica_bimestral", "periodica_trimestral", "periodica_cuatrimestral", "periodica_semestral", "periodica_anual", "acumulada_anual", "desde"}` -> `InvarianteViolado` si no.

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
| `clase_incidencia` | str | nunca | `periodica_quincenal`, `periodica_mensual`, `periodica_bimestral`, `periodica_trimestral`, `periodica_cuatrimestral`, `periodica_semestral`, `periodica_anual`, `acumulada_anual`, `desde` |
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

| columna | tipo | notas |
|---|---|---|
| `tipo` | str | — |
| `clase_incidencia` | str | — |
| `descripcion` | str | no vacío solo cuando `clase_incidencia = "desde"`; vacío en otros casos |
| `estado_calculo` | str | — |
| `periodo_inicio` | `PeriodoQuincenal \| PeriodoMensual` | — |
| `periodo_fin` | `PeriodoQuincenal \| PeriodoMensual` | — |

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

### Transformaciones de ResultadoIndice — `dominio/conversion.py`

#### empalmar — MODIFICADO — CERRADO

##### Firma

```python
def empalmar(
    resultados: list[ResultadoIndice],
    forzar: bool = False,
    version_nombres: VersionCanasta | None = None,
) -> ResultadoIndice:
```

##### Responsabilidad

Concatena tramos del mismo `tipo` en un único `ResultadoIndice`, normalizando nombres de categorías entre versiones de canasta.

##### Precondiciones

| condición | si no se cumple |
|---|---|
| `len(resultados) >= 2` | `InvarianteViolado` |
| todos los inputs tienen el mismo `manifiesto[i].tipo` | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=False` | `InvarianteViolado` |

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `resultados` | `list[ResultadoIndice]` | orden cronológico; al menos dos elementos; mismo `tipo` |
| `forzar` | `bool` | si `True`, permite `periodo_referencia` distintos emitiendo `UserWarning` |
| `version_nombres` | `VersionCanasta \| None` | versión de referencia para normalizar categorías; `None` = `max(versions)` de los inputs |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | `.manifiesto` = concatenación de todos los inputs; `.resumen`, `.reporte`, `.diagnostico` mergeados; `periodo_referencia` resuelto según postcondiciones |

##### Postcondiciones

- `periodo_referencia` resuelto:
  - todos `None` → resultado `None`
  - mezcla `None` + un único valor explícito → hereda ese valor
  - `forzar=True` + dos valores explícitos distintos → `UserWarning` describiendo cada `periodo_referencia`
- `version_nombres` resuelto: `None` → `max(versions)` de inputs; si no existe mapa `(tipo, version)` en `RENOMBRES_INDICES`, los índices de ese tramo no se renombran
- Entradas no mutadas

##### Errores y advertencias

| condición | resultado |
|---|---|
| `len(resultados) < 2` | `InvarianteViolado` |
| `tipo` distinto entre inputs | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=False` | `InvarianteViolado` |
| `periodo_referencia` distintos con `forzar=True` | `UserWarning` |

##### Efectos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

> **Restricción:** solo para `ResultadoIndice`. No existe `empalmar` para `ResultadoVariacion` ni `ResultadoIncidencia` — siempre empalmar el `ResultadoIndice` fuente antes de calcular variaciones o incidencias.

##### Ejemplo mínimo

```python
hist = empalmar([indice_2018, indice_2024])
hist_2018 = empalmar([indice_2018, indice_2024], version_nombres=2018)
```

---

#### rebasar — SIN CAMBIO — CERRADO

##### Firma

```python
def rebasar(
    resultado: ResultadoIndice,
    periodo_referencia: PeriodoQuincenal | PeriodoMensual,
    valor_base: float = 100.0,
) -> ResultadoIndice:
```

##### Responsabilidad

Reexpresa todos los índices de `resultado` relativo a `periodo_referencia`: `valor / valor_en_ref × valor_base`.

##### Precondiciones

| condición | si no se cumple |
|---|---|
| `periodo_referencia` existe en `resultado` | `InvarianteViolado` |
| valor de algún índice en `periodo_referencia` no es NaN (`sin_datos` o `fallida`) | `InvarianteViolado` |

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | resultado a reexpresar; quincenal o mensual |
| `periodo_referencia` | `PeriodoQuincenal \| PeriodoMensual` | periodo en que los índices valdrán `valor_base` |
| `valor_base` | `float` | valor de referencia; default `100.0` |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | mismo contenido reescalado; `.periodo_referencia` seteado al periodo indicado |

##### Postcondiciones

- `resultado` original no mutado
- salida mantiene invariantes de `ResultadoIndice`
- `.periodo_referencia` del resultado = `periodo_referencia`

##### Errores y advertencias

| condición | resultado |
|---|---|
| `periodo_referencia` no existe en `resultado` | `InvarianteViolado` |
| índice con `estado_calculo = sin_datos` o `fallida` en `periodo_referencia` | `InvarianteViolado` |

##### Efectos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Ejemplo mínimo

```python
rebased = rebasar(hist, periodo_referencia=PeriodoQuincenal(2018, 7, 2))
```

---

#### a_mensual — SIN CAMBIO — CERRADO

##### Firma

```python
def a_mensual(resultado: ResultadoIndice) -> ResultadoIndice:
```

##### Responsabilidad

Convierte un `ResultadoIndice` quincenal a mensual promediando 1Q y 2Q de cada mes.

##### Precondiciones

| condición | si no se cumple |
|---|---|
| `resultado` tiene periodos quincenales (`PeriodoQuincenal`) | `InvarianteViolado` |

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | resultado quincenal a convertir |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | periodos = `PeriodoMensual`; valor = promedio simple 1Q y 2Q; si solo una quincena disponible → `estado_calculo = parcial` |

##### Postcondiciones

- `resultado` original no mutado
- salida mantiene invariantes de `ResultadoIndice`
- todos los periodos del resultado son `PeriodoMensual`

##### Errores y advertencias

| condición | resultado |
|---|---|
| `resultado` ya tiene periodos mensuales | `InvarianteViolado` |

##### Efectos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Ejemplo mínimo

```python
mensual = a_mensual(indice)
```

---

### Cálculo de variaciones — `dominio/calculo/variaciones.py`

#### Grupo: variaciones — SIN CAMBIO — CERRADO

##### Semántica compartida

- Todas reciben `resultado: ResultadoIndice`
- Todas devuelven `ResultadoVariacion`
- Todas expresan variación en puntos porcentuales en columna `variacion_pp`
- Sin IO; sin infraestructura; entradas no mutadas

##### Funciones

| función | firma | retorno | contrato específico |
|---|---|---|---|
| `variacion_periodica` | `(resultado, frecuencia)` | `ResultadoVariacion` | una variación por periodo según `frecuencia` |
| `variacion_acumulada_anual` | `(resultado)` | `ResultadoVariacion` | ene→periodo_actual vs dic_año_anterior; una fila por periodo |
| `variacion_desde` | `(resultado, desde, hasta, incluir_parciales)` | `ResultadoVariacion` | variación total del rango; una fila por índice |

##### Precondiciones compartidas

| condición | si no se cumple |
|---|---|
| `resultado` con al menos un periodo computable | `InvarianteViolado` |

##### Postcondiciones compartidas

- `resultado` original no mutado
- salida mantiene invariantes de `ResultadoVariacion`

##### Errores y advertencias compartidos

Ninguno aplicable a todas las funciones. Ver errores en cada subfunción.

##### Efectos compartidos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Diferencias por función

###### `variacion_periodica`

| aspecto | contrato |
|---|---|
| parámetro extra | `frecuencia: Literal["quincenal", "mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual"]` |
| regla temporal | vs N periodos anteriores: quincenal=1Q, mensual=1M, bimestral=2M, trimestral=3M, cuatrimestral=4M, semestral=6M, anual=12M |
| filas ausentes | periodos sin periodo anterior disponible en `resultado` |
| error: `frecuencia` inválida | `frecuencia` fuera del conjunto válido → `InvarianteViolado` |
| error: frecuencia incompatible | `frecuencia="quincenal"` con resultado mensual → `InvarianteViolado` |

###### `variacion_acumulada_anual`

| aspecto | contrato |
|---|---|
| regla temporal | ene_año → periodo_actual vs dic_año_anterior |
| filas ausentes | periodos donde dic_año_anterior no existe en `resultado` |

###### `variacion_desde`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoQuincenal \| PeriodoMensual`, `hasta: PeriodoQuincenal \| PeriodoMensual \| None`, `incluir_parciales: bool = True` |
| `hasta=None` | último periodo disponible en `resultado` |
| `incluir_parciales=False` | excluye periodos con `estado_calculo = parcial` |
| dimensión del resultado | una fila por índice (no por periodo) |
| precondición: rango válido | `desde` no posterior a `hasta` → `InvarianteViolado` |
| precondición: periodos existen | `desde`/`hasta` deben existir en `resultado` → `InvarianteViolado` |

##### Ejemplo mínimo

```python
vars_m = variacion_periodica(indice, frecuencia="mensual")
acum   = variacion_acumulada_anual(indice)
rango  = variacion_desde(indice, desde=PeriodoMensual(2015, 1), hasta=PeriodoMensual(2024, 12))
```

---

### Cálculo de incidencias — `dominio/calculo/incidencias.py`

#### Grupo: incidencias — SIN CAMBIO — CERRADO

##### Semántica compartida

- Todas reciben `inpc: ResultadoIndice`, `clasificacion: ResultadoIndice`, `canastas: dict[int, CanastaCanonica]`
- Todas devuelven `ResultadoIncidencia`
- Todas expresan incidencia en puntos porcentuales en columna `incidencia_pp`
- `id_corrida` del `ManifestDerivado` concatena IDs de los manifiestos de `inpc` y `clasificacion`
- Sin IO; sin infraestructura; entradas no mutadas

##### Funciones

| función | firma | retorno | contrato específico |
|---|---|---|---|
| `incidencia_periodica` | `(inpc, clasificacion, canastas, frecuencia)` | `ResultadoIncidencia` | incidencia periodo a periodo por genérico |
| `incidencia_acumulada_anual` | `(inpc, clasificacion, canastas)` | `ResultadoIncidencia` | ene→periodo_actual; suma de genéricos = variación anual acumulada del INPC |
| `incidencia_desde` | `(inpc, clasificacion, canastas, desde, hasta, incluir_parciales)` | `ResultadoIncidencia` | incidencia total del rango; una fila por genérico |

##### Precondiciones compartidas

| condición | si no se cumple |
|---|---|
| `inpc.periodo_referencia == clasificacion.periodo_referencia` | `InvarianteViolado` |
| ambos `periodo_referencia = None` → misma escala asumida; responsabilidad del llamador | — |

##### Postcondiciones compartidas

- entradas no mutadas
- salida mantiene invariantes de `ResultadoIncidencia`

##### Errores y advertencias compartidos

| condición | resultado |
|---|---|
| `inpc.periodo_referencia != clasificacion.periodo_referencia` | `InvarianteViolado` |

##### Efectos compartidos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Diferencias por función

###### `incidencia_periodica`

| aspecto | contrato |
|---|---|
| parámetro extra | `frecuencia: Literal["quincenal", "mensual", "bimestral", "trimestral", "cuatrimestral", "semestral", "anual"]` |
| regla temporal | vs N periodos anteriores: quincenal=1Q, mensual=1M, bimestral=2M, trimestral=3M, cuatrimestral=4M, semestral=6M, anual=12M |
| error: `frecuencia` inválida | `frecuencia` fuera del conjunto válido → `InvarianteViolado` |
| error: frecuencia incompatible | `frecuencia="quincenal"` con resultado mensual → `InvarianteViolado` |

###### `incidencia_acumulada_anual`

| aspecto | contrato |
|---|---|
| regla temporal | ene_año → periodo_actual vs dic_año_anterior |
| propiedad clave | suma de `incidencia_pp` de todos los genéricos = variación anual acumulada del INPC en ese periodo |

###### `incidencia_desde`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoQuincenal \| PeriodoMensual \| None`, `hasta: PeriodoQuincenal \| PeriodoMensual \| None`, `incluir_parciales: bool = True` |
| `desde=None` | primer periodo disponible |
| `hasta=None` | último periodo disponible |
| `incluir_parciales=False` | excluye genéricos con `estado_calculo = parcial` |
| precondición: rango válido | `desde` no posterior a `hasta` → `InvarianteViolado` |
| precondición: periodos existen | `desde`/`hasta` deben existir en resultado cuando se especifican → `InvarianteViolado` |

##### Ejemplo mínimo

```python
inc_m = incidencia_periodica(inpc, clasificacion, canastas, frecuencia="mensual")
inc_a = incidencia_acumulada_anual(inpc, clasificacion, canastas)
rango = incidencia_desde(inpc, clasificacion, canastas, desde=PeriodoMensual(2024, 1))
```

---

### Consulta de variaciones — `dominio/consulta/variaciones.py`

#### Grupo: inflación — NUEVO — CERRADO

##### Semántica compartida

- Todas reciben `resultado: ResultadoVariacion`
- Devuelven escalares, pares o DataFrame — no `ResultadoX`
- Operan sobre `variacion_pp`; sin IO; sin infraestructura; `resultado` no mutado
- `inflacion_acumulada` e `inflacion_promedio` solo tienen sentido si `resultado` proviene de `variacion_periodica`; con `variacion_desde` o `variacion_acumulada_anual` los valores ya son totales

##### Funciones

| función | firma | retorno | contrato específico |
|---|---|---|---|
| `inflacion_en` | `(resultado, periodo)` | `pd.DataFrame` | índice=`indice`; col=`variacion_pp`; todas las categorías en el periodo |
| `inflacion_acumulada` | `(resultado, desde, hasta, indice)` | `float` | suma de `variacion_pp` en `[desde, hasta]` para el `indice` |
| `inflacion_promedio` | `(resultado, desde, hasta, indice, metodo)` | `float` | TCAC o media aritmética en el rango para el `indice` |
| `inflacion_maxima` | `(resultado, desde, hasta, indice)` | `tuple[PeriodoX, str, float]` | `(periodo, indice, variacion_pp)` del máximo en el rango |
| `inflacion_minima` | `(resultado, desde, hasta, indice)` | `tuple[PeriodoX, str, float]` | `(periodo, indice, variacion_pp)` del mínimo en el rango |

##### Precondiciones compartidas

| condición | si no se cumple |
|---|---|
| `periodo`/`desde`/`hasta` existen en `resultado` cuando se especifican | `InvarianteViolado` |
| `indice` existe en `resultado` cuando se especifica | `InvarianteViolado` |

##### Postcondiciones compartidas

- `resultado` original no mutado
- sin IO; sin infraestructura

##### Errores y advertencias compartidos

| condición | aplica a | resultado |
|---|---|---|
| `periodo` no existe en resultado | `inflacion_en` | `InvarianteViolado` |
| `desde`/`hasta` no existe en resultado | `inflacion_acumulada`, `inflacion_promedio`, `inflacion_maxima`, `inflacion_minima` | `InvarianteViolado` |
| `desde` posterior a `hasta` | `inflacion_acumulada`, `inflacion_promedio`, `inflacion_maxima`, `inflacion_minima` | `InvarianteViolado` |
| `indice` no existe en resultado | `inflacion_acumulada`, `inflacion_promedio`; `inflacion_maxima`/`minima` cuando se especifica | `InvarianteViolado` |

##### Efectos compartidos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Diferencias por función

###### `inflacion_en`

| aspecto | contrato |
|---|---|
| parámetro extra | `periodo: PeriodoQuincenal \| PeriodoMensual` |
| retorno | `pd.DataFrame`; índice=`indice`; col=`variacion_pp`; todas las categorías |

###### `inflacion_acumulada`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX`, `hasta: PeriodoX \| None`, `indice: str` |
| `hasta=None` | último periodo disponible |
| retorno | `float` = suma de `variacion_pp` en el rango |

###### `inflacion_promedio`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None`, `hasta: PeriodoX \| None`, `indice: str`, `metodo: Literal["tcac", "simple"] = "tcac"` |
| `desde=None` | primer periodo disponible |
| `hasta=None` | último periodo disponible |
| `metodo="tcac"` | tasa de crecimiento anual compuesta |
| `metodo="simple"` | media aritmética de `variacion_pp` |

###### `inflacion_maxima`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None = None`, `hasta: PeriodoX \| None = None`, `indice: str \| None = None` |
| `desde=None` | sin límite inferior |
| `hasta=None` | sin límite superior |
| `indice=None` | máximo global entre todos los índices y periodos del rango |
| retorno | `tuple[PeriodoX, str, float]` = `(periodo, indice, variacion_pp)` |

###### `inflacion_minima`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None = None`, `hasta: PeriodoX \| None = None`, `indice: str \| None = None` |
| `desde=None` | sin límite inferior |
| `hasta=None` | sin límite superior |
| `indice=None` | mínimo global entre todos los índices y periodos del rango |
| retorno | `tuple[PeriodoX, str, float]` = `(periodo, indice, variacion_pp)` |

##### Ejemplo mínimo

```python
df      = inflacion_en(vars_m, periodo=PeriodoMensual(2024, 12))
acum    = inflacion_acumulada(vars_m, desde=PeriodoMensual(2024, 1), hasta=PeriodoMensual(2024, 12), indice="inpc")
p, i, v = inflacion_maxima(vars_m)
```

---

### Consulta de incidencias — `dominio/consulta/incidencias.py`

#### Grupo: consulta de incidencias — NUEVO — CERRADO

##### Semántica compartida

- Todas reciben `resultado: ResultadoIncidencia`
- Devuelven escalares, pares o DataFrame — no `ResultadoX`
- Operan sobre `incidencia_pp`; sin IO; sin infraestructura; `resultado` no mutado
- `incidencia_acumulada` e `incidencia_promedio` solo tienen sentido si `resultado` proviene de `incidencia_periodica`; con `incidencia_desde` o `incidencia_acumulada_anual` los valores ya son totales

##### Funciones

| función | firma | retorno | contrato específico |
|---|---|---|---|
| `incidencia_en` | `(resultado, periodo)` | `pd.DataFrame` | índice=`indice`; col=`incidencia_pp`; todas las categorías en el periodo |
| `incidencia_acumulada` | `(resultado, desde, hasta, indice)` | `float` | suma de `incidencia_pp` en `[desde, hasta]` para el `indice` |
| `incidencia_promedio` | `(resultado, desde, hasta, indice)` | `float` | media aritmética de `incidencia_pp` en el rango para el `indice` |
| `mayor_incidencia` | `(resultado, desde, hasta, indice)` | `tuple[PeriodoX, str, float]` | `(periodo, indice, incidencia_pp)` del máximo en el rango |
| `menor_incidencia` | `(resultado, desde, hasta, indice)` | `tuple[PeriodoX, str, float]` | `(periodo, indice, incidencia_pp)` del mínimo en el rango |

##### Precondiciones compartidas

| condición | si no se cumple |
|---|---|
| `periodo`/`desde`/`hasta` existen en `resultado` cuando se especifican | `InvarianteViolado` |
| `indice` existe en `resultado` cuando se especifica | `InvarianteViolado` |

##### Postcondiciones compartidas

- `resultado` original no mutado
- sin IO; sin infraestructura

##### Errores y advertencias compartidos

| condición | aplica a | resultado |
|---|---|---|
| `periodo` no existe en resultado | `incidencia_en` | `InvarianteViolado` |
| `desde`/`hasta` no existe en resultado | `incidencia_acumulada`, `incidencia_promedio`, `mayor_incidencia`, `menor_incidencia` | `InvarianteViolado` |
| `desde` posterior a `hasta` | `incidencia_acumulada`, `incidencia_promedio`, `mayor_incidencia`, `menor_incidencia` | `InvarianteViolado` |
| `indice` no existe en resultado | `incidencia_acumulada`, `incidencia_promedio`; `mayor_incidencia`/`menor_incidencia` cuando se especifica | `InvarianteViolado` |

##### Efectos compartidos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

##### Diferencias por función

###### `incidencia_en`

| aspecto | contrato |
|---|---|
| parámetro extra | `periodo: PeriodoQuincenal \| PeriodoMensual` |
| retorno | `pd.DataFrame`; índice=`indice`; col=`incidencia_pp`; todas las categorías |

###### `incidencia_acumulada`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX`, `hasta: PeriodoX \| None`, `indice: str` |
| `hasta=None` | último periodo disponible |
| retorno | `float` = suma de `incidencia_pp` en el rango |

###### `incidencia_promedio`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None`, `hasta: PeriodoX \| None`, `indice: str` |
| `desde=None` | primer periodo disponible |
| `hasta=None` | último periodo disponible |
| retorno | `float` = media aritmética de `incidencia_pp` en el rango |

###### `mayor_incidencia`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None = None`, `hasta: PeriodoX \| None = None`, `indice: str \| None = None` |
| `desde=None` | sin límite inferior |
| `hasta=None` | sin límite superior |
| `indice=None` | máximo global entre todos los índices y periodos del rango |
| retorno | `tuple[PeriodoX, str, float]` = `(periodo, indice, incidencia_pp)` |

###### `menor_incidencia`

| aspecto | contrato |
|---|---|
| parámetros extra | `desde: PeriodoX \| None = None`, `hasta: PeriodoX \| None = None`, `indice: str \| None = None` |
| `desde=None` | sin límite inferior |
| `hasta=None` | sin límite superior |
| `indice=None` | mínimo global entre todos los índices y periodos del rango |
| retorno | `tuple[PeriodoX, str, float]` = `(periodo, indice, incidencia_pp)` |

##### Ejemplo mínimo

```python
df      = incidencia_en(inc_m, periodo=PeriodoMensual(2024, 12))
p, i, v = mayor_incidencia(inc_m)
p, i, v = mayor_incidencia(inc_m, indice="Alimentos")
```

---

### Validación interna — PENDIENTE

Privadas — llamadas solo desde `api/validaciones.py`. Contratos completos pendientes; se documentarán al implementar.

| Función | Archivo | Devuelve |
|---|---|---|
| `validar_indices` | `dominio/validacion/indices.py` | `ValidacionIndice` |
| `validar_variaciones` | `dominio/validacion/variaciones.py` | `ValidacionVariacion` |
| `validar_incidencias` | `dominio/validacion/incidencias.py` | `ValidacionIncidencia` |

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
