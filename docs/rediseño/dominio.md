# Rediseño dominio/

## Alcance

- Cubre contratos de datos y funciones puras de `dominio/`.
- Excluye IO, infraestructura, orquestación y API pública.
- Excluye strings de periodos; dominio recibe solo `Periodo*`.
- Material transitorio removido de esta sección vive temporalmente en `transiscion.md`.

## Decisiones generales

- `ResultadoCalculo` **eliminado** — renombrado a `ResultadoIndice`.
- `ResultadoIndice` **no** embebe canasta — canasta es parámetro explícito donde se requiere.
- `ResultadoIndice` agrega atributo `periodo_base: PeriodoQuincenal | None`.
- `empalmar` verifica `periodo_base` compatible entre inputs y propaga `reporte`, `diagnostico` y `resumen`.
- `ResumenValidacionVariaciones` eliminado — absorbido por `ValidacionVariacion`.
- Jerarquía separada en dos bases: `Resultado` y `ResultadoValidacion`.
- `ValidacionX` contiene un `ResultadoX` vía composición; no hereda de `Resultado`.
- Invariantes lanzan `InvarianteViolado`, nunca `ValueError`.

---

## Semántica compartida

### Mapa de propiedades

| propiedad | existe en | tipo | significado |
|---|---|---|---|
| `.df` | `Resultado*` | `pd.DataFrame` | resultado mínimo en formato largo |
| `.resultado` | `Resultado*` | `Vista` | resultado completo con metadata; expone formato largo y ancho |
| `.pipe(fn, *args, **kwargs)` | `Resultado*` | callable | encadenamiento estilo pandas sobre objeto resultado |
| `.como_tabla(ancho: bool = False)` | `Resultado*` | `pd.DataFrame` | helper tabular de presentación |
| `_repr_html_()` | `Resultado*` | HTML | representación rica para notebooks |
| `.resumen` | `Resultado*`, `Validacion*` | `pd.DataFrame` | vista compacta; esquema propio de cada subclase |
| `.reporte` | `Resultado*`, `Validacion*` | `pd.DataFrame` | detalle; esquema propio de cada subclase |
| `.diagnostico` | `Resultado*`, `Validacion*` | `pd.DataFrame` | anomalías, faltantes o cobertura; esquema propio de cada subclase |
| `.calculo` | `Validacion*` | `ResultadoX` | resultado validado sobre el que opera la validación |

### Vista compartida de resultados

`Vista` envuelve un `pd.DataFrame` con MultiIndex `(periodo, X)` y agrega acceso uniforme a formato largo y ancho.

- `.resultado` devuelve `Vista`, no `pd.DataFrame` plano.
- `.resultado.largo` devuelve DataFrame completo en formato largo con metadata.
- `.resultado.ancho` devuelve solo columna calculada, pivoteada por `periodo`.
- `Vista` usa `unstack("periodo")`; `periodo` se asume como primer nivel del MultiIndex.

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

### PENDIENTE

- Definir catálogos compartidos por contexto.
- Definir contrato NaN compartido.
- Definir convenciones canónicas de formato largo/ancho e índices.

---

## Contratos de datos

### Semántica compartida global — PROVISIONAL

Comparte semántica entre `Resultado*` y `Validacion*`. Se marca `PROVISIONAL` porque `Validacion*` aún no tiene contrato definitivo.

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

#### PENDIENTE

- Definir catálogos compartidos por contexto.
- Definir contrato NaN compartido.
- Definir convenciones globales de filas ausentes vs NaN.
- Confirmar si `Validacion*` preserva exactamente esta semántica o requiere asimetrías explícitas.

### Semántica compartida de `Resultado` — PROVISIONAL

Comparte semántica entre `ResultadoIndice`, `ResultadoVariacion` y `ResultadoIncidencia`. Se marca `PROVISIONAL` mientras se redistribuyen los contratos concretos.

#### Mapa de propiedades de `Resultado`

| propiedad | tipo | significado |
|---|---|---|
| `.df` | `pd.DataFrame` | resultado mínimo en formato largo |
| `.resultado` | `Vista` | resultado completo con metadata; expone formato largo y ancho |
| `.pipe(fn, *args, **kwargs)` | callable | encadenamiento estilo pandas sobre objeto resultado |
| `.como_tabla(ancho: bool = False)` | `pd.DataFrame` | helper tabular de presentación |
| `_repr_html_()` | HTML | representación rica para notebooks |

#### Semántica de propiedades de `Resultado`

- `.df` = resultado mínimo; contiene solo columna calculada en formato largo.
- `.resultado` = resultado completo; conserva metadata y expone `.largo` y `.ancho`.
- `.resultado.largo` = DataFrame completo con metadata en formato largo.
- `.resultado.ancho` = columna calculada pivoteada por `periodo`.
- `Vista` usa `unstack("periodo")`; `periodo` se asume como primer nivel del MultiIndex.
- `.pipe(fn, *args, **kwargs)` = encadenamiento estilo pandas sobre objeto resultado.
- `.como_tabla(ancho: bool = False)` = helper tabular de presentación.
- `_repr_html_()` = representación rica para notebooks.

#### PENDIENTE

- Confirmar si toda la familia `Resultado*` comparte exactamente esta semántica sin asimetrías adicionales.

### Semántica compartida de `Validacion` — PROVISIONAL

Comparte semántica entre `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia`. Se marca `PROVISIONAL` porque `Validacion*` aún no tiene contrato definitivo.

#### Mapa de propiedades de `Validacion`

| propiedad | tipo | significado |
|---|---|---|
| `.calculo` | `ResultadoX` | resultado validado sobre el que opera la validación |

#### Semántica de propiedades de `Validacion`

- `.calculo` = resultado de dominio que sirve como entrada y referencia principal de la validación.

#### PENDIENTE

- Confirmar propiedades adicionales compartidas por toda la familia `Validacion*`.
- Confirmar si `Validacion*` expone también `.df`, `.pipe`, `.como_tabla` y `_repr_html_()` como contrato común.

### Resultado (base) — NUEVO — PROVISIONAL

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
- subclase valida invariantes propios antes de llamar `super().__init__(df)`.

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

### ResultadoIndice — MODIFICADO — PROVISIONAL

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
    periodo_base: PeriodoQuincenal | None = None,
) -> None:
```

- `df` usa MultiIndex `(periodo, indice)` -> `InvarianteViolado` si no.
- `df` contiene columna `indice_replicado` -> `InvarianteViolado` si no.
- `reporte_df` y `diagnostico_df` se pasan al constructor -> no se reconstruyen desde `df` después del cálculo.
- `.manifiesto` = `list[ManifestUnidad]` -> un elemento por canasta; `empalmar` concatena listas.
- `ManifestUnidad.periodo_base` registra escala base por tramo.
- `.periodo_base` se deriva del manifiesto:
  - un único valor distinto en todas las entradas -> devuelve ese valor
  - `None` en alguna entrada, o valores mixtos -> devuelve `None`
- acceso a `id_corrida` ocurre vía `.manifiesto`; no existe property única para resultados empalmados.

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | MultiIndex `(periodo, indice)` |
| columnas | `indice_replicado` |
| formato | largo mínimo heredado de `Resultado` |
| origen | derivado de `self._df_completo[["indice_replicado"]]` |

#### `.resultado`

| aspecto | contrato |
|---|---|
| tipo | `Vista` |
| columna calculada | `indice_replicado` |
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
| valores | `indice_replicado` pivoteado |
| filas | índices |
| columnas | periodos |
| NaN implícito | no aplica por fila ausente; casos no computados ya pueden existir en largo con `indice_replicado=NaN` |

#### `.resumen`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | `id_corrida` |
| granularidad | una fila por `ManifestUnidad` |
| cálculo | derivado desde `self._df_completo` + `self._manifiesto`; no se almacena |

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

PENDIENTE: redistribuir lentamente desde `transiscion.md` los contratos de `ResultadoVariacion`, `ResultadoIncidencia` y `Validacion*`.

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
