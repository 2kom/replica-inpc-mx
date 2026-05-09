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
