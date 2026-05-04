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
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

Un elemento para canasta simple; `empalmar` concatena listas. `resumen` se recalcula desde df merged + manifiestos concatenados.

**`ResultadoVariacion.manifiesto` / `ResultadoIncidencia.manifiesto`: `ManifestDerivado`** — no combinable (terminales):

```python
@dataclass
class ManifestDerivado:
    id_corrida: str   # hereda del ResultadoIndice origen
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

### Resultado (base) — NUEVO

Clase base abstracta compartida por `ResultadoIndice`, `ResultadoVariacion` y `ResultadoIncidencia`.

**Interfaz:**

- `.df` — DataFrame interno; escape hatch para análisis externos
- `.pipe(fn, *args, **kwargs)` — encadenamiento estilo pandas
- `_repr_html_` — display en Jupyter
- `.como_tabla(ancho: bool = False)` — vista tabular
- `.resumen` — abstracto; cada subclase implementa con su propio esquema
- `.reporte` — abstracto; cada subclase implementa con su propio esquema
- `.diagnostico` — abstracto; cada subclase implementa con su propio esquema

---

### ResultadoIndice — MODIFICADO

Renombrado desde `ResultadoCalculo`. Hereda de `Resultado`.

**Cambios respecto a v1:**

- Nombre: `ResultadoCalculo` → `ResultadoIndice`
- Agrega `.periodo_base: PeriodoQuincenal | None` — `None` = escala nativa; seteado por `rebasar()`
- Agrega `.manifiesto: list[ManifestUnidad]` — un elemento por canasta; `empalmar` concatena listas
- Implementa `.resumen`, `.reporte`, `.diagnostico`

**`ManifestUnidad` (dataclass embebida):**

```python
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

**`.resumen`** — equivalente a `ResumenValidacion` v1 sin columnas INEGI: `estado_corrida`, `periodo_inicio`, `periodo_fin`, `version`, `total_nulls`.

**`.reporte`** — equivalente a `ReporteDetalladoValidacion` v1 sin columnas INEGI: cobertura de genéricos y ponderadores por periodo.

**`.diagnostico`** — equivalente a `DiagnosticoFaltantes` v1: genéricos ausentes en series CSV.

---

### ResultadoVariacion — MODIFICADO

Hereda de `Resultado`. Mueve de `dominio/modelos/variacion.py` a `dominio/calculo/variacion.py`.

**Cambios respecto a v1:**

- Hereda de `Resultado` (agrega `.pipe()`, `.resumen`, `.reporte`, `.diagnostico`)
- Agrega `.manifiesto: ManifestDerivado`
- Agrega `estado_calculo` en df — alineado con `ResultadoIncidencia` (confirmar en implementación)
- `.resumen`, `.reporte`, `.diagnostico` con esquemas nuevos — pendiente de definir

**`ManifestDerivado` (dataclass embebida, compartida con `ResultadoIncidencia`):**

```python
@dataclass
class ManifestDerivado:
    id_corrida: str
    tipo: str
    descripcion: str  # "mensual", "desde Ene 2015 hasta Dic 2024", etc.
    fecha: datetime
```

**Propiedades sin cambio:** `.tipo`, `.descripcion`, `.clase_variacion`, `.periodos_semiok`, `.indices_parciales`.

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

- `forzar=False` (default): lanza `InvarianteViolado` si `periodo_base` no es homogéneo entre inputs
- `forzar=True`: permite mezcla de escalas distintas + emite `UserWarning` describiendo qué `periodo_base` tiene cada tramo
- Concatena `.manifiesto` de cada tramo
- Aplica `RENOMBRES_INDICES` (`correspondencia_canastas.py`) para normalizar nombres de categorías entre versiones
- Propaga `.resumen`, `.reporte`, `.diagnostico` (merge automático)

> **Nota:** para normalización manual de categorías antes de empalmar, ver `normalizar_categorias` en `api/indices.py` — pendiente de agregar.

#### rebasar

```python
def rebasar(
    resultado: ResultadoIndice,
    periodo_base: PeriodoQuincenal,
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

