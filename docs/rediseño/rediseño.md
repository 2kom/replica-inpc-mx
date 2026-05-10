# Rediseño del proyecto

Documento rector. Define los principios que gobiernan todos los documentos de diseño en `docs/rediseño/`.

## Propósito e intención

Los documentos en `docs/rediseño/` son la **futura `docs/diseño.md`**, no un borrador temporal. Al completarse v2, estos documentos reemplazan a `docs/diseño.md` y se convierten en la fuente de verdad del sistema. Todo lo que se escriba aquí debe estar redactado con esa permanencia en mente.

`docs/diseño.md` sigue vigente solo para las secciones de v1 que `docs/rediseño/` aún no ha supersedido. Las secciones supersedidas se marcan explícitamente en `diseño.md` con una referencia al archivo de rediseño correspondiente.

---

## Principios de documentación

### 1. Separación Reference / Explanation

Cada decisión de diseño tiene dos partes distintas que nunca deben mezclarse:

| tipo | pregunta | dónde vive |
|---|---|---|
| **Reference** | ¿qué es? ¿qué devuelve? ¿cuáles son sus invariantes? | contratos de datos, firmas |
| **Explanation** | ¿por qué este diseño y no otro? | sección `## Decisiones` al final del archivo |

Mezclar el "qué" con el "por qué" en la misma sección produce prosa difícil de actualizar y de indexar.

---

### 2. Semántica una vez, schemas por clase

Cuando varias clases comparten el mismo concepto (`.resultado`, `.reporte`, `.diagnostico`, `estado_calculo`), la **semántica** se documenta una sola vez en una sección compartida. Cada clase solo documenta su **schema** (columnas, tipos, invariantes propios).

**Prohibido:** copiar y pegar la descripción de `.reporte` en `ResultadoVariacion` y en `ResultadoIncidencia` con cambios menores. Si hay diferencias, van en una subsección explícita de la clase.

---

### 3. Invariantes como proposiciones, no como prose

Los contratos se expresan como afirmaciones verificables:

```
✓  "filas con estado_calculo=sin_datos están AUSENTES en .resultado.largo"
✗  "podrías notar que las filas con estado sin_datos no aparecen en el largo"
```

Cada invariante en una línea. Formato: condición → consecuencia.

---

### 4. Catálogos centralizados

Un catálogo (lista de valores posibles + significado) se define **una sola vez** en la sección semántica compartida, con etiqueta de contexto. Las secciones de cada clase solo referencian el catálogo, nunca lo repiten.

Ejemplo: `estado_calculo` tiene tres catálogos distintos según el contexto (`.resultado.largo`, `.reporte`, `.resumen`). Los tres se documentan juntos en la sección semántica, con su contexto etiquetado.

---

### 5. Asimetrías documentadas explícitamente

Cuando una clase se comporta distinto al patrón base, la diferencia se pone en una subsección **`> Asimetrías`** al inicio de la sección de la clase. No se esconde en prose ni se asume que el lector la infiere.

Ejemplo:

> **Asimetría respecto al patrón `ResultadoDerivado`:** `ResultadoIndice.resultado.largo` incluye filas con `indice_replicado=NaN` cuando `estado_calculo` es `sin_datos` o `fallida`. Los derivados (`ResultadoVariacion`, `ResultadoIncidencia`) omiten esas filas — el NaN es implícito en `.resultado.ancho`.

---

### 6. La estructura responde las preguntas frecuentes

El documento debe estar organizado de forma que las preguntas de uso habitual se respondan por la estructura, no por comentarios inline.

Preguntas que la estructura debe responder sola:

- ¿Cuándo uso `.df` vs `.resultado.largo`?
- ¿Cuándo uso `.reporte` vs `.diagnostico`?
- ¿Qué valores puede tener `estado_calculo` aquí?
- ¿Esta propiedad existe en todas las clases o solo en esta?

Si alguna de estas preguntas requiere leer prose para responderse, la estructura está fallando.

---

### 7. Contrato NaN explícito

Todo DataFrame documentado debe indicar explícitamente:

- Qué columnas pueden contener NaN y bajo qué condición
- Si una fila puede estar **ausente** (vs presente con NaN)
- Si el NaN es "implícito" en formato ancho (por `unstack`)

Formato sugerido: tabla con columna `NaN cuando`.

---

### 8. Sin forward references implícitas

Si una sección referencia un concepto definido en otra, usa un enlace explícito o una nota `(ver §X.Y)`. No asumas que el lector leyó en orden.

---

### 9. Decisiones van al final

Toda decisión de diseño (¿por qué no X?, ¿por qué Y en vez de Z?) va en la sección `## Decisiones` al final del archivo, con número secuencial. El cuerpo del documento solo describe el diseño resultante.

---

### 10. Nivel de abstracción consistente por sección

Cada sección adopta una perspectiva y no la mezcla:

- **Perspectiva de usuario** (Reference): `inpc.resultado.largo`, `rep.calcular_indice(...)`
- **Perspectiva de implementación**: `self._df_completo`, `super().__init__(...)`

La sección de contratos usa perspectiva de usuario. La perspectiva de implementación va en comentarios de código o en la sección de decisiones, no en el contrato.

---

### 11. Estado explícito de cada sección

Toda sección de contrato lleva una etiqueta de estado en el encabezado:

| etiqueta | significado |
|---|---|
| `CERRADO` | contrato estable, puede implementarse |
| `PROVISIONAL` | firmas definidas, pueden cambiar al implementar |
| `PENDIENTE` | no definido aún — no implementar |

Sin etiqueta = no se sabe si es confiable. Un documento con secciones sin etiqueta no puede usarse como fuente de verdad para implementar.

---

### 12. Alcance declarado al inicio de cada archivo

Todo archivo de diseño comienza con una sección corta que declara:
- Qué cubre este archivo
- Qué excluye intencionalmente (y dónde encontrarlo si aplica)

Evita que el lector busque información que no está porque nunca debió estar aquí.

---

### 13. Ejemplos mínimos para comportamiento no obvio

No tutoriales. Para propiedades con comportamiento contraintuitivo, un snippet de 2-3 líneas es más claro que tres oraciones de prose.

Criterio: si la descripción en prose requiere más de dos cláusulas condicionales ("si X entonces Y, pero si Z entonces W"), agregar un ejemplo.

---

### 14. Sin gaps implícitos

Si algo está sin decidir, se escribe explícitamente en el lugar donde debería estar la información:

```
PENDIENTE: definir comportamiento de .reporte cuando manifiesto tiene múltiples versiones
```

No se deja ausente. Un gap implícito es un bug en la documentación.

---

### 15. Single source of truth entre archivos

Ninguna información se duplica entre `docs/diseño.md` y `docs/rediseño/`. Regla de propiedad:

- Si la sección existe en `docs/rediseño/` → es la fuente de verdad; `docs/diseño.md` referencia hacia allá
- Si solo existe en `docs/diseño.md` → sigue vigente hasta que `docs/rediseño/` la superseda
- Nunca dos versiones del mismo contrato en dos archivos sin que una referencie explícitamente a la otra

---

### 16. Doc-first

El contrato se escribe y se marca `CERRADO` **antes** de implementar. Si el código existe y el doc no, el doc está en deuda. No se acepta documentar código ya escrito como si fuera diseño — eso produce docs que describen la implementación en vez de contratos que la guían.

---

### 17. Invariantes documentados = tests existentes

Todo invariante en un contrato tiene un test correspondiente que lo verifica. Un invariante sin test es una promesa sin garantía. Al implementar: si no puedes escribir el test para el invariante, el invariante está mal definido — se regresa al doc.

---

### 18. Orden canónico dentro de secciones de clase

Todas las secciones de clase siguen el mismo orden interno. El lector sabe dónde buscar sin leer la sección entera:

```
> Asimetrías              ← si aplica; va primero
Constructor + invariantes
.df
.resultado (.largo / .ancho)
.indices_parciales        ← si aplica
.resumen
.reporte
.diagnostico
```

---

### 19. Actualizaciones atómicas

Cambiar un nombre de concepto o renombrar una columna = un solo commit que actualiza **doc + código + tests** simultáneamente. No se acepta un estado intermedio donde parte del sistema usa el nombre viejo. Si el cambio es demasiado grande para un solo commit, se bifurca en una rama y se fusiona al terminar — nunca se fusiona parcial.

---

## Estructura estándar de un archivo de capa

```
# Rediseño <capa>/

## Alcance
  - Cubre:
  - Excluye:
  - Fuente de verdad:

## Decisiones generales
  [Lista de decisiones de alto nivel — sin prosa, bullets]

## Semántica compartida
  [Solo si hay ≥2 contratos con comportamiento compartido]
  - Mapa de propiedades
  - Catálogos por contexto
  - Contrato NaN
  - Convenciones de nombres

## Contratos / Puertos / API / Funciones
  [Usar la plantilla específica del tipo de contrato]

## Funciones
  [Solo si aplica; una subsección por función o grupo relacionado]

## Decisiones
  [§D1, §D2, ... — cada decisión numerada]
```

---

## Plantilla: dominio / contratos de datos

Esta plantilla aplica a `docs/rediseño/dominio.md`, sección `## Contratos de datos`. No aplica a contratos de API, puertos, casos de uso ni funciones de dominio.

### Semántica compartida

```
## Semántica compartida — [CERRADO | PROVISIONAL | PENDIENTE]

### Mapa de propiedades

| propiedad | existe en | tipo | significado | contrato |
|---|---|---|---|---|
| `.df` | ... | `pd.DataFrame` | ... | §... |
| `.resultado` | ... | `Vista` | ... | §... |

### Catálogos

#### `<catalogo>` en `<contexto>`

| valor | significado | aplica en |
|---|---|---|
| ... | ... | ... |

### Contrato NaN

| contexto | columna | NaN cuando | fila ausente cuando | NaN implícito en ancho |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

### Convenciones

- Formato largo: ...
- Formato ancho: ...
- Índices: ...
```

### Contrato de clase de dominio

````
### NombreClase — [NUEVO | MODIFICADO | SIN CAMBIO] — [CERRADO | PROVISIONAL | PENDIENTE]

> **Asimetrías respecto a `<patrón/base>`:**
> Omitir si no aplica.

#### Constructor + invariantes

```python
def __init__(...) -> None:
    ...
```

- condición → consecuencia
- condición inválida → `InvarianteViolado`

#### `.df`

| aspecto | contrato |
|---|---|
| tipo | `pd.DataFrame` |
| índice | ... |
| columnas | ... |
| filas ausentes | ... |
| NaN | ver §Semántica compartida / Contrato NaN |

#### `.resultado`

Devuelve: `Vista`.

##### `.resultado.largo`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| ... | ... | ... | ... |

##### `.resultado.ancho`

| aspecto | contrato |
|---|---|
| filas | ... |
| columnas | ... |
| valores | ... |
| NaN implícito | ... |

#### `.indices_parciales`

Omitir si no aplica.

| aspecto | contrato |
|---|---|
| tipo | ... |
| existe cuando | ... |
| índice | ... |
| columnas | ... |

#### `.resumen`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| ... | ... | ... | ... |

#### `.reporte`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| ... | ... | ... | ... |

#### `.diagnostico`

| columna | tipo | NaN cuando | notas |
|---|---|---|---|
| ... | ... | ... | ... |

#### PENDIENTE

- PENDIENTE: definir ...
````

---

## Plantilla: dominio / funciones de dominio

Esta plantilla aplica a `docs/rediseño/dominio.md`, sección `## Funciones de dominio`. No aplica a contratos de datos, API pública, puertos ni casos de uso.

### Función individual

Usar para funciones con contrato propio completo: `empalmar`, `rebasar`, `a_mensual`.

````
### nombre_funcion — [NUEVO | MODIFICADO | SIN CAMBIO] — [CERRADO | PROVISIONAL | PENDIENTE]

#### Firma

```python
def nombre_funcion(...) -> TipoRetorno:
    ...
```

#### Responsabilidad

Una frase. Qué garantiza la función, no por qué existe.

#### Precondiciones

| condición | si no se cumple |
|---|---|
| ... | `InvarianteViolado` |
| ... | `UserWarning` |

#### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | ... |
| `periodo_base` | `PeriodoQuincenal | PeriodoMensual` | ... |

#### Retorno

| tipo | contrato |
|---|---|
| `ResultadoIndice` | ... |

#### Postcondiciones

- condición de entrada válida → propiedad garantizada
- `resultado` original → no mutado
- salida → mantiene invariantes de `ResultadoX`

#### Errores y advertencias

| condición | resultado |
|---|---|
| ... | `InvarianteViolado` |
| ... | `UserWarning` |

#### Efectos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |
| usa fecha/hora actual | no/sí, condición |

#### Ejemplo mínimo

```python
...
```

#### PENDIENTE

- PENDIENTE: definir ...
````

### Grupo de funciones

Usar cuando varias funciones comparten semántica y solo difieren en una regla específica: variaciones, incidencias, validación interna.

````
### Nombre del grupo — [NUEVO | MODIFICADO | SIN CAMBIO] — [CERRADO | PROVISIONAL | PENDIENTE]

#### Semántica compartida

- Todas reciben ...
- Todas devuelven ...
- Todas preservan ...
- Todas registran ...

#### Funciones

| función | firma | retorno | contrato específico |
|---|---|---|---|
| `funcion_a` | `...` | `ResultadoX` | ... |
| `funcion_b` | `...` | `ResultadoX` | ... |

#### Precondiciones compartidas

| condición | si no se cumple |
|---|---|
| ... | `InvarianteViolado` |

#### Postcondiciones compartidas

- condición de entrada válida → propiedad garantizada
- entradas originales → no mutadas
- salida → mantiene invariantes de `ResultadoX`

#### Errores y advertencias compartidos

| condición | resultado |
|---|---|
| ... | `InvarianteViolado` |
| ... | `UserWarning` |

#### Efectos compartidos

| efecto | contrato |
|---|---|
| IO | no |
| muta entradas | no |
| depende de infraestructura | no |

#### Diferencias por función

##### `funcion_a`

| aspecto | contrato |
|---|---|
| regla temporal | ... |
| filas ausentes | ... |
| caso parcial | ... |

##### `funcion_b`

| aspecto | contrato |
|---|---|
| regla temporal | ... |
| filas ausentes | ... |
| caso parcial | ... |

#### Ejemplo mínimo

```python
...
```

#### PENDIENTE

- PENDIENTE: definir ...
````

---

## Plantilla: api/ módulo

Esta plantilla aplica a `docs/rediseño/api.md`, sección `## Módulo por módulo`. No aplica a contratos de dominio, puertos ni casos de uso.

Las funciones de `api/` se dividen en dos categorías:

- **Manuales** — el usuario controla cada paso; aceptan `str | Periodo*` en parámetros de periodo; devuelven objetos de dominio, escalares o series según la función. Aplica en todos los módulos excepto `flujos.py`.
- **Flujo** — el usuario pasa insumos crudos; la función orquesta todo internamente; no hay acceso a resultados intermedios. Solo en `flujos.py`.

### Cabecera de módulo

```
### nombre_modulo.py — [RESUELTO | PROVISIONAL | PENDIENTE] (firmas [completas | provisionales])
```

### Función manual individual

Usar para funciones con contrato propio completo: `calcular_indice`, `empalmar`, `rebasar`, `cargar_canasta`, etc.

`````
#### nombre_funcion — [RESUELTO | PROVISIONAL | PENDIENTE]

##### Firma

```python
def nombre_funcion(
    param: Tipo,
    periodo: str | PeriodoMensual | PeriodoQuincenal = ...,
) -> ResultadoX:
```

##### Parámetros

| parámetro | tipo api | contrato |
|---|---|---|
| `param` | `ResultadoIndice` | ... |
| `periodo` | `str \| PeriodoMensual \| PeriodoQuincenal` | ver §Manejo de periodos |
| `param_pendiente` | PENDIENTE | descripción del tipo esperado y por qué está sin definir |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoX` | descripción de qué representa |

Tipos posibles según función:
- objeto dominio único: `ResultadoIndice`, `ResultadoVariacion`, `ResultadoIncidencia`, `ValidacionX`
- escalar: `float`
- par: `tuple[PeriodoX, float]` — para funciones tipo `inflacion_maxima`, `inflacion_minima`
- serie: `pd.Series` — para funciones tipo `incidencia_en`, `incidencia_acumulada`; índice = `generico`
- múltiple: `tuple[ValidacionIndice, ValidacionVariacion, ValidacionIncidencia]` — para funciones de validación

##### Errores

| condición | error |
|---|---|
| ... | `ErrorX` |

##### Notas

- bullet por nota de UX o comportamiento no obvio

##### Ejemplo

```python
rep.nombre_funcion(...)
```
`````

### Grupo de funciones manuales

Usar cuando varias funciones del mismo módulo comparten parámetros y estructura de retorno: `variacion_*`, `incidencia_*`, `inflacion_*`.

`````
#### Grupo: nombre_grupo — [RESUELTO | PROVISIONAL | PENDIENTE]

##### Funciones (series)

Omitir si el grupo no tiene funciones que devuelvan objetos de dominio.

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `funcion_a` | `funcion_a(resultado, frecuencia)` | `ResultadoVariacion` | ... |
| `funcion_b` | `funcion_b(resultado, desde, hasta)` | `ResultadoVariacion` | ... |

##### Funciones (escalares)

Omitir si el grupo no tiene funciones que devuelvan escalares, pares o series.

| función | firma resumida | retorno | notas |
|---|---|---|---|
| `funcion_c` | `funcion_c(resultado, desde, hasta)` | `float` | ... |
| `funcion_d` | `funcion_d(resultado)` | `tuple[PeriodoX, float]` | ... |
| `funcion_e` | `funcion_e(resultado, periodo)` | `pd.Series` | índice = `generico` |

##### Parámetros comunes

| parámetro | tipo api | contrato |
|---|---|---|
| `resultado` | `ResultadoIndice` | ... |
| `periodo` | `str \| PeriodoMensual \| PeriodoQuincenal` | ver §Manejo de periodos |
| `param_pendiente` | PENDIENTE | descripción del tipo esperado y por qué está sin definir |

##### Diferencias por función

| función | parámetro específico | tipo | contrato |
|---|---|---|---|
| `funcion_a` | `frecuencia` | `Literal["quincenal", "mensual", "anual"]` | ... |
| `funcion_b` | `desde`, `hasta` | `str \| Periodo*` | periodos inclusivos |

##### Errores comunes

| condición | error |
|---|---|
| ... | `ErrorX` |

##### Ejemplos

```python
rep.funcion_a(resultado, frecuencia="mensual")
rep.funcion_b(resultado, desde="Ene 2015", hasta="Dic 2024")
```
`````

### Función de flujo

Solo aplica en `flujos.py`. Recibe insumos crudos y orquesta múltiples pasos de dominio internamente.

`````
#### nombre_flujo — [RESUELTO | PROVISIONAL | PENDIENTE]

##### Firma

```python
def nombre_flujo(
    canastas: list[CanastaCanonica],
    series: list[SerieNormalizada],
    ...
) -> ResultadoX:
```

##### Parámetros

| parámetro | tipo | contrato |
|---|---|---|
| `canastas` | `list[CanastaCanonica]` | orden cronológico; una por versión |
| `series` | `list[SerieNormalizada]` | mismo orden y longitud que `canastas` |

##### Retorno

| tipo | contrato |
|---|---|
| `ResultadoX` | descripción de qué representa |

##### Orquestación interna

Pasos que ejecuta la función en orden:

1. ...
2. ...

El usuario no tiene acceso a resultados intermedios. Para control granular usar funciones manuales.

##### Requiere

- `rep.set_token(...)` o env var `INEGI_TOKEN` — solo si la función hace llamadas a INEGI

##### Errores

| condición | error |
|---|---|
| token no configurado cuando se requiere | `ErrorConfiguracion` |
| longitudes de `canastas` y `series` distintas | `InvarianteViolado` |

##### Ejemplo

```python
rep.nombre_flujo(canastas, series)
```
`````

### Funciones diferidas

Sección al final del módulo. Identificadas pero no implementadas en v2.

```
#### Funciones diferidas

- `nombre` — qué haría; por qué se difiere
```
